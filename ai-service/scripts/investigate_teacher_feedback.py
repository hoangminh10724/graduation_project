"""Run pinned local audio inference and context checks for all teacher passages."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
from html import escape
from importlib.metadata import version
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ai-service"))
from app.phoneme_recognition import LocalPhonemeRecognizer
from app.feedback_probes import phones_in_window, summarize_probe, token_edit_distance

SOURCES = ["data/annotations/user_feedback_20261115/candidate_annotations.jsonl",
           "data/annotations/teacher_feedback_batch_02/prepared/candidate_annotations.jsonl"]
# Defined before inference. These check concrete reports, not every general
# correction or the unmentioned phones in a word. Never retune on these cases.
PROBES = {
    ("P4_12", "comparison"): ("last_s_or_z", "z", "s"),
    ("P4_12", "show"): ("first_s_or_sh", "s", "ʃ"),
    ("P5_15", "mistakes"): ("s_immediately_before_first_t", "s_absent_before_t", "s_present_before_t"),
    ("P5_15", "consistent"): ("s_immediately_before_first_t", "s_absent_before_t", "s_present_before_t"),
    ("P6_08", "demonstrate"): ("s_immediately_before_first_t", "s_absent_before_t", "s_present_before_t"),
    ("P5_15", "improvements"): ("last_two_s_t_order", "st", "ts")
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def collect_annotations():
    annotations, candidates, parents = [], [], {}
    for source in SOURCES:
        for row in read_jsonl(ROOT / source):
            parent_id = row["parent_clip_id"]
            parent_path = row["parent_audio_path"]
            if parent_id in parents and parents[parent_id] != parent_path:
                raise ValueError(f"Conflicting parent path: {parent_id}")
            parents[parent_id] = parent_path
            items = row.get("candidates")
            if items is None:
                items = [{"audio_path": row["candidate_audio_path"],
                          "candidate_parent_span_seconds": row["candidate_parent_span_seconds"],
                          "parent_ASR_word_span_seconds": row["parent_asr_word_span_seconds"],
                          "occurrence": 1}]
            annotation = {"id": row["id"], "parent_id": parent_id,
                          "word": row["commented_word"], "comment": row["raw_comment"],
                          "flags": row.get("review_flags", []),
                          "mapping_note": row.get("mapping_note"), "source": source,
                          "candidates": []}
            for item in items:
                candidate_id = row["id"] + f":occurrence:{item['occurrence']}"
                candidate = {"id": candidate_id, "annotation_id": row["id"],
                             "parent_id": parent_id, "word": row["commented_word"],
                             "audio_path": item["audio_path"],
                             "parent_span": item["candidate_parent_span_seconds"],
                             "ASR_word_span": item["parent_ASR_word_span_seconds"]}
                candidates.append(candidate)
                annotation["candidates"].append(candidate_id)
            annotations.append(annotation)
    if len({row["id"] for row in candidates}) != len(candidates):
        raise ValueError("Duplicate candidate ID")
    return annotations, candidates, parents


def infer_group(recognizer, entries, path, *, resume):
    records = read_jsonl(path) if resume and path.is_file() else []
    cache = {row["id"]: row for row in records}
    expected_ids = {row["id"] for row in entries}
    if not set(cache) <= expected_ids:
        raise ValueError("Cached IDs do not match this run")
    with path.open("a" if resume else "w", encoding="utf-8") as stream:
        for index, entry in enumerate(entries, 1):
            audio = ROOT / entry["audio_path"]
            digest = sha(audio)
            if entry["id"] in cache:
                if cache[entry["id"]]["audio_sha256"] != digest:
                    raise ValueError(f"Audio changed: {audio}")
                continue
            start = time.monotonic()
            prediction = recognizer.predict(audio)
            row = {**entry, "audio_sha256": digest,
                   "runtime_seconds": round(time.monotonic() - start, 4), **prediction}
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
            stream.flush()
            cache[row["id"]] = row
            print(f"{path.stem} {index}/{len(entries)}: {entry['id']}", flush=True)
    return cache


def build_report(output, annotations, comparisons, parents, summary):
    comparisons_by_id = {row["id"]: row for row in comparisons}
    sections = []
    for annotation in annotations:
        full_url = os.path.relpath(ROOT / parents[annotation["parent_id"]], output).replace("\\", "/")
        children = []
        for candidate_id in annotation["candidates"]:
            result = comparisons_by_id[candidate_id]
            crop_url = os.path.relpath(ROOT / result["audio_path"], output).replace("\\", "/")
            probe = result["teacher_report_probe"]
            status = probe["status"] if probe else "No exact-error probe: feedback too broad or out of selected probe scope"
            children.append(f'''<article><p><strong>{escape(candidate_id)}</strong></p>
<audio controls preload="none" src="{escape(crop_url, quote=True)}"></audio>
<p>Parent word-window output: <code>{escape(' '.join(result['variants']['parent_pad_0.00']))}</code></p>
<p>Crop word-window output: <code>{escape(' '.join(result['variants']['crop_pad_0.00']))}</code></p>
<p>Full crop output (includes neighboring context): <code>{escape(' '.join(result['crop_predicted_phones']))}</code></p>
<p>Probe: {escape(status)}. This is model-pattern consistency, not accuracy.</p>
<details><summary>Context / timing variants and probe details</summary><pre>{escape(json.dumps({'variants':result['variants'],'probe':probe},ensure_ascii=False,indent=2))}</pre></details></article>''')
        sections.append(f'''<section><h2>{escape(annotation['parent_id'])}: {escape(annotation['word'])}</h2>
<p>{escape(annotation['comment'])}</p><p class="flag">{escape(', '.join(annotation['flags']) or 'Candidate timestamps remain approximate.')}</p>
<details><summary>Full recording</summary><audio controls preload="none" src="{escape(full_url, quote=True)}"></audio></details>
{''.join(children) if children else '<p>Word location unresolved; parent audio is available above. No error score assigned.</p>'}</section>''')
    header = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>WordSpeak: model investigation against teacher feedback</title>
<style>body{{font:17px/1.6 system-ui,sans-serif;max-width:1050px;margin:32px auto;padding:0 20px}}audio{{width:100%}}section{{border-top:2px solid #64748b;padding:16px 0}}article{{border-top:1px solid #ddd;margin:20px 0}}pre{{white-space:pre-wrap}}code{{font:18px/1.7 system-ui;background:#eef2f6}}.flag{{background:#fff4d6;padding:8px}}</style>
<h1>Audio model vs. teacher comments: development investigation</h1>
<p>{summary['parent_recordings_inferred']} full recordings and {summary['candidate_passages_inferred']} candidate passages processed locally.
Reference words and teacher corrections were never passed to the acoustic recognizer.</p>
<p><strong>These outputs are exploratory phoneme predictions, not measured learner mouth positions or pronunciation scores.</strong>
Teacher reports are partial; ASR timings are approximate. No classification accuracy is claimed.
Full-recording and crop inference are compared under 0, 80 and 200 ms word-window padding.
Read the original blind review pages for independent annotation; this page intentionally reveals model predictions.</p>
<p>Six predeclared positional probes: {escape(json.dumps(summary['positional_probe_status_counts']))}.
Stable disagreement is a case for review, not proof the teacher or model is wrong.</p>'''
    (output / "review.html").write_text(header + "\n".join(sections) + "</html>\n", encoding="utf-8")
    lines = ["# Investigation of model predictions against teacher feedback", "",
        f"Full recordings processed: {summary['parent_recordings_inferred']}; candidate passages: {summary['candidate_passages_inferred']}.",
        "", "The acoustic model received only audio. Teacher comments and canonical text were not recognition inputs.",
        "", "## Context checks", "",
        f"Exact base-window parent/crop sequence matches: {summary['base_window_exact_context_matches']} / {len(comparisons)}.",
        "This measures sensitivity to context and approximate word timing, not recognition accuracy.",
        "", "## Predeclared positional probes", "",
        "| Recording | Word | Outcome |", "|---|---|---|"]
    for row in comparisons:
        probe = row["teacher_report_probe"]
        if probe:
            lines.append(f"| {row['parent_id']} | {row['word']} | {probe['status']} |")
    lines += ["", "### Variant observations", ""]
    for row in comparisons:
        if row["teacher_report_probe"]:
            lines += [f"{row['parent_id']} / {row['word']}: " + json.dumps(
                row["teacher_report_probe"]["observations"], ensure_ascii=False), ""]
    lines += ["## Interpretation", "",
        "No overall, ten-class, per-speaker or articulatory accuracy is established. There are no independent full actual-heard phonetic transcripts here.",
        "The probes test reported /s/–/z/ and /s/–/ʃ/ patterns, internal /s/ before /t/, and -ts/-st order. They do not convert vague vowel-length or stress coaching into exact error labels.",
        "All six contexts (full/cropped audio at three timing paddings) must yield the same resolvable feature to call a probe context-stable. This conservative rule is not calibrated confidence.",
        "Model/tokenization/accent choices and ASR boundaries can cause disagreement. Repeated occurrences remain separate candidates without inheriting the teacher's error label.",
        "No training, threshold fitting, model selection or untouched-corpus-test evaluation was performed.",
        "", "## Files", "", "- parent_predictions.jsonl and candidate_predictions.jsonl: raw predictions with audio hashes.",
        "- comparisons.jsonl: per-candidate context and probe evidence.",
        "- summary.json and run_config.json: counts, provenance and limitations.",
        "- review.html: playback and model predictions; do not use as a blind annotation interface."]
    (output / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "data/results/teacher_feedback_investigation")
    parser.add_argument("--model", type=Path, default=ROOT / "data/models/phoneme-recognition")
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    annotations, candidates, parents = collect_annotations()
    output = args.output.resolve()
    if output.exists() and any(output.iterdir()) and not args.resume:
        parser.error("Output exists; use --resume or a new --output")
    output.mkdir(parents=True, exist_ok=True)
    provenance = json.loads((args.model / "provenance.json").read_text(encoding="utf-8"))
    config = {"model_id": provenance["model_id"], "revision": provenance["revision"],
        "sources": {source: sha(ROOT / source) for source in SOURCES},
        "implementation_sha256": {str(p.relative_to(ROOT).as_posix()): sha(p) for p in
            [Path(__file__), ROOT / "ai-service/app/feedback_probes.py", ROOT / "ai-service/app/phoneme_recognition.py"]},
        "runtime_versions": {name: version(name) for name in ["torch", "transformers", "numpy", "soundfile"]},
        "threads": args.threads,
        "probes": {f"{key[0]}:{key[1]}": list(value) for key, value in PROBES.items()}}
    config_path = output / "run_config.json"
    if args.resume and config_path.exists():
        if json.loads(config_path.read_text(encoding="utf-8")) != config:
            raise ValueError("Run configuration changed; start a new output directory")
    else:
        write_json(config_path, config)
    recognizer = LocalPhonemeRecognizer(args.model, threads=args.threads)
    parent_predictions = infer_group(recognizer,
        [{"id": key, "audio_path": value} for key, value in sorted(parents.items())],
        output / "parent_predictions.jsonl", resume=args.resume)
    crop_predictions = infer_group(recognizer, candidates,
        output / "candidate_predictions.jsonl", resume=args.resume)
    comparisons = []
    for candidate in candidates:
        crop = crop_predictions[candidate["id"]]
        parent = parent_predictions[candidate["parent_id"]]
        variants = {}
        for padding in [0.0, 0.08, 0.2]:
            variants[f"parent_pad_{padding:.2f}"] = phones_in_window(parent, candidate["ASR_word_span"], padding=padding)
            variants[f"crop_pad_{padding:.2f}"] = phones_in_window(crop, candidate["ASR_word_span"], offset=candidate["parent_span"][0], padding=padding)
        parent_base, crop_base = variants["parent_pad_0.00"], variants["crop_pad_0.00"]
        probe_spec = PROBES.get((candidate["parent_id"], candidate["word"]))
        probe = summarize_probe(variants, *probe_spec) if probe_spec else None
        comparisons.append({**candidate, "variants": variants,
            "crop_predicted_phones": crop["predicted_phones"],
            "base_window_token_edit_distance": token_edit_distance(parent_base, crop_base),
            "base_window_sequence_exact_match": parent_base == crop_base,
            "teacher_report_probe": probe, "classification_correct": None,
            "actual_mouth_position": None})
    (output / "comparisons.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in comparisons), encoding="utf-8")
    status_counts = Counter(r["teacher_report_probe"]["status"] for r in comparisons if r["teacher_report_probe"])
    summary = {"created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "complete_development_investigation_not_accuracy_benchmark",
        "annotation_word_entries": len(annotations), "parent_recordings_inferred": len(parent_predictions),
        "candidate_passages_inferred": len(crop_predictions),
        "unresolved_word_entries": sum(not r["candidates"] for r in annotations),
        "base_window_exact_context_matches": sum(r["base_window_sequence_exact_match"] for r in comparisons),
        "predeclared_probe_candidates": sum(r["teacher_report_probe"] is not None for r in comparisons),
        "positional_probe_status_counts": dict(status_counts),
        "inference_runtime_seconds_excluding_model_load": round(sum(r["runtime_seconds"] for r in list(parent_predictions.values()) + list(crop_predictions.values())), 2),
        "audio_duration_seconds_inferred_with_repeated_content": round(sum(r["duration_seconds"] for r in list(parent_predictions.values()) + list(crop_predictions.values())), 2),
        "classification_accuracy": None, "articulatory_position_accuracy": None,
        "training_performed": False, "reference_text_used_by_acoustic_model": False,
        "corpus_held_out_test_used": False,
        "limitations": ["ASR and CTC timings are approximate.", "Teacher comments are sparse partial references.",
                        "Context stability is not calibrated confidence or correctness.", "No measured articulatory positions are available."]}
    write_json(output / "summary.json", summary)
    build_report(output, annotations, comparisons, parents, summary)
    print(json.dumps(summary, ensure_ascii=True, indent=2), flush=True)


if __name__ == "__main__":
    main()
