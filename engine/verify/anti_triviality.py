"""Phase 8B anti-triviality gate (General Rule 14).

A test counts toward the floor only if it asserts a meaningful behavioral
outcome tied to a specific requirement/flow/edge-case ID. Trivial checks
("element exists", "page loads") and near-duplicates do not count.
"""
from __future__ import annotations

BEHAVIORAL_MARKERS = (
    "displays", "shows", "equals", "contains", "rejects", "redirects",
    "updates", "persists", "returns", "calculates", "prevents", "allows",
)


def check_test_substance(test, requirement_id) -> bool:
    if not requirement_id:
        return False
    assertions = test.get("assertions") or []
    if not assertions:
        return False
    return any(
        any(marker in assertion.lower() for marker in BEHAVIORAL_MARKERS)
        for assertion in assertions
    )
