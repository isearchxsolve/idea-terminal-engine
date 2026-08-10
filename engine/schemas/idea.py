"""Idea artifact schema."""
from __future__ import annotations

from engine import schemas as S

NAME = "Idea"
REQUIRED = S.COMMON_REQUIRED + ("content", "validation_status")
TYPES = dict(S.COMMON_TYPES, content=str, validation_status=str)


def validate(data):
    S.check_mapping(data, NAME)
    S.check_required(data, REQUIRED, NAME)
    S.check_types(data, TYPES, NAME)
    return data
