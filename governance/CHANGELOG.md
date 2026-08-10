# Changelog

## v0.1.5 — OmniRoute gateway integration (credit-saver pass)

- Installed and running OmniRoute AI gateway locally on `http://localhost:20128/v1`.
- `config/models.json`: added `omniroute` provider as the primary adapter; NVIDIA NIM
  kept as direct fallback provider.
- Free zero-config roles: `BUILDER_DRAFT` and `QA` now route to
  `oc/nemotron-3-ultra-free` (zero-cost via OmniRoute/OpenCode free tier).
- Judgment roles route to `nvidia/z-ai/glm-5.2` through the gateway (uses existing
  NIM key, but gains queue/rate/failover management).
- `engine/agents/runners.py`: request body now forces `stream: false` so the gateway
  returns a standard JSON completion instead of SSE chunks.
- `config/secrets.example.json` documents both `OMNIROUTE_*` and `NIM_*` keys.
- Live verification: free Nemotron call completed through gateway in 126 ms at $0.
- Tests: 42 passed.

## v0.1.4 — orchestrator + inference client implemented (headroom pass)

- engine/agents/runners.py: real OpenAI-compatible NIM client (stdlib urllib),
  paced + budgeted per call, strict error classification; call_json for
  contract-parsed responses (malformed JSON = inference failure).
- engine/orchestrator.py: full single-loop state driver (RECEIVED -> RELEASED)
  with workspace-confined model file writes, mechanical evidence gates,
  BEHOLDER verdicts, bounded repair, and the Phase 9 QA-floor tension policy.
- engine/evidence_runner.py: whitelisted, shell-free, timeout-bounded command
  execution producing Evidence artifacts.
- Limiter rewritten sync (threading); config gains [inference] and [exec].
- GLM handover reduced to: secrets, review, doctor, live selftest, debug.

## v0.1.3 — stop-and-ask model-switch protocol

- Added governance/MODEL_ROUTING.md: routing rule (Nemotron = volume-only,
  mechanically checked; GLM-5.2 = judgment), driver-seat assignment (next
  handover on GLM-5.2), and a mandatory stop-and-ask protocol: no agent changes
  routing unilaterally; observed triggers force AWAITING_APPROVAL + human decision.

## v0.1.2 — routing revision on benchmark data

- Benchmark data (AA Intelligence Index 51 vs 38; GLM wins SWE-Bench Verified +
  BrowseComp; Terminal-Bench 64% vs 54%) shows Nemotron too weak for judgment roles.
- New routing rule: Nemotron only for high-volume, mechanically-verifiable roles
  (BUILDER_DRAFT, QA). BEHOLDER / BLUEPRINT / PLAN / REPAIR_DIAG return to GLM-5.2.
- Known-limitation update: primary verification axis same-model again (documented);
  anti-triviality axis now cross-model (QA Nemotron vs BEHOLDER GLM-5.2).

## v0.1.1 — scaffold completion (ground build)

- Added `AWAITING_APPROVAL` state to the state machine: human gate for
  critical/irreversible actions; transitions back to BUILDING / QA_VERIFYING /
  REPAIRING, or to FAILED.
- Added `engine/audit.py` — append-only JSONL audit log per run (General Rule 8).
- QA floor is a coverage-of-flows gate: `required_flow_coverage = 1.0` with explicit,
  logged exemptions only; numeric counts (200 standard / 500 complex) are a floor
  metric, never the gate by itself (anti-triviality still mandatory).
- Recorded known limitation: QA + BEHOLDER both on Nemotron (anti-triviality axis
  still same-model); BEHOLDER vs BUILDER_FINAL now cross-model.
- Reconciled governance: `stack-v2.md` supersedes `stack.md` v1; model IDs
  standardized on `z-ai/glm-5.2` (retained roles) + `nvidia/nemotron-3-ultra`.

## v0.1.0 — Nemotron shift applied

- GLM-5.2 retained for ORCHESTRATOR / BUILDER_FINAL / REPAIR_APPLY / RELEASE;
  Nemotron-3-Ultra takes reasoning-heavy and high-volume draft roles.
