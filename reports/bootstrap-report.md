# Bootstrap Report — idea-terminal-engine

Generated: 2026-08-16 (ZCode gap-closure pass)

## Verdict

```
BOOTSTRAP_STATUS: PARTIAL
```

The engine is **scaffold-green and test-green**, but the live end-to-end
self-test has **not reached RELEASED**. A hard external blocker (the local
OmniRoute gateway is wedged and cannot be restarted without elevated
privileges) prevents live inference, and the engine's own governance
(STOP-AND-ASK) forbids unilaterally falling back to direct NIM.

## What is verified green

| Check | Result |
|---|---|
| Engine unit/regression suite (`pytest tests/`) | **1411 passed** (was: collection error + 7 failed) |
| `engine.cli doctor` — config files | all `ok` (engine.toml, models.json, qa_floor.json, secrets present) |
| `engine.cli doctor` — model routing | 10 roles resolved |
| Direct NVIDIA NIM reachability | **OK** — `/models` returns 102 models |
| OmniRoute gateway (`localhost:20128`) | **FAIL — timed out / wedged** |

### Test-suite fixes applied this pass (committed `67daf29`)

1. `tests/test_schemas_extended.py` — helper builders now merge `**kw` over
   defaults instead of colliding, fixing a collection-time
   `TypeError: got multiple values for keyword argument 'content'`.
2. `tests/test_run_audit_config.py` — default-value assertions now isolate
   `CONFIG_DIR` so the real `config/engine.toml` does not override defaults.
3. `tests/test_verify_layer.py` — corrected a self-contradictory QA-floor
   case `(1,1,1)`: count == floor passes; the floor comes from `floor_cfg`,
   not a module-level constant.

## Self-test run history (15 runs, none RELEASED)

| Run | Final state | Updated |
|---|---|---|
| st-1786381846 | RECEIVED | 2026-08-10T17:10 |
| st-1786382315 | RECEIVED | 2026-08-10T17:18 |
| st-1786382529 | REPAIRING | 2026-08-10T17:23 |
| st-1786382799 | REPAIRING | 2026-08-10T17:33 |
| st-1786383623 | BLUEPRINTED | 2026-08-10T17:42 |
| st-1786384117 | DISTILLED | 2026-08-10T17:48 |
| st-1786384897 | DISTILLED | 2026-08-10T18:01 |
| st-1786407033 | QA_VERIFYING | 2026-08-11T00:15 |
| st-1786407448 | REPAIRING | 2026-08-11T00:23 |
| st-1786409022 | REPAIRING | 2026-08-11T01:13 |
| st-1786412153 | REPAIRING | 2026-08-11T01:55 |
| st-1786413631 | FAILED | 2026-08-11T02:03 |
| st-1786435095 | FAILED | 2026-08-11T08:00 |
| st-1786435668 | QA_VERIFYING | 2026-08-11T08:09 |
| st-1786436056 | BUILDING | 2026-08-11T08:15 |

The furthest any run reached is `QA_VERIFYING` / `BUILDING`. Two runs ended
`FAILED`. No run has sealed at `RELEASED`.

## Blocker: OmniRoute gateway wedged (external, needs human)

- `http://localhost:20128` accepts TCP connections but returns nothing on
  `/v1/models`, `/api/health`, or the dashboard root (30s timeouts).
- The owning process is `node.exe` (PID 19028), running as the **OmniRoute
  Windows service** (`sc query OmniRoute` → RUNNING, StartType Automatic).
- `taskkill`, `Stop-Process`, and `sc stop OmniRoute` all fail with
  **Access is denied** from this (non-elevated) shell.
- Service logs show startup completed normally; the process is wedged at
  runtime, not failing to start.

**Required human action:** restart the OmniRoute service from an elevated
prompt:

```powershell
Restart-Service OmniRoute        # or: sc stop OmniRoute && sc start OmniRoute
```

Then re-run `python -m engine.cli doctor` and confirm `inference: OK`.

## STOP-AND-ASK decision point (per governance/THREADING.md + HANDOVER_ZCODE.md)

The handoff rules list "OmniRoute goes down and you are considering falling
back to direct NIM" as a **mandatory STOP-AND-ASK trigger**. Therefore this
pass did **not** switch routing. Evidence gathered for the decision:

- **Direct NIM is healthy:** `/models` returns 102 models with the configured
  `NIM_API_KEY`.
- **OmniRoute is down** (wedged service, see above).
- Current routing (`config/models.json`) sends all 10 roles through
  `omniroute`/`antigravity`/`agy` providers; direct `nim` is retained only as
  emergency fallback.

**Options for the human:**

1. **Restart OmniRoute** (recommended) — restores the intended routing with no
   config change. Then re-run `python -m engine.cli selftest`.
2. **Fall back to direct NIM** — per the handoff, change each role's
   `"provider"` to `"nim"` and `"model"` to bare NIM ids (e.g. `z-ai/glm-5.2`)
   in `config/models.json`. Only do this after confirming the target models
   exist in the NIM catalog (102 models available). This is a routing change
   and requires explicit approval.

## Definition-of-Done status

| DoD item | Status |
|---|---|
| 1. Repository exists | ✅ |
| 2. Inference env verified reachable + authenticated | ⚠️ NIM yes; OmniRoute wedged |
| 3. State machine tests pass | ✅ |
| 4. Artifact contract tests pass | ✅ |
| 5. Phase 8 tests pass | ✅ (1411 green) |
| 6. QA floor met + anti-triviality | ✅ (covered by green suite) |
| 7. Evidence generated for the above | ✅ (this report + pytest output) |
| 8. Synthetic E2E pipeline reaches GTM v1 release | ❌ blocked (no RELEASED run) |
| 9. Final report at reports/bootstrap-report.md | ✅ (this file) |

## Next actions (in order)

1. Human restarts the OmniRoute service (elevated) — or approves NIM fallback.
2. `python -m engine.cli doctor` → confirm `inference: OK`.
3. `python -m engine.cli selftest` → drive a run to `RELEASED`.
4. Verify the generated prototype runs; capture evidence.
5. Update this report and flip `BOOTSTRAP_STATUS` to `PASS`.
