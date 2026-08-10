# Portability — moving the engine to a new computer

## What is portable

Everything in this repo is local, file-based, and dependency-light. No cloud accounts, no managed services, no infra. Moving computers = moving this directory + installing the runtime prerequisites + carrying your NIM key.

## What you must NOT leave behind on the old machine

- `config/secrets.json` — contains your NIM API key. If you do NOT take it, the new machine cannot inference. If you leave it on the old machine, treat the key as still live until you rotate it on the NVIDIA dashboard.
- `clients/` — every idea, every run, all evidence, all audit logs. This is the IP of the engine's output. Do not lose it.
- `reports/` — engine-level bootstrap report, inference environment audit, self-test results.
- `governance/` — the rules; without it, the engine has no operating contract.

## What you MUST NOT copy to the new machine

- `.venv/`, `__pycache__/`, `node_modules/`, `.pytest_cache/` — regenerated from requirements on the new machine. Carrying them is wasted bytes and version-skew risk on a different OS.
- Any committed secrets. If you accidentally copy `config/secrets.json` over an insecure channel, rotate the NIM key from the NVIDIA console.

## Pre-flight checklist on the new machine (in order)

1. **Install Python 3.11+** (`python --version` to verify)
2. **Install Git** (`git --version`)
3. **Install Node.js 20+** (`node --version`) — required for Playwright browser E2E
4. **Install Playwright browsers** after checkout: `python -m playwright install`
5. **Install GitHub CLI** if you push/pull from GitHub (`gh --version`)
6. **Create the working parent directory** (e.g. `D:\`), copy the `idea-terminal-engine/` folder into it.
7. **Recreate the Python venv:**
   ```
   cd D:\ideaation_to_prototype\idea-terminal-engine
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
8. **Recreate `config/secrets.json`** from your secure copy (or set the key as an env var `NIM_API_KEY`). Never commit this file.
9. **Verify inference reachability:** `python -m engine.cli doctor` — performs Phase 0 + Phase 0.5 environment discovery and a minimal inference call. If it cannot reach the endpoint, fix network / key before running any engine work.
10. **Run Phase 9 self-test** to confirm the engine still works end-to-end on the new box:
   ```
   python -m engine.cli selftest
   ```
   A passing self-test is the only portability proof that matters.

## Portability contract: what the engine guarantees

- **No hostnames burned into code.** NIM endpoint URL lives in `config/models.json` (or env var), not in `engine/`.
- **No absolute paths burned into code.** All paths resolve relative to repo root via `engine/paths.py`.
- **No OS-specific shell calls in the engine hot path.** Lessons for BUILDER may shell out, but the engine core is pure Python stdlib.
- **Single source of truth for engine version:** `engine/VERSION`. Each run records `engine_version` + `engine_commit_sha` in its `reports/bootstrap-report.md`. A run shipped on engine v0.1 is reproducible against engine v0.1 even after you ship v0.2.
- **Deterministic file layout:** `clients/<id>/<run>/` is identical in shape on every machine.

## Migration ≠ upgrade

Moving computers is migration. It is NOT a stealth upgrade.

If the new machine has a newer Python, a newer Playwright, a newer NIM model ID — treat each as a separate change. Bump `engine/VERSION`, re-run Phase 9 self-test, re-run engine regression suite (`tests/`). Only after both pass is the engine considered healthy on the new machine.

## Backup

Minimum backup: zip the repo (excluding `.venv/`, `__pycache__/`, `node_modules/`, `.git/` if you keep a remote) and store on encrypted external drive AND a cloud drive you control. The NIM API key in `config/secrets.json` is the only sensitive byte in that zip.

A clean repo + clean `.venv/` + clean secrets.json = the engine. Everything else is IP and audit history.

## TL;DR

1. Copy `idea-terminal-engine/` (excluding `.venv/`, `__pycache__/`, `node_modules/`).
2. New machine: install Python 3.11+, Git, Node 20+, GitHub CLI.
3. Recreate venv from `requirements.txt`.
4. Restore `config/secrets.json` from secure backup.
5. `python -m engine.cli doctor` then `python -m engine.cli selftest`.
6. If both pass, the engine is alive on the new machine.
