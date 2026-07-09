"""Offline tests for the SWE-bench Docker evaluator's pure helpers.

The Docker path itself (network + containers + minutes) is exercised manually /
in a dedicated experiment, not in the unit suite. Here we test the report
parsing and predictions writing, which is where mapping bugs would hide.
"""

from __future__ import annotations

import json
from pathlib import Path

from se_support.evaluation.swebench_eval import (
    _eval_from_report,
    instance_id_from_task,
    write_predictions,
)
from se_support.schemas import TaskSpec

FIXTURES = Path(__file__).parent / "fixtures"


def _task() -> TaskSpec:
    rec = json.loads((FIXTURES / "swebench_sample.jsonl").read_text().splitlines()[0])
    return TaskSpec(
        task_id=f"swebench_verified__{rec['instance_id']}",
        dataset="swebench_verified",
        repo=rec["repo"],
        base_commit=rec["base_commit"],
    )


def test_instance_id_recovery():
    assert instance_id_from_task(_task()) == "astropy__astropy-12345"


def test_write_predictions(tmp_path):
    path = tmp_path / "preds.jsonl"
    iid = write_predictions(_task(), "diff --git ...", path)
    assert iid == "astropy__astropy-12345"
    preds = json.loads(path.read_text())
    assert preds["instance_id"] == iid
    assert preds["model_patch"] == "diff --git ..."


def test_eval_from_per_instance_report():
    instance_id = "astropy__astropy-12345"
    report = {
        instance_id: {
            "patch_successfully_applied": True,
            "resolved": True,
            "tests_status": {
                "FAIL_TO_PASS": {"success": ["t::a", "t::b"], "failure": []},
                "PASS_TO_PASS": {"success": ["t::c"], "failure": ["t::d"]},
            },
        }
    }
    ev = _eval_from_report(report, instance_id, "run1")
    assert ev.resolved is True
    assert ev.patch_applies is True
    assert ev.fail_to_pass_passed == 2 and ev.fail_to_pass_total == 2
    assert ev.pass_to_pass_passed == 1 and ev.pass_to_pass_total == 2


def test_eval_from_report_unresolved():
    instance_id = "x__y-1"
    report = {
        instance_id: {
            "patch_successfully_applied": True,
            "resolved": False,
            "tests_status": {
                "FAIL_TO_PASS": {"success": [], "failure": ["t::a"]},
                "PASS_TO_PASS": {"success": ["t::c"], "failure": []},
            },
        }
    }
    ev = _eval_from_report(report, instance_id, "run1")
    assert ev.resolved is False
    assert ev.fail_to_pass_passed == 0 and ev.fail_to_pass_total == 1
