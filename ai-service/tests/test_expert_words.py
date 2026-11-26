"""Check warning denominators without treating a model abstention as a correct answer."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from evaluate_expert_words import summarize


def test_warning_denominators():
    cases = [
        ("a", "difference", "possible_difference", "s", "s"),
        ("a", "acceptable", "possible_difference", "s", ""),
        ("b", "difference", "uncertain", None, "s"),
        ("b", "difference", "possible_difference", "t", "s"),
        ("c", "unclear", "possible_difference", "s", ""),
    ]
    rows = [dict(speaker=s, verdict=v, status=o, predicted=p, heard_phone=h) for s,v,o,p,h in cases]
    result = summarize(rows)
    assert result["warning_precision"] == result["warning_recall"] == 2 / 3
    assert result["specific_warning_precision"] == 1 / 3
    assert result["decision_coverage"] == 3 / 4
    assert result["counts"]["false_warnings"] == result["counts"]["missed_differences"] == 1
    assert summarize(rows[-1:])["warning_precision"] is None
