import numpy as np
import pytest
from app import tutor_observation as tutor


@pytest.mark.parametrize("focus,checked,span", [
    ("catch up", "up", (0.8, 1.6)),
    ("rain check", None, (1.6, 2.4)),
    ("give up", None, None),
    ("", "up", None),
])
def test_expression_scopes_acoustic_check(monkeypatch, focus, checked, span):
    words = [dict(word=w, start=i*0.4, end=(i+1)*0.4)
             for i,w in enumerate(["Up", "there,", "catch", "up!", "Rain", "check."])]
    monkeypatch.setattr(tutor, "recognize", lambda _: dict(text="Test", words=words))
    monkeypatch.setattr(tutor, "decode", lambda _: np.zeros(40000, dtype=np.float32))
    class Analyzer:
        def analyze_prompt(self, audio, prompt, scope):
            assert prompt["word"] == checked and audio.startswith(b"RIFF")
            return dict(status="uncertain", target_phone=prompt["target_phone"], predicted_phone=None)
    monkeypatch.setattr(tutor, "get_demo_service", Analyzer)
    evidence = tutor.observe(b"fixture", focus)["observation"]
    assert evidence.get("word") == checked
    if focus == "catch up":
        assert evidence["start"] > 1
    if span:
        assert list(evidence["expression"].values()) == pytest.approx(span)
    else:
        assert "expression" not in evidence
