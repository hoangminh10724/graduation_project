"""Test CTC semantics that affect diagnostic results, without a model download."""
import pytest
from app.phoneme_recognition import collapse_ctc, convolution_geometry


def decode(ids):
    return collapse_ctc(ids, [0.8] * len(ids), {0: "<pad>", 1: "s", 2: "ʃ", 3: "z"},
                        blank_id=0, special_ids={0}, sample_rate=16000,
                        frame_stride=320, receptive_field=400, duration=1.0)


def test_blank_separates_repeated_sounds():
    spans = decode([0, 1, 1, 0, 1, 2])
    assert [span["phone"] for span in spans] == ["s", "s", "ʃ"]
    assert spans[0]["start_seconds"] == 0.02
    assert spans[0]["end_seconds"] == 0.065
    assert spans[1]["start_seconds"] == 0.08


def test_newly_supported_z_is_still_preserved_as_the_observed_label():
    span = decode([3])[0]
    assert span["phone"] == "z"
    assert span["target_arpabet"] == 'Z'
    assert span["in_target_inventory"] is True

def test_opaque_phone_is_preserved_without_an_english_mapping():
    span=collapse_ctc([1],[.8],{0:'<pad>',1:'i5'},blank_id=0,special_ids={0},sample_rate=16000,frame_stride=320,receptive_field=400,duration=1)[0]
    assert span['phone']=='i5' and span['target_arpabet'] is None
    assert span['in_target_inventory'] is False


def test_all_blank_ctc_prediction_has_no_phones():
    assert decode([0, 0, 0]) == []


def test_convolution_timing_matches_model_configuration():
    assert convolution_geometry([10, 3, 3, 3, 3, 2, 2], [5, 2, 2, 2, 2, 2, 2]) == (400, 320)


def test_misaligned_probability_array_fails():
    with pytest.raises(ValueError):
        collapse_ctc([1], [], {}, blank_id=0, special_ids={0}, sample_rate=16000,
                     frame_stride=320, receptive_field=400, duration=1)
