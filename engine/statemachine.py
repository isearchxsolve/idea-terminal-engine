"""Run state machine. Illegal transitions raise; terminal states absorb."""
from __future__ import annotations

STATES = {
    "RECEIVED", "DISTILLED", "BLUEPRINTED", "PLANNED", "BUILDING",
    "QA_VERIFYING", "REPAIRING", "AWAITING_APPROVAL", "RELEASED", "FAILED",
}
TERMINAL = {"RELEASED", "FAILED"}

TRANSITIONS = {
    "RECEIVED": {"DISTILLED", "FAILED"},
    "DISTILLED": {"BLUEPRINTED", "FAILED"},
    "BLUEPRINTED": {"PLANNED", "FAILED"},
    "PLANNED": {"BUILDING", "FAILED"},
    "BUILDING": {"QA_VERIFYING", "REPAIRING", "AWAITING_APPROVAL", "FAILED"},
    "QA_VERIFYING": {"RELEASED", "REPAIRING", "AWAITING_APPROVAL", "FAILED"},
    "REPAIRING": {"BUILDING", "QA_VERIFYING", "AWAITING_APPROVAL", "FAILED"},
    # Human gate for critical/irreversible actions; approved work resumes,
    # denied work fails closed.
    "AWAITING_APPROVAL": {"BUILDING", "QA_VERIFYING", "REPAIRING", "FAILED"},
    "RELEASED": set(),
    "FAILED": set(),
}


class IllegalTransitionError(Exception):
    pass


class StateMachine:
    def __init__(self, state: str = "RECEIVED"):
        if state not in STATES:
            raise IllegalTransitionError(f"unknown state: {state!r}")
        self.state = state

    @property
    def is_terminal(self) -> bool:
        return self.state in TERMINAL

    def transition(self, to: str) -> str:
        if to not in STATES:
            raise IllegalTransitionError(f"unknown state: {to!r}")
        if to not in TRANSITIONS[self.state]:
            raise IllegalTransitionError(f"{self.state} -> {to} is illegal")
        self.state = to
        return self.state

    def to_dict(self) -> dict:
        return {"state": self.state}

    @classmethod
    def from_dict(cls, data: dict) -> "StateMachine":
        return cls(state=data["state"])
