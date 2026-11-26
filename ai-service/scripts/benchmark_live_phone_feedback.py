"""Compare live context-mode warnings with independent corpus phone-quality ratings.

All eligible validation rows, no tuning. A low expert rating is a proxy for a
problem, not an annotation identifying which alternative phone was heard.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ai-service"))
from app.english_inventory import ARPABET, PROMPTS


def matching_cases(row):
    if not .25 <= row["duration_seconds"] <= 4:
        return
    words = row["pronunciation_labels"]["words"]
    counts = Counter(w["text"].lower() for w in words)
    for word in words:
        key = word["text"].lower()
        prompt = PROMPTS.get(key)
        if counts[key] != 1 or not prompt or not prompt["primary"]:
            continue
        phone = ARPABET[prompt["target_phone"]]
        # Keep stress where the teaching target explicitly distinguishes it.
        indices = [i for i, label in enumerate(word["phones"])
                   if (label if phone[-1].isdigit() else re.sub(r"\d+$", "", label)) == phone]
        if len(indices) == 1:
            yield key, word["phones-accuracy"][indices[0]]


def summarize(rows):
    warnings = [r for r in rows if r["status"] == "possible_difference"]
    low = sum(r["expert_rating"] < 1 for r in rows)
    confirmed = sum(r["expert_rating"] < 1 for r in warnings)
    return {"cases": len(rows), "low_rated": low, "warnings": len(warnings),
            "warnings_on_low_rated": confirmed,
            "precision_against_low_rating": confirmed / len(warnings) if warnings else None,
            "recall_against_low_rating": confirmed / low if low else None,
            "statuses": dict(Counter(r["status"] for r in rows))}


def main():
    manifest = ROOT / "data/prepared/validation.jsonl"
    rows = []
    with httpx.Client(base_url="http://127.0.0.1:8013", timeout=180, trust_env=False) as client:
        config = client.get("/demo/config").raise_for_status().json()
        for line in manifest.read_text(encoding="utf-8").splitlines():
            example = json.loads(line)
            for key, rating in matching_cases(example):
                resp = client.post("/demo/analyze", data={"prompt_id": key, "input_scope": "context"},
                                   files={"audio": ("clip.wav", (ROOT / example["audio_path"]).read_bytes())})
                result = resp.raise_for_status().json()
                assert result["mode"] == "live_audio" and result["target_phone"] == PROMPTS[key]["target_phone"]
                rows.append({"id": example["id"], "speaker": example["speaker_id"], "word": key,
                             "expert_rating": rating, "status": result["status"],
                             "predicted_phone": result["predicted_phone"], "diagnosis": result["diagnosis"]["kind"]})
    keys = sorted({r["word"] for r in rows})
    report = {"build": config["build"], "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
              "dataset": "speechocean762 validation; complete eligible short utterances; context mode",
              "criterion": "expert target-phone quality < 1 on the 0 to 2 scale",
              "speakers": len({r["speaker"] for r in rows}), "targets": len(keys),
              "overall": summarize(rows), "by_prompt": {k: summarize([r for r in rows if r["word"] == k]) for k in keys},
              "heard_phone_accuracy": None, "rows": rows}
    output = ROOT / "reports/conversation_handoff/live_phone_validation.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report["overall"]))


if __name__ == "__main__":
    main()
