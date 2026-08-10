"""RELEASE gating. Hard gate: RELEASE cannot proceed without both phases."""
from __future__ import annotations

from engine.verify.anti_triviality import check_test_substance


class GateError(Exception):
    pass


def check_release_gates(release_data):
    if not release_data.get("verification_gate_passed"):
        raise GateError("Phase 8 (unit/integration) gate not passed")
    if not release_data.get("qa_gate_passed"):
        raise GateError("Phase 8B (QA) gate not passed")
    return True


def check_qa_floor(tests, requirement_ids, floor_cfg, exemptions=None):
    """Coverage-of-flows gate + count floor + anti-triviality.

    Counts are a floor metric; the gate is coverage of non-exempt flows by
    substantive tests plus the configured minimum count.
    """
    exemptions = set(exemptions or [])
    required = [r for r in requirement_ids if r not in exemptions]
    if not required:
        raise GateError("no non-exempt requirement ids supplied")
    substantive = [t for t in tests
                   if check_test_substance(t, t.get("requirement_id"))]
    covered = {t["requirement_id"] for t in substantive}
    missing = [r for r in required if r not in covered]
    coverage = 1.0 - (len(missing) / len(required))
    floor = (floor_cfg.get("complex_min_tests") if floor_cfg.get("complex")
             else floor_cfg.get("standard_min_tests", 0))
    if len(substantive) < floor:
        raise GateError(
            f"substantive test count {len(substantive)} below floor {floor}"
        )
    if coverage < float(floor_cfg.get("required_flow_coverage", 1.0)):
        raise GateError(
            f"flow coverage {coverage:.2f} below required; uncovered: {missing}"
        )
    return {"substantive_tests": len(substantive), "coverage": coverage,
            "uncovered": missing}
