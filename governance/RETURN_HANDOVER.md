# RETURN HANDOVER — inference wiring + Phase 9 self-test

**For:** returning architect agent. **Driver seat: GLM-5.2** (see MODEL_ROUTING.md).
**From:** ground-build scaffold session (v0.1.3).

## 1. Current state (verified, evidence-backed)

- Scaffold complete; `py -m pytest tests/ -v` = 37/37 PASS, zero inference calls.
  (Use the `py` launcher: system Python 3.11.9 has pytest; the hermes venv
  `python` has neither pip nor pytest.)
- `python -m engine.cli doctor` passes env/config discovery; inference = NOT WIRED.
- `python -m engine.cli new --client test --run r1 --source scripts/selftest_idea.txt
  --source-type text --source-ref handover` creates `clients/test/r1/` in RECEIVED
  with verbatim intake + audit log.
- `scripts/bootstrap.py` writes reports/environment.md, inference-environment.md
  (NOT WIRED), bootstrap-report.md (PARTIAL).
- v0.1.4: `engine/orchestrator.py` (full state loop), the real NIM client in
  `runners.py`, and `evidence_runner.py` are IMPLEMENTED and unit-tested with
  canned responders (42 tests, zero live inference). The per-role JSON
  contracts in orchestrator.py are the spec.

## 2. Binding strategy — MODEL ROUTING + STOP-AND-ASK (restate verbatim)

Routing rule: **Nemotron only for high-volume roles whose output is mechanically
verifiable (BUILDER_DRAFT, QA). GLM-5.2 for every role where judgment is the
product (ORCHESTRATOR, BLUEPRINT, PLAN, BUILDER_FINAL, BEHOLDER, REPAIR_DIAG,
REPAIR_APPLY, RELEASE).** Single source of truth: `config/models.json`.

STOP-AND-ASK PROTOCOL (mandatory): no agent may change model routing, add a
model, or add a provider on its own authority. On any trigger the agent MUST
(1) STOP the run (enter AWAITING_APPROVAL), (2) log the observation (audit log +
reports/), (3) present observation + options to the human operator, (4) WAIT for
a decision; fail closed while waiting. Triggers: (1) GLM latency makes a standard
run exceed 4h wall-clock; (2) Nemotron output fails its mechanical check on >30%
of ≥100 calls of the same task class; (3) observed same-model blind spot
(BEHOLDER misses a real bug); (4) persistent 429 storms not resolved by capped
backoff; (5) any role needs a model id absent from config/models.json. Dormant
break-even additions (human decision only, in order): local Ollama draft model →
Z.ai direct / OpenRouter prepaid balance → OpenAI API for BEHOLDER only.

## 3. Remaining steps (you, GLM-5.2) — plumbing is done as of v0.1.4

Your job is live execution and judgment, not plumbing:

1. Create `config/secrets.json` from `config/secrets.example.json` (gitignored;
   never commit; never log keys).
2. Review runners.py / orchestrator.py / evidence_runner.py for contract drift
   against real model output; fix only with evidence (keep tests green).
3. `python -m engine.cli doctor` → inference check must pass (minimal test call,
   record rate limits in reports/inference-environment.md). STOP if unreachable.
4. `python -m engine.cli selftest` → Phase 9 synthetic run from
   `scripts/selftest_idea.txt` through to GTM v1 release. For a product this
   small, coverage may exhaust below the numeric floor — the orchestrator
   records that as logged tension (never pads with trivial tests).
5. Update `reports/bootstrap-report.md` with final numbers; print
   `BOOTSTRAP_STATUS: PASS / PARTIAL / FAILED` with the report path.

## 4. Hard rules while wiring

- No hardcoded model ids / timeouts / budgets (config only).
- No paid dependency, tier, or routing change without the stop-and-ask protocol.
- Distinguish inference-call failure from verification failure everywhere.
- If something cannot be completed safely: STOP that operation, record why,
  continue independent safe work.
