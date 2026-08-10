"""Execution plan + task schemas."""
from __future__ import annotations

from engine import schemas as S

NAME = "ExecutionPlan"
REQUIRED = S.COMMON_REQUIRED + ("tasks",)
TYPES = dict(S.COMMON_TYPES, tasks=list)

TASK_REQUIRED = ("id", "type", "dependencies", "acceptance_criteria", "budget")


def validate(data):
    S.check_mapping(data, NAME)
    S.check_required(data, REQUIRED, NAME)
    S.check_types(data, TYPES, NAME)
    for task in data["tasks"]:
        S.check_mapping(task, "Task")
        S.check_required(task, TASK_REQUIRED, "Task")
        if not isinstance(task["dependencies"], list):
            raise S.SchemaError("Task: dependencies must be a list")
        if not isinstance(task["acceptance_criteria"], list):
            raise S.SchemaError("Task: acceptance_criteria must be a list")
        if not isinstance(task["budget"], dict):
            raise S.SchemaError("Task: budget must be an object")
    return data
