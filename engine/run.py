"""Run directory creation — the ONLY way run directories get made (Rule: isolation)."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from engine import audit, paths
from engine.statemachine import StateMachine

RUN_SUBDIRS = ("intake", "blueprint", "execution", "artifacts",
               "verification", "logs", "reports", "gtm")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_run(client_id, run_id, intake_source, source_type="text",
               source_ref="unknown", clients_base=None):
    """Create a fresh, isolated run tree with verbatim intake + RECEIVED state."""
    base = Path(clients_base) if clients_base is not None else paths.CLIENTS_DIR
    run_dir = base / client_id / run_id
    if run_dir.exists():
        raise FileExistsError(f"run already exists: {run_dir}")
    for sub in RUN_SUBDIRS:
        (run_dir / sub).mkdir(parents=True, exist_ok=True)

    # Phase 1.5: raw, untouched intake capture — the proof of original ask.
    intake_id = f"INT-{uuid.uuid4().hex[:12]}"
    src = Path(intake_source)
    content = src.read_text(encoding="utf-8") if src.is_file() else str(intake_source)
    (run_dir / "intake" / "raw.txt").write_text(content, encoding="utf-8")
    meta = {
        "intake_id": intake_id,
        "timestamp": _now(),
        "source_type": source_type,
        "source_ref": source_ref,
        "client_id": client_id,
        "run_id": run_id,
    }
    (run_dir / "intake" / "meta.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8")

    # RECEIVED state; nothing enters DISTILL directly.
    sm = StateMachine("RECEIVED")
    (run_dir / "state.json").write_text(
        json.dumps({**sm.to_dict(), "updated_at": _now()}, indent=2),
        encoding="utf-8")

    audit.log(run_dir, "run_created", intake_id=intake_id, source_ref=source_ref)
    return run_dir


def load_state(run_dir) -> str:
    data = json.loads((Path(run_dir) / "state.json").read_text(encoding="utf-8"))
    return data["state"]
