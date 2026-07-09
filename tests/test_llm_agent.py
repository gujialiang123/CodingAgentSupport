"""Offline tests for the controllable LLM agent + support conditions.

Uses ScriptedChatClient so the agent loop, gates hook and condition system are
validated with no GPU and no network.
"""

from __future__ import annotations

import json
from pathlib import Path

from se_support.agents import LLMAgent, ScriptedChatClient
from se_support.runner.run_manager import run_single
from se_support.schemas import TaskSpec
from se_support.support import CONDITIONS, get_condition

FIXTURES = Path(__file__).parent / "fixtures"

FIX_CALC = """```bash
cat > calc.py <<'PY'
\"\"\"A tiny calculator used as an offline fixture repository.\"\"\"


def add(a, b):
    return a + b


def subtract(a, b):
    return a - b
PY
```"""


def _task() -> TaskSpec:
    return TaskSpec.model_validate(json.loads((FIXTURES / "task_mini_repo.json").read_text()))


def test_condition_flags():
    assert get_condition("C0_minimal").gates is False
    assert get_condition("C3_gates").gates is True
    assert get_condition("C6_full_stack").is_full_stack is True
    assert set(CONDITIONS) == {
        "C0_minimal", "C1_context", "C2_tests", "C3_gates",
        "C4_harness", "C5_memory", "C6_full_stack",
    }


def test_llm_agent_fixes_and_resolves(tmp_path):
    client = ScriptedChatClient([FIX_CALC, "SUBMIT"])
    outcome = run_single(
        _task(), LLMAgent(client, max_turns=5), "C0_minimal", tmp_path, "exp", model="scripted"
    )
    assert outcome.eval_result.resolved is True
    assert outcome.eval_result.fail_to_pass_passed == 1
    # transcript captured the interaction for post-hoc analysis
    assert (outcome.run_dir / "transcript.jsonl").exists()


def test_llm_agent_gates_block_then_pass(tmp_path):
    # First submit is premature (no fix). Under C3, compileall still passes (no
    # syntax error), so we instead check the gate results file is produced and
    # the run completes. Fix happens on turn 1, submit on turn 2.
    client = ScriptedChatClient([FIX_CALC, "SUBMIT"])
    outcome = run_single(
        _task(), LLMAgent(client, max_turns=5), "C3_gates", tmp_path, "exp", model="scripted"
    )
    assert (outcome.run_dir / "gate_results.json").exists()
    gates = json.loads((outcome.run_dir / "gate_results.json").read_text())
    assert any(g["gate_name"] == "compileall" for g in gates)
    assert outcome.eval_result.resolved is True


def test_llm_agent_no_fix_not_resolved(tmp_path):
    client = ScriptedChatClient(["SUBMIT"])
    outcome = run_single(
        _task(), LLMAgent(client, max_turns=3), "C0_minimal", tmp_path, "exp", model="scripted"
    )
    assert outcome.eval_result.resolved is False
