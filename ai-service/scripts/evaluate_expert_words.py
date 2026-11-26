"""Evaluate the live word-practice mode on independently annotated word intervals."""
import argparse
from collections import Counter, defaultdict
from hashlib import sha256
from io import BytesIO
import json
import math
from pathlib import Path
import random
import sys
import wave

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.english_inventory import normalize_label


def word_audio(path, start, end):
    with wave.open(str(path), "rb") as source:
        rate = source.getframerate()
        if (rate, source.getnchannels(), source.getsampwidth()) != (16000, 1, 2):
            raise ValueError("Supply mono 16 kHz PCM16 WAV and preserve the source timeline.")
        if not 0 <= start < end <= source.getnframes() / rate:
            raise ValueError("Word interval lies outside the recording.")
        first, last = round(start * rate), round(end * rate)
        if not 4000 <= last - first <= 64000:
            return None
        source.setpos(first)
        frames = source.readframes(last - first)
    buffer = BytesIO()
    with wave.open(buffer, "wb") as clip:
        clip.setparams((1, 2, rate, 0, "NONE", "not compressed"))
        clip.writeframes(frames)
    return buffer.getvalue()


def ratios(counts):
    def divide(n, d):
        return counts[n] / counts[d] if counts[d] else None
    return {"warning_precision": divide("true_warnings", "warnings"),
            "warning_recall": divide("true_warnings", "expert_differences"),
            "specific_warning_precision": divide("correct_specific_warnings", "warnings"),
            "decision_coverage": divide("decisions", "rated")}


def summarize(rows):
    by_speaker = defaultdict(Counter)
    for row in rows:
        c = by_speaker[row["speaker"]]
        c["occurrences"] += 1
        status = row["status"]
        c["status_" + status] += 1
        if row["verdict"] == "unclear":
            c["expert_unclear"] += 1
            continue
        c["rated"] += 1
        difference = row["verdict"] == "difference"
        warning = status == "possible_difference"
        c["expert_differences"] += difference
        c["decisions"] += status in ("model_match", "possible_difference")
        c["warnings"] += warning
        c["true_warnings"] += warning and difference
        c["false_warnings"] += warning and not difference
        c["missed_differences"] += difference and not warning
        c["correct_specific_warnings"] += bool(warning and difference and row["predicted"]
            and normalize_label(row["predicted"]) == normalize_label(row["heard_phone"]))
    counts = sum(by_speaker.values(), Counter())
    estimates = ratios(counts)
    intervals = {metric: None for metric in estimates}
    if len(by_speaker) >= 2:
        rng = random.Random(20261122)
        samples = defaultdict(list)
        clusters = list(by_speaker.values())
        for _ in range(2000):
            sample = sum(rng.choices(clusters, k=len(clusters)), Counter())
            for metric, value in ratios(sample).items():
                if value is not None:
                    samples[metric].append(value)
        for metric, values in samples.items():
            values.sort()
            if len(values) >= 1950:
                intervals[metric] = [values[math.floor((len(values)-1)*p)] for p in (.025,.975)]
    return {"speakers": len(by_speaker), "counts": dict(counts), **estimates,
            "speaker_bootstrap_95pct": intervals}


def evaluate(manifest, client):
    raw = manifest.read_bytes()
    config = client.get("/demo/config").raise_for_status().json()
    prompts = {p["id"]: p for p in config["prompts"]}
    rows, seen = [], set()
    for index, line in enumerate(raw.decode("utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        try:
            key = row["prompt_id"]
            speaker, occurrence = row["speaker"], row["id"]
            if not speaker or not occurrence or occurrence in seen:
                raise ValueError("Provide a speaker and unique occurrence ID.")
            seen.add(occurrence)
            verdict = row["verdict"]
            if verdict not in ("acceptable", "difference", "unclear"):
                raise ValueError("Unrecognized expert verdict.")
            heard = row.get("heard_phone", "")
            if verdict == "difference" and not heard.strip():
                raise ValueError("An adjudicated difference needs an actual-heard phone or deletion label.")
            clip = word_audio(manifest.parent / row["audio"], row["start"], row["end"])
            predicted = None
            if key not in prompts:
                status = "unsupported_prompt"
            elif clip is None:
                status = "unsupported_duration"
            else:
                response = client.post("/demo/analyze", data={"prompt_id": key, "input_scope": "word"},
                                       files={"audio": ("word.wav", clip, "audio/wav")})
                result = response.raise_for_status().json()
                if result["mode"] != "live_audio" or result["target_phone"] != prompts[key]["target_phone"]:
                    raise ValueError("Unexpected live model or target.")
                status, predicted = result["status"], result["predicted_phone"]
            rows.append(dict(id=occurrence, speaker=speaker, prompt_id=key, verdict=verdict,
                             heard_phone=heard, predicted=predicted, status=status,
                             clip_sha256=sha256(clip).hexdigest() if clip else None))
        except (ValueError, KeyError, TypeError, OSError, wave.Error, httpx.HTTPError) as exc:
            raise ValueError(f"Manifest line {index}: {exc}") from exc
    if not rows:
        raise ValueError("Manifest contains no occurrences.")
    groups = defaultdict(list)
    contrasts = defaultdict(Counter)
    for row in rows:
        target = prompts.get(row["prompt_id"], {}).get("target_phone", "unsupported")
        groups[target].append(row)
        if row["status"] == "possible_difference":
            proposed = normalize_label(row["predicted"] or "unspecified")
            counts = contrasts[f"{target} -> {proposed}"]
            counts["warnings"] += 1
            if row["verdict"] != "unclear":
                counts["rated_warnings"] += 1
                counts["confirmed"] += (row["verdict"] == "difference"
                    and normalize_label(row["heard_phone"]) == proposed)
    return {"build": config["build"], "manifest_sha256": sha256(raw).hexdigest(),
            "overall": summarize(rows), "by_intended_phone": {k:summarize(v) for k,v in groups.items()},
            "proposed_contrasts": {k: {**v, "precision": v["confirmed"] / v["rated_warnings"]
                if v["rated_warnings"] else None} for k, v in contrasts.items()},
            "rows": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    with httpx.Client(base_url="http://127.0.0.1:8013", timeout=180, trust_env=False) as client:
        report = evaluate(args.manifest, client)
    with args.report.open("x", encoding="utf-8") as output:
        json.dump(report, output, ensure_ascii=False, indent=2)
    print(json.dumps(report["overall"], indent=2))
