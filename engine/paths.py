"""Path resolution — single source of truth for filesystem locations.

No absolute paths anywhere else in engine code. Everything derives from
the engine root, computed by walking up from this file.
"""
from __future__ import annotations

from pathlib import Path

# engine/paths.py -> engine/ -> repo root
ENGINE_DIR = Path(__file__).resolve().parent
REPO_ROOT = ENGINE_DIR.parent

# Engine-internal
SCHEMAS_DIR = ENGINE_DIR / "schemas"
AGENTS_DIR = ENGINE_DIR / "agents"
VERIFY_DIR = ENGINE_DIR / "verify"
PACING_DIR = ENGINE_DIR / "pacing"

# Shared, engine-level
CLIENTS_DIR = REPO_ROOT / "clients"
GOVERNANCE_DIR = REPO_ROOT / "governance"
SCRIPTS_DIR = REPO_ROOT / "scripts"
TESTS_DIR = REPO_ROOT / "tests"
REPORTS_DIR = REPO_ROOT / "reports"
CONFIG_DIR = REPO_ROOT / "config"


def run_dir(client_id: str, run_id: str) -> Path:
    """Per-run root directory.

    This is the ONLY place that knows the run layout. Every caller must use it.
    """
    return CLIENTS_DIR / client_id / run_id


def run_subdir(client_id: str, run_id: str, name: str) -> Path:
    """A known sub-directory of a run."""
    name = name.rstrip("/")
    if name not in {
        "intake", "blueprint", "execution", "artifacts",
        "verification", "logs", "reports", "gtm",
    }:
        raise ValueError(f"unknown run subdir: {name!r}")
    return run_dir(client_id, run_id) / name


def ensure_run_dirs(client_id: str, run_id: str) -> None:
    """Create the full run directory tree. Idempotent."""
    base = run_dir(client_id, run_id)
    for sub in ("intake", "blueprint", "execution", "artifacts",
                "verification", "logs", "reports", "gtm"):
        (base / sub).mkdir(parents=True, exist_ok=True)


def config_path(name: str) -> Path:
    return CONFIG_DIR / name
