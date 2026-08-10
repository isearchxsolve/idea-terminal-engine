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


def _parse_simple_toml(text: str) -> dict:
    """Minimal TOML subset: [section] headers and key = value scalars."""
    out: dict = {}
    section = out
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = out.setdefault(line[1:-1].strip(), {})
            continue
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip()
        if val.startswith('"') or val.startswith("'"):
            val = val[1:-1]
        elif val.startswith("[") and val.endswith("]"):
            inner = val[1:-1].strip()
            val = [item.strip().strip('"').strip("'")
                   for item in inner.split(",") if item.strip()] if inner else []
        elif val.lower() in ("true", "false"):
            val = val.lower() == "true"
        else:
            try:
                val = float(val) if "." in val else int(val)
            except ValueError:
                pass
        section[key] = val
    return out


def load_engine_config() -> dict:
    cfg = json.loads(json.dumps(DEFAULTS))  # deep copy of defaults
    path = paths.config_path("engine.toml")
    if path.exists():
        data = _parse_simple_toml(path.read_text(encoding="utf-8"))
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
