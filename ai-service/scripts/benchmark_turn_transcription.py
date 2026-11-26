"""Benchmark the turn endpoint on one deterministic validation clip per speaker."""
import hashlib
import json
from pathlib import Path
import re
from statistics import median
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ai-service"))
sys.path.append(str(ROOT / "data/speech-tools"))
from fastapi.testclient import TestClient
from app.main import app


def tokens(text):
    return re.findall(r"[a-z0-9]+(?:'[a-z0-9]+)?", text.lower().replace("’", "'"))


def distance(reference, observed):
    row = list(range(len(observed) + 1))
    for i, word in enumerate(reference, 1):
        previous, row = row, [i]
        for j, hypothesis in enumerate(observed, 1):
            row.append(min(previous[j] + 1, row[-1] + 1,
                           previous[j - 1] + (word != hypothesis)))
    return row[-1]


def main():
    manifest = ROOT / "data/prepared/validation.jsonl"
    rows = [json.loads(line) for line in manifest.read_text(encoding="utf-8").splitlines()]
    sample = {}
    for row in sorted(rows, key=lambda r: hashlib.sha256(r["id"].encode()).digest()):
        sample.setdefault(row["speaker_id"], row)
    results = []
    with TestClient(app) as client:
        for row in sample.values():
            payload = (ROOT / row["audio_path"]).read_bytes()
            start = perf_counter()
            response = client.post("/transcribe", files={"audio": ("turn.wav", payload)})
            seconds = perf_counter() - start
            if response.status_code not in (200, 422):
                response.raise_for_status()
            body = response.json()
            reference, hypothesis = tokens(row["text"]), tokens(body.get("text", ""))
            results.append({"id": row["id"], "status": response.status_code,
                            "reference_words": len(reference), "edits": distance(reference, hypothesis),
                            "seconds": seconds, "audio_seconds": row["duration_seconds"]})
    warm = results[1:]
    report = {"dataset": "speechocean762 validation, one lowest SHA-256 clip ID per speaker",
              "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
              "model": "faster-whisper small.en, CPU int8, four threads, beam 5, VAD",
              "clips": len(results), "speakers": len(sample),
              "returned_transcripts": sum(r["status"] == 200 for r in results),
              "reference_words": sum(r["reference_words"] for r in results),
              "word_edits": sum(r["edits"] for r in results),
              "cold_seconds": results[0]["seconds"], "warm_median_seconds": median(r["seconds"] for r in warm),
              "warm_real_time_factor": sum(r["seconds"] for r in warm) / sum(r["audio_seconds"] for r in warm),
              "results": results}
    report["word_error_rate"] = report["word_edits"] / report["reference_words"]
    output = ROOT / "reports/conversation_handoff/transcription_validation.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k != "results"}, indent=2))


if __name__ == "__main__":
    main()
