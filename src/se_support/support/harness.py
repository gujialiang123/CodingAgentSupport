"""Enforced engineering workflow (EP-04) -- the C4 construct.

Turns C4 from a prompt reminder into a **runner-enforced** state machine
(EXPERIMENT_PLAN_2026-07-21.md §4 C4, §14 EP-04):

    DISCOVER -> DIAGNOSE -> PATCH -> VALIDATE -> SUBMIT

Enforcement rules:
* code edits are allowed only in PATCH and VALIDATE;
* leaving DISCOVER requires a localization record;
* leaving DIAGNOSE requires a diagnosis record;
* SUBMIT requires a validation record;
* every transition and every rejected action is logged.

This module contains the **pure** state machine. Enforcement over the agent's
workspace (reverting edits made in a non-edit state) lives in the agent loop,
which calls :meth:`HarnessStateMachine.can_edit` and the transition API.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class HarnessState(str, Enum):
    DISCOVER = "DISCOVER"
    DIAGNOSE = "DIAGNOSE"
    PATCH = "PATCH"
    VALIDATE = "VALIDATE"
    SUBMIT = "SUBMIT"


ORDER = [
    HarnessState.DISCOVER,
    HarnessState.DIAGNOSE,
    HarnessState.PATCH,
    HarnessState.VALIDATE,
    HarnessState.SUBMIT,
]

EDIT_STATES = {HarnessState.PATCH, HarnessState.VALIDATE}

# Record required to LEAVE a state.
_REQUIRED_RECORD_TO_LEAVE = {
    HarnessState.DISCOVER: "localization",
    HarnessState.DIAGNOSE: "diagnosis",
    HarnessState.VALIDATE: "validation",
}


@dataclass
class Transition:
    frm: str
    to: str
    ok: bool
    reason: str = ""


@dataclass
class Rejection:
    state: str
    action: str
    reason: str


@dataclass
class HarnessStateMachine:
    state: HarnessState = HarnessState.DISCOVER
    records: dict[str, str] = field(default_factory=dict)
    transitions: list[Transition] = field(default_factory=list)
    rejections: list[Rejection] = field(default_factory=list)

    # -- records --------------------------------------------------------------
    def record(self, kind: str, text: str) -> None:
        if text and text.strip():
            self.records[kind] = text.strip()

    def has_record(self, kind: str) -> bool:
        return bool(self.records.get(kind))

    # -- permissions ----------------------------------------------------------
    def can_edit(self) -> bool:
        return self.state in EDIT_STATES

    def reject(self, action: str, reason: str) -> Rejection:
        r = Rejection(state=self.state.value, action=action, reason=reason)
        self.rejections.append(r)
        return r

    # -- transitions ----------------------------------------------------------
    def _next_state(self) -> HarnessState | None:
        i = ORDER.index(self.state)
        return ORDER[i + 1] if i + 1 < len(ORDER) else None

    def request_transition(self, target: HarnessState | str) -> Transition:
        """Advance toward ``target`` (any later state).

        Auto-walks through intermediate states as long as each state's
        leave-requirement record exists. This keeps enforcement (cannot reach
        PATCH without localization+diagnosis; cannot reach SUBMIT without a
        validation record) while not trapping a model that requests a forward
        jump in one message.
        """
        if isinstance(target, str):
            try:
                target = HarnessState(target.upper())
            except ValueError:
                t = Transition(self.state.value, str(target), False, "unknown target state")
                self.transitions.append(t)
                return t

        cur_i = ORDER.index(self.state)
        tgt_i = ORDER.index(target)
        if tgt_i <= cur_i:
            t = Transition(self.state.value, target.value, False, "not a forward transition")
            self.transitions.append(t)
            return t

        # Atomic: only advance if every intermediate state's leave-requirement is
        # already satisfied; otherwise stay put and report what's missing.
        for i in range(cur_i, tgt_i):
            required = _REQUIRED_RECORD_TO_LEAVE.get(ORDER[i])
            if required and not self.has_record(required):
                t = Transition(self.state.value, target.value, False,
                               f"missing required {required} record")
                self.transitions.append(t)
                return t

        start = self.state
        self.state = target
        t = Transition(start.value, target.value, True)
        self.transitions.append(t)
        self.state = target
        return t

    def can_submit(self) -> bool:
        return self.state == HarnessState.SUBMIT
