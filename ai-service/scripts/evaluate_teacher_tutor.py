"""Replay reviewed passages through the spoken tutor on this workstation."""
import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import sys
import wave

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ai-service"))
sys.path.append(str(ROOT / "data/speech-tools"))
from fastapi import HTTPException
from app.transcription import MAX_SECONDS, RATE
from app.tutor_observation import catalog, observe
from evaluate_expert_words import summarize


def context_audio(path, start, end):
    with wave.open(str(path), "rb") as src:
        if (src.getframerate(), src.getnchannels(), src.getsampwidth()) != (RATE, 1, 2):
            raise ValueError("Playback format differs from the reviewed WAV.")
        duration = src.getnframes() / RATE
        if not 0 <= start < end <= duration or end-start > MAX_SECONDS:
            raise ValueError("Reviewed interval is outside the supported turn.")
        offset = round(RATE * max(0, min((start+end-MAX_SECONDS)/2, duration-MAX_SECONDS)))
        src.setpos(offset)
        frames = src.readframes(MAX_SECONDS * RATE)
    buffer = BytesIO()
    with wave.open(buffer, "wb") as out:
        out.setparams((1, 2, RATE, 0, "NONE", ""))
        out.writeframes(frames)
    return buffer.getvalue(), offset / RATE


def evaluate(decisions, records, run=observe):
    index = {record["id"]: record for record in records}
    rows, seen, hashes = [], set(), {}
    skipped = 0
    for decision in decisions:
        verdict = decision.get("verdict")
        if not verdict:
            skipped += 1
            continue
        record = index[decision["recording"]]
        word = decision["word"].lower()
        item = decision["item"]
        if not isinstance(item, int) or not 0 <= item < len(record["items"]) or decision["word"] not in record["items"][item]["review_words"]:
            raise ValueError("Reviewed word does not belong to this teacher comment.")
        target = catalog[word]["target_phone"]
        if target != decision["target_phone"] or verdict not in ("acceptable", "difference", "unclear"):
            raise ValueError("Tutor target or reviewer decision is invalid.")
        heard = decision.get("heard_phone", "").strip()
        if verdict == "difference" and not heard:
            raise ValueError("A difference requires the independently heard sound or deletion.")
        path = ROOT / record["playback_audio"]
        for filename, expected in ((ROOT / record["source"], record["source_sha256"]), (path, decision["playback_sha256"])):
            if filename not in hashes:
                hashes[filename] = sha256(filename.read_bytes()).hexdigest()
            if hashes[filename] != expected:
                raise ValueError("Recording changed since review.")
        if decision["source_sha256"] != record["source_sha256"]:
            raise ValueError("Reviewed source recording changed.")
        start, end = decision["start"], decision["end"]
        occurrence = (hashes[path], round(start*RATE), round(end*RATE), word)
        if occurrence in seen:
            raise ValueError("Repeated rating for the same sound occurrence.")
        seen.add(occurrence)
        payload, offset = context_audio(path, start, end)
        try:
            observation = run(payload, word)["observation"]
        except HTTPException as exc:
            if exc.status_code != 422:
                raise
            observation = {"kind": "no_transcript"}
        status = observation["kind"]
        overlap = None
        if "word" in observation:
            left, right = offset+observation["start"], offset+observation["end"]
            overlap = max(0, min(end, right)-max(start, left)) / (max(end, right)-min(start, left))
            if observation["word"] != word or observation["target"] != target or overlap < .5:
                status = "unmatched_occurrence"
        rows.append(dict(recording=record["id"], speaker=(record.get("duplicate_audio_of") or record["id"]).split("_")[0],
                         word=word, target_phone=target, start=start, end=end, context_start=offset,
                         verdict=verdict, heard_phone=heard, status=status, interval_overlap=overlap,
                         predicted=observation.get("candidate"), tutor_observation=observation))
    return {"review_context": "Teacher comments visible; reviewer-located context, requested focus word.",
            "localization_rule": "Same word and target, intersection over union of intervals at least 0.5.",
            "notes_without_sound_rating": skipped, "rated_occurrences": len(rows),
            "unmatched_warnings": sum(r["status"] == "unmatched_occurrence" and
                                      r["tutor_observation"]["kind"] == "possible_difference" for r in rows),
            "overall": summarize(rows), "rows": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("review", type=Path)
    parser.add_argument("candidates", type=Path)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    raw = args.review.read_bytes()
    report = evaluate(json.loads(raw), json.loads(args.candidates.read_bytes()))
    report["review_sha256"] = sha256(raw).hexdigest()
    with args.report.open("x", encoding="utf-8") as output:
        json.dump(report, output, ensure_ascii=False, indent=2)
    print(f"Evaluated {report['rated_occurrences']} rated occurrences.")
