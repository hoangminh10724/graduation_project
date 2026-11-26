"""Recording evidence must remain visible without manufacturing a diagnosis."""
import pytest

from app.pronunciation_demo import DemoService, PROMPTS, interpret_live
from test_pronunciation_demo import prediction, wav


def analyze(phones, prompt="she", peak=.9):
    return interpret_live(prediction(phones, peak), PROMPTS[prompt], {}, "word")


def test_s_for_sh_explains_heard_sound_and_specific_adjustment():
    result = analyze(["s", "iː"])
    diagnosis = result["diagnosis"]
    assert diagnosis["kind"] == "comparison"
    assert "/s/" in diagnosis["heard"] and "see" in diagnosis["heard"]
    assert "/ʃ/" in diagnosis["target"] and "she" in diagnosis["target"]
    assert "candidate" in diagnosis["comparison"] and "ridge" in diagnosis["comparison"]
    assert "back" in diagnosis["adjustment"]
    assert diagnosis["heard"].startswith("Possible ")
    assert diagnosis["adjustment"].startswith("If /s/ matches what you hear")
    assert diagnosis["anatomy_measured"] is False and result["score"] is None


def test_weak_candidate_still_gives_both_sides_conditionally():
    result = analyze(["s", "iː"], peak=.2)
    assert result["status"] == "uncertain"
    assert result["diagnosis"]["heard"].startswith("Possible /s/")
    assert result["diagnosis"]["adjustment"].startswith("If /s/ matches what you hear:")
    assert "not a confirmed error" in result["diagnosis"]["note"]


def test_wrong_vowel_describes_what_differs_before_giving_a_movement():
    diagnosis = analyze(["s", "ɪ", "t"], "seat")["diagnosis"]
    assert "sit" in diagnosis["heard"] and "seat" in diagnosis["target"]
    assert "more open" in diagnosis["comparison"]
    assert "Raise" in diagnosis["adjustment"]


def test_adjacent_vowel_labels_give_candidates_instead_of_disappearing():
    result = analyze(["s", "ɛ", "ɪ", "t"], "seat")
    assert result["status"] == "uncertain"
    assert result["predicted_phone"] in {"ɛ", "ɪ"}
    assert result["details"]["unresolved_reason"] == "fragmented_vowel_evidence"
    diagnosis = result["diagnosis"]
    assert "/ɛ/ → /ɪ/" in diagnosis["heard"]
    assert diagnosis["adjustment"].startswith("If ")
    assert diagnosis["alternatives"] and "recognizer instability" in diagnosis["note"]


def test_changing_target_cannot_select_the_more_convenient_vowel_candidate():
    observed = prediction(["b", "ɛ", "æ", "d"])
    observed["spans"][2]["mean_frame_peak_probability"] = .95
    bed = interpret_live(observed, PROMPTS["bed"], {}, "word")
    bad = interpret_live(observed, PROMPTS["bad"], {}, "word")
    assert bed["predicted_phone"] == bad["predicted_phone"]
    assert bed["diagnosis"]["heard"] == bad["diagnosis"]["heard"]
    assert bed["status"] == bad["status"] == "uncertain"


def test_consonant_comparison_does_not_require_a_perfectly_decoded_vowel():
    result = analyze(["s", "ɛ", "ɪ"])
    assert result["predicted_phone"] == "s"
    assert result["status"] == "possible_difference"


def test_isolated_consonant_can_receive_a_comparison():
    result = analyze(["s"])
    assert result["predicted_phone"] == "s" and result["diagnosis"]["adjustment"]


@pytest.mark.parametrize("phones", [["s", "iː", "s", "ɪ"], ["b", "ɛ", "d", "b", "æ", "d"]])
def test_multiple_words_do_not_get_a_convenient_diagnosis(phones):
    result = analyze(phones)
    assert result["status"] == "uncertain" and result["predicted_phone"] is None
    assert "Decoded sequence" in result["diagnosis"]["heard"]
    assert "trim" in result["diagnosis"]["adjustment"]


def test_vowels_separated_by_a_pause_are_not_merged():
    observed = prediction(["ɛ", "æ"])
    observed["spans"][1].update(start_seconds=.6, end_seconds=.8)
    result = interpret_live(observed, PROMPTS["bed"], {}, "word")
    assert result["predicted_phone"] is None


def test_glide_is_explained_without_fabricating_one_tongue_position():
    result = analyze(["s", "aɪ", "t"], "seat")
    assert result["status"] == "possible_difference" and result["predicted_phone"] == 'aɪ'
    assert result["diagnosis"]["kind"] == "comparison"
    assert 'aɪ' in result['diagnosis']['heard']
    assert "glide" in result["diagnosis"]["adjustment"]
    assert result['articulation_feedback']['differences'][0]['dimension']=='vowel_movement'


def test_opaque_label_is_visible_but_not_reinterpreted_as_english():
    result = analyze(["s", "i5", "t"], "seat")
    assert result["predicted_phone"] is None
    assert "i5" in result["diagnosis"]["heard"]
    assert "could not reliably locate" in result["diagnosis"]["comparison"]


def test_missing_onset_does_not_become_a_confirmed_omission():
    result = analyze(["iː"])
    assert "No initial consonant was decoded" in result["diagnosis"]["comparison"]
    assert "recognizer may have missed" in result["diagnosis"]["comparison"]
    assert result["articulation_feedback"] is None


def test_silence_gives_a_recording_diagnosis_without_loading_model():
    service = DemoService(lambda: pytest.fail("Silence must not load a model"))
    result = service.analyze(wav([0] * 8000), "she", "word")
    assert result["diagnosis"]["kind"] == "audio_quality"
    assert "No pronunciation conclusion" in result["diagnosis"]["comparison"]
    assert result["predicted_phone"] is None


def test_length_notation_does_not_become_a_mouth_or_duration_error():
    result = analyze(["s", "i", "t"], "seat_long")
    diagnosis = result["diagnosis"]
    assert "same illustrated" in diagnosis["comparison"]
    assert "length has not been established" in diagnosis["comparison"]
    assert "No category-level adjustment" in diagnosis["adjustment"]


@pytest.mark.parametrize("peak", [.2, .9])
def test_bed_vowel_notation_is_not_treated_as_a_measured_jaw_error(peak):
    result = analyze(["b", "e", "d"], "bed", peak)
    assert "transcription conventions" in result["diagnosis"]["comparison"]
    assert "No category-level adjustment" in result["diagnosis"]["adjustment"]
    assert "Lower" not in result["diagnosis"]["adjustment"]
