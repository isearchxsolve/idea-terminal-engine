# IDEA-TERMINAL-ENGINE

An autonomous engine that drives a raw, natural-language idea to a verified, running prototype that also serves as **Go-to-Market Version 1 (GTM v1)**.

Two outcomes are both success for the *service*, even though only one is success for the *idea*:

1. The prototype works and is delivered as a tested, runnable GTM v1 candidate (local run) → client has something real, not a deck.
2. The prototype or the verification process itself surfaces that the idea does not hold up technically → client learns this in weeks, not years, before spending real capital.

## Scope boundary (stated to every client)

The engine verifies **TECHNICAL FEASIBILITY** and produces a **tested, runnable prototype codebase (local run)**.
It does not and cannot guarantee market success. "Verified" means "evidence-backed, working software (local run)" — not "validated business."

----

## Repo layout

```
idea-terminal-engine/
  engine/                 # reusable engine code (shared by all runs, never copied per idea)
    agents/               # ORCHESTRATOR, BUILDER, BEHOLDER, QA, RELEASE prompts + runners
    schemas/              # JSON Schema contracts for all artifacts
    verify/               # evidence validation, anti-triviality, repair loop
    pacing/               # concurrency shaper + call quotas (handles NIM 40 RPM / latency)
    cli.py                # entry point: `python -m engine.cli new ...`, `... step`, `... status`
    statemachine.py       # state + transition validation
    artifacts.py          # artifact read/write/validate
    run.py                # spin up a new run directory tree + RECEIVED state
  clients/                # per-idea area. ONE IDEA = ONE <client>/<run> directory.
    <client-id>/<run-id>/
      intake/             # verbatim raw intake artifact (Phase 1.5)
      state.json          # THIS run's state
      blueprint/          # Architecture + Requirements artifacts
      execution/          # Plans + Tasks
      artifacts/          # Evidence + Verification + Release
      verification/       # QA smoke + E2E results
      logs/               # audit log, inference-call log
      reports/            # bootstrap-report.md for this run
      gtm/                # GTM v1 target area for THIS run (local run until a real deploy target exists)
  governance/             # rules.md, security.md, definition-of-done.md, THREADING.md, PORTABILITY.md
  scripts/                # bootstrap, self-test runners, dev tooling
  tests/                  # engine regression suite (Phase 8)
  reports/                # engine-level reports (env discovery, inference env, bootstrap-report)
```

----

## Two-thread contract (see governance/THREADING.md for full text)

- **Engine thread (this one)** — engine design, debugging, Phase 9 self-test, engine improvements.
- **One new thread per idea** — one idea, one `clients/<id>/<run>/` directory, sealed at `RELEASED` / `FAILED`.

----

## Quick start

```sh
# from repo root
python -m engine.cli new --client client-001 --run run-001 --source path/to/idea.txt --source-type text --source-ref "operator chat 2026-08-10"
python -m engine.cli status --client client-001 --run run-001
python -m engine.cli step  --client client-001 --run run-001
```

## Cash cost

Build + first real client runs on free tier: **$0**. See `governance/stack.md` for the now / break-even tables and the exact trigger that must be logged before any paid row is added.

----

## Status

v0.1 prototype. Engine modules, schemas, state machine, agent-role runners, pacing layer, CLI, tests, and governance docs are in place. Inference call sites are **live via OmniRoute** (OpenAI-compatible adapter, all agent roles routed with fallback chains to NIM). This is a tested, runnable prototype codebase (local run) — no deployed URL exists yet.
