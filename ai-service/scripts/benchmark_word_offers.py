"""Audit word-practice offers against complete corpus transcripts, by recording."""
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ai-service"))
sys.path.append(str(ROOT / "data/speech-tools"))
from fastapi.testclient import TestClient
from app.main import app


def normalized(word):
    word = word.strip().lower()
    while word and unicodedata.category(word[0]).startswith("P"):
        word = word[1:]
    while word and unicodedata.category(word[-1]).startswith("P"):
        word = word[:-1]
    return word


def select_examples(rows, catalog):
    strata = {}
    for row in sorted(rows, key=lambda r: sha256(r["id"].encode()).digest()):
        has_target = any(normalized(w) in catalog for w in row["text"].split())
        strata.setdefault((row["speaker_id"], has_target), row)
    return list(strata.values())


def main():
    manifest = ROOT / "data/prepared/validation.jsonl"
    results = []
    totals = defaultdict(Counter)
    with TestClient(app) as client:
        config = client.get("/demo/config").raise_for_status().json()
        catalog = {prompt["word"].lower() for prompt in config["prompts"]}
        examples = select_examples([json.loads(line) for line in manifest.read_bytes().splitlines()], catalog)
        build = config["build"]
        for row in examples:
            reference = Counter(normalized(w) for w in row["text"].split() if normalized(w) in catalog)
            reply = client.post("/transcribe", files={"audio": ("turn.wav", (ROOT/row["audio_path"]).read_bytes())})
            if reply.status_code != 422:
                reply.raise_for_status()
            words = reply.json().get("words", [])
            offered = Counter()
            previous_end = 0
            for token in words:
                start, end = token["start"], token["end"]
                if start < previous_end or end < start or end > row["duration_seconds"]+.02:
                    offered.clear()
                    break
                previous_end = end
                word = normalized(token["word"])
                if word in catalog and 0 < end-start <= 4:
                    offered[word] += 1
            matched = reference & offered
            for word in reference.keys() | offered.keys():
                totals[word].update(reference=reference[word], offered=offered[word], matched=matched[word])
            results.append(dict(id=row["id"], speaker=row["speaker_id"], status=reply.status_code,
                                reference=reference, offered=offered, matched=matched))
    overall = sum(totals.values(), Counter())
    report = dict(build=build, dataset="speechocean762 validation",
        sampling="Lowest SHA-256 clip ID per speaker in each of two strata: contains a catalog word or does not.",
        metric="Per-clip lexical counts capped by reference multiplicity. Independent word times are unavailable.",
        manifest_sha256=sha256(manifest.read_bytes()).hexdigest(), clips=len(results),
        speakers=len({r["speaker"] for r in results}), overall=overall, by_word=totals, rows=results)
    output = ROOT / "reports/conversation_handoff/word_offer_validation.json"
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(report["clips"], report["speakers"], overall)


if __name__ == "__main__":
    main()
