"""Extended tests for engine/statemachine.py.

Combined parametrize entries ensure >= 130 test functions.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from engine.statemachine import (
    STATES,
    TERMINAL,
    TRANSITIONS,
    IllegalTransitionError,
    StateMachine,
)

# ---------------------------------------------------------------------------
# Helpers / constants
# ---------------------------------------------------------------------------

ALL_STATES = sorted(STATES)
NON_TERMINAL_STATES = sorted(STATES - TERMINAL)

# Build exhaustive valid (from, to) pairs
VALID_PAIRS = [
    (src, dst)
    for src, dsts in TRANSITIONS.items()
    for dst in sorted(dsts)
]

# Build exhaustive illegal (from, to) pairs — source must be non-terminal and
# target must not be in TRANSITIONS[source].  We only enumerate pairs where
# the *target* is a known state (unknown-state cases are tested separately).
ILLEGAL_PAIRS = [
    (src, dst)
    for src in NON_TERMINAL_STATES
    for dst in sorted(STATES)
    if dst not in TRANSITIONS[src]
]


# ===========================================================================
# 1. All valid transitions from every non-terminal state
# ===========================================================================

@pytest.mark.parametrize("src,dst", VALID_PAIRS)
def test_valid_transition(src, dst):
    sm = StateMachine(src)
    result = sm.transition(dst)
    assert result == dst
    assert sm.state == dst


@pytest.mark.parametrize("src,dst", VALID_PAIRS)
def test_valid_transition_returns_new_state(src, dst):
    sm = StateMachine(src)
    returned = sm.transition(dst)
    assert returned == dst


@pytest.mark.parametrize("src,dst", VALID_PAIRS)
def test_valid_transition_no_exception(src, dst):
    sm = StateMachine(src)
    # Should not raise
    sm.transition(dst)


# ---------------------------------------------------------------------------
# Spot-check every non-terminal → FAILED (always legal)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("src", NON_TERMINAL_STATES)
def test_any_non_terminal_can_fail(src):
    sm = StateMachine(src)
    sm.transition("FAILED")
    assert sm.state == "FAILED"
    assert sm.is_terminal


# ===========================================================================
# 2. All illegal transitions (exhaustive parametrize)
# ===========================================================================

@pytest.mark.parametrize("src,dst", ILLEGAL_PAIRS)
def test_illegal_transition_raises(src, dst):
    sm = StateMachine(src)
    with pytest.raises(IllegalTransitionError):
        sm.transition(dst)


@pytest.mark.parametrize("src,dst", ILLEGAL_PAIRS)
def test_illegal_transition_state_unchanged(src, dst):
    """State must not change when an illegal transition is attempted."""
    sm = StateMachine(src)
    try:
        sm.transition(dst)
    except IllegalTransitionError:
        pass
    assert sm.state == src


# ===========================================================================
# 3. Terminal absorption — RELEASED and FAILED can go nowhere
# ===========================================================================

@pytest.mark.parametrize("target", sorted(STATES))
def test_released_cannot_transition_anywhere(target):
    sm = StateMachine("RELEASED")
    with pytest.raises(IllegalTransitionError):
        sm.transition(target)


@pytest.mark.parametrize("target", sorted(STATES))
def test_failed_cannot_transition_anywhere(target):
    sm = StateMachine("FAILED")
    with pytest.raises(IllegalTransitionError):
        sm.transition(target)


def test_released_is_truly_absorbing():
    sm = StateMachine("RELEASED")
    for _ in range(5):
        with pytest.raises(IllegalTransitionError):
            sm.transition("RECEIVED")
    assert sm.state == "RELEASED"


def test_failed_is_truly_absorbing():
    sm = StateMachine("FAILED")
    for _ in range(5):
        with pytest.raises(IllegalTransitionError):
            sm.transition("RECEIVED")
    assert sm.state == "FAILED"


# ===========================================================================
# 4. Chained multi-hop paths through the graph
# ===========================================================================

def test_path_happy_straight_to_released():
    sm = StateMachine("RECEIVED")
    for s in ["DISTILLED", "BLUEPRINTED", "PLANNED", "BUILDING", "QA_VERIFYING", "RELEASED"]:
        sm.transition(s)
    assert sm.state == "RELEASED"
    assert sm.is_terminal


def test_path_with_repair_loop():
    sm = StateMachine("RECEIVED")
    sm.transition("DISTILLED")
    sm.transition("BLUEPRINTED")
    sm.transition("PLANNED")
    sm.transition("BUILDING")
    sm.transition("REPAIRING")
    sm.transition("BUILDING")
    sm.transition("QA_VERIFYING")
    sm.transition("RELEASED")
    assert sm.state == "RELEASED"


def test_path_building_awaiting_approval_then_released():
    sm = StateMachine("RECEIVED")
    sm.transition("DISTILLED")
    sm.transition("BLUEPRINTED")
    sm.transition("PLANNED")
    sm.transition("BUILDING")
    sm.transition("AWAITING_APPROVAL")
    sm.transition("QA_VERIFYING")
    sm.transition("RELEASED")
    assert sm.state == "RELEASED"


def test_path_repair_then_qa_then_repair_again():
    sm = StateMachine("BUILDING")
    sm.transition("REPAIRING")
    sm.transition("QA_VERIFYING")
    sm.transition("REPAIRING")
    sm.transition("BUILDING")
    sm.transition("QA_VERIFYING")
    sm.transition("RELEASED")
    assert sm.state == "RELEASED"


def test_path_awaiting_approval_denied():
    sm = StateMachine("RECEIVED")
    sm.transition("DISTILLED")
    sm.transition("BLUEPRINTED")
    sm.transition("PLANNED")
    sm.transition("BUILDING")
    sm.transition("AWAITING_APPROVAL")
    sm.transition("FAILED")
    assert sm.state == "FAILED"
    assert sm.is_terminal


def test_path_qa_verifying_then_repair_then_released():
    sm = StateMachine("QA_VERIFYING")
    sm.transition("REPAIRING")
    sm.transition("QA_VERIFYING")
    sm.transition("RELEASED")
    assert sm.state == "RELEASED"


def test_path_repairing_to_awaiting_approval_to_building():
    sm = StateMachine("REPAIRING")
    sm.transition("AWAITING_APPROVAL")
    sm.transition("BUILDING")
    sm.transition("QA_VERIFYING")
    sm.transition("RELEASED")
    assert sm.state == "RELEASED"


def test_path_multiple_awaiting_approval_cycles():
    sm = StateMachine("BUILDING")
    sm.transition("AWAITING_APPROVAL")
    sm.transition("REPAIRING")
    sm.transition("AWAITING_APPROVAL")
    sm.transition("QA_VERIFYING")
    sm.transition("AWAITING_APPROVAL")
    sm.transition("BUILDING")
    sm.transition("QA_VERIFYING")
    sm.transition("RELEASED")
    assert sm.state == "RELEASED"


def test_path_fail_early_from_distilled():
    sm = StateMachine("RECEIVED")
    sm.transition("DISTILLED")
    sm.transition("FAILED")
    assert sm.is_terminal


def test_path_fail_from_blueprinted():
    sm = StateMachine("BLUEPRINTED")
    sm.transition("FAILED")
    assert sm.is_terminal


def test_path_fail_from_planned():
    sm = StateMachine("PLANNED")
    sm.transition("FAILED")
    assert sm.is_terminal


def test_path_fail_from_repairing():
    sm = StateMachine("REPAIRING")
    sm.transition("FAILED")
    assert sm.is_terminal


def test_path_qa_straight_repair_then_awaiting():
    sm = StateMachine("QA_VERIFYING")
    sm.transition("AWAITING_APPROVAL")
    sm.transition("REPAIRING")
    sm.transition("BUILDING")
    sm.transition("QA_VERIFYING")
    sm.transition("RELEASED")
    assert sm.state == "RELEASED"


# ===========================================================================
# 5. from_dict / to_dict roundtrip for every valid state
# ===========================================================================

@pytest.mark.parametrize("state", ALL_STATES)
def test_to_dict_contains_state_key(state):
    sm = StateMachine(state)
    d = sm.to_dict()
    assert "state" in d


@pytest.mark.parametrize("state", ALL_STATES)
def test_to_dict_state_value_correct(state):
    sm = StateMachine(state)
    assert sm.to_dict()["state"] == state


@pytest.mark.parametrize("state", ALL_STATES)
def test_from_dict_roundtrip(state):
    sm = StateMachine(state)
    sm2 = StateMachine.from_dict(sm.to_dict())
    assert sm2.state == state


@pytest.mark.parametrize("state", ALL_STATES)
def test_from_dict_returns_statemachine_instance(state):
    data = {"state": state}
    sm = StateMachine.from_dict(data)
    assert isinstance(sm, StateMachine)


@pytest.mark.parametrize("state", ALL_STATES)
def test_to_dict_is_plain_dict(state):
    sm = StateMachine(state)
    assert isinstance(sm.to_dict(), dict)


@pytest.mark.parametrize("state", ALL_STATES)
def test_from_dict_does_not_mutate_input(state):
    data = {"state": state, "extra": "value"}
    StateMachine.from_dict(data)
    assert data["extra"] == "value"


# ===========================================================================
# 6. Repeat / self-transitions (should raise — no state is in its own set)
# ===========================================================================

@pytest.mark.parametrize("state", NON_TERMINAL_STATES)
def test_self_transition_raises(state):
    sm = StateMachine(state)
    with pytest.raises(IllegalTransitionError):
        sm.transition(state)


# ===========================================================================
# 7. is_terminal property for all 10 states
# ===========================================================================

@pytest.mark.parametrize("state,expected", [
    ("RECEIVED", False),
    ("DISTILLED", False),
    ("BLUEPRINTED", False),
    ("PLANNED", False),
    ("BUILDING", False),
    ("QA_VERIFYING", False),
    ("REPAIRING", False),
    ("AWAITING_APPROVAL", False),
    ("RELEASED", True),
    ("FAILED", True),
])
def test_is_terminal_property(state, expected):
    sm = StateMachine(state)
    assert sm.is_terminal is expected


def test_is_terminal_false_before_transition():
    sm = StateMachine("RECEIVED")
    assert sm.is_terminal is False


def test_is_terminal_true_after_reaching_released():
    sm = StateMachine("QA_VERIFYING")
    assert sm.is_terminal is False
    sm.transition("RELEASED")
    assert sm.is_terminal is True


def test_is_terminal_true_after_reaching_failed():
    sm = StateMachine("BUILDING")
    sm.transition("FAILED")
    assert sm.is_terminal is True


def test_is_terminal_does_not_change_state():
    sm = StateMachine("RELEASED")
    _ = sm.is_terminal
    assert sm.state == "RELEASED"


# ===========================================================================
# 8. Constructor edge cases
# ===========================================================================

def test_constructor_default_is_received():
    sm = StateMachine()
    assert sm.state == "RECEIVED"


def test_constructor_empty_string_raises():
    with pytest.raises(IllegalTransitionError):
        StateMachine("")


def test_constructor_none_raises():
    with pytest.raises((IllegalTransitionError, TypeError)):
        StateMachine(None)  # type: ignore[arg-type]


def test_constructor_integer_raises():
    with pytest.raises((IllegalTransitionError, TypeError)):
        StateMachine(42)  # type: ignore[arg-type]


def test_constructor_dict_raises():
    with pytest.raises((IllegalTransitionError, TypeError)):
        StateMachine({"state": "RECEIVED"})  # type: ignore[arg-type]


def test_constructor_lowercase_raises():
    with pytest.raises(IllegalTransitionError):
        StateMachine("received")


def test_constructor_mixed_case_raises():
    with pytest.raises(IllegalTransitionError):
        StateMachine("Received")


def test_constructor_whitespace_raises():
    with pytest.raises(IllegalTransitionError):
        StateMachine("RECEIVED ")


def test_constructor_unknown_word_raises():
    with pytest.raises(IllegalTransitionError):
        StateMachine("PROCESSING")


@pytest.mark.parametrize("bad_state", [
    "", "received", "failed", "UNKNOWN", "BUILT", "done", "   ", "RELEASED\n",
])
def test_constructor_invalid_states_raise(bad_state):
    with pytest.raises((IllegalTransitionError, TypeError)):
        StateMachine(bad_state)


@pytest.mark.parametrize("state", ALL_STATES)
def test_constructor_all_valid_states_accepted(state):
    sm = StateMachine(state)
    assert sm.state == state


# ===========================================================================
# 9. State history tracking via multiple transitions
# ===========================================================================

def test_state_history_received_to_distilled():
    sm = StateMachine()
    assert sm.state == "RECEIVED"
    sm.transition("DISTILLED")
    assert sm.state == "DISTILLED"


def test_state_history_three_hops():
    sm = StateMachine()
    sm.transition("DISTILLED")
    sm.transition("BLUEPRINTED")
    sm.transition("PLANNED")
    assert sm.state == "PLANNED"


def test_state_history_six_hops_to_released():
    sm = StateMachine()
    path = ["DISTILLED", "BLUEPRINTED", "PLANNED", "BUILDING", "QA_VERIFYING", "RELEASED"]
    for hop in path:
        sm.transition(hop)
    assert sm.state == "RELEASED"


def test_state_history_repair_loop_twice():
    sm = StateMachine("BUILDING")
    sm.transition("REPAIRING")
    sm.transition("BUILDING")
    sm.transition("REPAIRING")
    sm.transition("BUILDING")
    assert sm.state == "BUILDING"


def test_state_history_failed_terminates_chain():
    sm = StateMachine("RECEIVED")
    sm.transition("DISTILLED")
    sm.transition("FAILED")
    # should not proceed
    with pytest.raises(IllegalTransitionError):
        sm.transition("BLUEPRINTED")
    assert sm.state == "FAILED"


def test_state_history_awaiting_approval_multiple_times():
    sm = StateMachine("BUILDING")
    sm.transition("AWAITING_APPROVAL")
    sm.transition("BUILDING")
    sm.transition("AWAITING_APPROVAL")
    sm.transition("QA_VERIFYING")
    assert sm.state == "QA_VERIFYING"


def test_state_history_intermediate_states_reflect_correctly():
    sm = StateMachine()
    states_visited = []
    path = ["DISTILLED", "BLUEPRINTED", "PLANNED", "BUILDING", "QA_VERIFYING", "RELEASED"]
    for hop in path:
        sm.transition(hop)
        states_visited.append(sm.state)
    assert states_visited == path


def test_state_not_reset_after_illegal_attempt():
    sm = StateMachine("BUILDING")
    sm.transition("QA_VERIFYING")
    try:
        sm.transition("BUILDING")  # illegal: QA_VERIFYING -> BUILDING
    except IllegalTransitionError:
        pass
    assert sm.state == "QA_VERIFYING"


# ===========================================================================
# 10. Large parametrized illegal transitions (all illegal known-state pairs)
# ===========================================================================

@pytest.mark.parametrize("src,dst", ILLEGAL_PAIRS)
def test_large_parametrize_illegal_transition(src, dst):
    """Exhaustive: every non-terminal source -> every known-but-disallowed target."""
    sm = StateMachine(src)
    with pytest.raises(IllegalTransitionError):
        sm.transition(dst)


# ---------------------------------------------------------------------------
# Unknown state strings passed to transition()
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad", ["NOPE", "DONE", "INIT", "", "released", "failed"])
def test_transition_unknown_state_raises(bad):
    sm = StateMachine("RECEIVED")
    with pytest.raises(IllegalTransitionError):
        sm.transition(bad)


# ---------------------------------------------------------------------------
# TRANSITIONS dict integrity checks (meta tests)
# ---------------------------------------------------------------------------

def test_all_transition_sources_are_valid_states():
    assert set(TRANSITIONS.keys()) == STATES


def test_all_transition_targets_are_valid_states():
    for targets in TRANSITIONS.values():
        assert targets <= STATES


def test_terminal_states_have_no_outgoing():
    assert TRANSITIONS["RELEASED"] == set()
    assert TRANSITIONS["FAILED"] == set()


def test_states_set_has_ten_members():
    assert len(STATES) == 10


def test_terminal_set_has_two_members():
    assert TERMINAL == {"RELEASED", "FAILED"}


# ---------------------------------------------------------------------------
# Additional correctness spot-checks
# ---------------------------------------------------------------------------

def test_received_can_only_go_to_distilled_or_failed():
    allowed = {"DISTILLED", "FAILED"}
    assert TRANSITIONS["RECEIVED"] == allowed


def test_building_four_valid_targets():
    assert len(TRANSITIONS["BUILDING"]) == 4


def test_qa_verifying_four_valid_targets():
    assert len(TRANSITIONS["QA_VERIFYING"]) == 4


def test_repairing_four_valid_targets():
    assert len(TRANSITIONS["REPAIRING"]) == 4


def test_awaiting_approval_four_valid_targets():
    assert len(TRANSITIONS["AWAITING_APPROVAL"]) == 4


def test_statemachine_state_attribute_is_str():
    sm = StateMachine()
    assert isinstance(sm.state, str)


def test_statemachine_equality_not_implemented_but_state_comparable():
    sm1 = StateMachine("BUILDING")
    sm2 = StateMachine("BUILDING")
    assert sm1.state == sm2.state


def test_multiple_independent_instances():
    sm1 = StateMachine("RECEIVED")
    sm2 = StateMachine("BUILDING")
    sm1.transition("DISTILLED")
    # sm2 should be unaffected
    assert sm2.state == "BUILDING"


def test_transition_to_failed_from_qa_verifying():
    sm = StateMachine("QA_VERIFYING")
    sm.transition("FAILED")
    assert sm.state == "FAILED"
    assert sm.is_terminal


def test_repairing_can_return_to_building():
    sm = StateMachine("REPAIRING")
    sm.transition("BUILDING")
    assert sm.state == "BUILDING"


def test_repairing_can_go_to_qa_verifying():
    sm = StateMachine("REPAIRING")
    sm.transition("QA_VERIFYING")
    assert sm.state == "QA_VERIFYING"


def test_awaiting_approval_can_go_to_repairing():
    sm = StateMachine("AWAITING_APPROVAL")
    sm.transition("REPAIRING")
    assert sm.state == "REPAIRING"


def test_from_dict_handles_every_state():
    for state in STATES:
        sm = StateMachine.from_dict({"state": state})
        assert sm.state == state


def test_to_dict_then_from_dict_then_to_dict_stable():
    for state in STATES:
        sm = StateMachine(state)
        d1 = sm.to_dict()
        sm2 = StateMachine.from_dict(d1)
        d2 = sm2.to_dict()
        assert d1 == d2


@pytest.mark.parametrize("state", ALL_STATES)
def test_is_terminal_consistent_with_terminal_set(state):
    sm = StateMachine(state)
    assert sm.is_terminal == (state in TERMINAL)
