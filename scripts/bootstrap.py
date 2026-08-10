"""Bootstrap: Phase 0 env discovery, Phase 0.5 inference check, Phase 8 tests,
Phase 10 report skeleton. No inference calls (scaffold stage)."""
from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine import paths  # noqa: E402


def main() -> int:
    reports = paths.REPORTS_DIR
    reports.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()

    # Phase 0 — environment discovery (read-only).
    env_lines = [
        "# Environment discovery",
        f"- timestamp: {now}",
        f"- os: {platform.platform()}",
        f"- python: {platform.python_version()}",
        f"- git: {shutil.which('git') or 'NOT FOUND'}",
        f"- node: {shutil.which('node') or 'not found'}",
    ]
    (reports / "environment.md").write_text("\n".join(env_lines) + "\n",
                                            encoding="utf-8")

    # Phase 0.5 — inference environment: not wired at scaffold stage.
    (reports / "inference-environment.md").write_text(
        "# Inference environment\n\n"
        "NOT WIRED (scaffold stage). Wire per governance/RETURN_HANDOVER.md; "
        "model routing per governance/MODEL_ROUTING.md. Do not proceed to "
        "Phase 1 of any client run until the inference check passes.\n",
        encoding="utf-8")

    # Phase 8 — run the full test suite as subprocess evidence.
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q"],
        cwd=str(paths.REPO_ROOT), capture_output=True, text=True,
    )
    phase8 = "PASS" if proc.returncode == 0 else "FAIL"

    # Phase 10 — report skeleton (final numbers filled after wiring).
    (reports / "bootstrap-report.md").write_text(
        "# Bootstrap report (scaffold stage)\n\n"
        f"- timestamp: {now}\n"
        f"- Phase 0 environment: recorded (reports/environment.md)\n"
        "- Phase 0.5 inference: NOT WIRED — blocking for client runs\n"
        f"- Phase 8 tests: {phase8}\n"
        "- Phase 8B: pending inference wiring\n"
        "- Phase 9 self-test: pending inference wiring\n"
        "- Known limitations: see governance/stack-v2.md and MODEL_ROUTING.md\n",
        encoding="utf-8")

    print(f"Phase 8 tests: {phase8}")
    print("BOOTSTRAP_STATUS:")
    print("PARTIAL (scaffold complete; inference not wired)")
    return 0 if phase8 == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
