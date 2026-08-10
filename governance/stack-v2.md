# Tech stack v2 — routing revision (supersedes stack.md v1)

## Routing rule

**Nemotron only for high-volume roles whose output is mechanically verifiable.
GLM-5.2 for every role where judgment is the product.**

Benchmark basis (Aug 2026): GLM-5.2 leads the Artificial Analysis Intelligence
Index 51 vs 38, wins SWE-Bench Verified and BrowseComp (Nemotron wins 0), and
leads Terminal-Bench 2.0 64% vs 54%. GLM's weakness is latency/throughput on the
free tier, not capability — so offload volume, never judgment.

## Model-role assignment (all NVIDIA NIM free tier, $0)

| Role | Model | Why |
|---|---|---|
| ORCHESTRATOR | `z-ai/glm-5.2` | Control = judgment; low volume |
| BLUEPRINT | `z-ai/glm-5.2` | Few calls, pure judgment |
| PLAN | `z-ai/glm-5.2` | Few calls, decomposition judgment |
| BUILDER draft | `nvidia/nemotron-3-ultra` | High volume; checked by tests + BUILDER_FINAL |
| BUILDER final | `z-ai/glm-5.2` | SWE-Bench leader, source of truth |
| BEHOLDER | `z-ai/glm-5.2` | Verification is judgment; low volume; a 38-index model is too weak to trust as verifier |
| QA (smoke+E2E) | `nvidia/nemotron-3-ultra` | High volume; tests mechanically checked by execution |
| REPAIR diagnosis | `z-ai/glm-5.2` | Root-cause = judgment; bounded by retry budget |
| REPAIR apply | `z-ai/glm-5.2` | Execution = coding |
| RELEASE | `z-ai/glm-5.2` | Low volume assembly |

Drafts + QA authoring are the bulk of call volume, so GLM load still drops
materially while every judgment role stays on the stronger model.

## Why this is not pre-provisioning (Rule 13)

Both models are free-tier NIM endpoints: $0 added. Splitting roles across two free
queues is throughput shaping (same class as the pacing limiter), not a paid
dependency. All paid additions remain dormant per the ladder below.

## Break-even triggers (dormant until observed + logged)

1. **Local draft model (Ollama qwen2.5-coder-7b)** — only if Nemotron on NIM still bottlenecks.
2. **Z.ai direct / OpenRouter prepaid balance** — only if 40 RPM wall-clock still >4h per standard run after this routing.
3. **OpenAI API for BEHOLDER only** — only after an observed same-model blind spot.

## Known limitations (recorded for engine v1)

- BEHOLDER and BUILDER_FINAL both run GLM-5.2: the primary verification axis is
  same-model again (intelligence chosen over diversity). Mitigation path is
  break-even trigger 3; every BEHOLDER verdict is evidence-bound, not vibe-bound.
- QA (Nemotron) is cross-checked by BEHOLDER (GLM-5.2): the Phase 8B
  anti-triviality axis IS cross-model.
