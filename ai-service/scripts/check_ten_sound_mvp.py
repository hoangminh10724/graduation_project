"""Historical ten-prompt integration checks, not an accuracy benchmark.

For the current General American inventory use check_american_expansion.py.

Choose utterances deterministically before inference from the existing training
partition. No target labels, transcripts or teacher comments enter the recognizer.
All outcomes, including unsupported phones and abstentions, are retained.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ai-service"))
from app.sound_catalog import PRIMARY_TARGETS, PROMPTS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8013")
    parser.add_argument("--output", type=Path, default=ROOT / "data/results/ten_sound_mvp")
    args = parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()):
        parser.error("Output already contains results; choose a new --output")
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = ROOT / "data/prepared/train.jsonl"
    corpus = [json.loads(s) for s in manifest.read_text(encoding="utf-8").splitlines()]
    chosen_prompts = ["seat", "sit", "bed", "bad", "two", "put", "ten", "can", "see", "she"]
    practice_targets = tuple(PROMPTS[p]["target_phone"] for p in chosen_prompts)
    assert len(set(practice_targets)) == 10
    assert set(practice_targets) <= set(PRIMARY_TARGETS)
    selected = []
    missing = []
    for prompt in chosen_prompts:
        eligible = [r for r in corpus if 0.25 <= r["duration_seconds"] <= 4
                    and re.findall(r"[a-z]+", r["text"].lower()).count(PROMPTS[prompt]["word"]) == 1]
        eligible.sort(key=lambda r: hashlib.sha256(("WordSpeak-ten-sound-integration-v1:" + r["id"]).encode()).hexdigest())
        speakers, picks = set(), []
        for row in eligible:
            if row["speaker_id"] in speakers:
                continue
            picks.append(row); speakers.add(row["speaker_id"])
            if len(picks) == 3:
                break
        if not picks:
            missing.append(prompt)
        selected.extend((prompt, row) for row in picks)
    results = []
    with httpx.Client(base_url=args.url, timeout=180, trust_env=False) as client:
        config = client.get("/demo/config").json()
        assert set(config["primary_targets"]) == set(PRIMARY_TARGETS)
        assert client.get("/demo/status").json()["training_running"] is False
        for index, (prompt, record) in enumerate(selected, 1):
            audio = ROOT / record["audio_path"]
            response = client.post("/demo/analyze", data={"prompt_id": prompt},
                files={"audio": (audio.name, audio.read_bytes(), "audio/wav")})
            assert response.status_code == 200, response.text
            result = response.json()
            assert result["mode"] == "live_audio" and result["score"] is None
            assert result["target_phone"] == PROMPTS[prompt]["target_phone"]
            results.append({"id": record["id"], "speaker_id": record["speaker_id"],
                "source_split": "train", "source_audio_path": record["audio_path"],
                "source_audio_sha256": hashlib.sha256(audio.read_bytes()).hexdigest(),
                "text_for_review_only": record["text"], "prompt_id": prompt, "response": result,
                "classification_correct": None})
            (args.output / "real_audio_checks.jsonl").write_text("".join(json.dumps(r,ensure_ascii=False)+"\n" for r in results),encoding="utf-8")
            print(f"{index}/{len(selected)} {prompt}: {result['status']}", flush=True)
        assert client.post("/assess", data={"text":"hello"}, files={"audio":("a.wav",b"RIFF")}).status_code == 501
    by_sound = {}
    for phone in practice_targets:
        relevant = [r for r in results if r["response"]["target_phone"] == phone]
        by_sound[phone] = {"requests": len(relevant),
            "statuses": dict(Counter(r["response"]["status"] for r in relevant)),
            "interpretation": "integration outcomes, not correct/incorrect labels"}
    summary = {"status": "PASS", "purpose":"Real-model end-to-end API coverage, not recognition accuracy",
        "build": config["build"], "primary_targets": list(practice_targets),
        "current_primary_targets": list(PRIMARY_TARGETS), "historical_subset": True,
        "source_manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
        "real_requests": len(results), "source_participant_ids":len({r["speaker_id"] for r in results}),
        "missing_source_prompts": missing, "by_sound": by_sound,
        "classification_accuracy":None, "training_performed":False,"untouched_corpus_test_used":False,
        "limitations":["Source utterances contain surrounding words and may have pronunciation errors.",
            "Selection uses text, duration and ID hash; not expert scores or model confidence.",
            "Model_match is not a human-verified correctness judgment.",
            "All outcomes are retained; no teacher feedback is converted into complete actual-heard phone sequences."]}
    (args.output / "summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=True,indent=2))


if __name__ == "__main__":
    main()
