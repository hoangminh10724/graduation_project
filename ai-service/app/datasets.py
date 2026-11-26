"""Read prepared dataset manifests from any working directory."""
import json
from pathlib import Path
from typing import Iterator

PROJECT_ROOT=Path(__file__).resolve().parents[2]


def iter_examples(manifest: str | Path, *, require_labels: bool=False) -> Iterator[dict]:
    """Yield examples with an absolute audio_path; optionally reject unlabeled data."""
    path=Path(manifest)
    if not path.is_absolute():path=PROJECT_ROOT/path
    with path.open(encoding='utf-8') as stream:
        for line_number,line in enumerate(stream,1):
            if not line.strip():continue
            example=json.loads(line)
            if require_labels and example.get('pronunciation_labels') is None:
                raise ValueError(f'{path}:{line_number}: no reference pronunciation labels')
            audio=PROJECT_ROOT/example['audio_path']
            if not audio.is_file():raise FileNotFoundError(audio)
            yield dict(example,audio_path=str(audio))
