import pytest

from engine.statemachine import IllegalTransitionError, StateMachine

HAPPY = ["DISTILLED", "BLUEPRINTED", "PLANNED", "BUILDING",
         "QA_VERIFYING", "RELEASED"]


def test_happy_path_to_released():
    sm = StateMachine()
    for state in HAPPY:
        sm.transition(state)
    assert sm.state == "RELEASED"
    assert sm.is_terminal


def test_illegal_transition_raises():
    sm = StateMachine()
    with pytest.raises(IllegalTransitionError):
        sm.transition("BUILDING")  # RECEIVED -> BUILDING is illegal


def test_terminal_states_absorbing():
    sm = StateMachine("RELEASED")
    with pytest.raises(IllegalTransitionError):
        sm.transition("FAILED")
    sm2 = StateMachine("FAILED")
    with pytest.raises(IllegalTransitionError):
        sm2.transition("RECEIVED")


def test_awaiting_approval_roundtrip():
    sm = StateMachine("BUILDING")
    sm.transition("AWAITING_APPROVAL")
    sm.transition("QA_VERIFYING")  # approved work resumes
    assert sm.state == "QA_VERIFYING"


def test_awaiting_approval_can_fail_closed():
    sm = StateMachine("REPAIRING")
    sm.transition("AWAITING_APPROVAL")
    sm.transition("FAILED")  # denied work fails closed
    assert sm.is_terminal


def test_unknown_state_rejected():
    with pytest.raises(IllegalTransitionError):
        StateMachine("NOPE")
    sm = StateMachine()
    with pytest.raises(IllegalTransitionError):
        sm.transition("NOPE")


def test_serialization_roundtrip():
    sm = StateMachine("PLANNED")
    assert StateMachine.from_dict(sm.to_dict()).state == "PLANNED"
