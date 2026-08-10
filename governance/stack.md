# Tech stack — now vs. break-even

## Now (build phase, $0 cash cost)

| Layer | Choice | Why |
|---|---|---|
| Inference | NVIDIA NIM `z-ai/glm-5.2` (free tier ~40 RPM) | Full-precision, 1M context, agentic-coding-tuned. Sufficient for build + Phase 9 self-test. |
| Editor / driver seat | Zed (free) | OpenAI-compatible endpoint, no lock-in. |
| Orchestration | Python stdlib + minimal deps | State machine is a single loop. No framework. |
| Run isolation | `engine/` + `clients/<id>/<run>/` directories | Enables reuse without cloning the engine. Free. |
| State / schemas | JSON Schema, local files | Inspectable, versionable, diffable. |
| Concurrency shaper | `engine/pacing/` — asyncio gate, in-flight cap, exponential backoff on 429/handoff failures. Stdlib only. | Free NIM latency + 40 RPM + retry storms = the engine's first real bottleneck. Don't pre-buy — pre-shape. |
| Browser QA | Playwright (prefer over Selenium — free, MIT, async-native) | Agent-authored E2E against the live app. |
| VCS | Git + GitHub free tier | Reproducibility (Rule 7). |
| Hosting (engine dev) | Local filesystem | No DB, no cloud, no K8s. Rule 6. |

**Cash cost to build engine + run self-test: $0.**

## Break-even stack — add ONLY when observed constraint triggers

Every row below is dormant until its trigger is logged in `reports/inference-environment.md` for a real run. No pre-provisioning (Rule 13).

| Layer | Choice | Trigger to add | Why this order |
|---|---|---|---|
| Local model for BUILDER drafts | Ollama / llama.cpp running `qwen2.5-coder-7b` or `deepseek-coder-v2-lite` locally | Observed NIM wall-clock per run crosses **4 hours** on a non-trivial product | Latency on NIM free is the dominant cost. A local model does the cheap-dollar BUILDER DRAFT work — babysitting test scaffolds, refactors, boilerplate — at zero per-call cost and ~ms latency. **GLM-5.2 via NIM stays the source of truth** for BLUEPRINT, PLAN, final BUILDER delivery, BEHOLDER, QA. Drafts are checked. |
| Broader model menu on NIM | Try `deepseek-v3`, `qwen3-coder`, `llama-3.1-70b` on NIM free as a benchmarked swap | Observed retry rate on `z-ai/glm-5.2` for the SAME task class crosses **30%** over 100 calls | Some sub-tasks (JSON schema validation, simple test diffs) suit a smaller/faster model. Same provider, same key, same `engine/` integration — just a `model_id` knob in config. |
| Paid NIM tier | NVIDIA NIM `z-ai/glm-5.2` paid | Free-tier RPM is the observed bottleneck on a material percentage of runs, not just one | Same integration → flip the tier knob, no code change. Try local-draft + concurrency shaping first. |
| Independent verification (BEHOLDER second opinion) | OpenAI **API**, pay-per-token, budget-capped, BEHOLDER-only | Observed case of same-model blind spot (Rule 13) | Mitigates same-model blind spot. **Do NOT add preemptively.** |
| Human productivity (you, building the engine) | ChatGPT Pro / Claude / any IDE subscription | Whenever it speeds you up | Separate purpose, separate budget. Never enters `engine/` runtime path. |
| GTM hosting for client runs | Free-tier Vercel / Netlify / Cloudflare Pages | Client run needs public URL | Cheap to near-free at v1 scale. Per-run upgrade only when that run's traffic demands it. |
| Persistence for high-volume runs (optional) | SQLite (file-based, $0) — not Postgres/MySQL | A single run's evidence log grows large enough that JSON files become a real observed bottleneck | Still local, still no infra. Don't pre-add. |

## What changed and what didn't

**Changed from original blueprint:**
- Added free, local concurrency shaper to the "now" stack (no new provider, no new dep).
- Added a local small-coder model for BUILDER DRAFT work as the second break-even step (not OpenAI) — because latency, not capability, is the real wall-clock problem on long runs.
- Added a model-menu benchmarking step on NIM free tier before buying paid tier.

**Unchanged:**
- GLM-5.2 on NIM stays source of truth for all verification (BUILDER final, BEHOLDER, QA, BLUEPRINT, PLAN).
- OpenAI is still last, only for BEHOLDER, only after observed same-model blind spot.
- No pre-provisioning (Rule 13) — every addition requires a logged, observed trigger.
- Architecture does not change; only `config/models.json` + an async gate in the orchestrator.
