"""Experimental raw-audio phoneme recognition, separate from pronunciation scoring.

Neither the expected word nor its canonical phones are supplied to the recognizer.
CTC timings are approximate model-frame spans, not verified phone boundaries.
"""
from itertools import groupby
import json
from pathlib import Path


from .english_inventory import ARPABET, normalize_label
TARGET_PHONES = ARPABET


def convolution_geometry(kernels, strides):
    """Return convolution receptive-field width and frame stride in samples."""
    width, jump = 1, 1
    if len(kernels) != len(strides) or not kernels:
        raise ValueError("Matching nonempty convolution configuration required")
    for kernel, stride in zip(kernels, strides):
        width += (kernel - 1) * jump
        jump *= stride
    return width, jump


def collapse_ctc(ids, peaks, vocabulary, *, blank_id, special_ids,
                 sample_rate, frame_stride, receptive_field, duration):
    """Collapse only adjacent repeats; a blank separates repeated phones.

    Peak probabilities are uncalibrated model diagnostics, never correctness scores.
    All non-special labels remain visible, including labels outside the ten targets.
    """
    if len(ids) != len(peaks):
        raise ValueError("One peak probability required per CTC frame")
    spans = []
    for token_id, frames_iter in groupby(enumerate(ids), key=lambda item: item[1]):
        frames = [index for index, _ in frames_iter]
        if token_id == blank_id or token_id in special_ids:
            continue
        phone = vocabulary[token_id]
        start = frames[0] * frame_stride / sample_rate
        end = (frames[-1] * frame_stride + receptive_field) / sample_rate
        spans.append({
            "phone": phone,
            "start_seconds": round(min(duration, start), 4),
            "end_seconds": round(min(duration, end), 4),
            "mean_frame_peak_probability": round(
                sum(float(peaks[index]) for index in frames) / len(frames), 5),
            "target_arpabet": TARGET_PHONES.get(normalize_label(phone)),
            "in_target_inventory": normalize_label(phone) in TARGET_PHONES,
        })
    return spans


class LocalPhonemeRecognizer:
    """Lazy dependencies allow decoding tests without downloading model weights."""

    def __init__(self, model_dir, *, threads=4):
        import torch
        from transformers import Wav2Vec2FeatureExtractor, Wav2Vec2ForCTC

        self.torch = torch
        torch.set_num_threads(threads)
        model_dir = Path(model_dir)
        self.extractor = Wav2Vec2FeatureExtractor.from_pretrained(
            model_dir, local_files_only=True)
        self.model = Wav2Vec2ForCTC.from_pretrained(
            model_dir, local_files_only=True, weights_only=True).eval()
        self.vocabulary = {v: k for k, v in json.loads(
            (model_dir / "vocab.json").read_text(encoding="utf-8")).items()}
        if set(self.vocabulary) != set(range(self.model.config.vocab_size)):
            raise ValueError("Vocabulary and acoustic model dimensions differ")
        self.blank_id = self.model.config.pad_token_id
        self.special_ids = {index for index, text in self.vocabulary.items()
                            if text.startswith("<") and text.endswith(">")}
        self.receptive_field, self.frame_stride = convolution_geometry(
            self.model.config.conv_kernel, self.model.config.conv_stride)
        self.provenance = json.loads((model_dir / "provenance.json").read_text(
            encoding="utf-8"))

    def predict(self, audio_path):
        import numpy as np
        import soundfile as sf

        audio, rate = sf.read(audio_path, dtype="float32", always_2d=True)
        if rate != 16000 or audio.shape[1] != 1:
            raise ValueError("Pilot requires prepared 16 kHz mono audio")
        audio = audio[:, 0]
        duration = len(audio) / rate
        if not 0.1 <= duration <= 30:
            raise ValueError("Pilot accepts 0.1–30 seconds per recording")
        if not np.isfinite(audio).all() or float(np.max(np.abs(audio))) < 1e-5:
            raise ValueError("Nonfinite or silent input")
        inputs = self.extractor(audio, sampling_rate=rate, return_tensors="pt")
        with self.torch.inference_mode():
            logits = self.model(**inputs).logits[0]
            peaks, ids = logits.float().softmax(-1).max(-1)
        spans = collapse_ctc(ids.tolist(), peaks.tolist(), self.vocabulary,
            blank_id=self.blank_id, special_ids=self.special_ids,
            sample_rate=rate, frame_stride=self.frame_stride,
            receptive_field=self.receptive_field, duration=duration)
        return {"duration_seconds": round(duration, 4),
                "predicted_phones": [span["phone"] for span in spans],
                "spans": spans,
                "timing_status": "approximate_ctc_frame_spans_not_verified_boundaries",
                "probability_status": "uncalibrated_not_pronunciation_accuracy",
                "articulation_status": "not_measured",
                "reference_transcript_used_by_model": False}
