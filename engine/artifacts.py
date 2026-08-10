"""Artifact persistence: save / load / validate with version stamping."""
from __future__ import annotations

import json
from pathlib import Path

from engine.schemas import (
    architecture, evidence, execution_plan, idea, release, requirements,
    verification,
)

REGISTRY = {
    "idea": idea,
    "requirements": requirements,
    "architecture": architecture,
    "execution_plan": execution_plan,
    "evidence": evidence,
    "verification": verification,
    "release": release,
}


def artifact_path(directory, kind: str) -> Path:
    if kind not in REGISTRY:
        raise KeyError(f"unknown artifact kind: {kind!r}")
    return Path(directory) / f"{kind}.json"


def load_artifact(directory, kind: str) -> dict:
    path = artifact_path(directory, kind)
    data = json.loads(path.read_text(encoding="utf-8"))
    return REGISTRY[kind].validate(data)


def save_artifact(directory, kind: str, data: dict) -> Path:
    """Validate then write. Re-saving an existing artifact bumps its version."""
    path = artifact_path(directory, kind)
    data = dict(data)
    if path.exists():
        old = json.loads(path.read_text(encoding="utf-8"))
        data["version"] = int(old.get("version", 0)) + 1
    else:
        data.setdefault("version", 1)
    REGISTRY[kind].validate(data)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path
