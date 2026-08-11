"""Safe command execution -> Evidence artifacts.

No shell, whitelisted executables only, run inside the run workspace,
timeout-bounded. Fail closed: disallowed or timed-out commands produce
failing evidence, never silent success.
"""
from __future__ import annotations

import os
import shlex
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from engine import config as cfg
from engine.agents.runners import VerificationFailureError

CAP = 20000


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_command(cmd, run_dir, task_id) -> dict:
    exec_cfg = cfg.load_engine_config().get("exec", {})
    allowed = exec_cfg.get("allowed_commands", ["python", "py", "node", "npx"])
    timeout = int(exec_cfg.get("timeout_seconds", 120))

    # posix split with escapes disabled: keeps Windows backslash paths intact
    # while still honoring quotes around arguments.
    lex = shlex.shlex(cmd, posix=True)
    lex.whitespace_split = True
    lex.escape = ""
    argv = list(lex)
    if not argv:
        raise VerificationFailureError("empty command")
    base = os.path.basename(argv[0]).replace(".exe", "")
    if base not in allowed:
        raise VerificationFailureError(f"command not allowed: {base!r}")
    if base in ("python", "py"):
        argv[0] = sys.executable
    elif base == "pytest":
        argv = [sys.executable, "-m", "pytest"] + argv[1:]

    workspace = Path(run_dir) / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    try:
        proc = subprocess.run(argv, cwd=str(workspace), capture_output=True,
                              text=True, timeout=timeout, shell=False)
        code, out, err = proc.returncode, proc.stdout, proc.stderr
    except (subprocess.TimeoutExpired, OSError) as exc:
        code, out, err = 124, "", f"execution failure: {exc}"

    return {
        "id": f"EV-{uuid.uuid4().hex[:12]}",
        "version": 1,
        "timestamp": _now(),
        "status": "recorded",
        "source_ref": f"task:{task_id}",
        "command": cmd,
        "exit_code": code,
        "stdout": out[:CAP],
        "stderr": err[:CAP],
        "files_changed": [],
        "tests_run": 0,
        "task_id": task_id,
    }
