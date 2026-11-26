"""Exploratory positional probes, not calibrated pronunciation judgments.

Teacher references are sparse word-level reports. Probe agreement must never be
reported as ten-class phoneme accuracy or measured articulatory correctness.
"""


def phones_in_window(prediction, word_span, *, offset=0.0, padding=0.0):
    """Select approximate CTC events by midpoint within an ASR word window."""
    start, end = word_span
    return [span["phone"] for span in prediction["spans"]
            if start - padding <= offset + (span["start_seconds"] + span["end_seconds"]) / 2 <= end + padding]


def token_edit_distance(left, right):
    previous = list(range(len(right) + 1))
    for i, item in enumerate(left, 1):
        current = [i]
        for j, other in enumerate(right, 1):
            current.append(min(current[-1] + 1, previous[j] + 1,
                               previous[j - 1] + (item != other)))
        previous = current
    return previous[-1]


def probe_sequence(phones, kind):
    if len(phones) < 2:
        return None
    if kind == "first_s_or_sh":
        return next((phone for phone in phones if phone in {"s", "ʃ"}), None)
    if kind == "last_s_or_z":
        return next((phone for phone in reversed(phones) if phone in {"s", "z"}), None)
    if kind == "s_immediately_before_first_t":
        if "t" not in phones:
            return None
        index = phones.index("t")
        if index == 0:
            return None  # The word onset may have been missed by the ASR window.
        return "s_present_before_t" if phones[index - 1] == "s" else "s_absent_before_t"
    if kind == "last_two_s_t_order":
        cluster = [phone for phone in phones if phone in {"s", "t"}]
        if len(cluster) < 2 or set(cluster[-2:]) != {"s", "t"}:
            return None
        return "".join(cluster[-2:])
    raise ValueError(f"Unknown probe: {kind}")


def summarize_probe(variants, kind, reported, expected):
    observations = {name: probe_sequence(phones, kind) for name, phones in variants.items()}
    values = list(observations.values())
    stable = bool(values) and None not in values and len(set(values)) == 1
    if not stable:
        status = "context_sensitive_or_unresolved"
    elif values[0] == reported:
        status = "model_pattern_matches_reported_error"
    elif values[0] == expected:
        status = "model_pattern_matches_expected_form_instead"
    else:
        status = "stable_other_model_pattern"
    return {"status": status, "stable_across_context_and_timing_variants": stable,
            "observations": observations,
            "meaning": "development_probe_consistency_not_correctness_or_accuracy"}
