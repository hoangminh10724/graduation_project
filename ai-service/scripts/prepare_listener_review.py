"""Build a local, blind listening task for the deduplicated Vietnamese batch."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
BATCH = ROOT / "data/prepared/new_collection_20261121"
OUTPUT = ROOT / "data/results/listener_review"


def main():
    rows = [json.loads(line) for line in (BATCH / "manifest.jsonl").read_text(encoding="utf-8").splitlines()]
    clips = {}
    key = {}
    for row in rows:
        if row["status"] != "prepared":
            continue
        source = ROOT / row["audio_path"]
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        clip_id = "clip-" + digest[:20]
        if clip_id in clips:
            raise ValueError("Duplicate prepared audio")
        clips[clip_id] = source
        key[clip_id] = {"recording": row["id"], "speaker": row["speaker_id"], "wav_sha256": digest}
    ids = sorted(clips)
    batch = hashlib.sha256("\n".join(ids).encode()).hexdigest()
    folder = OUTPUT / batch[:12]
    review = folder / "review"
    (review / "audio").mkdir(parents=True, exist_ok=True)
    for clip_id, source in clips.items():
        shutil.copyfile(source, review / "audio" / (clip_id + ".wav"))
    template = Path(__file__).with_name("listener_review.html").read_text(encoding="utf-8")
    (review / "index.html").write_text(template.replace('"__BATCH__"',json.dumps(batch)).replace('"__IDS__"',json.dumps(ids)),encoding="utf-8")
    (folder / "analysis_key.json").write_text(json.dumps(key, indent=2), encoding="utf-8")
    print(f"{len(ids)} recordings, {len(set(row['speaker'] for row in key.values()))} speakers: {review / 'index.html'}")


if __name__ == "__main__":
    main()
