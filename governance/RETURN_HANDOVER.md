# RETURN HANDOVER — OmniRoute live inference + Phase 9 self-test

**For:** returning architect agent. **Driver seat: `antigravity/claude-sonnet-4-6`**
via OmniRoute (fastest, best code performance). Fallback to
`antigravity/claude-opus-4-6-thinking` for deep reasoning. See `config/models.json`.
**From:** ground-build + OmniRoute integration session (v0.2.0).

## 1. Current state (verified, evidence-backed)

- Scaffold complete; `py -m pytest tests/ -v` = **42/42 PASS**, zero live inference
  in test suite (all tests use canned responders).
- **OmniRoute v3.8.49** installed as local AI gateway at `http://localhost:20128/v1`.
  Registered as Windows service (auto-start on boot via nssm).
- `config/secrets.json` present (gitignored) with OmniRoute API key.
- Environment variables set permanently (User scope):
  `OMNIROUTE_BASE_URL`, `OMNIROUTE_API_KEY`, `ANTHROPIC_BASE_URL`,
  `ANTHROPIC_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_API_KEY`.
- `python -m engine.cli doctor` passes env/config discovery + **inference LIVE**
  through OmniRoute (probes `/v1/models` and runs a test inference call).
- `python -m engine.cli new` creates RECEIVED runs with verbatim intake + audit.
- `engine/orchestrator.py` (full state loop), `runners.py` (OmniRoute adapter
  with fallback chains), and `evidence_runner.py` are IMPLEMENTED and
  unit-tested. The per-role JSON contracts in orchestrator.py are the spec.

### Verified working models (latency tested 2026-08-11)

| Model | Latency | Role usage |
|-------|---------|------------|
| antigravity/claude-sonnet-4-6 | 3.6s | BLUEPRINT, PLAN, BUILDER_FINAL, REPAIR_APPLY |
| agy/claude-sonnet-4-6 | 4.6s | fallback for above |
| antigravity/claude-opus-4-6-thinking | 5.3s | ORCHESTRATOR, BEHOLDER, RELEASE |
| agy/claude-opus-4-6-thinking | 6.0s | fallback for above |
| agy/gemini-3.6-flash-high | 4.6s | QA fallback |
| antigravity/gemini-3.6-flash-high | 3.3s | BUILDER_DRAFT, QA |
| nvidia/z-ai/glm-5.2 | 6.0s | fallback for reasoning roles |
| auto/coding:free | 4.7s | combo (routes to best free coding model) |

### Providers status

- **OmniRoute**: primary adapter, 18 free providers connected (agy, antigravity,
  nvidia, auto, etc.)
- **NIM direct**: still in models.json as fallback provider entry but all calls
  route through OmniRoute
- **GPT (cx/)**: 429 rate-limited via codex alias; all GPT models need paid keys
  OR codex cooldown
- **Kimi/Qwen**: need paid API keys (Moonshot AI, Alibaba Cloud) — not available
  through free tiers
- **OpenRouter, OpenCode, Cline, xAI**: dead or need payment

## 2. Binding strategy — MODEL ROUTING + STOP-AND-ASK (restate verbatim)

Routing rule: **OmniRoute is the single adapter. Claude (agy/antigravity) for
reasoning and judgment roles. Gemini for speed/volume roles (BUILDER_DRAFT, QA).
GLM-5.2 (nvidia) for diversity fallback.** All calls go through OmniRoute's
fallback chains for resilience. Single source of truth: `config/models.json`.

STOP-AND-ASK PROTOCOL (mandatory): no agent may change model routing, add a
model, or add a provider on its own authority. On any trigger the agent MUST
(1) STOP the run (enter AWAITING_APPROVAL), (2) log the observation (audit log +
reports/), (3) present observation + options to the human operator, (4) WAIT for
a decision; fail closed while waiting. Triggers: (1) any primary model latency
makes a standard run exceed 4h wall-clock; (2) model output fails its mechanical
check on >30% of ≥100 calls of the same task class; (3) observed same-model
blind spot (BEHOLDER misses a real bug); (4) persistent 429 storms not resolved
by capped backoff; (5) any role needs a model id absent from config/models.json;
(6) OmniRoute service stops or becomes unreachable. Dormant break-even additions
(human decision only, in order): local Ollama draft model → paid API keys for
specific providers (OpenAI for BEHOLDER, Moonshot for Kimi) → self-hosted models.

## 3. Remaining steps (you, returning agent) — plumbing is done as of v0.2.0

Your job is live execution and judgment, not plumbing:

1. ~~Create `config/secrets.json`~~ — **DONE**. OmniRoute key is configured.
2. Run `python -m engine.cli doctor` — verify inference check passes (LIVE).
   Record latency and rate-limit observations in `reports/inference-environment.md`.
   STOP if unreachable.
3. Review `runners.py` / `orchestrator.py` / `evidence_runner.py` for contract
   drift against real model output; fix only with evidence (keep 42 tests green).
4. `python -m engine.cli selftest` — Phase 9 synthetic run from
   `scripts/selftest_idea.txt` through to GTM v1 release. For a product this
   small, coverage may exhaust below the numeric floor — the orchestrator
   records that as logged tension (never pads with trivial tests).
5. Update `reports/bootstrap-report.md` with final numbers; print
   `BOOTSTRAP_STATUS: PASS / PARTIAL / FAILED` with the report path.

## 4. Infrastructure notes

- **OmniRoute service management**: `sc query OmniRoute`, `sc stop/start OmniRoute`,
  `nssm edit OmniRoute`. Dashboard: `http://localhost:20128/dashboard`.
- **Full setup script**: `scripts/omniroute_full_setup.py` — one script does
  everything (service install, provider config, env vars, CLI setup).
- **Claude Code CLI** and **Codex CLI** are configured to route through OmniRoute
  via environment variables (no payment needed).

## 5. Hard rules while wiring

- No hardcoded model ids / timeouts / budgets (config only).
- No paid dependency, tier, or routing change without the stop-and-ask protocol.
- Distinguish inference-call failure (`InferenceCallError`) from verification
  failure (`VerificationFailureError`) everywhere. NEVER conflate (Rule 11).
- If something cannot be completed safely: STOP that operation, record why,
  continue independent safe work.
- All inference calls paced via `RateLimiter.acquire()`/`release()`.
- Fallback chains in `config/models.json` ensure resilience when models are
  rate-limited or down.
