"""Claim vs evidence. A claim without evidence is NOT completion."""
from __future__ import annotations

from engine.schemas import evidence as evidence_schema


class UnsupportedClaimError(Exception):
    pass


def validate_completion(task, evidence):
    """Fail closed unless evidence actually supports the task's completion.

    Evidence that does not reference the task is ignored (it proves nothing
    about this task); evidence with a non-zero exit code rejects the claim.
    """
    if not evidence:
        raise UnsupportedClaimError(
            f"task {task.get('id')!r}: claim without evidence"
        )
    for ev in evidence:
        evidence_schema.validate(ev)
    matching = [ev for ev in evidence if ev.get("task_id") == task["id"]]
    if not matching:
        raise UnsupportedClaimError(
            f"task {task.get('id')!r}: no evidence references this task "
            f"(unrelated evidence ignored)"
        )
    failing = [ev for ev in matching if ev["exit_code"] != 0]
    if failing:
        raise UnsupportedClaimError(
            f"task {task.get('id')!r}: {len(failing)} failing evidence record(s)"
        )
    return matching
