"""Run a small reproducible audio-only pilot; no test-set tuning or training."""
import argparse
from datetime import datetime, timezone
import hashlib
from html import escape
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ai-service"))
from app.datasets import iter_examples
from app.phoneme_recognition import LocalPhonemeRecognizer, TARGET_PHONES


def write_review_page(reviews, output, *, filename="review.html"):
    """Local read-only playback index; predictions deliberately stay hidden."""
    sections = []
    for row in reviews:
        relative_audio = os.path.relpath(row["audio_path"], output).replace("\\", "/")
        transcript_status = row.get("transcript_review_status", "not reviewed")
        listening_status = row.get("intelligibility_review_status", "not reviewed")
        feedback = (f'<p><strong>Recorded human feedback:</strong> transcript: '
                    f'{escape(transcript_status)}; listening: {escape(listening_status)}. '
                    f'Individual phone labels and boundaries remain unverified.</p>'
                    if row.get("transcript_review_status") else "")
        sections.append(
            f'<section><h2>{escape(row["id"])}</h2>'
            f'<p>Supplied speaker ID: {escape(row["speaker_id"])}</p>'
            f'<audio controls preload="none" src="{escape(relative_audio, quote=True)}"></audio>'
            f'<p>Reference transcript (not a verified actual-phone label): '
            f'{escape(row["reference_text"])}</p>{feedback}</section>')
    page = '''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>WordSpeak: independent listening review</title>
<style>body{font:17px/1.6 system-ui,sans-serif;max-width:850px;margin:36px auto;padding:0 20px;color:#202b39}
section{border-top:1px solid #ccc;padding:16px 0}h2{font-size:19px}audio{width:100%}
code{background:#eee;padding:2px 5px}li{margin:8px 0}</style>
<h1>WordSpeak: independent listening review</h1>
<p>RECORDING_COUNT-recording smoke test. This page hides model predictions. No accuracy has been measured.</p>
<ol><li>A reviewer familiar with phonetic transcription should listen independently.
Record the sounds actually heard, rather than copying the expected pronunciation.</li>
<li>Enter the heard phones, checked boundaries, reviewer name and notes in
<code>human_review.jsonl</code> beside this page. Leave uncertain annotations empty;
do not guess. This playback page does not save annotations.</li>
<li>Flag noise, overlap, uncertain speaker identity or unusable boundaries.
Reference transcripts may contain mistakes, especially in the collected audio.</li></ol>
<p>Mouth/tongue positions have not been measured. This is a review aid, not a training label generator.</p>
'''
    (output / filename).write_text(
        page.replace("RECORDING_COUNT", str(len(reviews))) + "\n".join(sections) + "</html>\n", encoding="utf-8")


def select_examples(manifest, limit):
    if manifest.stem == "test":
        raise ValueError("Pilot must not use the held-out test manifest")
    examples = sorted(iter_examples(manifest), key=lambda row: hashlib.sha256(
        ("WordSpeak-phoneme-pilot-v1:" + row["id"]).encode()).hexdigest())
    # Avoid long utterances in this small CPU smoke test, without using scores or
    # recognizer confidence to select easy pronunciation.
    eligible = [row for row in examples if 0.1 <= row["duration_seconds"] <= 12]
    seen, chosen = set(), []
    for row in eligible:
        if row["speaker_id"] not in seen:
            chosen.append(row)
            seen.add(row["speaker_id"])
        if len(chosen) == limit:
            break
    if len(chosen) < limit:
        raise ValueError(f"Only {len(chosen)} distinct supplied speaker IDs eligible")
    return chosen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, action="append", required=True)
    parser.add_argument("--per-manifest", type=int, default=2)
    parser.add_argument("--model", type=Path,
                        default=ROOT / "data/models/phoneme-recognition")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "data/results/phoneme_pilot")
    parser.add_argument("--threads", type=int, default=4)
    args = parser.parse_args()
    if args.per_manifest < 1 or args.threads < 1:
        parser.error("Positive example and thread counts required")
    selected = []
    manifest_hashes = {}
    for manifest in args.manifest:
        manifest = manifest.resolve()
        manifest_hashes[str(manifest)] = hashlib.sha256(manifest.read_bytes()).hexdigest()
        selected.extend(select_examples(manifest, args.per_manifest))
    if args.output.exists() and any(args.output.iterdir()):
        parser.error("Output folder is not empty; choose a new --output to preserve reviews")
    args.output.mkdir(parents=True, exist_ok=True)
    recognizer = LocalPhonemeRecognizer(args.model, threads=args.threads)
    reviews = []
    predictions = []
    for example in selected:
        start = time.monotonic()
        prediction = recognizer.predict(example["audio_path"])
        record = {"id": example["id"], "speaker_id": example["speaker_id"],
                  "dataset": example["dataset"], "audio_path": example["audio_path"],
                  "reference_text_for_review_only": example["text"],
                  "runtime_seconds": round(time.monotonic() - start, 3), **prediction}
        predictions.append(record)
        reviews.append({"id": example["id"], "speaker_id": example["speaker_id"],
                        "audio_path": example["audio_path"],
                        "reference_text": example["text"],
                        "verified_heard_phones": None,
                        "verified_phone_boundaries": None,
                        "reviewer": None, "notes": None})
        print(json.dumps({"id": example["id"], "phones": prediction["predicted_phones"],
                          "seconds": record["runtime_seconds"]}, ensure_ascii=True), flush=True)
        # Checkpoint after every completed recording.
        (args.output / "predictions.jsonl").write_text("".join(
            json.dumps(row, ensure_ascii=False) + "\n" for row in predictions), encoding="utf-8")
    (args.output / "human_review.jsonl").write_text("".join(
        json.dumps(row, ensure_ascii=False) + "\n" for row in reviews), encoding="utf-8")
    write_review_page(reviews, args.output)
    (args.output / "summary.json").write_text(json.dumps({
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "audio_inference_smoke_test_not_accuracy_benchmark",
        "model_id": recognizer.provenance["model_id"],
        "revision": recognizer.provenance["revision"],
        "manifest_sha256": manifest_hashes, "recordings": len(predictions),
        "target_inventory": TARGET_PHONES, "human_verified_recordings": 0,
        "classification_accuracy": None, "actual_mouth_position_accuracy": None,
        "selection": "deterministic hash; distinct supplied speaker IDs; 0.1–12 seconds",
        "limitations": ["No training or tuning performed; full vocabulary decoding.",
                        "No canonical transcript supplied to the model.",
                        "Native IDs are source-local, not confirmed unique people.",
                        "Review template hides predictions to reduce anchoring.",
                        "Phone boundaries and output probabilities are not calibrated."]
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {len(predictions)} audio predictions to {args.output}")


if __name__ == "__main__":
    main()
