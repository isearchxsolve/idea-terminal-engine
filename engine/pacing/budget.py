"""Call and retry budgets — independent limits, fail closed (Rule 12).

The inference-call budget and the per-task retry budget are enforced
separately; exhausting either one stops the loop.
"""
from __future__ import annotations

from engine import config as cfg


class BudgetExhaustedError(Exception):
    pass


class BudgetTracker:
    def __init__(self, max_inference_calls: int = 4000, max_retries_per_task: int = 5):
        self.max_inference_calls = int(max_inference_calls)
        self.max_retries_per_task = int(max_retries_per_task)
        self.calls_used = 0
        self._retries = {}

    @classmethod
    def from_config(cls) -> "BudgetTracker":
        b = cfg.load_engine_config()["budget"]
        return cls(b["max_inference_calls"], b["max_retries_per_task"])

    def record_call(self):
        if self.calls_used >= self.max_inference_calls:
            raise BudgetExhaustedError(
                f"inference call budget exhausted ({self.max_inference_calls})"
            )
        self.calls_used += 1

    def record_retry(self, task_id: str):
        used = self._retries.get(task_id, 0)
        if used >= self.max_retries_per_task:
            raise BudgetExhaustedError(
                f"retry budget exhausted for task {task_id!r} "
                f"({self.max_retries_per_task})"
            )
        self._retries[task_id] = used + 1

    def retries_used(self, task_id: str) -> int:
        return self._retries.get(task_id, 0)
