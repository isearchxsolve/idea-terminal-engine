"""Minimal stdlib-only artifact validation (JSON-Schema-flavored)."""
from __future__ import annotations


class SchemaError(ValueError):
    """Raised when an artifact fails contract validation."""


def check_mapping(data, what: str):
    if not isinstance(data, dict):
        raise SchemaError(f"{what}: expected object, got {type(data).__name__}")
    return data


def check_required(data, fields, what: str):
    missing = [f for f in fields if f not in data or data[f] is None]
    if missing:
        raise SchemaError(f"{what}: missing required field(s): {missing}")


def check_types(data, types, what: str):
    for field, allowed in types.items():
        value = data.get(field)
        if field in data and value is not None and not isinstance(value, allowed):
            raise SchemaError(
                f"{what}: field {field!r} must be "
                f"{getattr(allowed, '__name__', allowed)}, got {type(value).__name__}"
            )


# Every artifact carries these (Phase 2 contract).
COMMON_REQUIRED = ("id", "version", "timestamp", "status", "source_ref")
COMMON_TYPES = {
    "id": str,
    "version": int,
    "timestamp": str,
    "status": str,
    "source_ref": str,
}
