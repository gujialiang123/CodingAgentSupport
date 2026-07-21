"""End-to-end pipeline test using the mock agent + fixture mini-repo.

Verifies the whole chain (workspace -> patch -> eval -> quality card) with no
LLM: gold patch resolves the task; empty/broken do not.
"""

from __future__ import annotations

import json
from pathlib import Path

from se_support.agents import MockAgent
from se_support.runner.patch_utils import diff_metrics
from se_support.runner.run_manager import run_single
from se_support.schemas import TaskSpec

FIXTURES = Path(__file__).parent / "fixtures"


def _task() -> TaskSpec:
    return TaskSpec.model_validate(json.loads((FIXTURES / "task_mini_repo.json").read_text()))


def test_gold_agent_resolves(tmp_path):
    outcome = run_single(
        _task(), MockAgent("gold"), "C6_full_stack", tmp_path, "test_exp", model="mock"
    )
    ev = outcome.eval_result
    assert ev.patch_applies is True
    assert ev.resolved is True
    assert ev.fail_to_pass_passed == ev.fail_to_pass_total == 1
    assert ev.pass_to_pass_passed == ev.pass_to_pass_total == 1
    assert outcome.quality_card.quality_level.startswith("Q2")
    # Artifacts exist.
    for name in ("task.json", "run_spec.json", "final.patch", "eval_result.json",
                 "quality_card.json", "transcript.jsonl", "commands.jsonl"):
        assert (outcome.run_dir / name).exists(), name


def test_empty_agent_does_not_resolve(tmp_path):
    outcome = run_single(
        _task(), MockAgent("empty"), "C0_minimal", tmp_path, "test_exp", model="mock"
    )
    assert outcome.eval_result.resolved is False
    assert outcome.eval_result.fail_to_pass_passed == 0
    assert outcome.quality_card.quality_level.startswith("Q1")


def test_broken_agent_flags_unrelated_change(tmp_path):
    outcome = run_single(
        _task(), MockAgent("broken"), "C0_minimal", tmp_path, "test_exp", model="mock"
    )
    card = outcome.quality_card
    assert card.resolved is False
    assert card.locality.unrelated_file_change_suspected is True
    assert card.locality.gold_file_overlap == 0.0


def test_diff_metrics_counts():
    diff = (
        "diff --git a/f.py b/f.py\n--- a/f.py\n+++ b/f.py\n"
        "@@ -1,2 +1,2 @@\n-old\n+new\n context\n"
    )
    dm = diff_metrics(diff)
    assert dm.files_touched == 1
    assert dm.loc_added == 1
    assert dm.loc_deleted == 1
    assert dm.files == ["f.py"]
