"""Experimental GOP for isolated, explicitly supported English words."""
import os
from functools import lru_cache
from pathlib import Path
from threading import Lock

from fastapi import HTTPException

from .gop import normalize_gop
from .phoneme_recognition import LocalPhonemeRecognizer
from .transcription import RATE, decode

WORDS = {
    "think": "θ ɪ ŋ k", "she": "ʃ iː", "see": "s iː", "sit": "s ɪ t",
    "seat": "s iː t", "bed": "b ɛ d", "bad": "b æ d", "book": "b ʊ k",
    "food": "f uː d", "pen": "p ɛ n", "ten": "t ɛ n", "key": "k iː",
}
LOCK = Lock()
EQUIVALENT_LABELS = {"iː": "i", "uː": "u", "ɛ": "e"}


@lru_cache(maxsize=1)
def recognizer():
    directory = Path(__file__).resolve().parents[2] / "data/models/phoneme-recognition"
    return LocalPhonemeRecognizer(os.getenv("WORDSPEAK_PHONEME_MODEL", directory))


def align(log_probs, tokens, blank):
    """Viterbi alignment over alternating blank and reference-phone states."""
    import numpy as np

    states = [blank]
    for token in tokens:
        states.extend((token, blank))
    scores = np.full(len(states), -np.inf)
    scores[0] = 0
    parents = []
    for frame in log_probs:
        choices = np.full((3, len(states)), -np.inf)
        choices[0] = scores
        choices[1, 1:] = scores[:-1]
        for i in range(3, len(states), 2):
            if states[i] != states[i - 2]:
                choices[2, i] = scores[i - 2]
        parents.append(choices.argmax(axis=0))
        scores = choices.max(axis=0) + frame[states]
    state = len(states) - 2 + int(scores[-1] > scores[-2])
    if not np.isfinite(scores[state]):
        raise HTTPException(422, "Recording too short for the selected word.")
    path = []
    for parent in reversed(parents):
        path.append(state)
        state -= int(parent[state])
    return np.array(path[::-1])


def assess_word(payload, word):
    import numpy as np

    samples = decode(payload)
    if not RATE // 4 <= len(samples) <= 4 * RATE or np.sqrt(np.mean(samples ** 2)) < 0.002:
        raise HTTPException(422, "Record one clearly audible word, 0.25 to 4 seconds long.")
    with LOCK:
        try:
            engine = recognizer()
            inputs = engine.extractor(samples, sampling_rate=RATE, return_tensors="pt")
            with engine.torch.inference_mode():
                probs = engine.model(**inputs).logits[0].float().log_softmax(-1).numpy()
        except (ImportError, OSError, ValueError, RuntimeError) as exc:
            raise HTTPException(503, "Local phoneme inference unavailable.") from exc
    labels = WORDS[word].split()
    ids = {label: index for index, label in engine.vocabulary.items()}
    tokens = [ids[label] for label in labels]
    if all(int(i) in engine.special_ids for i in probs.argmax(axis=1)):
        raise HTTPException(422, "No usable speech detected.")
    for label in set(labels) & EQUIVALENT_LABELS.keys():
        target = ids[label]
        alternate = ids[EQUIVALENT_LABELS[label]]
        probs[:, target] = np.logaddexp(probs[:, target], probs[:, alternate])
    path = align(probs, tokens, engine.blank_id)
    phones = []
    for i, (label, token) in enumerate(zip(labels, tokens)):
        frames = np.flatnonzero(path == 2 * i + 1)
        score = normalize_gop(float(probs[frames, token].mean()))
        phones.append({"ipa": label, "score": score,
                       "start": float(frames[0] * engine.frame_stride / RATE),
                       "end": float(min(len(samples), frames[-1] * engine.frame_stride + engine.receptive_field) / RATE)})
    score = round(sum(p["score"] for p in phones) / len(phones), 1)
    return {"sentence_score": score, "words": [{"word": word, "score": score, "phonemes": phones}],
            "errors": [], "hints": []}
