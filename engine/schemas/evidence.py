"""Evidence artifact schema. A claim without evidence is NOT completion."""
from __future__ import annotations

from engine import schemas as S

NAME = "Evidence"
REQUIRED = S.COMMON_REQUIRED + (
    "command", "exit_code", "stdout", "stderr", "files_changed", "tests_run",
)
TYPES = dict(
    S.COMMON_TYPES,
    command=str,
    exit_code=int,
    stdout=str,
    stderr=str,
    files_changed=list,
    tests_run=int,
)


def validate(data):
    S.check_mapping(data, NAME)
    S.check_required(data, REQUIRED, NAME)
    S.check_types(data, TYPES, NAME)
    return data
