import pytest

from engine.verify.release_gate import (
    GateError, check_qa_floor, check_release_gates,
)

REL = {"verification_gate_passed": True, "qa_gate_passed": True}
FLOOR = {"standard_min_tests": 2, "complex_min_tests": 3,
         "required_flow_coverage": 1.0}


def t(req, text="displays the message"):
    return {"requirement_id": req, "assertions": [text]}


def test_release_requires_both_gates():
    assert check_release_gates(REL)
    with pytest.raises(GateError):
        check_release_gates({**REL, "qa_gate_passed": False})
    with pytest.raises(GateError):
        check_release_gates({**REL, "verification_gate_passed": False})


def test_qa_floor_pass():
    res = check_qa_floor([t("F1"), t("F2")], ["F1", "F2"], FLOOR)
    assert res["coverage"] == 1.0
    assert res["substantive_tests"] == 2


def test_qa_floor_uncovered_flow_fails():
    with pytest.raises(GateError):
        check_qa_floor([t("F1")], ["F1", "F2"], FLOOR)


def test_trivial_tests_do_not_count_toward_coverage():
    with pytest.raises(GateError):
        check_qa_floor(
            [t("F1"), {"requirement_id": "F2", "assertions": ["element exists"]}],
            ["F1", "F2"], FLOOR)


def test_count_below_floor_fails_even_with_full_coverage():
    with pytest.raises(GateError):
        check_qa_floor([t("F1")], ["F1"], FLOOR)


def test_logged_exemption_excludes_flow():
    # Exemption removes F2 from coverage but NOT from the count floor.
    res = check_qa_floor(
        [t("F1"), t("F1", "shows the stored message")],
        ["F1", "F2"], FLOOR, exemptions=["F2"])
    assert res["coverage"] == 1.0
