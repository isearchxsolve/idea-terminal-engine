"""Architecture artifact schema."""
from __future__ import annotations

from engine import schemas as S

NAME = "Architecture"
REQUIRED = S.COMMON_REQUIRED + ("components", "interfaces", "data_flow", "tech_choices")
TYPES = dict(
    S.COMMON_TYPES,
    components=list,
    interfaces=list,
    data_flow=str,
    tech_choices=list,
)


def validate(data):
    S.check_mapping(data, NAME)
    S.check_required(data, REQUIRED, NAME)
    S.check_types(data, TYPES, NAME)
    return data
