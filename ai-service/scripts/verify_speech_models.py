"""Check local speech model assets against the versions used for the handoff results."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def verify(directory, reference):
    issues = []
    for name, expected in reference["files"].items():
        try:
            with (directory / name).open("rb") as stream:
                actual = hashlib.file_digest(stream, "sha256").hexdigest()
            if actual != expected:
                issues.append(f"{name}: SHA-256 mismatch")
        except OSError as exc:
            issues.append(f"{name}: {exc.strerror}")
    if "revision" in reference:
        try:
            provenance = json.loads((directory / "provenance.json").read_text(encoding="utf-8"))
            if any(provenance.get(k) != reference[k] for k in ("model_id", "revision")):
                issues.append("provenance.json: model ID or revision differs")
        except (ValueError, OSError, AttributeError) as exc:
            issues.append(f"provenance.json: {exc}")
    return issues


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phoneme-dir", type=Path, default=ROOT / "data/models/phoneme-recognition")
    parser.add_argument("--whisper-dir", type=Path, default=ROOT / "data/models/native-preparation/whisper-small.en")
    args = parser.parse_args()
    refs = json.loads((ROOT / "reports/conversation_handoff/speech_model_hashes.json").read_text(encoding="utf-8"))
    failed = False
    for kind, path in (("phoneme", args.phoneme_dir), ("transcription", args.whisper_dir)):
        issues = verify(path, refs[kind])
        if issues:
            failed = True
            for issue in issues:
                print(f"{kind}: {issue}")
        else:
            print(f"{kind}: {len(refs[kind]['files'])} files match the handoff.")
    raise SystemExit(int(failed))


if __name__ == "__main__":
    main()
