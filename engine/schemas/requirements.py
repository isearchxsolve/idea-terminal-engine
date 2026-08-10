"""Requirements artifact schema.

Must enumerate discrete user flows and edge cases — the traceability basis
for Phase 8B.
"""
from __future__ import annotations

from engine import schemas as S

NAME = "Requirements"
REQUIRED = S.COMMON_REQUIRED + ("flows", "edge_cases")
TYPES = dict(S.COMMON_TYPES, flows=list, edge_cases=list)


def _check_ids(items, label: str):
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"]:
            raise S.SchemaError(f"{NAME}: each {label} needs a non-empty string id")


def validate(data):
    S.check_mapping(data, NAME)
    S.check_required(data, REQUIRED, NAME)
    S.check_types(data, TYPES, NAME)
    if not data["flows"]:
        raise S.SchemaError(f"{NAME}: must enumerate at least one user flow")
    _check_ids(data["flows"], "flow")
    _check_ids(data["edge_cases"], "edge case")
    return data
