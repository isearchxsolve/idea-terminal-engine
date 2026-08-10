# Definition of Done (engine build)

The engine bootstrap is complete only when:

1. The repository exists.
2. The inference environment is verified reachable and authenticated (Phase 0.5).
3. The state machine works (Phase 3 tests pass).
4. Artifact contracts validate (Phase 2 tests pass).
5. Phase 8 tests pass (schemas, state transitions, illegal transitions, evidence validation, retry handling, inference-call-failure vs verification-failure handling, budget exhaustion, failure handling, release gating).
6. Phase 8B QA floor is met WITH the anti-triviality check passing.
7. Evidence is generated for all of the above.
8. The synthetic end-to-end pipeline (Phase 9) executes through to GTM v1 release.
9. The final report exists at `reports/bootstrap-report.md`.

Print at completion:

```
BOOTSTRAP_STATUS:
PASS / PARTIAL / FAILED
```

with path to final report.

## Per-run definition of done

A run is done when `state.json` is `RELEASED` or `FAILED`, the run-level `reports/bootstrap-report.md` exists, and no operation is still in-flight. Sealed runs are read-only.
