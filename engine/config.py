"""Central config loading. Config lives in config/, never in source (Rule 9)."""
from __future__ import annotations

import json

from engine import paths

DEFAULTS = {
    "pacing": {
        "max_in_flight": 3,
        "min_interval_seconds": 1.6,
        "backoff_base_seconds": 2.0,
        "backoff_max_seconds": 60.0,
    },
    "budget": {
        "max_inference_calls": 4000,
        "max_retries_per_task": 5,
    },
    "inference": {
        "timeout_seconds": 120,
        "max_output_tokens": 4096,
    },
    "exec": {
        "timeout_seconds": 120,
        "allowed_commands": ["python", "py", "node", "npx"],
    },
}


import tomllib

def load_engine_config() -> dict:
    cfg = json.loads(json.dumps(DEFAULTS))  # deep copy of defaults
    path = paths.config_path("engine.toml")
    if path.exists():
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        for sect, vals in data.items():
            cfg.setdefault(sect, {}).update(vals)
    return cfg


def load_json(name: str) -> dict:
    with open(paths.config_path(name), encoding="utf-8") as fh:
        return json.load(fh)


def load_models() -> dict:
    return load_json("models.json")


def load_qa_floor() -> dict:
    return load_json("qa_floor.json")
