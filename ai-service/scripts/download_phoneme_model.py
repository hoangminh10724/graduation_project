"""Download a pinned, public phoneme model without sending any audio anywhere."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request

MODEL_ID = "facebook/wav2vec2-lv-60-espeak-cv-ft"
REVISION = "ae45363bf3413b374fecd9dc8bc1df0e24c3b7f4"
FILES = ("config.json", "preprocessor_config.json", "vocab.json",
         "tokenizer_config.json", "special_tokens_map.json", "README.md",
         "pytorch_model.bin")
ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "data/models/phoneme-recognition")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    records = []
    for name in FILES:
        url = f"https://huggingface.co/{MODEL_ID}/resolve/{REVISION}/{name}"
        dest = args.output / name
        if not dest.is_file():
            partial = dest.with_name(name + ".partial")
            print(f"Downloading {name}", flush=True)
            with urllib.request.urlopen(url, timeout=90) as response:
                expected = response.headers.get("Content-Length")
                count = 0
                with partial.open("wb") as stream:
                    while chunk := response.read(4 * 1024 * 1024):
                        stream.write(chunk)
                        count += len(chunk)
                if expected is not None and count != int(expected):
                    raise RuntimeError(f"Incomplete download: {name}")
            partial.replace(dest)
        digest = hashlib.sha256()
        with dest.open("rb") as stream:
            while chunk := stream.read(4 * 1024 * 1024):
                digest.update(chunk)
        records.append({"file": name, "bytes": dest.stat().st_size,
                        "sha256": digest.hexdigest(), "source_url": url})
        print(f"Ready: {name} ({dest.stat().st_size:,} bytes)", flush=True)
    (args.output / "provenance.json").write_text(json.dumps({
        "model_id": MODEL_ID, "revision": REVISION, "license": "Apache-2.0",
        "files": records,
        "note": "Hashes record local download integrity; audio is never uploaded."
    }, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
