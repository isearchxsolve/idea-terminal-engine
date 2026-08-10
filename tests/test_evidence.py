import pytest

from engine.verify.evidence_validator import (
    UnsupportedClaimError, validate_completion,
)

TASK = {"id": "T1"}


def ev(task_id="T1", exit_code=0):
    return {"id": "e", "version": 1, "timestamp": "t", "status": "recorded",
            "source_ref": "r", "command": "pytest", "exit_code": exit_code,
            "stdout": "", "stderr": "", "files_changed": [], "tests_run": 1,
            "task_id": task_id}


def test_claim_without_evidence_fails():
    with pytest.raises(UnsupportedClaimError):
        validate_completion(TASK, [])


def test_evidence_without_claim_ignored():
    # Evidence for another task proves nothing about this one.
    with pytest.raises(UnsupportedClaimError):
        validate_completion(TASK, [ev(task_id="OTHER")])


def test_failing_evidence_rejects_claim():
    with pytest.raises(UnsupportedClaimError):
        validate_completion(TASK, [ev(exit_code=1)])


def test_matching_passing_evidence_passes():
    # Unrelated evidence is ignored; matching passing evidence supports.
    assert validate_completion(TASK, [ev(), ev(task_id="OTHER")])
