import hashlib
from pathlib import Path
import sys
import wave

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from evaluate_teacher_tutor import evaluate


def test_reviewed_occurrence_and_other_occurrence(tmp_path):
    path = tmp_path / "recording.wav"
    with wave.open(str(path), "wb") as wav:
        wav.setparams((1, 2, 16000, 0, "NONE", ""))
        wav.writeframes(bytes(32 * 32000))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    record = dict(id="P00_01", source=str(path), playback_audio=str(path), source_sha256=digest,
                  items=[{"review_words": ["both"]}])
    decision = dict(recording="P00_01", item=0, word="both", start=29, end=29.5, verdict="difference",
                    heard_phone="s", target_phone="θ", source_sha256=digest, playback_sha256=digest)
    def observed(payload, word):
        assert word == "both"
        return {"observation": dict(kind="possible_difference", word=word, target="θ", candidate="s",
                                    start=27, end=27.5)}
    report = evaluate([decision, {"note": "passage only"}], [record], observed)
    assert report["overall"]["specific_warning_precision"] == 1
    assert report["notes_without_sound_rating"] == 1
    other = evaluate([{**decision, "start": 30, "end": 30.5}], [record], observed)
    assert other["unmatched_warnings"] == 1
    assert other["overall"]["specific_warning_precision"] is None
    assert other["overall"]["warning_recall"] == 0
    with pytest.raises(ValueError, match="changed"):
        evaluate([{**decision, "playback_sha256": "wrong"}], [record], observed)
