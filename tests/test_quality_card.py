"""Tests for quality card v1: process metrics + revised Q-levels (EP-08)."""

from __future__ import annotations

import json
from pathlib import Path

from se_support.agents import LLMAgent, ScriptedChatClient
from se_support.quality import recompute_card_from_run_dir
from se_support.quality.quality_card import _quality_level
from se_support.runner.run_manager import run_single
from se_support.schemas import EvalResult, TaskSpec
from se_support.schemas.patch_quality_card import QualityLevel

FIXTURES = Path(__file__).parent / "fixtures"

FIX_CALC = (
    "```bash\ncat > calc.py <<'PY'\n"
    "def add(a, b):\n    return a + b\n\n\n"
    "def subtract(a, b):\n    return a - b\nPY\n```"
)


def _task() -> TaskSpec:
    return TaskSpec.model_validate(json.loads((FIXTURES / "task_mini_repo.json").read_text()))


def test_qlevel_caps_at_q2_for_resolved():
    ev = EvalResult(run_id="r", patch_applies=True, build_success=True, resolved=True)
    assert _quality_level(ev) == QualityLevel.Q2_functionally_correct  # never auto-Q3


def test_qlevel_q0_and_q1():
    assert _quality_level(EvalResult(run_id="r", patch_applies=False)) == QualityLevel.Q0_invalid
    ev = EvalResult(run_id="r", patch_applies=True, build_success=True, resolved=False)
    assert _quality_level(ev) == QualityLevel.Q1_plausible_failing


def test_process_metrics_captured(tmp_path):
    client = ScriptedChatClient([FIX_CALC, "SUBMIT"])
    outcome = run_single(
        _task(), LLMAgent(client, max_turns=5), "C0_minimal", tmp_path, "exp", model="scripted"
    )
    proc = outcome.quality_card.process
    assert proc.turns >= 2
    assert proc.commands_run >= 1
    assert proc.stop_reason == "submitted"


def test_card_recomputable_offline(tmp_path):
    client = ScriptedChatClient([FIX_CALC, "SUBMIT"])
    outcome = run_single(
        _task(), LLMAgent(client, max_turns=5), "C0_minimal", tmp_path, "exp", model="scripted"
    )
    # Recompute purely from saved artifacts; process + correctness must match.
    recomputed = recompute_card_from_run_dir(outcome.run_dir)
    assert recomputed.resolved == outcome.quality_card.resolved
    assert recomputed.quality_level == outcome.quality_card.quality_level
    assert recomputed.process.stop_reason == "submitted"
