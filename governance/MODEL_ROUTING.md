# Model routing strategy + stop-and-ask protocol (binding on every agent)

## Routing rule

**Nemotron only for high-volume roles whose output is mechanically verifiable
(BUILDER_DRAFT, QA). GLM-5.2 for every role where judgment is the product
(ORCHESTRATOR, BLUEPRINT, PLAN, BUILDER_FINAL, BEHOLDER, REPAIR_DIAG,
REPAIR_APPLY, RELEASE).** Single source of truth: `config/models.json`.

As of v0.1.5 all calls go through the local **OmniRoute** gateway on
`http://localhost:20128/v1`:

- `BUILDER_DRAFT` / `QA` use the zero-config free provider `oc/nemotron-3-ultra-free`.
- All judgment roles use `nvidia/z-ai/glm-5.2` (still billed to your NIM key, but
  queued/rated/failover-managed by the gateway).
- The direct `nim` provider is retained in `config/models.json` as an emergency
  fallback: change a role's `"provider"` back to `"nim"` and its `"model"` to the
  bare NIM id if OmniRoute is down.

## Benchmark basis (Aug 2026)

- Artificial Analysis Intelligence Index: GLM-5.2 = 51 vs Nemotron-3-Ultra = 38.
- GLM wins SWE-Bench Verified and BrowseComp; Nemotron wins 0 benchmarks.
- Terminal-Bench 2.0: GLM 64% vs Nemotron 54%.
- GLM's constraint is free-tier latency/throughput, not capability.
  Therefore: offload volume, never judgment.

## Driver-seat assignment

The agent that wires inference and runs the Phase 9 self-test (the next
handover) MUST run on GLM-5.2: low-volume, high-stakes agentic coding is
exactly the axis GLM leads. Nemotron stays inside the engine, on the two
mechanically-checked volume roles only.

## STOP-AND-ASK PROTOCOL (mandatory)

No agent may change model routing, add a model, or add a provider on its own
authority (extends General Rule 13). On any trigger below the agent MUST:

1. STOP the run (enter `AWAITING_APPROVAL`),
2. log the observation (audit log + `reports/`),
3. present the observation and the options to the human operator,
4. WAIT for a decision. Fail closed while waiting — never improvise a swap.

Triggers (each requires an observed, logged event, never a prediction):

1. GLM-5.2 latency makes a standard run's wall-clock exceed 4 hours.
2. Nemotron output fails its mechanical check on >30% of ≥100 calls of the
   same task class (drafts or QA authoring).
3. Observed same-model blind spot: BEHOLDER misses a real bug that a human or
   a later phase catches.
4. Persistent 429 / throttling storms not resolved by the pacing limiter's
   capped backoff.
5. Any role requires a model id not present in `config/models.json`.

Dormant break-even additions (human decision only, in this order):
additional OmniRoute free providers (Antigravity, OpenRouter free tier) →
local Ollama draft model → Z.ai direct / OpenRouter prepaid balance →
OpenAI API for BEHOLDER only.

This protocol is part of the sign-off / return handover prompt: every handover
must restate it verbatim.
