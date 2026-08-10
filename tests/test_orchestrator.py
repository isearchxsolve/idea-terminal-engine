"""Orchestrator loop tests with canned responders (zero live inference)."""
import json
import sys

import pytest

from engine import orchestrator, run as runmod
from engine.agents import runners
from engine.agents.runners import InferenceCallError
from engine.pacing.budget import BudgetTracker
from engine.pacing.limiter import RateLimiter

OK_CMD = f"{sys.executable} -c \"print('ok')\""
BAD_CMD = f"{sys.executable} -c \"import sys; sys.exit(1)\""


def fast_limiter():
    return RateLimiter(max_in_flight=3, min_interval_seconds=0.0,
                       backoff_base_seconds=0.01, backoff_max_seconds=0.05)


def make_canned(acceptance=OK_CMD, beholder_passed=True,
                final_files=None):
    table = {
        "ORCHESTRATOR": {
            "idea": {"content": "echo app", "validation_status": "distilled"},
            "requirements": {
                "flows": [{"id": "F1", "description": "submit and see it"}],
                "edge_cases": [{"id": "E1"}]}},
        "BLUEPRINT": {"components": ["web"], "interfaces": [],
                      "data_flow": "in->out", "tech_choices": ["python"],
                      "complexity": "standard"},
        "PLAN": {"tasks": [{"id": "T1", "type": "build", "dependencies": [],
                            "acceptance_criteria": [acceptance],
                            "budget": {}}]},
        "BUILDER_DRAFT": {"files": {"app.py": "print('hi')"}},
        "BUILDER_FINAL": {"files": final_files or {"app.py": "print('hi')"}},
        "BEHOLDER": {"passed": beholder_passed},
        "QA": {"tests": [{"id": "q1", "requirement_id": "F1",
                          "assertions": ["displays the message"],
                          "command": OK_CMD}]},
        "REPAIR_DIAG": {"diagnosis": "draft was wrong"},
        "REPAIR_APPLY": {"files": {"app.py": "print('fixed')"}},
        "RELEASE": {"gtm_surface_url": "http://localhost:8000"},
    }

    def canned(role, prompt, context=None, limiter=None, budget=None):
        return json.dumps(table[role])
    return canned


def test_happy_path_to_released(tmp_path, monkeypatch):
    monkeypatch.setattr(runners, "call_model", make_canned())
    rd = runmod.create_run("c", "r1", "Build an echo app", clients_base=tmp_path)
    state = orchestrator.run_to_terminal(
        rd, max_steps=50, limiter=fast_limiter(),
        budget=BudgetTracker(max_inference_calls=200, max_retries_per_task=2))
    assert state == "RELEASED"
    arts = rd / "artifacts"
    for kind in ("idea", "requirements", "architecture", "execution_plan",
                 "verification", "release"):
        assert (arts / f"{kind}.json").exists()
    assert (rd / "workspace" / "app.py").exists()


def test_repair_budget_exhaustion_fails_closed(tmp_path, monkeypatch):
    monkeypatch.setattr(runners, "call_model", make_canned(acceptance=BAD_CMD))
    rd = runmod.create_run("c", "r2", "Build an echo app", clients_base=tmp_path)
    state = orchestrator.run_to_terminal(
        rd, max_steps=20, limiter=fast_limiter(),
        budget=BudgetTracker(max_inference_calls=200, max_retries_per_task=1))
    assert state == "FAILED"


def test_unsafe_model_paths_fail_closed(tmp_path, monkeypatch):
    monkeypatch.setattr(
        runners, "call_model",
        make_canned(final_files={"../evil.py": "x"}))
    rd = runmod.create_run("c", "r3", "Build an echo app", clients_base=tmp_path)
    state = orchestrator.run_to_terminal(
        rd, max_steps=20, limiter=fast_limiter(),
        budget=BudgetTracker(max_inference_calls=200, max_retries_per_task=1))
    assert state == "FAILED"
    assert not (tmp_path / "c" / "r3" / "evil.py").exists()


def test_beholder_rejection_routes_to_repair_then_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(runners, "call_model",
                        make_canned(beholder_passed=False))
    rd = runmod.create_run("c", "r4", "Build an echo app", clients_base=tmp_path)
    state = orchestrator.run_to_terminal(
        rd, max_steps=20, limiter=fast_limiter(),
        budget=BudgetTracker(max_inference_calls=200, max_retries_per_task=1))
    assert state == "FAILED"


def test_missing_secrets_is_inference_failure(monkeypatch):
    monkeypatch.delenv("NIM_API_KEY", raising=False)
    monkeypatch.delenv("OMNIROUTE_API_KEY", raising=False)
    monkeypatch.setattr(runners, "load_secrets", lambda: {})
    with pytest.raises(InferenceCallError):
        runners.call_model("QA", "x", limiter=fast_limiter(),
                           budget=BudgetTracker())
