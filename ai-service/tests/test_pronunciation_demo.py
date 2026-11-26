import io
import json
from pathlib import Path
import struct
import wave

from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.pronunciation_demo import DemoService, get_demo_service, interpret_live, PROMPTS


def wav(samples=None, rate=16000):
    samples = samples if samples is not None else [1000, -1000] * 4000
    output = io.BytesIO()
    with wave.open(output, "wb") as stream:
        stream.setnchannels(1); stream.setsampwidth(2); stream.setframerate(rate)
        stream.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    return output.getvalue()


def prediction(phones, peak=0.9):
    return {"predicted_phones": phones,
            "spans": [{"phone": p, "start_seconds": i * 0.15, "end_seconds": i * 0.15 + 0.12,
                       "mean_frame_peak_probability": peak} for i, p in enumerate(phones)],
            "timing_status": "approximate_ctc_frame_spans_not_verified_boundaries"}


class FakeRecognizer:
    def __init__(self):
        self.seen_paths = []

    def predict(self, path):
        self.seen_paths.append(Path(path))
        assert Path(path).is_file()
        return prediction(["s", "iː"])


def test_selected_prompt_does_not_fill_predicted_sound():
    result = interpret_live(prediction(["s", "iː"]), PROMPTS["she"], {})
    assert result["status"] == "possible_difference"
    assert result["predicted_phone"] == "s" and result["target_phone"] == "ʃ"
    assert result["score"] is None and result["practice_cue"] is None
    assert result["diagnosis"]["kind"] == "unverified_word_location"
    assert result["articulation_feedback"] is None
    assert "Select the complete word" in result["diagnosis"]["adjustment"]


def test_final_z_does_not_replace_initial_sh_in_shows():
    result = interpret_live(prediction(["ʃ", "oʊ", "z"]), PROMPTS["shows"], {})
    assert result["predicted_phone"] == "ʃ"
    assert result["status"] == "model_match"


def test_multiple_word_anchors_abstain_instead_of_picking_any_s():
    result = interpret_live(prediction(["s", "iː", "n", "ʃ", "iː"]), PROMPTS["see"], {})
    assert result["status"] == "uncertain" and result["predicted_phone"] is None


def test_surrounding_speech_does_not_fill_the_expected_consonant():
    result = interpret_live(prediction(["ɑː", "f", "ə", "n", "s", "oʊ", "z"]), PROMPTS["shows"], {})
    assert result["predicted_phone"] == "s" and result["target_phone"] == "ʃ"
    assert result["status"] == "possible_difference"


def test_unrelated_s_before_the_anchor_does_not_replace_sh():
    result = interpret_live(prediction(["s", "ʃ", "oʊ", "z"]), PROMPTS["shows"], {})
    assert result["predicted_phone"] == "ʃ"


def test_wrong_vowel_anchor_abstains():
    assert interpret_live(prediction(["s", "æ"]), PROMPTS["see"], {})["status"] == "uncertain"


def test_weak_model_evidence_is_not_a_pronunciation_grade():
    result = interpret_live(prediction(["s", "iː"], peak=0.2), PROMPTS["see"], {})
    assert result["status"] == "uncertain" and result["score"] is None


def test_silence_does_not_load_model():
    service = DemoService(lambda: pytest.fail("Model should not load for silence"))
    assert service.analyze(wav([0] * 8000), "see")["status"] == "uncertain"


def test_invalid_audio_and_unknown_prompt_do_not_load_model():
    service = DemoService(lambda: pytest.fail("Invalid request loaded model"))
    client = TestClient(app)
    app.dependency_overrides[get_demo_service] = lambda: service
    try:
        assert client.post("/demo/analyze", data={"prompt_id": "see"}, files={"audio": ("x.wav", b"RIFF")}).status_code == 400
        assert client.post("/demo/analyze", data={"prompt_id": "other"}, files={"audio": ("x.wav", wav())}).status_code == 400
        assert client.post("/demo/analyze", data={"prompt_id": "see"}, files={"audio": ("x.wav", wav(rate=8000))}).status_code == 400
    finally:
        app.dependency_overrides.clear()


def test_live_api_uses_recording_and_deletes_temporary_file():
    recognizer = FakeRecognizer()
    service = DemoService(lambda: recognizer)
    client = TestClient(app)
    app.dependency_overrides[get_demo_service] = lambda: service
    try:
        response = client.post("/demo/analyze", data={"prompt_id": "she"}, files={"audio": ("word.wav", wav(), "audio/wav")})
        assert response.status_code == 200
        result = response.json()
        assert result["mode"] == "live_audio" and result["predicted_phone"] == "s"
        assert result["status"] == "possible_difference"
        assert all(not path.exists() for path in recognizer.seen_paths)
    finally:
        app.dependency_overrides.clear()


def test_demo_page_assets_and_reference_config():
    client = TestClient(app)
    page = client.get("/demo")
    assert page.status_code == 200
    assert page.headers["cache-control"] == "no-store"
    assert client.get("/demo/assets/audio.mjs?v=mic-playback-3").headers["cache-control"] == "no-store"
    config = client.get("/demo/config").json()
    assert config["reference_revision"] == "american-references-1"
    assert "sit" in config["guides"]["ɪ"]["sound_example"]
    assert "seat" in config["guides"]["iː"]["sound_example"]
    assert config["guides"]["ɪ"]["features"] != config["guides"]["iː"]["features"]
    from app.phoneme_recognition import TARGET_PHONES
    assert set(config["primary_targets"]) == set(TARGET_PHONES)
    assert {p["target_phone"] for p in config["prompts"] if p["primary"]} == set(TARGET_PHONES)
    assert all(client.get(guide["svg_url"]).status_code == 200 for guide in config["guides"].values())
    assert client.get("/demo/examples/not-an-example").status_code == 404


def test_cached_examples_keep_conflict_and_uncertainty_visible():
    # Integration check only when the local investigation artifacts are available.
    from app.pronunciation_demo import ROOT
    if not (ROOT / "data/results/teacher_feedback_investigation/comparisons.jsonl").is_file():
        pytest.skip("Local dataset files are not part of the repository")
    client = TestClient(app)
    show = client.get("/demo/examples/shows").json()
    assert show["mode"] == "cached_development_example" and show["predicted_phone"] == "s"
    assert show["status"] == "possible_difference"
    for key in ["mistakes", "improvements"]:
        result = client.get(f"/demo/examples/{key}").json()
        assert result["status"] == "uncertain" and result["score"] is None


def test_same_observed_vowel_is_not_replaced_by_the_selected_target():
    observed = prediction(["s", "ɪ", "t"])
    seat = interpret_live(observed, PROMPTS["seat"], {})
    sit = interpret_live(observed, PROMPTS["sit"], {})
    assert seat["predicted_phone"] == sit["predicted_phone"] == "ɪ"
    assert seat["status"] == "possible_difference" and sit["status"] == "model_match"


def test_bed_bad_share_consonant_anchors_but_not_the_predicted_vowel():
    observed = prediction(["b", "æ", "d"])
    assert interpret_live(observed, PROMPTS["bed"], {})["predicted_phone"] == "æ"
    assert interpret_live(observed, PROMPTS["bad"], {})["status"] == "model_match"


def test_food_can_report_a_different_back_vowel():
    result = interpret_live(prediction(["f", "ʊ", "d"]), PROMPTS["food"], {})
    assert result["predicted_phone"] == "ʊ" and result["status"] == "possible_difference"


@pytest.mark.parametrize("prompt,observed,expected", [
    ("pen", ["f", "ɛ", "n"], "f"), ("ten", ["d", "ɛ", "n"], "d"),
    ("key", ["g", "iː"], "ɡ")])
def test_stops_have_competing_predictions(prompt, observed, expected):
    result = interpret_live(prediction(observed), PROMPTS[prompt], {})
    assert result["predicted_phone"] == expected and result["status"] == "possible_difference"


def test_unmarked_vowel_length_is_not_silently_certified():
    result = interpret_live(prediction(["s", "i", "t"]), PROMPTS["seat_long"], {})
    assert result["status"] == "uncertain" and result["predicted_phone"] == "i"
    assert result["details"]["vowel_duration_assessed"] is False


def test_opaque_multilingual_label_is_not_forced_into_english():
    result = interpret_live(prediction(["s", "i5", "t"]), PROMPTS["seat"], {})
    assert result["status"] == "uncertain" and result["predicted_phone"] is None
    assert "i5" in result["raw_phones"]


def test_brief_ctc_emission_is_not_used_as_vowel_duration():
    observed = prediction(["s", "iː", "t"])
    observed["spans"][1]["end_seconds"] = observed["spans"][1]["start_seconds"] + 0.025
    result = interpret_live(observed, PROMPTS["seat"], {})
    assert result["status"] == "model_match"
    assert result["details"]["vowel_duration_assessed"] is False


def test_repeated_vowel_frame_does_not_choose_the_convenient_occurrence():
    result = interpret_live(prediction(["b", "ɛ", "d", "b", "æ", "d"]), PROMPTS["bed"], {})
    assert result["status"] == "uncertain" and result["predicted_phone"] is None


def test_model_status_distinguishes_idle_from_inference():
    service = None
    class CheckingRecognizer:
        def predict(self, path):
            assert service.status()["phase"] == "inference"
            return prediction(["s", "iː"])
    service = DemoService(CheckingRecognizer)
    assert service.status()["model_loaded"] is False
    service.analyze(wav(), "see")
    state = service.status()
    assert state["model_loaded"] is True and state["phase"] == "idle"
    assert state["completed_inferences"] == 1 and state["training_running"] is False


def test_practice_cue_compares_references_without_claiming_anatomy():
    result = interpret_live(prediction(["s", "ɪ", "t"]), PROMPTS["seat"], {}, "word")
    assert "higher" in result["practice_cue"]
    assert "reference" in result["practice_cue"]
    assert result["score"] is None


def test_uncertain_notation_does_not_produce_a_correction():
    result = interpret_live(prediction(["s", "i", "t"]), PROMPTS["seat_long"], {})
    assert result["status"] == "uncertain" and result["practice_cue"] is None


@pytest.mark.parametrize("prompt,phones,heard", [
    ("seat", ["s", "ɪ", "k"], "ɪ"),
    ("sit", ["s", "iː", "t"], "i"),
    ("bed", ["p", "æ", "t"], "æ"),
    ("bad", ["b", "ɛ", "t"], "ɛ"),
    ("food", ["v", "ʊ", "t"], "ʊ"),
    ("pen", ["f", "æ", "n"], "f"),
    ("ten", ["d", "ɪ", "n"], "d"),
    ("key", ["g", "æ"], "ɡ"),
    ("see", ["ʃ", "æ"], "ʃ"),
    ("she", ["s", "ʊ"], "s"),
])
def test_word_mode_can_identify_substitution_with_wrong_neighbors(prompt, phones, heard):
    result = interpret_live(prediction(phones), PROMPTS[prompt], {}, "word")
    assert result["predicted_phone"] == heard
    assert result["status"] == "possible_difference"
    feedback = result["articulation_feedback"]
    assert feedback["anatomy_measured"] is False
    assert feedback["differences"]
    assert all(item["adjustment"] for item in feedback["differences"])


def test_word_mode_does_not_choose_a_target_from_a_phrase():
    result = interpret_live(prediction(["s", "eɪ", "b", "æ", "d", "n", "aʊ"]), PROMPTS["bed"], {}, "word")
    assert result["predicted_phone"] is None
    assert result["status"] == "uncertain"
    assert "one vowel nucleus" in result["message"]


def test_word_mode_does_not_invent_a_missing_consonant():
    result = interpret_live(prediction(["iː"]), PROMPTS["see"], {}, "word")
    assert result["predicted_phone"] is None
    assert "No starting consonant" in result["message"]
    assert result["articulation_feedback"] is None


def test_same_word_audio_keeps_same_observed_vowel_under_other_target():
    audio = prediction(["p", "æ", "t"])
    bed = interpret_live(audio, PROMPTS["bed"], {}, "word")
    bad = interpret_live(audio, PROMPTS["bad"], {}, "word")
    assert bed["predicted_phone"] == bad["predicted_phone"] == "æ"
    assert bed["status"] == "possible_difference" and bad["status"] == "model_match"


def test_weak_candidate_is_visible_but_not_a_confirmed_error():
    result = interpret_live(prediction(["s", "iː"], peak=.2), PROMPTS["she"], {}, "word")
    assert result["status"] == "uncertain" and result["predicted_phone"] == "s"
    assert result["articulation_feedback"]["evidence"] == "weak_model_hypothesis"


@pytest.mark.parametrize("phones,prompt,reason", [
    (["s", "iː"], "she", "weak_acoustic_evidence"),
    (["s", "i5", "t"], "seat", "unsupported_sound_category"),
])
def test_phrase_location_precedes_physical_feedback(phones, prompt, reason):
    result = interpret_live(prediction(phones, peak=.2), PROMPTS[prompt], {}, "context")
    assert result["status"] == "uncertain" and result["details"]["unresolved_reason"] == reason
    assert result["diagnosis"]["kind"] == "unverified_word_location"
    assert result["practice_cue"] is None and result["articulation_feedback"] is None
    assert "/None/" not in result["diagnosis"]["heard"]
    assert result["practice_cue"] is None and result["score"] is None


def test_feedback_distinguishes_voicing_from_tongue_place():
    result = interpret_live(prediction(["d", "ɛ", "n"]), PROMPTS["ten"], {}, "word")
    differences = result["articulation_feedback"]["differences"]
    assert [d["dimension"] for d in differences] == ["voicing"]
    assert differences[0]["target_reference"] == "off"


def test_open_front_vowel_and_dental_lisp_have_real_contrast_guides():
    vowel = interpret_live(prediction(["b", "a", "d"]), PROMPTS["bed"], {}, "word")
    assert vowel["predicted_phone"] == "a" and vowel["status"] == "possible_difference"
    dental = interpret_live(prediction(["θ", "iː"]), PROMPTS["see"], {}, "word")
    assert dental["predicted_phone"] == "θ"
    assert dental["articulation_feedback"]["differences"][0]["dimension"] == "place"


def test_live_api_passes_word_mode_and_rejects_unknown_scope():
    service = DemoService(FakeRecognizer)
    client = TestClient(app)
    app.dependency_overrides[get_demo_service] = lambda: service
    try:
        response = client.post("/demo/analyze", data={"prompt_id": "she", "input_scope": "word"}, files={"audio": ("word.wav", wav(), "audio/wav")})
        result = response.json()
        assert result["details"]["input_scope"] == "word"
        assert result["articulation_feedback"]["differences"]
        assert client.post("/demo/analyze", data={"prompt_id": "she", "input_scope": "guess"}, files={"audio": ("word.wav", wav())}).status_code == 422
    finally:
        app.dependency_overrides.clear()
