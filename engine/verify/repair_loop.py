"""Bounded repair loop (Phase 6). Never retries past either budget."""
from __future__ import annotations

from engine.pacing.budget import BudgetExhaustedError


def repair(task, failure, budget):
    """Return a re-queued task, or FAILED once the retry budget is exhausted."""
    try:
        budget.record_retry(task["id"])
    except BudgetExhaustedError as exc:
        return {"status": "FAILED", "task_id": task["id"], "reason": str(exc)}
    new_task = dict(task)
    new_task["retry_count"] = int(task.get("retry_count", 0)) + 1
    new_task["last_failure"] = failure
    return {"status": "REPAIR_QUEUED", "task": new_task}
