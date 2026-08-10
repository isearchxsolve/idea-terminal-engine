"""Append-only audit log per run (General Rule 8)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def log(run_dir, event: str, **fields) -> dict:
    logs = Path(run_dir) / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    entry = {"timestamp": _now(), "event": event}
    entry.update(fields)
    with open(logs / "audit.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")
    return entry
