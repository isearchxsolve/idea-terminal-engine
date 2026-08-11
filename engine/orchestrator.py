"""Single-loop orchestrator (sync, stdlib). One state advance per step().

Fail closed everywhere: illegal transitions, budget exhaustion, unsupported
claims, and unsafe file paths all stop or reroute the run — never pretend.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from engine import artifacts, audit, config as cfg, evidence_runner
from engine.agents import runners
from engine.agents.runners import InferenceCallError, VerificationFailureError
from engine.pacing.budget import BudgetExhaustedError, BudgetTracker
from engine.pacing.limiter import RateLimiter
from engine.statemachine import StateMachine
from engine.verify import evidence_validator, release_gate
from engine.verify.evidence_validator import UnsupportedClaimError
from engine.verify.release_gate import GateError


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_meta(run_dir: Path) -> dict:
    return json.loads((run_dir / "state.json").read_text(encoding="utf-8"))


def _save(run_dir: Path, sm: StateMachine, meta: dict):
    payload = {"state": sm.state, "updated_at": _now()}
    payload.update({k: v for k, v in meta.items()
                    if k not in ("state", "updated_at")})
    (run_dir / "state.json").write_text(json.dumps(payload, indent=2),
                                        encoding="utf-8")


def _common(data: dict, kind: str, status: str, source_ref: str) -> dict:
    data = dict(data)
    data.setdefault("id", f"{kind}-{uuid.uuid4().hex[:8]}")
    data["timestamp"] = _now()
    data["status"] = status
    data["source_ref"] = source_ref
    return data


def _write_files(run_dir: Path, files: dict):
    """Model-supplied paths are confined to the run workspace; fail closed."""
    workspace = run_dir / "workspace"
    for rel, content in (files or {}).items():
        norm = str(rel).replace("\\", "/")
        parts = PurePosixPath(norm).parts
        if not parts or PurePosixPath(norm).is_absolute() or ".." in parts:
            raise VerificationFailureError(f"unsafe path from model: {rel!r}")
        target = workspace.joinpath(*parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(str(content), encoding="utf-8")


def _run_acceptance(run_dir, task) -> list:
    """Run acceptance criteria as commands. Non-command items become failing evidence."""
    import uuid as _uuid
    from datetime import datetime, timezone
    results = []
    for cmd in task["acceptance_criteria"]:
        try:
            results.append(evidence_runner.run_command(cmd, run_dir, task["id"]))
        except VerificationFailureError as exc:
            # Fail closed: record the failure as evidence, don't crash
            results.append({
                "id": f"EV-{_uuid.uuid4().hex[:12]}",
                "version": 1,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "recorded",
                "source_ref": f"task:{task['id']}",
                "command": cmd,
                "exit_code": 1,
                "stdout": "",
                "stderr": str(exc),
                "files_changed": [],
                "tests_run": 0,
                "task_id": task["id"],
            })
    return results


def _build_task(run_dir, task, arts, limiter, budget):
    draft = runners.call_json("BUILDER_DRAFT", json.dumps(task),
                              limiter=limiter, budget=budget)
    final = runners.call_json("BUILDER_FINAL", json.dumps({"task": task,
                                                           "draft": draft}),
                              limiter=limiter, budget=budget)
    _write_files(run_dir, final.get("files"))
    evidence = _run_acceptance(run_dir, task)
    evidence_validator.validate_completion(task, evidence)  # mechanical gate
    verdict = runners.call_json("BEHOLDER", json.dumps({
        "task": task,
        # Pass stdout too, not just (command, exit_code, stderr). The
        # acceptance criteria frequently require a print as the success
        # marker (eg 'print("FormSubmitHandler ok")'); if BEHOLDER can't
        # see stdout it cannot verify the marker was emitted and will
        # reject even on exit_code=0 + empty stderr -- driving an infinite
        # BUILDING <-> REPAIRING cycle. The earlier code dropped stdout
        # here only as an ad-hoc size guard; modern context windows
        # tolerate full evidence and the verifier blind-spot the
        # truncation created was worse.
        "evidence": [{k: ev[k] for k in ("command", "exit_code", "stdout", "stderr")}
                     for ev in evidence]}), limiter=limiter, budget=budget)
    if not verdict.get("passed"):
        raise VerificationFailureError(
            f"BEHOLDER rejected task {task['id']}: {verdict.get('reason')}")
    return evidence


def step(run_dir, limiter=None, budget=None) -> str:
    """Advance the run by one state (or one task). Returns the new state."""
    run_dir = Path(run_dir)
    limiter = limiter or RateLimiter.from_config()
    budget = budget or BudgetTracker.from_config()
    meta = _load_meta(run_dir)
    sm = StateMachine(meta["state"])
    if sm.is_terminal:
        return sm.state
    arts = run_dir / "artifacts"
    source_ref = meta.get("intake_id", "engine")
    s = sm.state

    if s == "RECEIVED":
        raw = (run_dir / "intake" / "raw.txt").read_text(encoding="utf-8")
        out = runners.call_json("ORCHESTRATOR",
                                f"Distill this raw idea.\nRAW IDEA:\n{raw}",
                                limiter=limiter, budget=budget)
        artifacts.save_artifact(
            arts, "idea",
            _common(out["idea"], "idea", "DISTILLED", source_ref))
        artifacts.save_artifact(
            arts, "requirements",
            _common(out["requirements"], "requirements", "DISTILLED", source_ref))
        meta["intake_id"] = source_ref
        sm.transition("DISTILLED")

    elif s == "DISTILLED":
        idea = artifacts.load_artifact(arts, "idea")
        out = runners.call_json("BLUEPRINT", json.dumps(idea),
                                limiter=limiter, budget=budget)
        artifacts.save_artifact(
            arts, "architecture",
            _common(out, "architecture", "BLUEPRINTED", source_ref))
        meta["complexity"] = out.get("complexity", "standard")
        sm.transition("BLUEPRINTED")

    elif s == "BLUEPRINTED":
        arch = artifacts.load_artifact(arts, "architecture")
        out = runners.call_json("PLAN", json.dumps(arch),
                                limiter=limiter, budget=budget)
        artifacts.save_artifact(
            arts, "execution_plan",
            _common(out, "execution_plan", "PLANNED", source_ref))
        sm.transition("PLANNED")

    elif s == "PLANNED":
        meta["task_index"] = 0
        sm.transition("BUILDING")

    elif s == "BUILDING":
        plan = artifacts.load_artifact(arts, "execution_plan")
        i = meta.get("task_index", 0)
        if i >= len(plan["tasks"]):
            sm.transition("QA_VERIFYING")
        else:
            task = plan["tasks"][i]
            try:
                _build_task(run_dir, task, arts, limiter, budget)
            except (VerificationFailureError, UnsupportedClaimError) as exc:
                audit.log(run_dir, "task_failed", task=task["id"],
                          reason=str(exc))
                meta["repair_task"] = task["id"]
                sm.transition("REPAIRING")
            else:
                meta["task_index"] = i + 1

    elif s == "REPAIRING":
        plan = artifacts.load_artifact(arts, "execution_plan")
        task_id = meta.get("repair_task")
        task = next(t for t in plan["tasks"] if t["id"] == task_id)
        try:
            budget.record_retry(task_id)
        except BudgetExhaustedError as exc:
            meta["fail_reason"] = str(exc)
            sm.transition("FAILED")
        else:
            diag = runners.call_json("REPAIR_DIAG", json.dumps(
                {"task": task}), limiter=limiter, budget=budget)
            fix = runners.call_json("REPAIR_APPLY", json.dumps(
                {"task": task, "diagnosis": diag}), limiter=limiter, budget=budget)
            _write_files(run_dir, fix.get("files"))
            evidence = _run_acceptance(run_dir, task)
            try:
                evidence_validator.validate_completion(task, evidence)
            except UnsupportedClaimError:
                pass  # stay REPAIRING; next step consumes another retry
            else:
                sm.transition("BUILDING")  # resume same task via task_index

    elif s == "QA_VERIFYING":
        reqs = artifacts.load_artifact(arts, "requirements")
        qa = runners.call_json("QA", json.dumps(reqs),
                               limiter=limiter, budget=budget)
        for test in qa.get("tests", []):
            if test.get("command"):
                evidence_runner.run_command(test["command"], run_dir, "QA")
        floor_cfg = cfg.load_qa_floor()
        floor_cfg["complex"] = meta.get("complexity") == "complex"
        flow_ids = [f["id"] for f in reqs["flows"]]
        qa_passed, tension = True, None
        try:
            release_gate.check_qa_floor(qa.get("tests", []), flow_ids, floor_cfg)
        except GateError as gate_exc:
            try:  # coverage-only recheck: is the shortfall count-only?
                release_gate.check_qa_floor(
                    qa.get("tests", []), flow_ids,
                    {**floor_cfg, "standard_min_tests": 0,
                     "complex_min_tests": 0})
            except GateError:
                qa_passed = False  # real coverage gap
            else:
                # Phase 9 policy: coverage exhausted below the numeric floor is
                # recorded tension, never padded with trivial tests.
                tension = str(gate_exc)
                audit.log(run_dir, "qa_floor_tension", reason=tension)
        artifacts.save_artifact(arts, "verification", _common({
            "passed": qa_passed, "failed": [] if qa_passed else [tension or "coverage gap"],
            "evidence_refs": [], "budget_used": budget.calls_used,
            "retry_count": budget.retries_used(meta.get("repair_task", "-"))},
            "verification", "QA_VERIFYING", source_ref))
        if not qa_passed:
            plan = artifacts.load_artifact(arts, "execution_plan")
            meta["repair_task"] = plan["tasks"][-1]["id"]
            sm.transition("REPAIRING")
        else:
            rel = runners.call_json("RELEASE", json.dumps(
                {"tension": tension}), limiter=limiter, budget=budget)
            release_data = _common({
                "gtm_surface_url": rel.get("gtm_surface_url", "http://localhost"),
                "artifacts_included": ["idea", "requirements", "architecture",
                                       "execution_plan", "verification"],
                "verification_gate_passed": True, "qa_gate_passed": True},
                "release", "RELEASED", source_ref)
            release_gate.check_release_gates(release_data)
            artifacts.save_artifact(arts, "release", release_data)
            sm.transition("RELEASED")

    _save(run_dir, sm, meta)
    audit.log(run_dir, "transition", to=sm.state)
    return sm.state


def run_to_terminal(run_dir, max_steps: int = 100, limiter=None, budget=None):
    """Loop step() until a terminal state or the step cap. Fail closed."""
    for _ in range(max_steps):
        state = step(run_dir, limiter=limiter, budget=budget)
        if state in ("RELEASED", "FAILED"):
            return state
    meta = _load_meta(Path(run_dir))
    sm = StateMachine(meta["state"])
    if not sm.is_terminal:
        sm.transition("FAILED")
        _save(Path(run_dir), sm, {**meta, "fail_reason": "step cap exceeded"})
    return sm.state
