# HANDOVER PROMPT — Zcode / next agent

You are taking over **IDEA-TERMINAL-ENGINE** at **v0.1.5**.

- Repo: https://github.com/isearchxsolve/idea-terminal-engine
- Local path: `d:\ideation_to_prototype\idea-terminal-engine`
- Branch: `main`, fully pushed and in sync with origin.

## Verified state (do not rebuild from scratch)

1. `py -m pytest tests/ -q` = **42 passed**.
2. **OmniRoute AI gateway is installed and running locally** on `http://localhost:20128/v1`.
   - NVIDIA NIM provider connected and healthy.
   - Free zero-config provider `oc` available (`oc/nemotron-3-ultra-free`).
3. `config/secrets.json` is present and gitignored. It contains:
   - `OMNIROUTE_BASE_URL` + `OMNIROUTE_API_KEY`
   - `NIM_BASE_URL` + `NIM_API_KEY`
   Do **not** commit this file. Do not overwrite it unless the human tells you to.
4. `config/models.json` is the single source of truth for routing.
5. `engine/agents/runners.py` forces `stream: false` on every request so OmniRoute returns normal JSON.

## Your mission

Finish the live self-test and get the engine from "scaffold green" to "first real run works".

Priority order:

1. `python -m engine.cli doctor` — confirm inference can reach OmniRoute and get a non-empty response.
2. `python -m engine.cli selftest` — run the full pipeline on `scripts/selftest_idea.txt`.
   - This will advance through RECEIVED → DISTILLED → BLUEPRINTED → PLANNED → BUILDING → QA_VERIFYING → RELEASED (or FAILED).
   - If it hits `AWAITING_APPROVAL`, stop and ask the human.
   - If it hits `FAILED`, read `logs/audit.jsonl` and the run's state file, diagnose, fix, retry.
3. Fix any prompt-drift / JSON-shape issues surfaced by the live run. Keep changes minimal.
4. Once selftest reaches `RELEASED`, verify the generated prototype actually runs:
   - Inspect `clients/selftest/st-*/workspace/app.py`.
   - Run the acceptance command produced by the engine and confirm evidence is captured.
5. Update `reports/bootstrap-report.md` with the result and print `BOOTSTRAP_STATUS`.

## Critical rules

- **Fail closed.** A missing secret, malformed JSON, or empty model response is an **inference failure**, not a verification failure. Treat them differently.
- **Do not conflate the two failure classes.** `InferenceCallError` = retry with backoff; `VerificationFailureError` = evidence-backed rejection, trigger repair.
- **Never pad the QA floor.** If coverage is exhausted below the numeric floor, log tension and stop — do not invent tests.
- **Workspace confinement is mandatory.** Model-generated file paths must stay inside the run directory. Reject absolute paths or `..`.
- **Never commit `config/secrets.json`.** It is gitignored. Use `config/secrets.example.json` as the template.
- **Do not change model routing unilaterally.** Use the STOP-AND-ASK protocol below.

## Current routing (source of truth: `config/models.json`)

| Role | Provider | Model | Cost |
|---|---|---|---|
| ORCHESTRATOR, BLUEPRINT, PLAN, BUILDER_FINAL, BEHOLDER, REPAIR_DIAG, REPAIR_APPLY, RELEASE | omniroute | `nvidia/z-ai/glm-5.2` | NIM-billed |
| BUILDER_DRAFT, QA | omniroute | `oc/nemotron-3-ultra-free` | $0 |

Direct `nim` provider is retained as emergency fallback. To use it, change a role's `"provider"` to `"nim"` and `"model"` to bare NIM ids like `z-ai/glm-5.2`.

## Commands you will use

```powershell
# Verify everything is wired
py -m engine.cli doctor

# Run the full selftest
py -m engine.cli selftest

# Inspect a run's state
py -m engine.cli status --client selftest --run st-<timestamp>

# Run unit tests (no live inference)
py -m pytest tests/ -q
```

## STOP-AND-ASK protocol (mandatory)

Before switching models, adding providers, or changing routing, you MUST:

1. Stop the run (enter `AWAITING_APPROVAL` if possible).
2. Log the observation in the run's `logs/audit.jsonl` and `reports/`.
3. Present the observation + options to the human.
4. Wait for a decision. Fail closed while waiting.

Triggers:

- GLM-5.2 wall-clock for a standard run exceeds 4 hours.
- Nemotron free output fails mechanical check on >30% of ≥100 calls of the same task class.
- BEHOLDER misses a bug that a human or later phase catches.
- Persistent 429/throttling not resolved by the limiter's capped backoff.
- Any role needs a model id not in `config/models.json`.
- OmniRoute goes down and you are considering falling back to direct NIM.

## Known limitations

- QA + BEHOLDER are still same-model on the GLM axis for judgment; the anti-triviality cross-check is QA Nemotron vs BEHOLDER GLM.
- Browser E2E testing is not yet wired; QA currently runs whitelisted shell commands.
- Deployment to a public URL is not yet implemented.

## End condition

Report back with:

- Final selftest state (`RELEASED` or `FAILED`).
- Number of inference calls and retries consumed.
- Any bugs fixed and their root cause.
- Whether the generated prototype actually runs when invoked manually.
- A short `BOOTSTRAP_STATUS` line.

Do not start adding new features until the selftest reaches `RELEASED`.
