"""Extended schema tests — at least 130 test functions.

Covers: happy-path validation, missing fields, type mismatches, non-dict
inputs, schema-specific rules, and the low-level check_* helpers.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from engine.schemas import (
    SchemaError,
    check_mapping,
    check_required,
    check_types,
    architecture,
    evidence,
    execution_plan,
    idea,
    release,
    requirements,
    verification,
)

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _base(**kw):
    d = {"id": "x", "version": 1, "timestamp": "t", "status": "s", "source_ref": "r"}
    d.update(kw)
    return d


def _idea(**kw):
    defaults = {"content": "c", "validation_status": "pending"}
    defaults.update(kw)
    return _base(**defaults)


def _req(**kw):
    defaults = {"flows": [{"id": "F1"}], "edge_cases": [{"id": "E1"}]}
    defaults.update(kw)
    return _base(**defaults)


def _arch(**kw):
    defaults = {"components": [], "interfaces": [], "data_flow": "x", "tech_choices": []}
    defaults.update(kw)
    return _base(**defaults)


def _plan(**kw):
    defaults = {
        "tasks": [
            {
                "id": "T1",
                "type": "build",
                "dependencies": [],
                "acceptance_criteria": ["x"],
                "budget": {},
            }
        ],
    }
    defaults.update(kw)
    return _base(**defaults)


def _ev(**kw):
    defaults = {
        "command": "cmd", "exit_code": 0, "stdout": "", "stderr": "",
        "files_changed": [], "tests_run": 0,
    }
    defaults.update(kw)
    return _base(**defaults)


def _ver(**kw):
    defaults = {
        "passed": True, "failed": [], "evidence_refs": [],
        "budget_used": 0, "retry_count": 0,
    }
    defaults.update(kw)
    return _base(**defaults)


def _rel(**kw):
    defaults = {
        "gtm_surface_url": "http://x", "artifacts_included": [],
        "verification_gate_passed": True, "qa_gate_passed": True,
    }
    defaults.update(kw)
    return _base(**defaults)


# ===========================================================================
# 1. Happy-path: each schema validates a valid minimal dict
# ===========================================================================

@pytest.mark.parametrize("validate,data", [
    (idea.validate,         _idea()),
    (requirements.validate, _req()),
    (architecture.validate, _arch()),
    (execution_plan.validate, _plan()),
    (evidence.validate,     _ev()),
    (verification.validate, _ver()),
    (release.validate,      _rel()),
], ids=["idea","requirements","architecture","execution_plan","evidence","verification","release"])
def test_happy_path(validate, data):
    result = validate(data)
    assert isinstance(result, dict)


# ===========================================================================
# 2. Missing required fields — parametrized per schema
# ===========================================================================

# --- idea: 7 required fields ---
@pytest.mark.parametrize("field", ["id","version","timestamp","status","source_ref","content","validation_status"])
def test_idea_missing_field(field):
    d = _idea()
    del d[field]
    with pytest.raises(SchemaError):
        idea.validate(d)


# --- requirements: 7 required fields ---
@pytest.mark.parametrize("field", ["id","version","timestamp","status","source_ref","flows","edge_cases"])
def test_requirements_missing_field(field):
    d = _req()
    del d[field]
    with pytest.raises(SchemaError):
        requirements.validate(d)


# --- architecture: 9 required fields ---
@pytest.mark.parametrize("field", [
    "id","version","timestamp","status","source_ref",
    "components","interfaces","data_flow","tech_choices",
])
def test_architecture_missing_field(field):
    d = _arch()
    del d[field]
    with pytest.raises(SchemaError):
        architecture.validate(d)


# --- execution_plan: 6 required fields ---
@pytest.mark.parametrize("field", ["id","version","timestamp","status","source_ref","tasks"])
def test_execution_plan_missing_field(field):
    d = _plan()
    del d[field]
    with pytest.raises(SchemaError):
        execution_plan.validate(d)


# --- evidence: 11 required fields ---
@pytest.mark.parametrize("field", [
    "id","version","timestamp","status","source_ref",
    "command","exit_code","stdout","stderr","files_changed","tests_run",
])
def test_evidence_missing_field(field):
    d = _ev()
    del d[field]
    with pytest.raises(SchemaError):
        evidence.validate(d)


# --- verification: 10 required fields ---
@pytest.mark.parametrize("field", [
    "id","version","timestamp","status","source_ref",
    "passed","failed","evidence_refs","budget_used","retry_count",
])
def test_verification_missing_field(field):
    d = _ver()
    del d[field]
    with pytest.raises(SchemaError):
        verification.validate(d)


# --- release: 9 required fields ---
@pytest.mark.parametrize("field", [
    "id","version","timestamp","status","source_ref",
    "gtm_surface_url","artifacts_included","verification_gate_passed","qa_gate_passed",
])
def test_release_missing_field(field):
    d = _rel()
    del d[field]
    with pytest.raises(SchemaError):
        release.validate(d)


# ===========================================================================
# 3. None value treated as missing (check_required)
# ===========================================================================

@pytest.mark.parametrize("field", ["id","version","timestamp","status","source_ref","content","validation_status"])
def test_idea_none_field(field):
    d = _idea()
    d[field] = None
    with pytest.raises(SchemaError):
        idea.validate(d)


@pytest.mark.parametrize("field", ["id","version","timestamp","status","source_ref","flows","edge_cases"])
def test_requirements_none_field(field):
    d = _req()
    d[field] = None
    with pytest.raises(SchemaError):
        requirements.validate(d)


@pytest.mark.parametrize("field", [
    "id","version","timestamp","status","source_ref",
    "command","exit_code","stdout","stderr","files_changed","tests_run",
])
def test_evidence_none_field(field):
    d = _ev()
    d[field] = None
    with pytest.raises(SchemaError):
        evidence.validate(d)


# ===========================================================================
# 4. Type mismatch tests
# ===========================================================================

# --- idea type mismatches ---
@pytest.mark.parametrize("field,bad_value", [
    ("id",                1),
    ("version",           "1"),
    ("timestamp",         42),
    ("status",            123),
    ("source_ref",        []),
    ("content",           999),
    ("validation_status", False),
])
def test_idea_type_mismatch(field, bad_value):
    d = _idea()
    d[field] = bad_value
    with pytest.raises(SchemaError):
        idea.validate(d)


# --- requirements type mismatches ---
@pytest.mark.parametrize("field,bad_value", [
    ("id",          0),
    ("version",     "two"),
    ("timestamp",   {}),
    ("status",      []),
    ("source_ref",  True),
    ("flows",       "list"),
    ("edge_cases",  42),
])
def test_requirements_type_mismatch(field, bad_value):
    d = _req()
    d[field] = bad_value
    with pytest.raises(SchemaError):
        requirements.validate(d)


# --- architecture type mismatches ---
@pytest.mark.parametrize("field,bad_value", [
    ("id",           999),
    ("version",      "v2"),
    ("timestamp",    []),
    ("status",       0),
    ("source_ref",   {}),
    ("components",   "list"),
    ("interfaces",   42),
    ("data_flow",    []),
    ("tech_choices", {}),
])
def test_architecture_type_mismatch(field, bad_value):
    d = _arch()
    d[field] = bad_value
    with pytest.raises(SchemaError):
        architecture.validate(d)


# --- execution_plan type mismatches (top-level) ---
@pytest.mark.parametrize("field,bad_value", [
    ("id",       []),
    ("version",  "3"),
    ("timestamp", 0),
    ("status",   {}),
    ("source_ref", 1),
    ("tasks",    "not-a-list"),
])
def test_execution_plan_type_mismatch(field, bad_value):
    d = _plan()
    d[field] = bad_value
    with pytest.raises(SchemaError):
        execution_plan.validate(d)


# --- evidence type mismatches ---
@pytest.mark.parametrize("field,bad_value", [
    ("id",            9),
    ("version",       "1"),
    ("timestamp",     []),
    ("status",        0),
    ("source_ref",    {}),
    ("command",       42),
    ("exit_code",     "0"),
    ("stdout",        []),
    ("stderr",        1),
    ("files_changed", "list"),
    ("tests_run",     "5"),
])
def test_evidence_type_mismatch(field, bad_value):
    d = _ev()
    d[field] = bad_value
    with pytest.raises(SchemaError):
        evidence.validate(d)


# --- verification type mismatches ---
@pytest.mark.parametrize("field,bad_value", [
    ("id",           0),
    ("version",      "v"),
    ("timestamp",    1),
    ("status",       []),
    ("source_ref",   9),
    ("passed",       "true"),
    ("failed",       "list"),
    ("evidence_refs", {}),
    ("budget_used",  "100"),
    ("retry_count",  "0"),
])
def test_verification_type_mismatch(field, bad_value):
    d = _ver()
    d[field] = bad_value
    with pytest.raises(SchemaError):
        verification.validate(d)


# --- release type mismatches ---
@pytest.mark.parametrize("field,bad_value", [
    ("id",                       1),
    ("version",                  "2"),
    ("timestamp",                []),
    ("status",                   0),
    ("source_ref",               {}),
    ("gtm_surface_url",          42),
    ("artifacts_included",       "list"),
    ("verification_gate_passed", "true"),
    ("qa_gate_passed",           1),
])
def test_release_type_mismatch(field, bad_value):
    d = _rel()
    d[field] = bad_value
    with pytest.raises(SchemaError):
        release.validate(d)


# ===========================================================================
# 5. Non-dict inputs — each schema, 4 bad types each = 28 tests
# ===========================================================================

_ALL_SCHEMAS = [
    ("idea", idea.validate),
    ("requirements", requirements.validate),
    ("architecture", architecture.validate),
    ("execution_plan", execution_plan.validate),
    ("evidence", evidence.validate),
    ("verification", verification.validate),
    ("release", release.validate),
]

@pytest.mark.parametrize("schema_name,validate", _ALL_SCHEMAS,
    ids=[s for s, _ in _ALL_SCHEMAS])
def test_non_dict_list(schema_name, validate):
    with pytest.raises(SchemaError):
        validate([1, 2, 3])


@pytest.mark.parametrize("schema_name,validate", _ALL_SCHEMAS,
    ids=[s for s, _ in _ALL_SCHEMAS])
def test_non_dict_string(schema_name, validate):
    with pytest.raises(SchemaError):
        validate("hello")


@pytest.mark.parametrize("schema_name,validate", _ALL_SCHEMAS,
    ids=[s for s, _ in _ALL_SCHEMAS])
def test_non_dict_int(schema_name, validate):
    with pytest.raises(SchemaError):
        validate(42)


@pytest.mark.parametrize("schema_name,validate", _ALL_SCHEMAS,
    ids=[s for s, _ in _ALL_SCHEMAS])
def test_non_dict_none(schema_name, validate):
    with pytest.raises(SchemaError):
        validate(None)


# ===========================================================================
# 6. Requirements-specific edge cases
# ===========================================================================

def test_requirements_empty_flows_raises():
    with pytest.raises(SchemaError):
        requirements.validate(_req(flows=[]))


def test_requirements_flow_no_id_field():
    with pytest.raises(SchemaError):
        requirements.validate(_req(flows=[{"name": "no-id"}]))


def test_requirements_flow_empty_string_id():
    with pytest.raises(SchemaError):
        requirements.validate(_req(flows=[{"id": ""}]))


def test_requirements_flow_int_id():
    with pytest.raises(SchemaError):
        requirements.validate(_req(flows=[{"id": 123}]))


def test_requirements_edge_case_no_id_field():
    with pytest.raises(SchemaError):
        requirements.validate(_req(edge_cases=[{"label": "no-id"}]))


def test_requirements_edge_case_empty_string_id():
    with pytest.raises(SchemaError):
        requirements.validate(_req(edge_cases=[{"id": ""}]))


def test_requirements_edge_case_int_id():
    with pytest.raises(SchemaError):
        requirements.validate(_req(edge_cases=[{"id": 0}]))


def test_requirements_multiple_valid_flows():
    d = _req(flows=[{"id": "F1"}, {"id": "F2"}, {"id": "F3"}], edge_cases=[])
    result = requirements.validate(d)
    assert len(result["flows"]) == 3


def test_requirements_multiple_valid_edge_cases():
    d = _req(
        flows=[{"id": "F1"}],
        edge_cases=[{"id": "E1"}, {"id": "E2"}, {"id": "E3"}],
    )
    result = requirements.validate(d)
    assert len(result["edge_cases"]) == 3


def test_requirements_valid_with_many_flows_and_edge_cases():
    flows = [{"id": f"F{i}"} for i in range(10)]
    edges = [{"id": f"E{i}"} for i in range(5)]
    result = requirements.validate(_req(flows=flows, edge_cases=edges))
    assert result["flows"] == flows


def test_requirements_second_flow_bad_id_raises():
    with pytest.raises(SchemaError):
        requirements.validate(_req(flows=[{"id": "F1"}, {"id": ""}]))


def test_requirements_edge_cases_empty_list_valid():
    # empty edge_cases is allowed (only flows must be non-empty)
    result = requirements.validate(_req(flows=[{"id": "F1"}], edge_cases=[]))
    assert result["edge_cases"] == []


def test_requirements_flow_missing_id_key_raises():
    with pytest.raises(SchemaError):
        requirements.validate(_req(flows=[{}]))


# ===========================================================================
# 7. ExecutionPlan-specific edge cases
# ===========================================================================

def test_execution_plan_empty_tasks_valid():
    # tasks=[] is valid per schema; no task iteration happens
    result = execution_plan.validate(_plan(tasks=[]))
    assert result["tasks"] == []


def test_execution_plan_task_dependencies_not_list():
    d = _plan(tasks=[{
        "id": "T1", "type": "build",
        "dependencies": "none",
        "acceptance_criteria": ["x"],
        "budget": {},
    }])
    with pytest.raises(SchemaError):
        execution_plan.validate(d)


def test_execution_plan_task_acceptance_criteria_not_list():
    d = _plan(tasks=[{
        "id": "T1", "type": "build",
        "dependencies": [],
        "acceptance_criteria": "pass",
        "budget": {},
    }])
    with pytest.raises(SchemaError):
        execution_plan.validate(d)


def test_execution_plan_task_budget_not_dict():
    d = _plan(tasks=[{
        "id": "T1", "type": "build",
        "dependencies": [],
        "acceptance_criteria": ["x"],
        "budget": ["list"],
    }])
    with pytest.raises(SchemaError):
        execution_plan.validate(d)


@pytest.mark.parametrize("missing_field", ["id", "type", "dependencies", "acceptance_criteria", "budget"])
def test_execution_plan_task_missing_required_field(missing_field):
    task = {
        "id": "T1", "type": "build",
        "dependencies": [],
        "acceptance_criteria": ["x"],
        "budget": {},
    }
    del task[missing_field]
    d = _plan(tasks=[task])
    with pytest.raises(SchemaError):
        execution_plan.validate(d)


def test_execution_plan_multiple_valid_tasks():
    tasks = [
        {"id": f"T{i}", "type": "build", "dependencies": [], "acceptance_criteria": ["x"], "budget": {}}
        for i in range(5)
    ]
    result = execution_plan.validate(_plan(tasks=tasks))
    assert len(result["tasks"]) == 5


def test_execution_plan_task_is_not_dict():
    d = _plan(tasks=["not-a-dict"])
    with pytest.raises(SchemaError):
        execution_plan.validate(d)


def test_execution_plan_task_budget_empty_dict_valid():
    result = execution_plan.validate(_plan(tasks=[{
        "id": "T1", "type": "build",
        "dependencies": [], "acceptance_criteria": [], "budget": {},
    }]))
    assert result["tasks"][0]["budget"] == {}


# ===========================================================================
# 8. Release-specific
# ===========================================================================

def test_release_verification_gate_passed_false_valid():
    result = release.validate(_rel(verification_gate_passed=False))
    assert result["verification_gate_passed"] is False


def test_release_qa_gate_passed_false_valid():
    result = release.validate(_rel(qa_gate_passed=False))
    assert result["qa_gate_passed"] is False


def test_release_both_gates_false_valid():
    result = release.validate(_rel(verification_gate_passed=False, qa_gate_passed=False))
    assert not result["qa_gate_passed"]
    assert not result["verification_gate_passed"]


def test_release_artifacts_included_empty_list_valid():
    result = release.validate(_rel(artifacts_included=[]))
    assert result["artifacts_included"] == []


def test_release_artifacts_included_non_empty_list_valid():
    result = release.validate(_rel(artifacts_included=["a.zip", "b.tar.gz"]))
    assert len(result["artifacts_included"]) == 2


def test_release_gtm_url_arbitrary_string_valid():
    result = release.validate(_rel(gtm_surface_url="ftp://internal/release"))
    assert result["gtm_surface_url"] == "ftp://internal/release"


def test_release_gtm_url_empty_string_valid():
    # schema only checks type=str, not content
    result = release.validate(_rel(gtm_surface_url=""))
    assert result["gtm_surface_url"] == ""


# ===========================================================================
# 9. Evidence-specific
# ===========================================================================

def test_evidence_exit_code_zero_valid():
    result = evidence.validate(_ev(exit_code=0))
    assert result["exit_code"] == 0


def test_evidence_exit_code_one_valid():
    result = evidence.validate(_ev(exit_code=1))
    assert result["exit_code"] == 1


def test_evidence_exit_code_negative_valid():
    result = evidence.validate(_ev(exit_code=-1))
    assert result["exit_code"] == -1


def test_evidence_exit_code_large_int_valid():
    result = evidence.validate(_ev(exit_code=255))
    assert result["exit_code"] == 255


def test_evidence_files_changed_empty_list_valid():
    result = evidence.validate(_ev(files_changed=[]))
    assert result["files_changed"] == []


def test_evidence_files_changed_non_empty_valid():
    result = evidence.validate(_ev(files_changed=["src/a.py", "src/b.py"]))
    assert len(result["files_changed"]) == 2


def test_evidence_tests_run_zero_valid():
    result = evidence.validate(_ev(tests_run=0))
    assert result["tests_run"] == 0


def test_evidence_tests_run_large_number_valid():
    result = evidence.validate(_ev(tests_run=9999))
    assert result["tests_run"] == 9999


def test_evidence_empty_stdout_stderr_valid():
    result = evidence.validate(_ev(stdout="", stderr=""))
    assert result["stdout"] == ""
    assert result["stderr"] == ""


def test_evidence_non_empty_stdout_valid():
    result = evidence.validate(_ev(stdout="All tests passed"))
    assert "passed" in result["stdout"]


# ===========================================================================
# 10. Verification-specific
# ===========================================================================

def test_verification_passed_false_valid():
    result = verification.validate(_ver(passed=False))
    assert result["passed"] is False


def test_verification_failed_non_empty_list_valid():
    result = verification.validate(_ver(failed=["T1", "T2"]))
    assert result["failed"] == ["T1", "T2"]


def test_verification_evidence_refs_non_empty_valid():
    result = verification.validate(_ver(evidence_refs=["ev-001"]))
    assert len(result["evidence_refs"]) == 1


def test_verification_budget_used_zero_valid():
    result = verification.validate(_ver(budget_used=0))
    assert result["budget_used"] == 0


def test_verification_budget_used_large_valid():
    result = verification.validate(_ver(budget_used=3999))
    assert result["budget_used"] == 3999


def test_verification_retry_count_zero_valid():
    result = verification.validate(_ver(retry_count=0))
    assert result["retry_count"] == 0


def test_verification_retry_count_positive_valid():
    result = verification.validate(_ver(retry_count=5))
    assert result["retry_count"] == 5


# ===========================================================================
# 11. check_mapping helper
# ===========================================================================

def test_check_mapping_with_non_dict_list_raises():
    with pytest.raises(SchemaError):
        check_mapping([], "Test")


def test_check_mapping_with_non_dict_string_raises():
    with pytest.raises(SchemaError):
        check_mapping("hello", "Test")


def test_check_mapping_with_non_dict_int_raises():
    with pytest.raises(SchemaError):
        check_mapping(42, "Test")


def test_check_mapping_with_none_raises():
    with pytest.raises(SchemaError):
        check_mapping(None, "Test")


def test_check_mapping_with_dict_returns_data():
    d = {"a": 1}
    result = check_mapping(d, "Test")
    assert result is d


def test_check_mapping_with_empty_dict_returns_data():
    d = {}
    result = check_mapping(d, "Test")
    assert result is d


def test_check_mapping_error_message_contains_what():
    with pytest.raises(SchemaError, match="MyThing"):
        check_mapping([], "MyThing")


def test_check_mapping_error_message_contains_type():
    with pytest.raises(SchemaError, match="list"):
        check_mapping([], "Test")


@pytest.mark.parametrize("bad", [tuple(), set(), 1.5, b"bytes"])
def test_check_mapping_various_non_dicts(bad):
    with pytest.raises(SchemaError):
        check_mapping(bad, "Test")


# ===========================================================================
# 12. check_required helper
# ===========================================================================

def test_check_required_raises_if_field_missing():
    with pytest.raises(SchemaError):
        check_required({"a": 1}, ["a", "b"], "Test")


def test_check_required_raises_if_field_is_none():
    with pytest.raises(SchemaError):
        check_required({"a": None}, ["a"], "Test")


def test_check_required_passes_when_all_present():
    check_required({"a": 1, "b": "x"}, ["a", "b"], "Test")  # no exception


def test_check_required_empty_fields_list_always_passes():
    check_required({}, [], "Test")  # no exception


def test_check_required_extra_fields_do_not_cause_failure():
    check_required({"a": 1, "b": 2, "c": 3}, ["a"], "Test")  # no exception


def test_check_required_error_message_contains_missing_field():
    with pytest.raises(SchemaError, match="missing_key"):
        check_required({}, ["missing_key"], "Test")


@pytest.mark.parametrize("none_field", ["id", "version", "status"])
def test_check_required_none_treated_as_missing(none_field):
    d = {"id": "x", "version": 1, "status": "s"}
    d[none_field] = None
    with pytest.raises(SchemaError):
        check_required(d, list(d.keys()), "Test")


def test_check_required_all_required_present_and_valued():
    fields = ["f1", "f2", "f3"]
    data = {f: i for i, f in enumerate(fields)}
    check_required(data, fields, "Test")  # no exception


# ===========================================================================
# 13. check_types helper
# ===========================================================================

def test_check_types_raises_if_wrong_type():
    with pytest.raises(SchemaError):
        check_types({"count": "five"}, {"count": int}, "Test")


def test_check_types_passes_when_types_match():
    check_types({"name": "Alice", "age": 30}, {"name": str, "age": int}, "Test")


def test_check_types_skips_none_values():
    # field present but None → skip (optional-like behaviour)
    check_types({"x": None}, {"x": int}, "Test")  # no exception


def test_check_types_skips_absent_keys():
    # field not in data at all → skip
    check_types({}, {"x": str}, "Test")  # no exception


def test_check_types_error_message_mentions_field():
    with pytest.raises(SchemaError, match="myfield"):
        check_types({"myfield": 99}, {"myfield": str}, "Test")


def test_check_types_error_message_mentions_expected_type():
    with pytest.raises(SchemaError, match="str"):
        check_types({"f": 1}, {"f": str}, "Test")


def test_check_types_list_type_mismatch():
    with pytest.raises(SchemaError):
        check_types({"items": "not-a-list"}, {"items": list}, "Test")


def test_check_types_bool_type_mismatch():
    with pytest.raises(SchemaError):
        check_types({"flag": "true"}, {"flag": bool}, "Test")


def test_check_types_multiple_fields_first_bad_raises():
    with pytest.raises(SchemaError):
        check_types({"a": 1, "b": "wrong"}, {"a": int, "b": int}, "Test")


@pytest.mark.parametrize("value,expected_type", [
    ("hello", str),
    (42, int),
    (True, bool),
    ([1, 2], list),
    ({"k": "v"}, dict),
])
def test_check_types_correct_types_pass(value, expected_type):
    check_types({"field": value}, {"field": expected_type}, "Test")


# ===========================================================================
# 14. Architecture additional edge cases
# ===========================================================================

def test_architecture_components_non_empty_list_valid():
    result = architecture.validate(_arch(components=["svc-a", "svc-b"]))
    assert len(result["components"]) == 2


def test_architecture_interfaces_non_empty_list_valid():
    result = architecture.validate(_arch(interfaces=["REST", "gRPC"]))
    assert len(result["interfaces"]) == 2


def test_architecture_tech_choices_non_empty_list_valid():
    result = architecture.validate(_arch(tech_choices=["Python", "Redis"]))
    assert len(result["tech_choices"]) == 2


def test_architecture_data_flow_non_empty_string_valid():
    result = architecture.validate(_arch(data_flow="A -> B -> C"))
    assert result["data_flow"] == "A -> B -> C"


# ===========================================================================
# 15. Additional parametrize coverage for validate() return value
# ===========================================================================

@pytest.mark.parametrize("validate,data,check_key,check_val", [
    (idea.validate,          _idea(content="hello"),           "content",       "hello"),
    (requirements.validate,  _req(flows=[{"id":"F9"}]),         "flows",         [{"id":"F9"}]),
    (architecture.validate,  _arch(data_flow="stream"),         "data_flow",     "stream"),
    (evidence.validate,      _ev(command="pytest"),             "command",       "pytest"),
    (verification.validate,  _ver(retry_count=3),               "retry_count",   3),
    (release.validate,       _rel(gtm_surface_url="http://y"),  "gtm_surface_url","http://y"),
])
def test_validate_returns_data_with_correct_field(validate, data, check_key, check_val):
    result = validate(data)
    assert result[check_key] == check_val


# ===========================================================================
# 16. SchemaError is a subclass of ValueError
# ===========================================================================

def test_schema_error_is_value_error():
    assert issubclass(SchemaError, ValueError)


def test_schema_error_can_be_raised_and_caught_as_value_error():
    with pytest.raises(ValueError):
        raise SchemaError("test")


# ===========================================================================
# 17. Verify extra unknown fields are tolerated (schemas only check required)
# ===========================================================================

@pytest.mark.parametrize("validate,data", [
    (idea.validate,         _idea(extra_field="ignored")),
    (requirements.validate, _req(extra="yes")),
    (architecture.validate, _arch(surprise=42)),
    (evidence.validate,     _ev(custom_meta={})),
    (verification.validate, _ver(annotation="ok")),
    (release.validate,      _rel(notes="final")),
])
def test_extra_fields_tolerated(validate, data):
    result = validate(data)
    assert isinstance(result, dict)
