"""Tests for the enforced C4 harness (EP-04): state machine + agent integration."""

from __future__ import annotations

import json
from pathlib import Path

from se_support.agents import LLMAgent, ScriptedChatClient
from se_support.runner.run_manager import run_single
from se_support.schemas import TaskSpec
from se_support.support.harness import HarnessState, HarnessStateMachine

FIXTURES = Path(__file__).parent / "fixtures"


def _task() -> TaskSpec:
    return TaskSpec.model_validate(json.loads((FIXTURES / "task_mini_repo.json").read_text()))


# -- pure state machine ------------------------------------------------------
def test_edit_permission_by_state():
    sm = HarnessStateMachine()
    assert sm.state == HarnessState.DISCOVER
    assert sm.can_edit() is False
    sm.record("localization", "calc.subtract")
    assert sm.request_transition("DIAGNOSE").ok
    assert sm.can_edit() is False
    sm.record("diagnosis", "uses + instead of -")
    assert sm.request_transition("PATCH").ok
    assert sm.can_edit() is True


def test_transition_requires_record():
    sm = HarnessStateMachine()
    t = sm.request_transition("DIAGNOSE")  # no localization yet
    assert not t.ok and "localization" in t.reason
    assert sm.state == HarnessState.DISCOVER


def test_cannot_skip_states():
    sm = HarnessStateMachine()
    sm.record("localization", "x")
    t = sm.request_transition("PATCH")  # skipping DIAGNOSE
    assert not t.ok
    assert sm.state == HarnessState.DISCOVER


def test_submit_requires_full_workflow():
    sm = HarnessStateMachine()
    assert sm.can_submit() is False
    sm.record("localization", "x")
    sm.request_transition("DIAGNOSE")
    sm.record("diagnosis", "y")
    sm.request_transition("PATCH")
    sm.request_transition("VALIDATE")
    assert sm.can_submit() is False  # need validation record
    sm.record("validation", "ran tests, pass")
    assert sm.request_transition("SUBMIT").ok
    assert sm.can_submit() is True


# -- agent integration -------------------------------------------------------
FIX_EDIT = (
    "```bash\npython - <<'PY'\n"
    "open('calc.py','w').write("
    "'def add(a,b):\\n    return a+b\\n\\n\\ndef subtract(a,b):\\n    return a-b\\n')\n"
    "PY\n```"
)


def test_agent_reverts_edits_before_patch_state(tmp_path):
    # Agent tries to edit while still in DISCOVER -> must be reverted, not resolved.
    client = ScriptedChatClient([FIX_EDIT, "SUBMIT"])
    outcome = run_single(
        _task(), LLMAgent(client, max_turns=4), "C4_harness", tmp_path, "exp", model="scripted"
    )
    # Edit was reverted (still buggy) and premature SUBMIT blocked -> not resolved.
    assert outcome.eval_result.resolved is False
    st = json.loads((outcome.run_dir / "state_transitions.json").read_text())
    assert any(r.get("type") == "rejection" and r["action"] == "edit" for r in st)


def test_agent_full_workflow_resolves(tmp_path):
    client = ScriptedChatClient([
        "LOCALIZATION: calc.subtract returns a+b\nNEXT_STATE: DIAGNOSE",
        "DIAGNOSIS: subtract uses + instead of -\nNEXT_STATE: PATCH",
        FIX_EDIT,
        "NEXT_STATE: VALIDATE",
        "VALIDATION: ran pytest, subtract now correct\nNEXT_STATE: SUBMIT",
        "SUBMIT",
    ])
    outcome = run_single(
        _task(), LLMAgent(client, max_turns=10), "C4_harness", tmp_path, "exp", model="scripted"
    )
    assert outcome.eval_result.resolved is True
    st = json.loads((outcome.run_dir / "state_transitions.json").read_text())
    oks = [r for r in st if r.get("type") == "transition" and r["ok"]]
    assert len(oks) == 4  # DISCOVER->...->SUBMIT
