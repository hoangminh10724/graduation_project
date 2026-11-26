"""Prepare auditable, partial teacher comments and candidate word passages.

This never turns canonical words, model predictions, generic praise or mouth
instructions into actual-heard phone labels or measured articulatory positions.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
from html import escape
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ai-service"))
from app.phoneme_recognition import TARGET_PHONES


def read_blocks(text):
    headers = list(re.finditer(r"^P\d+_\d+\s*$", text, re.MULTILINE))
    blocks = {}
    for index, header in enumerate(headers):
        clip_id = header.group().strip()
        if clip_id in blocks:
            raise ValueError(f"Duplicate source recording ID: {clip_id}")
        end = headers[index + 1].start() if index + 1 < len(headers) else len(text)
        blocks[clip_id] = text[header.end():end].strip()
    return blocks


def normalized_word(text):
    return re.sub(r"[^a-z]", "", text.lower())


def find_candidates(parent, target, aliases):
    primary = [w for s in parent["primary_asr"]["segments"] for w in s["words"]]
    secondary = [w for s in parent.get("checks", {}).get("cross_asr", {}).get("segments", [])
                 for w in s.get("words", [])]
    # Exact forms take priority over hypotheses based on ASR substitutions.
    # Every repeated occurrence remains a candidate; none inherits the error label.
    for forms, kind in [({target}, "exact_word"), (set(aliases), "alias_hypothesis")]:
        if not forms:
            continue
        for words, model in [(primary, "primary"), (secondary, "cross_check")]:
            hits = [w for w in words if normalized_word(w["word"]) in forms]
            if hits:
                return hits, f"{model}_{kind}"
    return [], "unresolved_no_exact_or_declared_alias_match"


def main():
    import soundfile as sf

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path,
        default=ROOT / "data/annotations/teacher_feedback_batch_02")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    source_dir = args.source_dir.resolve()
    output = (args.output or source_dir / "prepared").resolve()
    if output.exists() and any(output.iterdir()):
        parser.error("Output is not empty; choose a new --output to preserve existing review")
    raw_path = source_dir / "source_feedback.txt"
    specs_path = source_dir / "comment_specs.json"
    blocks = read_blocks(raw_path.read_text(encoding="utf-8"))
    source = json.loads(specs_path.read_text(encoding="utf-8"))
    if set(blocks) != set(source["records"]):
        raise ValueError("Raw feedback IDs and mapping specification IDs differ")
    parent_dir = ROOT / "data/processed/vietnamese"
    parents = {r["clip_id"]: r for r in map(json.loads,
        (parent_dir / "manifest.jsonl").read_text(encoding="utf-8").splitlines())}
    if not set(blocks) <= set(parents):
        raise ValueError(f"Missing parent recordings: {set(blocks) - set(parents)}")
    output.mkdir(parents=True, exist_ok=True)
    (output / "candidate_audio").mkdir(exist_ok=True)
    rows, sections = [], []
    parent_manifest = []
    used_comments = set()
    for clip_id, specs in source["records"].items():
        parent = parents[clip_id]
        parent_audio = parent_dir / parent["audio"]
        audio, rate = sf.read(parent_audio, dtype="float32", always_2d=True)
        if rate != 16000 or audio.shape[1] != 1:
            raise ValueError(f"Unexpected prepared audio format: {parent_audio}")
        paragraphs = [s.strip() for s in re.split(r"\n\s*\n", blocks[clip_id]) if s.strip()]
        relative_parent = parent_audio.relative_to(ROOT).as_posix()
        full_url = os.path.relpath(parent_audio, output).replace("\\", "/")
        items_html = []
        for number, spec in enumerate(specs, 1):
            comment_matches = [(i, p) for i, p in enumerate(paragraphs)
                               if p.casefold().startswith(spec["anchor"].casefold())]
            if len(comment_matches) != 1:
                raise ValueError(f"Ambiguous source paragraph: {clip_id}/{spec['anchor']}")
            paragraph_index, comment = comment_matches[0]
            used_comments.add((clip_id, paragraph_index))
            hits, method = find_candidates(parent, spec["word"], spec.get("aliases", []))
            flags = list(spec.get("flags", []))
            if len(hits) > 1:
                flags.append("multiple_occurrences_not_individually_labeled")
            if "alias" in method:
                flags.append("ASR_alias_does_not_verify_spoken_word_or_error")
            if method.startswith("cross_check"):
                flags.append("cross_check_ASR_timestamp_not_independently_verified")
            if not hits:
                flags.append("unresolved_word_location")
            candidates = []
            candidate_html = []
            for occurrence, hit in enumerate(hits, 1):
                start = max(0.0, float(hit["start"]) - 0.35)
                end = min(len(audio) / rate, float(hit["end"]) + 0.35)
                if end <= start:
                    raise ValueError(f"Invalid candidate span for {clip_id}/{spec['word']}")
                filename = f"{clip_id}_{number:02d}_{spec['word']}_{occurrence:02d}.wav"
                crop_path = output / "candidate_audio" / filename
                crop = audio[round(start * rate):round(end * rate)]
                if len(crop) == 0:
                    raise ValueError(f"Empty crop: {filename}")
                sf.write(crop_path, crop, rate, subtype="PCM_16")
                candidate = {
                    "occurrence": occurrence, "ASR_word": hit["word"].strip(),
                    "audio_path": crop_path.relative_to(ROOT).as_posix(),
                    "parent_ASR_word_span_seconds": [hit["start"], hit["end"]],
                    "candidate_parent_span_seconds": [round(start, 4), round(end, 4)],
                    "ASR_word_probability_uncalibrated": hit.get("probability"),
                    "timing_status": "automatic_word_span_with_context_not_phone_boundaries",
                    "label_applies_to_this_occurrence": None,
                    "human_verified_word_match": False
                }
                candidates.append(candidate)
                candidate_html.append(
                    f'<p>Candidate {occurrence}: ASR “{escape(hit["word"].strip())}”, '
                    f'{start:.2f}–{end:.2f}s in prepared parent. '
                    f'Error applicability is unconfirmed.</p>'
                    f'<audio controls preload="none" src="candidate_audio/{escape(filename, quote=True)}"></audio>')
            row = {
                "id": f"teacher_feedback_batch02:{clip_id}:{number:02d}:{spec['word']}",
                "parent_clip_id": clip_id, "speaker_id": f"vietnamese_comparison:{parent['participant_id']}",
                "parent_audio_path": relative_parent,
                "original_source_sha256": parent["source_sha256"],
                "source_feedback_path": raw_path.relative_to(ROOT).as_posix(),
                "source_paragraph_index_zero_based": paragraph_index,
                "commented_word": spec["word"], "raw_comment": comment,
                "feedback_author_role": source["author_role"], "author_name": source["author_name"],
                "label_status": "teacher_provided_partial_feedback",
                "reported_issue": spec["issue"], "reported_realization": spec.get("actual"),
                "candidate_focus_phones": spec["focus"],
                "focus_phone_status": "analyst_interpretation_not_verified_heard_phone_labels",
                "mapping_note": spec.get("note"), "mapping_reference": spec.get("reference"),
                "word_matching_method": method, "review_flags": flags,
                "candidates": candidates, "verified_heard_phones": None,
                "verified_phone_boundaries": None, "actual_mouth_position": None,
                "recommended_use": "development_diagnostics_and_partial_annotation_review"
            }
            rows.append(row)
            flag_html = escape(", ".join(flags) or "automatic candidate match; listening confirmation pending")
            items_html.append(
                f'<article><h3>{escape(spec["word"])}</h3><p>{escape(comment)}</p>'
                f'<p class="flag">{flag_html}</p>'
                f'<p>Comment focus (interpreted, unverified): {escape(" / ".join(spec["focus"]) or "word / stress / informal instruction")}</p>'
                + (f'<p>{escape(spec["note"])}</p>' if spec.get("note") else "")
                + ("".join(candidate_html) if candidates else '<p>No reliable word location found automatically; use the full parent recording above.</p>')
                + '</article>')
        parent_manifest.append({
            "parent_clip_id": clip_id, "speaker_id": f"vietnamese_comparison:{parent['participant_id']}",
            "parent_audio_path": relative_parent, "source_feedback_raw": blocks[clip_id],
            "teacher_feedback_is_exhaustive": False,
            "unmapped_general_or_rule_paragraphs": [p for i, p in enumerate(paragraphs)
                                                    if (clip_id, i) not in used_comments]
        })
        sections.append(
            f'<section><h2>{escape(clip_id)}</h2><p>Full prepared recording:</p>'
            f'<audio controls preload="none" src="{escape(full_url, quote=True)}"></audio>'
            f'<details><summary>Complete original feedback</summary><pre>{escape(blocks[clip_id])}</pre></details>'
            + "".join(items_html) + '</section>')
    phone_mentions = Counter(phone for row in rows for phone in set(row["candidate_focus_phones"]))
    coverage = []
    for phone, arpabet in TARGET_PHONES.items():
        matching = [r for r in rows if phone in r["candidate_focus_phones"]]
        coverage.append({"ipa": phone, "arpabet": arpabet,
            "new_batch_focus_word_entries": len(matching),
            "entry_ids": [r["id"] for r in matching],
            "isolated_phone_examples_verified": 0,
            "cluster_only": bool(matching) and all("cluster_level_not_isolated_phone_label" in r["review_flags"] for r in matching),
            "note": "Comment-focus count only; not a count of correct, erroneous, independent or verified phone samples."})
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "teacher_feedback_imported_with_candidate_word_matching",
        "source_sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest(),
        "specification_sha256": hashlib.sha256(specs_path.read_bytes()).hexdigest(),
        "parent_recordings": len(parent_manifest),
        "supplied_participant_ids": len({r["speaker_id"] for r in parent_manifest}),
        "original_word_specific_comments": len(used_comments),
        "word_focus_entries": len(rows),
        "entries_with_candidate_passages": sum(bool(r["candidates"]) for r in rows),
        "candidate_passages": sum(len(r["candidates"]) for r in rows),
        "entries_with_multiple_candidate_occurrences": sum(len(r["candidates"]) > 1 for r in rows),
        "unresolved_word_locations": [r["id"] for r in rows if not r["candidates"]],
        "dictionary_conflict_flags": [r["id"] for r in rows if "dictionary_conflict_dj_vs_ʒ" in r["review_flags"]],
        "candidate_phone_focus_mentions": dict(phone_mentions),
        "ten_target_coverage": coverage,
        "human_adjudicated_phone_sequences": 0, "verified_articulatory_labels": 0,
        "classification_accuracy": None,
        "limitations": ["Teacher comments are partial and not exhaustive correctness labels.",
            "Model-ASR word matches and timestamps are candidate links, not phonetic ground truth.",
            "Repeated word occurrences do not each inherit a reported error.",
            "Mouth instructions describe a teaching target, not measured learner geometry.",
            "Informal respelling, dictionary conflicts and accent-dependent wording remain flagged.",
            "These exploratory learner recordings are not added to training or the held-out corpus test set."]
    }
    for filename, items in [("candidate_annotations.jsonl", rows), ("recording_feedback.jsonl", parent_manifest)]:
        (output / filename).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in items), encoding="utf-8")
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    coverage_rows = "".join(
        f'<tr><td>/{escape(r["ipa"])}/</td><td>{r["new_batch_focus_word_entries"]}</td>'
        f'<td>{"cluster correction only" if r["cluster_only"] else "candidate focus" if r["new_batch_focus_word_entries"] else "no direct comment focus in this batch"}</td></tr>'
        for r in coverage)
    header = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>WordSpeak: teacher feedback batch 02</title><style>body{{font:17px/1.6 system-ui,sans-serif;max-width:950px;margin:32px auto;padding:0 20px;color:#1e293b}}audio{{width:100%}}section{{border-top:2px solid #94a3b8;margin-top:28px}}article{{border-top:1px solid #ddd;padding:8px 0 16px}}pre{{white-space:pre-wrap;font:inherit}}.flag{{background:#fff4d6;padding:8px}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ddd;padding:7px;text-align:left}}</style>
<h1>Teacher feedback: ten additional recordings</h1>
<p>{len(used_comments)} word-specific source comments, {len(rows)} target-word entries, {summary["candidate_passages"]} candidate passages.
The same comment can mention two words; a word can have several possible occurrences.</p>
<p>The user identifies the feedback provider as a teacher. Original wording is preserved.
No model phoneme predictions are displayed. Reported feedback and machine-assisted location matching are separate.</p>
<p><strong>No training-set additions, classification accuracy or actual mouth positions are established here.</strong>
Unmentioned sounds remain unlabeled. Candidates have context padding and are not exact phone crops.
This playback page does not save annotations.</p>
<h2>Proposed ten sounds: feedback-focus coverage</h2>
<p>Counts describe interpreted comment focus, not verified phone examples or balanced evaluation coverage.
Vowel respellings and /e/–/ɛ/ conventions need review. /t/ appears only in a cluster-order correction.</p>
<table><tr><th>Sound</th><th>Word entries</th><th>Meaning</th></tr>{coverage_rows}</table>'''
    (output / "review.html").write_text(header + "\n".join(sections) + "</html>\n", encoding="utf-8")
    # Index both teacher-feedback batches without replacing their source records.
    prior_path = ROOT / "data/annotations/user_feedback_20261115/candidate_annotations.jsonl"
    prior = [json.loads(s) for s in prior_path.read_text(encoding="utf-8").splitlines()]
    total_parents = {r["parent_clip_id"] for r in rows + prior}
    combined = {
        "teacher_feedback_recordings": len(total_parents),
        "supplied_participant_ids": len({r["speaker_id"] for r in rows + prior}),
        "word_focus_entries": len(rows) + len(prior),
        "batch_paths": [str(prior_path.relative_to(ROOT).as_posix()),
                        str((output / "candidate_annotations.jsonl").relative_to(ROOT).as_posix())],
        "classification_accuracy": None,
        "note": "Index of partial feedback; no claim that every sound in these recordings is labeled."
    }
    (ROOT / "data/annotations/teacher_feedback_index.json").write_text(json.dumps(combined, indent=2), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ["parent_recordings", "original_word_specific_comments", "word_focus_entries", "candidate_passages", "entries_with_candidate_passages", "unresolved_word_locations"]}, indent=2))
    print(f"Combined teacher-feedback recordings: {len(total_parents)}")
    print(f"Playback: {output / 'review.html'}")


if __name__ == "__main__":
    main()
