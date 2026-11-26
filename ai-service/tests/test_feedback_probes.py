from app.feedback_probes import phones_in_window, probe_sequence, summarize_probe, token_edit_distance


def test_final_s_does_not_hide_missing_internal_s():
    assert probe_sequence(["m", "ɪ", "t", "eɪ", "k", "s"],
                          "s_immediately_before_first_t") == "s_absent_before_t"
    assert probe_sequence(["m", "ɪ", "s", "t", "eɪ", "k", "s"],
                          "s_immediately_before_first_t") == "s_present_before_t"


def test_earlier_s_does_not_hide_missing_s_next_to_t():
    assert probe_sequence(["k", "ə", "n", "s", "ɪ", "t", "ə", "n", "t"],
                          "s_immediately_before_first_t") == "s_absent_before_t"


def test_missing_anchor_is_unresolved_not_an_error():
    assert probe_sequence(["m", "ɪ", "s"], "s_immediately_before_first_t") is None
    assert probe_sequence(["t", "s"], "s_immediately_before_first_t") is None


def test_context_disagreement_does_not_become_agreement():
    result = summarize_probe({"parent": ["ʃ", "oʊ"], "crop": ["s", "oʊ"]},
                             "first_s_or_sh", "s", "ʃ")
    assert result["status"] == "context_sensitive_or_unresolved"


def test_crop_timestamps_are_translated_to_parent_coordinates():
    prediction = {"spans": [{"phone": "s", "start_seconds": 0.3, "end_seconds": 0.5},
                            {"phone": "z", "start_seconds": 0.7, "end_seconds": 0.9}]}
    assert phones_in_window(prediction, [10.35, 10.65], offset=10) == ["s"]


def test_edit_distance_uses_phone_tokens_not_ipa_characters():
    assert token_edit_distance(["dʒ", "ɪ"], ["ʒ", "ɪ"]) == 1
    assert token_edit_distance([], ["t", "s"]) == 2


def test_cluster_order_is_preserved():
    assert probe_sequence(["ɪ", "m", "p", "r", "uː", "v", "m", "ə", "n", "t", "s"],
                          "last_two_s_t_order") == "ts"
