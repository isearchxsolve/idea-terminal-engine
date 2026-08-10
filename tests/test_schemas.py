import pytest

from engine.schemas import (
    SchemaError, architecture, evidence, execution_plan, idea, release,
    requirements, verification,
)


def base(**over):
    d = {"id": "a1", "version": 1, "timestamp": "t", "status": "s",
         "source_ref": "r"}
    d.update(over)
    return d


def test_all_schemas_validate():
    idea.validate(base(content="c", validation_status="pending"))
    requirements.validate(base(flows=[{"id": "F1"}], edge_cases=[{"id": "E1"}]))
    architecture.validate(base(components=[], interfaces=[], data_flow="x",
                               tech_choices=[]))
    execution_plan.validate(base(tasks=[{
        "id": "T1", "type": "build", "dependencies": [],
        "acceptance_criteria": ["works"], "budget": {}}]))
    evidence.validate(base(command="cmd", exit_code=0, stdout="", stderr="",
                           files_changed=[], tests_run=1))
    verification.validate(base(passed=True, failed=[], evidence_refs=[],
                               budget_used=1, retry_count=0))
    release.validate(base(gtm_surface_url="http://x", artifacts_included=[],
                          verification_gate_passed=True, qa_gate_passed=True))


def test_missing_field_rejected():
    with pytest.raises(SchemaError):
        idea.validate(base(content="c"))  # validation_status missing


def test_wrong_type_rejected():
    with pytest.raises(SchemaError):
        evidence.validate(base(command="c", exit_code="0", stdout="",
                               stderr="", files_changed=[], tests_run=0))


def test_non_object_rejected():
    with pytest.raises(SchemaError):
        idea.validate([])


def test_requirements_empty_flows_rejected():
    with pytest.raises(SchemaError):
        requirements.validate(base(flows=[], edge_cases=[]))


def test_requirements_flow_without_id_rejected():
    with pytest.raises(SchemaError):
        requirements.validate(base(flows=[{"id": ""}], edge_cases=[]))


def test_task_missing_budget_rejected():
    with pytest.raises(SchemaError):
        execution_plan.validate(base(tasks=[{
            "id": "T1", "type": "build", "dependencies": [],
            "acceptance_criteria": []}]))
