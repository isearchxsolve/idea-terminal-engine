"""Release artifact schema."""
from __future__ import annotations

from engine import schemas as S

NAME = "Release"
REQUIRED = S.COMMON_REQUIRED + (
    "gtm_surface_url", "artifacts_included",
    "verification_gate_passed", "qa_gate_passed",
)
TYPES = dict(
    S.COMMON_TYPES,
    gtm_surface_url=str,
    artifacts_included=list,
    verification_gate_passed=bool,
    qa_gate_passed=bool,
)


def validate(data):
    S.check_mapping(data, NAME)
    S.check_required(data, REQUIRED, NAME)
    S.check_types(data, TYPES, NAME)
    return data
