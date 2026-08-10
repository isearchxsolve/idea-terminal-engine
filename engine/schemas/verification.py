"""VerificationResult artifact schema."""
from __future__ import annotations

from engine import schemas as S

NAME = "VerificationResult"
REQUIRED = S.COMMON_REQUIRED + (
    "passed", "failed", "evidence_refs", "budget_used", "retry_count",
)
TYPES = dict(
    S.COMMON_TYPES,
    passed=bool,
    failed=list,
    evidence_refs=list,
    budget_used=int,
    retry_count=int,
)


def validate(data):
    S.check_mapping(data, NAME)
    S.check_required(data, REQUIRED, NAME)
    S.check_types(data, TYPES, NAME)
    return data
