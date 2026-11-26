import numpy as np
from app.transcription import RATE
from app.tutor_observation import phrasing_observation


def test_phrasing_bookmark_follows_internal_quiet_region():
    signal = np.full(RATE * 3, .15, dtype=np.float32)
    signal[RATE:RATE + RATE//2] = 0
    words = [{"start":0, "end":1}, {"start":1.5, "end":3}]
    observation = phrasing_observation(signal, words)
    assert (observation["start"], observation["end"]) == (1.0, 1.5)
    assert phrasing_observation(signal, words[:1]) is None
    assert phrasing_observation(np.zeros_like(signal), words) is None
    signal[:RATE] = 0
    assert phrasing_observation(signal, words) is None
