"""Ten-target pronunciation preview with generic articulation references."""
from functools import lru_cache
from typing import Literal
import io
import json
import math
import os
from pathlib import Path
import struct
from tempfile import NamedTemporaryFile
from threading import Lock
import wave
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

ROOT = Path(__file__).resolve().parents[2]
ASSETS = Path(__file__).resolve().parent / "demo_static"
MAX_BYTES = 2 * 1024 * 1024
from .sound_catalog import GUIDES, PROMPTS, PRIMARY_TARGETS, SOURCES, practice_cue
from .sound_matching import match_sound
SOUNDS = set(GUIDES)
BUILD = 'american-sounds-v1'
EXAMPLES = {
    "comparison": {"parent": "P4_12", "word": "comparison", "target": "s"},
    "shows": {"parent": "P4_12", "word": "show", "target": "ʃ"},
    "mistakes": {"parent": "P5_15", "word": "mistakes", "target": "s"},
    "improvements": {"parent": "P5_15", "word": "improvements", "target": "s"},
}


def preview_result(target, *, mode="live_audio", status="uncertain", predicted=None,
                   raw=None, message="No reliable sound comparison yet.", reasons=None, details=None, practice_cue=None,
                   articulation_feedback=None, diagnosis=None):
    return {"mode": mode, "status": status, "target_phone": target,
            "predicted_phone": predicted, "raw_phones": raw or [], "message": message,
            "reasons": reasons or [], "score": None, "audio_url": None,
            "teacher_feedback": None, "details": details or {}, "practice_cue": practice_cue,
            "articulation_feedback": articulation_feedback, "diagnosis": diagnosis}


def validate_wav(payload):
    """Validate before model loading; no quiet/invalid recording becomes a grade."""
    if len(payload) > MAX_BYTES:
        raise HTTPException(413, "Recording is too large. Use a short word.")
    try:
        with wave.open(io.BytesIO(payload), "rb") as stream:
            if (stream.getnchannels(), stream.getsampwidth(), stream.getframerate(), stream.getcomptype()) != (1, 2, 16000, "NONE"):
                raise HTTPException(400, "Use mono 16 kHz PCM-16 WAV. The demo page converts recordings for you.")
            frames = stream.getnframes()
            duration = frames / 16000
            if not 0.25 <= duration <= 4:
                raise HTTPException(400, "Select one complete word lasting 0.25 to 4 seconds.")
            pcm = stream.readframes(frames)
            if len(pcm) != frames * 2:
                raise HTTPException(400, "The WAV recording is incomplete.")
    except (wave.Error, EOFError) as exc:
        raise HTTPException(400, "Cannot read this WAV. Record or prepare the audio again.") from exc
    values = [item[0] / 32768 for item in struct.iter_unpack("<h", pcm)]
    rms = math.sqrt(sum(x * x for x in values) / len(values))
    clipped = sum(abs(x) >= 0.99 for x in values) / len(values)
    issues = []
    if rms < 0.003:
        issues.append("Audio is too quiet or silent. Move closer and try again.")
    if clipped > 0.01:
        issues.append("Audio is distorted by clipping. Lower the recording level and try again.")
    return {"duration_seconds": round(duration, 4), "rms": round(rms, 6),
            "clipping_fraction": round(clipped, 6)}, issues


def interpret_live(prediction, prompt, quality, input_scope="context"):
    result = match_sound(prediction, prompt, input_scope)
    details = result["details"]
    if (input_scope == "context" and details.get("candidate_anchor_count") == 1
            and result["predicted"] != prompt["target_phone"] and not details.get("accepted_variant")
            and details.get("unresolved_reason") not in {"notation_or_length", "stress_not_assessed", "accent_or_notation"}):
        # A single matching sequence of nearby phones does not identify a word.
        details["word_location_unverified"] = True
        result["practice_cue"] = result["articulation_feedback"] = None
        result["message"] = f"Listen for “{prompt['word']}” and select the complete word before comparing sounds."
        result["reasons"] = ["The candidate may belong to another word in this phrase."]
    result["details"]["audio_quality"] = quality
    response = preview_result(prompt["target_phone"], **result)
    from .sound_diagnosis import sound_diagnosis
    response["diagnosis"] = sound_diagnosis(response, prompt)
    return response


class DemoService:
    def __init__(self, recognizer_factory=None):
        self._recognizer_factory = recognizer_factory
        self._recognizer = None
        self._lock = Lock()
        self._state_lock = Lock()
        self._phase = "idle"
        self._completed_inferences = 0
        self._last_finished = None

    def status(self):
        with self._state_lock:
            return {"build": BUILD, "feedback_revision": "american-contrasts-1", "model_loaded": self._recognizer is not None,
                    "phase": self._phase, "completed_inferences": self._completed_inferences,
                    "last_finished_utc": self._last_finished, "training_running": False}

    def _phase_is(self, phase):
        with self._state_lock:
            self._phase = phase

    def analyze(self, payload, prompt_id, input_scope="context"):
        if prompt_id not in PROMPTS:
            raise HTTPException(400, "Choose a supported demo word.")
        return self.analyze_prompt(payload, PROMPTS[prompt_id], input_scope)

    def analyze_prompt(self, payload, prompt, input_scope):
        if input_scope not in {"word", "context"}:
            raise HTTPException(400, "Choose word or context input mode.")
        quality, issues = validate_wav(payload)
        if issues:
            result = preview_result(prompt["target_phone"], message="Please try another recording.",
                                    reasons=issues, details={"audio_quality": quality})
            from .sound_diagnosis import sound_diagnosis
            result["diagnosis"] = sound_diagnosis(result, prompt)
            return result
        # One inference at a time bounds CPU/model memory and protects lazy loading.
        with self._lock:
            self._phase_is("loading_model" if self._recognizer is None else "inference")
            if self._recognizer is None:
                if self._recognizer_factory:
                    self._recognizer = self._recognizer_factory()
                else:
                    from .phoneme_recognition import LocalPhonemeRecognizer
                    model_dir = Path(os.environ.get("WORDSPEAK_PHONEME_MODEL", ROOT / "data/models/phoneme-recognition"))
                    try:
                        self._recognizer = LocalPhonemeRecognizer(model_dir, threads=4)
                    except (ImportError, OSError, ValueError, RuntimeError) as exc:
                        self._phase_is("idle")
                        raise HTTPException(503, "The local speech model is unavailable. See the demo setup instructions.") from exc
            self._phase_is("inference")
            temporary = None
            try:
                with NamedTemporaryFile(suffix=".wav", delete=False) as file:
                    temporary = Path(file.name)
                    file.write(payload)
                try:
                    prediction = self._recognizer.predict(temporary)
                    with self._state_lock:
                        self._completed_inferences += 1
                        self._last_finished = datetime.now(timezone.utc).isoformat()
                except (OSError, ValueError, RuntimeError) as exc:
                    raise HTTPException(503, "Local speech analysis failed. Try again or check the model setup.") from exc
            finally:
                self._phase_is("idle")
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
        return interpret_live(prediction, prompt, quality, input_scope)


@lru_cache(maxsize=1)
def get_demo_service():
    return DemoService()


def load_example(example_id):
    if example_id not in EXAMPLES:
        raise HTTPException(404, "Unknown development example.")
    definition = EXAMPLES[example_id]
    comparisons_path = ROOT / "data/results/teacher_feedback_investigation/comparisons.jsonl"
    if not comparisons_path.is_file():
        raise HTTPException(404, "Run the teacher-feedback investigation to enable these examples.")
    rows = [json.loads(line) for line in comparisons_path.read_text(encoding="utf-8").splitlines()]
    matches = [r for r in rows if r["parent_id"] == definition["parent"] and r["word"] == definition["word"]]
    if len(matches) != 1:
        raise HTTPException(404, "This example does not have a unique investigation passage.")
    row = matches[0]
    audio = (ROOT / row["audio_path"]).resolve()
    # Dataset records are local inputs, but do not let a changed record expose
    # arbitrary files through the audio endpoint.
    if not audio.is_relative_to((ROOT / "data/annotations").resolve()) or not audio.is_file():
        raise HTTPException(404, "Example audio is unavailable.")
    comment = None
    for relative in ["data/annotations/user_feedback_20261115/candidate_annotations.jsonl",
                     "data/annotations/teacher_feedback_batch_02/prepared/candidate_annotations.jsonl"]:
        path = ROOT / relative
        if path.is_file():
            for line in path.read_text(encoding="utf-8").splitlines():
                annotation = json.loads(line)
                if annotation["id"] == row["annotation_id"]:
                    comment = annotation["raw_comment"]
    probe = row["teacher_report_probe"]
    supported = (probe and probe["status"] == "model_pattern_matches_reported_error"
                 and probe["stable_across_context_and_timing_variants"])
    predicted = None
    if probe and probe["stable_across_context_and_timing_variants"]:
        observations = list(probe["observations"].values())
        if observations and len(set(observations)) == 1:
            if observations[0] in SOUNDS:
                predicted = observations[0]
            elif observations[0] == "s_present_before_t":
                predicted = "s"
    result = preview_result(definition["target"], mode="cached_development_example",
        status="possible_difference" if supported else "uncertain",
        predicted=predicted,
        raw=row["variants"]["parent_pad_0.00"],
        message=("The stored model pattern matches the error the teacher reported."
                 if supported else "The model and teacher disagree here, or the word window is unresolved."),
        reasons=["Previously computed development example; no fresh inference is being claimed.",
                 "The passage may include neighboring words. Its timings are approximate."],
        details={"probe": probe, "parent_recording": row["parent_id"],
                 "word": row["word"], "approximate_word_span": row["ASR_word_span"],
                 "classification_accuracy": None})
    result["audio_url"] = f"/demo/examples/{example_id}/audio"
    result["teacher_feedback"] = comment
    if supported:
        result["practice_cue"] = practice_cue(predicted, definition["target"])
        from .sound_catalog import articulation_feedback
        result["articulation_feedback"] = articulation_feedback(predicted, definition["target"])
    if definition["target"] in GUIDES:
        from .sound_diagnosis import sound_diagnosis
        result["diagnosis"] = sound_diagnosis(result, {"target_phone": definition["target"],
            "word": definition["word"], "family": GUIDES[definition["target"]]["family"]})
    return result, audio


router = APIRouter(prefix="/demo", tags=["experimental pronunciation demo"])


@router.get("")
def demo_page():
    return FileResponse(ASSETS / "index.html", media_type="text/html")


@router.get("/review")
def review_page():
    return FileResponse(ASSETS / "account-review.html", media_type="text/html")


@router.get("/config")
def demo_config():
    from .teaching_guides import teaching_config
    from .sound_catalog import reference_profile
    from .sound_diagnosis import EXAMPLES as PHONE_EXAMPLES
    from .english_inventory import ACCENT, MONOPHTHONGS, DIPHTHONGS, CONSONANTS
    examples = []
    for key, item in EXAMPLES.items():
        try:
            load_example(key)
            available = True
        except HTTPException:
            available = False
        examples.append({"id": key, "word": item["word"], "available": available})
    return {"account_review_enabled": os.environ.get("WORDSPEAK_ACCOUNT_REVIEW") == "1", "build": BUILD, "feedback_revision": "american-contrasts-1",
            "reference_revision": "american-references-1", 'accent':ACCENT,
            'inventory_counts':{'core':len(PRIMARY_TARGETS),'vowels':len(MONOPHTHONGS)+len(DIPHTHONGS),'consonants':len(CONSONANTS)},
            "primary_targets": list(PRIMARY_TARGETS),
            "prompts": [{"id": key, "word": item["word"], "phrase": item["phrase"],
                         "target_phone": item["target_phone"], "family": item["family"],
                         "primary": item["primary"], 'category':item.get('category','Extra contrast practice'),
                         'focus_position':item.get('focus_position','initial'),'recognition_status':'experimental_unvalidated'} for key, item in PROMPTS.items() if key not in {'seat_long','food_long'}],
            "guides": {phone: {**guide, "sound_example": PHONE_EXAMPLES.get(phone),
                               "features": reference_profile(phone)["features"]} for phone, guide in GUIDES.items()},
            "examples": examples,
            "maximum_recording_seconds": 4, "sources": SOURCES,
            "teaching": teaching_config()}



@router.post("/analyze")
async def analyze_word(audio: UploadFile = File(...), prompt_id: str = Form(...),
                       input_scope: Literal["word", "context"] = Form("context"),
                       service: DemoService = Depends(get_demo_service)):
    try:
        payload = await audio.read(MAX_BYTES + 1)
    finally:
        await audio.close()
    return await run_in_threadpool(service.analyze, payload, prompt_id, input_scope)


@router.get("/status")
def demo_status(service: DemoService = Depends(get_demo_service)):
    return service.status()


@router.get("/examples/{example_id}")
def example_result(example_id: str):
    return load_example(example_id)[0]


@router.get("/examples/{example_id}/audio")
def example_audio(example_id: str):
    _, path = load_example(example_id)
    return FileResponse(path, media_type="audio/wav")
