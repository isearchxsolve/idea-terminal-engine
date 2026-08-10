# Threading contract

## Why two thread classes

A single long-lived chat thread contaminates ideas with each other. State, audit chains, and budget logs get tangled. The fix is structural: **one idea per thread, one thread per idea.**

## Engine thread (this one, persistent)

Scope:
- Designing `engine/` code
- Debugging the state machine, schemas, agents, verify loop
- Running Phase 9 self-test
- Improving the engine itself
- Stack / break-even decisions
- Regression-testing `engine/` after changes

This thread may read and write anywhere under `engine/`, `governance/`, `scripts/`, `tests/`, `reports/`. It does NOT write under `clients/` except when executing a Phase 9 self-test run, in which case it operates only inside `clients/self-test/`.

## Idea threads (one per idea, sealed at terminal state)

Scope:
- Exactly one `clients/<client-id>/<run-id>/` directory
- Operates on that run's state, intake, blueprint, execution, artifacts, verification, logs, reports, gtm

Hard rules:
1. **One idea per thread.** Two ideas in one thread = state and audit contamination. Halt and split.
2. **Engine code is read-only from an idea thread.** Any proposal to edit `engine/` halts the run and surfaces to the operator. Engine work belongs in the engine thread.
3. **Every file op must target `clients/<client-id>/<run-id>/`.** Proposals to write to repo root or `engine/` halt the run.
4. **Never reuse a thread across `RELEASED` / `FAILED`.** Sealed is sealed. Iteration = new run = new thread, pointing at the prior `intake/` file as its source.

## New-idea SOP (operator)

Before starting:
- Engine exists at repo root with `engine/` populated and Phase 9 self-test passed.
- Open Zed with the repo as workspace.

### Step 1 — Capture verbatim
Untouched raw original (Slack text, transcript, napkin typescript, etc.). This is your Phase 1.5 audit anchor.

### Step 2 — Open a NEW thread
Menu → Assistant → New Thread. Do not reuse prior threads.

First message, fill brackets:

```
ENGINE LOCATION: D:\ideation_to_prototype\idea-terminal-engine
ENGINE COMMIT: <run `git rev-parse --short HEAD` and paste; or "latest">
CLIENT ID: <short-slug, e.g. "client-003">
RUN ID: <short-slug, e.g. "run-001">
SOURCE TYPE: <slack | email | transcript | notes | verbal | other>
SOURCE REFERENCE: <who said it, when, how received>

RAW INTAKE (verbatim, untouched):
---
<paste exact original here>
---

Execute: intake capture -> DISTILL -> proceed through state machine until you hit a CRITICAL or IRREVERSIBLE gate. Stop there and ask me.
```

### Step 3 — Watch for the three stop types

| Stop type | Why | Operator action |
|---|---|---|
| `CRITICAL_APPROVAL` | About to do something irreversible (delete, deploy, spend budget, push to public) | Approve with "yes, proceed" or redirect. |
| `BUDGET_EXHAUSTED` | Retry count OR inference-call budget hit (Rule 12) | Bump budget explicitly, or accept `FAILED`. Don't ignore. |
| `COMPLETED` | state = `RELEASED` or `FAILED` | Verify `reports/bootstrap-report.md` exists, verify `state.json` matches final state, close the thread. |

### Step 4 — Seal the run
1. `clients/<client-id>/<run-id>/reports/bootstrap-report.md` exists
2. `state.json` shows `RELEASED` or `FAILED`
3. Close the thread. Do not keep it alive "in case I want to iterate."

A later iteration on the same idea = a new run directory = a new thread, with `intake/` pointing at the prior run's intake artifact as its source/reference.

## Parallelism

Different ideas in different threads at the same time → no cross-contamination, no state collision, because each touches a different `clients/` tree and the same read-only `engine/`.
