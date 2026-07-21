"""Tests for the experiment scheduler (EP-09 / A3)."""

from __future__ import annotations

import json
from pathlib import Path

from se_support.agents import LLMAgent, ScriptedChatClient
from se_support.experiment import build_schedule, run_experiment
from se_support.schemas import TaskSpec

FIXTURES = Path(__file__).parent / "fixtures"

FIX_CALC = (
    "```bash\ncat > calc.py <<'PY'\n"
    "def add(a, b):\n    return a + b\n\n\n"
    "def subtract(a, b):\n    return a - b\nPY\n```"
)


def _task() -> TaskSpec:
    return TaskSpec.model_validate(json.loads((FIXTURES / "task_mini_repo.json").read_text()))


def test_schedule_is_deterministic_and_covers_all_cells():
    t = _task()
    s1 = build_schedule([t], ["C0_minimal", "C6_full_stack"], [0, 1], rng_seed=7)
    s2 = build_schedule([t], ["C0_minimal", "C6_full_stack"], [0, 1], rng_seed=7)
    assert [c.key for c in s1] == [c.key for c in s2]  # deterministic
    assert len(s1) == 4  # 1 task x 2 conditions x 2 seeds
    assert len({c.run_id for c in s1}) == 4  # unique run ids


def test_run_experiment_and_resume(tmp_path):
    t = _task()

    def agent_factory():
        return LLMAgent(ScriptedChatClient([FIX_CALC, "SUBMIT"]), max_turns=4)

    rows = run_experiment(
        "exp_sched", [t], ["C0_minimal"], agent_factory,
        runs_root=tmp_path, model="scripted", sandbox_policy=None, progress=False,
    )
    assert len(rows) == 1
    assert rows[0]["resolved"] is True

    # Resume: second call skips the completed cell (no re-run).
    rows2 = run_experiment(
        "exp_sched", [t], ["C0_minimal"], agent_factory,
        runs_root=tmp_path, model="scripted", sandbox_policy=None, progress=False,
    )
    assert rows2[0].get("skipped") is True
    assert rows2[0]["resolved"] is True


def test_run_experiment_concurrent(tmp_path):
    t = _task()

    def agent_factory():
        return LLMAgent(ScriptedChatClient([FIX_CALC, "SUBMIT"]), max_turns=4)

    rows = run_experiment(
        "exp_conc", [t], ["C0_minimal", "C6_full_stack"], agent_factory,
        runs_root=tmp_path, model="scripted", sandbox_policy=None, progress=False,
        max_workers=2,
    )
    assert len(rows) == 2
    assert all(r.get("error") is None for r in rows)
