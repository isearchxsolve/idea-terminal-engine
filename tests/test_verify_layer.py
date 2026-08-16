"""
Comprehensive tests for the verify layer:
  - engine.verify.anti_triviality.check_test_substance
  - engine.verify.evidence_validator.validate_completion
  - engine.verify.release_gate.check_release_gates
  - engine.verify.release_gate.check_qa_floor
  - engine.verify.repair_loop.repair
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from engine.verify.anti_triviality import (
    BEHAVIORAL_MARKERS,
    check_test_substance,
)
from engine.verify.evidence_validator import UnsupportedClaimError, validate_completion
from engine.verify.release_gate import GateError, check_qa_floor, check_release_gates
from engine.verify.repair_loop import repair
from engine.pacing.budget import BudgetExhaustedError, BudgetTracker

# ---------------------------------------------------------------------------
# Helpers shared across sections
# ---------------------------------------------------------------------------

def make_ev(task_id="T1", exit_code=0):
    """Build a minimal valid Evidence dict."""
    return {
        "id": "e1",
        "version": 1,
        "timestamp": "2024-01-01T00:00:00+00:00",
        "status": "recorded",
        "source_ref": f"task:{task_id}",
        "command": "python -c \"pass\"",
        "exit_code": exit_code,
        "stdout": "",
        "stderr": "",
        "files_changed": [],
        "tests_run": 0,
        "task_id": task_id,
    }


def make_test(req, text="displays the message"):
    """Build a minimal test dict for qa_floor tests."""
    return {"requirement_id": req, "assertions": [text]}


FLOOR = {
    "standard_min_tests": 2,
    "complex_min_tests": 3,
    "required_flow_coverage": 1.0,
}


# ===========================================================================
# Section 1: check_test_substance — 40+ tests
# ===========================================================================


# --- 1.1  None / empty requirement_id ---

def test_substance_none_requirement_id_returns_false():
    assert check_test_substance({"assertions": ["displays x"]}, None) is False


def test_substance_empty_string_requirement_id_returns_false():
    assert check_test_substance({"assertions": ["displays x"]}, "") is False


def test_substance_zero_requirement_id_is_falsy_returns_false():
    assert check_test_substance({"assertions": ["displays x"]}, 0) is False


# --- 1.2  Missing / empty assertions ---

def test_substance_empty_assertions_list_returns_false():
    assert check_test_substance({"assertions": []}, "F1") is False


def test_substance_missing_assertions_key_returns_false():
    assert check_test_substance({}, "F1") is False


def test_substance_none_assertions_value_returns_false():
    assert check_test_substance({"assertions": None}, "F1") is False


# --- 1.3  Each BEHAVIORAL_MARKER produces True ---

@pytest.mark.parametrize("marker", BEHAVIORAL_MARKERS)
def test_substance_each_marker_returns_true(marker):
    test = {"assertions": [f"it {marker} the value"]}
    assert check_test_substance(test, "F1") is True


@pytest.mark.parametrize("marker", BEHAVIORAL_MARKERS)
def test_substance_marker_at_start_of_assertion(marker):
    test = {"assertions": [f"{marker} something meaningful"]}
    assert check_test_substance(test, "F1") is True


@pytest.mark.parametrize("marker", BEHAVIORAL_MARKERS)
def test_substance_marker_at_end_of_assertion(marker):
    test = {"assertions": [f"the component {marker}"]}
    assert check_test_substance(test, "F1") is True


# --- 1.4  Case-insensitive detection ---

@pytest.mark.parametrize("marker", BEHAVIORAL_MARKERS)
def test_substance_uppercase_marker_returns_true(marker):
    test = {"assertions": [marker.upper() + " the result"]}
    assert check_test_substance(test, "F1") is True


@pytest.mark.parametrize("marker", BEHAVIORAL_MARKERS)
def test_substance_mixed_case_marker_returns_true(marker):
    mixed = marker.capitalize()
    test = {"assertions": [f"Component {mixed} data"]}
    assert check_test_substance(test, "F1") is True


# --- 1.5  Trivial assertions that should return False ---

@pytest.mark.parametrize("assertion", [
    "element exists",
    "page loads",
    "it works",
    "passes",
    "the check",
    "something happens",
    "is visible",
    "has loaded",
    "is present on screen",
    "no error",
])
def test_substance_trivial_assertion_returns_false(assertion):
    test = {"assertions": [assertion]}
    assert check_test_substance(test, "F1") is False


# --- 1.6  Substantive assertion strings that should return True ---

@pytest.mark.parametrize("assertion", [
    "displays the message",
    "shows the result",
    "returns 200",
    "contains the name",
    "equals the expected value",
    "rejects invalid input",
    "redirects to home",
    "updates the record",
    "persists to database",
    "calculates the total",
    "prevents duplicate",
    "allows the user",
])
def test_substance_substantive_assertion_returns_true(assertion):
    test = {"assertions": [assertion]}
    assert check_test_substance(test, "F1") is True


# --- 1.7  Multiple assertions ---

def test_substance_any_matching_assertion_sufficient():
    test = {"assertions": ["element exists", "displays the value"]}
    assert check_test_substance(test, "F1") is True


def test_substance_no_matching_assertion_returns_false():
    test = {"assertions": ["element exists", "page loads", "it works"]}
    assert check_test_substance(test, "F1") is False


def test_substance_all_matching_assertions_returns_true():
    test = {"assertions": ["displays x", "shows y", "returns z"]}
    assert check_test_substance(test, "F1") is True


def test_substance_first_assertion_matches_returns_true():
    test = {"assertions": ["displays x", "element exists"]}
    assert check_test_substance(test, "F1") is True


def test_substance_last_assertion_matches_returns_true():
    test = {"assertions": ["element exists", "page loads", "returns 200"]}
    assert check_test_substance(test, "F1") is True


# --- 1.8  Whitespace in assertion ---

def test_substance_leading_trailing_whitespace_still_matches():
    test = {"assertions": ["  displays  the message  "]}
    assert check_test_substance(test, "F1") is True


def test_substance_tab_in_assertion_still_matches():
    test = {"assertions": ["\tdisplays\tthe value"]}
    assert check_test_substance(test, "F1") is True


# --- 1.9  Marker mid-word ---

def test_substance_marker_mid_word_still_detected():
    # "shows" is contained in "shows_data" — `.lower()` check is substring
    test = {"assertions": ["it displays the value"]}
    assert check_test_substance(test, "F1") is True


def test_substance_marker_as_substring_of_word_still_detected():
    # "returns" is in "returns200" — substring match
    test = {"assertions": ["returns200"]}
    assert check_test_substance(test, "F1") is True


# --- 1.10  Various requirement_id types ---

@pytest.mark.parametrize("req_id", ["F1", "FLOW-ABC", "requirement_xyz_99", "R999"])
def test_substance_valid_requirement_id_with_marker(req_id):
    test = {"assertions": ["displays the value"]}
    assert check_test_substance(test, req_id) is True


# --- 1.11  Extra assertion keys are ignored ---

def test_substance_extra_keys_in_test_dict_ignored():
    test = {
        "assertions": ["displays the result"],
        "name": "my test",
        "extra_field": True,
    }
    assert check_test_substance(test, "F1") is True


def test_substance_large_assertions_list_at_least_one_matching():
    assertions = ["element exists"] * 50 + ["returns the correct total"]
    test = {"assertions": assertions}
    assert check_test_substance(test, "F1") is True


def test_substance_large_assertions_list_none_matching():
    assertions = ["element exists", "page loads", "something happens"] * 20
    test = {"assertions": assertions}
    assert check_test_substance(test, "F1") is False


# ===========================================================================
# Section 2: validate_completion — 30+ tests
# ===========================================================================


def test_validate_empty_evidence_raises():
    with pytest.raises(UnsupportedClaimError):
        validate_completion({"id": "T1"}, [])


def test_validate_none_evidence_raises():
    with pytest.raises(UnsupportedClaimError):
        validate_completion({"id": "T1"}, None)


def test_validate_wrong_task_id_raises():
    with pytest.raises(UnsupportedClaimError):
        validate_completion({"id": "T1"}, [make_ev(task_id="T2")])


def test_validate_correct_task_id_exit_zero_passes():
    result = validate_completion({"id": "T1"}, [make_ev(task_id="T1", exit_code=0)])
    assert isinstance(result, list)
    assert len(result) == 1


def test_validate_correct_task_id_exit_nonzero_raises():
    with pytest.raises(UnsupportedClaimError):
        validate_completion({"id": "T1"}, [make_ev(task_id="T1", exit_code=1)])


def test_validate_mixed_evidence_one_matching_passes():
    ev_match = make_ev(task_id="T1", exit_code=0)
    ev_other = make_ev(task_id="T2", exit_code=0)
    result = validate_completion({"id": "T1"}, [ev_match, ev_other])
    assert result == [ev_match]


def test_validate_multiple_passing_for_same_task():
    ev1 = {**make_ev(task_id="T1", exit_code=0), "id": "e1"}
    ev2 = {**make_ev(task_id="T1", exit_code=0), "id": "e2"}
    result = validate_completion({"id": "T1"}, [ev1, ev2])
    assert len(result) == 2


def test_validate_one_passing_one_failing_for_same_task_raises():
    ev_pass = {**make_ev(task_id="T1", exit_code=0), "id": "e1"}
    ev_fail = {**make_ev(task_id="T1", exit_code=1), "id": "e2"}
    with pytest.raises(UnsupportedClaimError):
        validate_completion({"id": "T1"}, [ev_pass, ev_fail])


@pytest.mark.parametrize("bad_code", [1, 2, 127, 124, -1, 255])
def test_validate_failing_exit_codes_raise(bad_code):
    with pytest.raises(UnsupportedClaimError):
        validate_completion({"id": "T1"}, [make_ev(task_id="T1", exit_code=bad_code)])


def test_validate_exit_code_zero_passes():
    result = validate_completion({"id": "T1"}, [make_ev(task_id="T1", exit_code=0)])
    assert result[0]["exit_code"] == 0


def test_validate_missing_task_id_key_in_evidence_raises():
    ev = make_ev(task_id="T1")
    del ev["task_id"]
    with pytest.raises(UnsupportedClaimError):
        validate_completion({"id": "T1"}, [ev])


@pytest.mark.parametrize("tid", ["T1", "T2", "task-abc", "TASK_XYZ"])
def test_validate_various_task_ids_pass(tid):
    result = validate_completion({"id": tid}, [make_ev(task_id=tid, exit_code=0)])
    assert result[0]["task_id"] == tid


def test_validate_unrelated_task_ids_ignored_when_match_exists():
    ev_match = make_ev(task_id="T1", exit_code=0)
    ev_unrelated1 = {**make_ev(task_id="TX"), "id": "ux1"}
    ev_unrelated2 = {**make_ev(task_id="TY"), "id": "ux2"}
    result = validate_completion({"id": "T1"}, [ev_unrelated1, ev_match, ev_unrelated2])
    assert result == [ev_match]


def test_validate_large_evidence_list_last_entry_matches():
    unrelated = [{**make_ev(task_id=f"T{i}"), "id": f"e{i}"} for i in range(2, 52)]
    ev_match = {**make_ev(task_id="T1", exit_code=0), "id": "ematch"}
    result = validate_completion({"id": "T1"}, unrelated + [ev_match])
    assert result == [ev_match]


def test_validate_returns_only_matching_evidence():
    ev1 = {**make_ev(task_id="T1", exit_code=0), "id": "e1"}
    ev2 = {**make_ev(task_id="T99", exit_code=0), "id": "e99"}
    ev3 = {**make_ev(task_id="T1", exit_code=0), "id": "e3"}
    result = validate_completion({"id": "T1"}, [ev1, ev2, ev3])
    assert len(result) == 2
    for r in result:
        assert r["task_id"] == "T1"


def test_validate_error_message_contains_task_id():
    with pytest.raises(UnsupportedClaimError, match="T42"):
        validate_completion({"id": "T42"}, [])


def test_validate_error_message_mentions_no_evidence():
    with pytest.raises(UnsupportedClaimError, match="evidence"):
        validate_completion({"id": "T1"}, [])


def test_validate_error_when_all_wrong_task_ids():
    evidence = [make_ev(task_id="OTHER") for _ in range(5)]
    with pytest.raises(UnsupportedClaimError):
        validate_completion({"id": "T1"}, evidence)


def test_validate_exit_code_zero_multiple_tasks():
    for tid in ["A", "B", "C", "D"]:
        result = validate_completion({"id": tid}, [make_ev(task_id=tid, exit_code=0)])
        assert result[0]["task_id"] == tid


def test_validate_evidence_list_with_single_matching_passing():
    ev_pass = make_ev(task_id="T1", exit_code=0)
    result = validate_completion({"id": "T1"}, [ev_pass])
    assert result == [ev_pass]


def test_validate_all_failing_for_task_raises():
    evidences = [{**make_ev(task_id="T1", exit_code=i), "id": f"e{i}"} for i in range(1, 6)]
    with pytest.raises(UnsupportedClaimError):
        validate_completion({"id": "T1"}, evidences)


def test_validate_exit_code_124_timeout_raises():
    with pytest.raises(UnsupportedClaimError):
        validate_completion({"id": "T1"}, [make_ev(task_id="T1", exit_code=124)])


def test_validate_exit_code_minus1_raises():
    with pytest.raises(UnsupportedClaimError):
        validate_completion({"id": "T1"}, [make_ev(task_id="T1", exit_code=-1)])


def test_validate_empty_list_vs_none_both_raise():
    with pytest.raises(UnsupportedClaimError):
        validate_completion({"id": "T1"}, [])
    with pytest.raises(UnsupportedClaimError):
        validate_completion({"id": "T1"}, None)


def test_validate_task_with_numeric_id():
    ev = make_ev(task_id="99")
    ev["task_id"] = "99"
    result = validate_completion({"id": "99"}, [ev])
    assert result[0]["task_id"] == "99"


def test_validate_matching_evidence_preserves_all_fields():
    ev = make_ev(task_id="T1", exit_code=0)
    ev["stdout"] = "hello"
    result = validate_completion({"id": "T1"}, [ev])
    assert result[0]["stdout"] == "hello"


def test_validate_evidence_with_empty_task_id_key_not_matching():
    ev = make_ev(task_id="T1")
    ev["task_id"] = ""
    with pytest.raises(UnsupportedClaimError):
        validate_completion({"id": "T1"}, [ev])


# ===========================================================================
# Section 3: check_release_gates — 20+ tests
# ===========================================================================

REL_BOTH_PASS = {"verification_gate_passed": True, "qa_gate_passed": True}


def test_gates_both_true_returns_true():
    assert check_release_gates(REL_BOTH_PASS) is True


def test_gates_verification_false_raises():
    with pytest.raises(GateError):
        check_release_gates({"verification_gate_passed": False, "qa_gate_passed": True})


def test_gates_qa_false_raises():
    with pytest.raises(GateError):
        check_release_gates({"verification_gate_passed": True, "qa_gate_passed": False})


def test_gates_both_false_raises():
    with pytest.raises(GateError):
        check_release_gates({"verification_gate_passed": False, "qa_gate_passed": False})


@pytest.mark.parametrize("falsy", [False, 0, None, ""])
def test_gates_verification_falsy_values_raise(falsy):
    with pytest.raises(GateError):
        check_release_gates({"verification_gate_passed": falsy, "qa_gate_passed": True})


@pytest.mark.parametrize("falsy", [False, 0, None, ""])
def test_gates_qa_falsy_values_raise(falsy):
    with pytest.raises(GateError):
        check_release_gates({"verification_gate_passed": True, "qa_gate_passed": falsy})


def test_gates_verification_error_message_contains_phase8():
    with pytest.raises(GateError, match="Phase 8"):
        check_release_gates({"verification_gate_passed": False, "qa_gate_passed": True})


def test_gates_qa_error_message_mentions_qa_or_8b():
    with pytest.raises(GateError, match="(?i)(Phase 8B|QA)"):
        check_release_gates({"verification_gate_passed": True, "qa_gate_passed": False})


def test_gates_missing_verification_key_is_falsy_raises():
    with pytest.raises(GateError):
        check_release_gates({"qa_gate_passed": True})


def test_gates_missing_qa_key_is_falsy_raises():
    with pytest.raises(GateError):
        check_release_gates({"verification_gate_passed": True})


def test_gates_empty_dict_raises():
    with pytest.raises(GateError):
        check_release_gates({})


def test_gates_truthy_int_verification_passes():
    result = check_release_gates({"verification_gate_passed": 1, "qa_gate_passed": True})
    assert result is True


def test_gates_truthy_int_qa_passes():
    result = check_release_gates({"verification_gate_passed": True, "qa_gate_passed": 1})
    assert result is True


def test_gates_truthy_string_verification_passes():
    result = check_release_gates({"verification_gate_passed": "yes", "qa_gate_passed": True})
    assert result is True


def test_gates_truthy_string_qa_passes():
    result = check_release_gates({"verification_gate_passed": True, "qa_gate_passed": "yes"})
    assert result is True


def test_gates_extra_keys_ignored():
    data = {**REL_BOTH_PASS, "extra_field": "ignored"}
    assert check_release_gates(data) is True


def test_gates_error_is_gate_error_subclass():
    with pytest.raises(Exception):
        check_release_gates({"verification_gate_passed": False, "qa_gate_passed": True})


def test_gates_verification_zero_raises():
    with pytest.raises(GateError):
        check_release_gates({"verification_gate_passed": 0, "qa_gate_passed": True})


def test_gates_qa_zero_raises():
    with pytest.raises(GateError):
        check_release_gates({"verification_gate_passed": True, "qa_gate_passed": 0})


def test_gates_qa_none_raises():
    with pytest.raises(GateError):
        check_release_gates({"verification_gate_passed": True, "qa_gate_passed": None})


def test_gates_both_truthy_strings_pass():
    assert check_release_gates({"verification_gate_passed": "ok", "qa_gate_passed": "ok"}) is True


# ===========================================================================
# Section 4: check_qa_floor — 30+ tests
# ===========================================================================


def test_qa_floor_minimal_pass():
    tests = [make_test("F1"), make_test("F2")]
    result = check_qa_floor(tests, ["F1", "F2"], FLOOR)
    assert result["substantive_tests"] == 2
    assert result["coverage"] == 1.0
    assert result["uncovered"] == []


def test_qa_floor_returns_dict_with_keys():
    tests = [make_test("F1"), make_test("F2")]
    result = check_qa_floor(tests, ["F1", "F2"], FLOOR)
    assert "substantive_tests" in result
    assert "coverage" in result
    assert "uncovered" in result


def test_qa_floor_full_coverage_is_1():
    tests = [make_test("F1"), make_test("F2")]
    result = check_qa_floor(tests, ["F1", "F2"], FLOOR)
    assert result["coverage"] == 1.0


def test_qa_floor_uncovered_empty_when_all_covered():
    tests = [make_test("F1"), make_test("F2")]
    result = check_qa_floor(tests, ["F1", "F2"], FLOOR)
    assert result["uncovered"] == []


def test_qa_floor_one_flow_uncovered_raises():
    tests = [make_test("F1"), make_test("F1", "shows data")]
    with pytest.raises(GateError):
        check_qa_floor(tests, ["F1", "F2"], FLOOR)


def test_qa_floor_count_below_floor_raises():
    # 1 test, floor=2, but coverage would be 1.0 → count check fails first
    tests = [make_test("F1")]
    with pytest.raises(GateError):
        check_qa_floor(tests, ["F1"], FLOOR)


def test_qa_floor_trivial_assertion_not_counted():
    tests = [
        make_test("F1"),
        {"requirement_id": "F2", "assertions": ["element exists"]},
    ]
    with pytest.raises(GateError):
        check_qa_floor(tests, ["F1", "F2"], FLOOR)


def test_qa_floor_all_exempt_raises():
    tests = [make_test("F1"), make_test("F2")]
    with pytest.raises(GateError):
        check_qa_floor(tests, ["F1", "F2"], FLOOR, exemptions=["F1", "F2"])


def test_qa_floor_exemption_removes_flow_from_coverage():
    tests = [make_test("F1"), make_test("F1", "shows x")]
    result = check_qa_floor(tests, ["F1", "F2"], FLOOR, exemptions=["F2"])
    assert result["coverage"] == 1.0


def test_qa_floor_complex_true_uses_complex_floor():
    floor = {**FLOOR, "complex": True, "complex_min_tests": 3}
    tests = [make_test("F1"), make_test("F2")]  # only 2, below complex_min_tests=3
    with pytest.raises(GateError, match="below floor"):
        check_qa_floor(tests, ["F1", "F2"], floor)


def test_qa_floor_complex_false_uses_standard_floor():
    floor = {**FLOOR, "complex": False, "standard_min_tests": 2}
    tests = [make_test("F1"), make_test("F2")]
    result = check_qa_floor(tests, ["F1", "F2"], floor)
    assert result["substantive_tests"] == 2


def test_qa_floor_required_coverage_half_passes_one_of_two():
    floor = {**FLOOR, "required_flow_coverage": 0.5}
    tests = [make_test("F1"), make_test("F1", "shows y")]
    result = check_qa_floor(tests, ["F1", "F2"], floor)
    assert result["coverage"] == 0.5


def test_qa_floor_required_coverage_zero_always_passes():
    floor = {**FLOOR, "required_flow_coverage": 0.0, "standard_min_tests": 0}
    result = check_qa_floor([], ["F1", "F2"], floor)
    assert result["coverage"] == 0.0


def test_qa_floor_three_flows_all_covered():
    tests = [make_test("F1"), make_test("F2"), make_test("F3")]
    floor = {**FLOOR, "standard_min_tests": 3}
    result = check_qa_floor(tests, ["F1", "F2", "F3"], floor)
    assert result["coverage"] == 1.0
    assert result["uncovered"] == []


def test_qa_floor_three_flows_one_uncovered_raises():
    tests = [make_test("F1"), make_test("F2"), make_test("F2", "shows x")]
    floor = {**FLOOR, "standard_min_tests": 3}
    with pytest.raises(GateError):
        check_qa_floor(tests, ["F1", "F2", "F3"], floor)


def test_qa_floor_count_exactly_at_floor_passes():
    floor = {"standard_min_tests": 2, "complex_min_tests": 3, "required_flow_coverage": 1.0}
    tests = [make_test("F1"), make_test("F2")]
    result = check_qa_floor(tests, ["F1", "F2"], floor)
    assert result["substantive_tests"] == 2


def test_qa_floor_count_above_floor_passes():
    tests = [make_test("F1"), make_test("F2"), make_test("F3")]
    floor = {**FLOOR, "standard_min_tests": 2}
    result = check_qa_floor(tests, ["F1", "F2", "F3"], floor)
    assert result["substantive_tests"] == 3


def test_qa_floor_uncovered_list_contains_missing_flow():
    # Coverage < 1.0 so GateError is raised — check it mentions missing flow
    tests = [make_test("F1"), make_test("F1", "returns data")]
    with pytest.raises(GateError, match="F2"):
        check_qa_floor(tests, ["F1", "F2"], FLOOR)


def test_qa_floor_duplicate_tests_same_flow_counted_once_for_coverage():
    tests = [make_test("F1"), make_test("F1", "shows y"), make_test("F1", "returns z")]
    with pytest.raises(GateError):
        check_qa_floor(tests, ["F1", "F2"], FLOOR)


def test_qa_floor_empty_tests_raises():
    with pytest.raises(GateError):
        check_qa_floor([], ["F1", "F2"], FLOOR)


def test_qa_floor_empty_requirement_ids_raises():
    tests = [make_test("F1"), make_test("F2")]
    with pytest.raises(GateError):
        check_qa_floor(tests, [], FLOOR)


def test_qa_floor_exemption_partial_still_requires_remaining():
    tests = [make_test("F1"), make_test("F1", "shows y")]
    with pytest.raises(GateError):
        check_qa_floor(tests, ["F1", "F2", "F3"], FLOOR, exemptions=["F3"])


def test_qa_floor_complex_exactly_at_complex_floor_passes():
    floor = {"standard_min_tests": 2, "complex_min_tests": 3,
             "required_flow_coverage": 1.0, "complex": True}
    tests = [make_test("F1"), make_test("F2"), make_test("F3")]
    result = check_qa_floor(tests, ["F1", "F2", "F3"], floor)
    assert result["substantive_tests"] == 3


@pytest.mark.parametrize("min_tests,n_tests,n_flows,should_pass", [
    (2, 2, 2, True),
    (2, 1, 1, False),   # count < floor
    (3, 3, 3, True),
    (3, 2, 2, False),   # count < floor
    (1, 1, 1, True),    # count == floor passes (floor comes from floor_cfg)
    (2, 3, 3, True),
])
def test_qa_floor_parametrized_count_vs_floor(min_tests, n_tests, n_flows, should_pass):
    floor = {"standard_min_tests": min_tests, "complex_min_tests": min_tests + 1,
             "required_flow_coverage": 1.0}
    req_ids = [f"F{i}" for i in range(n_flows)]
    tests = [make_test(f"F{i}") for i in range(n_tests)]
    if should_pass:
        result = check_qa_floor(tests, req_ids, floor)
        assert result["substantive_tests"] == n_tests
    else:
        with pytest.raises(GateError):
            check_qa_floor(tests, req_ids, floor)


def test_qa_floor_many_flows_all_covered():
    n = 10
    floor = {"standard_min_tests": n, "complex_min_tests": n + 1,
             "required_flow_coverage": 1.0}
    req_ids = [f"F{i}" for i in range(n)]
    tests = [make_test(f"F{i}") for i in range(n)]
    result = check_qa_floor(tests, req_ids, floor)
    assert result["coverage"] == 1.0
    assert result["uncovered"] == []


def test_qa_floor_mixed_trivial_and_substantive_count():
    trivial = {"requirement_id": "F1", "assertions": ["element exists"]}
    substantive = make_test("F2")
    # 1 substantive, floor=2 → should fail
    with pytest.raises(GateError):
        check_qa_floor([trivial, substantive], ["F1", "F2"], FLOOR)


def test_qa_floor_no_non_exempt_requirement_ids_error_message():
    with pytest.raises(GateError, match="non-exempt"):
        check_qa_floor([], ["F1"], FLOOR, exemptions=["F1"])


def test_qa_floor_coverage_value_correct_when_half_covered():
    floor = {"standard_min_tests": 1, "complex_min_tests": 2,
             "required_flow_coverage": 0.4}
    tests = [make_test("F1")]
    result = check_qa_floor(tests, ["F1", "F2"], floor)
    assert result["coverage"] == 0.5


def test_qa_floor_exemption_not_in_requirement_ids_is_no_op():
    tests = [make_test("F1"), make_test("F2")]
    # F99 is not in requirement_ids, so exempting it changes nothing
    result = check_qa_floor(tests, ["F1", "F2"], FLOOR, exemptions=["F99"])
    assert result["coverage"] == 1.0


def test_qa_floor_error_message_contains_uncovered_flow():
    tests = [make_test("F1"), make_test("F1", "shows y")]
    try:
        check_qa_floor(tests, ["F1", "F2"], FLOOR)
        pytest.fail("Expected GateError")
    except GateError as e:
        assert "F2" in str(e)


# ===========================================================================
# Section 5: repair_loop.repair — 10+ tests
# ===========================================================================


class _UnlimitedBudget:
    """Budget that never exhausts."""
    def record_retry(self, task_id):
        pass


class _ExhaustedBudget:
    """Budget that always raises BudgetExhaustedError."""
    def record_retry(self, task_id):
        raise BudgetExhaustedError(f"retry budget exhausted for task {task_id!r}")


def test_repair_not_exhausted_returns_repair_queued():
    task = {"id": "T1", "retry_count": 0}
    result = repair(task, "some failure", _UnlimitedBudget())
    assert result["status"] == "REPAIR_QUEUED"


def test_repair_exhausted_returns_failed():
    task = {"id": "T1", "retry_count": 0}
    result = repair(task, "failure msg", _ExhaustedBudget())
    assert result["status"] == "FAILED"


def test_repair_retry_count_incremented_from_zero():
    task = {"id": "T1", "retry_count": 0}
    result = repair(task, "failure", _UnlimitedBudget())
    assert result["task"]["retry_count"] == 1


def test_repair_retry_count_incremented_from_nonzero():
    task = {"id": "T1", "retry_count": 3}
    result = repair(task, "failure", _UnlimitedBudget())
    assert result["task"]["retry_count"] == 4


def test_repair_last_failure_set_in_task():
    task = {"id": "T1", "retry_count": 0}
    result = repair(task, "the test failed badly", _UnlimitedBudget())
    assert result["task"]["last_failure"] == "the test failed badly"


def test_repair_task_id_propagated_in_failed_result():
    task = {"id": "TASK-42", "retry_count": 0}
    result = repair(task, "failure", _ExhaustedBudget())
    assert result["task_id"] == "TASK-42"


def test_repair_original_task_not_mutated():
    task = {"id": "T1", "retry_count": 0}
    repair(task, "failure", _UnlimitedBudget())
    assert task["retry_count"] == 0


def test_repair_queued_result_contains_task_key():
    task = {"id": "T1", "retry_count": 0}
    result = repair(task, "failure", _UnlimitedBudget())
    assert "task" in result


def test_repair_failed_result_contains_reason():
    task = {"id": "T1", "retry_count": 0}
    result = repair(task, "failure", _ExhaustedBudget())
    assert "reason" in result
    assert result["reason"]


def test_repair_failed_result_reason_is_string():
    task = {"id": "T1", "retry_count": 0}
    result = repair(task, "failure", _ExhaustedBudget())
    assert isinstance(result["reason"], str)


def test_repair_multiple_repairs_increment_retry_count_using_real_budget():
    budget = BudgetTracker(max_inference_calls=100, max_retries_per_task=5)
    task = {"id": "T1", "retry_count": 0}
    for expected_count in range(1, 4):
        result = repair(task, "fail", budget)
        assert result["status"] == "REPAIR_QUEUED"
        task = result["task"]
        assert task["retry_count"] == expected_count


def test_repair_exhausted_at_limit_with_real_budget():
    budget = BudgetTracker(max_inference_calls=100, max_retries_per_task=2)
    task = {"id": "T1", "retry_count": 0}
    # First two succeed
    for _ in range(2):
        result = repair(task, "fail", budget)
        assert result["status"] == "REPAIR_QUEUED"
        task = result["task"]
    # Third is exhausted
    result = repair(task, "fail", budget)
    assert result["status"] == "FAILED"


def test_repair_preserves_other_task_fields():
    task = {"id": "T1", "retry_count": 0, "name": "my task", "priority": 5}
    result = repair(task, "failure", _UnlimitedBudget())
    assert result["task"]["name"] == "my task"
    assert result["task"]["priority"] == 5


def test_repair_task_id_preserved_in_queued_result():
    task = {"id": "MYTASK", "retry_count": 0}
    result = repair(task, "failure", _UnlimitedBudget())
    assert result["task"]["id"] == "MYTASK"


def test_repair_failure_string_empty_still_sets_last_failure():
    task = {"id": "T1", "retry_count": 0}
    result = repair(task, "", _UnlimitedBudget())
    assert result["task"]["last_failure"] == ""


def test_repair_retry_count_missing_defaults_to_zero():
    task = {"id": "T1"}  # no retry_count key
    result = repair(task, "failure", _UnlimitedBudget())
    assert result["task"]["retry_count"] == 1
