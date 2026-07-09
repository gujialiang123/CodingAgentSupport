"""Offline tests for the SWE-bench importer + sampler (T2), no download."""

from __future__ import annotations

from pathlib import Path

from se_support.datasets import (
    import_swebench_verified,
    load_tasks,
    record_to_taskspec,
    sample_tasks,
)
from se_support.datasets.swebench_importer import _as_list

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE = FIXTURES / "swebench_sample.jsonl"


def test_as_list_parses_json_string():
    assert _as_list('["a::b", "c::d"]') == ["a::b", "c::d"]
    assert _as_list("") == []
    assert _as_list(["x"]) == ["x"]
    assert _as_list(None) == []


def test_record_to_taskspec(tmp_path):
    import json

    rec = json.loads(SAMPLE.read_text().splitlines()[0])
    task = record_to_taskspec(rec, tmp_path / "gold", tmp_path / "test")
    assert task.dataset == "swebench_verified"
    assert task.task_id == "swebench_verified__astropy__astropy-12345"
    assert task.repo == "astropy/astropy"
    assert task.fail_to_pass_tests == ["astropy/units/tests/test_core.py::test_new"]
    assert task.pass_to_pass_tests == ["astropy/units/tests/test_core.py::test_existing"]
    assert task.metadata.repo_group == "astropy"
    # gold + test patches written to disk
    assert Path(task.gold_patch_path).exists()
    assert Path(task.test_patch_path).exists()
    assert task.issue_title.startswith("Unit conversion fails")
    assert task.environment_setup_commit is not None


def test_import_from_fixture(tmp_path):
    out = tmp_path / "tasks.jsonl"
    n = import_swebench_verified(
        out, fixture_path=SAMPLE,
        gold_dir=tmp_path / "gold", test_dir=tmp_path / "test",
    )
    assert n == 2
    tasks = load_tasks(out)
    assert len(tasks) == 2
    assert {t.metadata.repo_group for t in tasks} == {"astropy", "django"}


def test_import_limit(tmp_path):
    out = tmp_path / "tasks.jsonl"
    n = import_swebench_verified(
        out, fixture_path=SAMPLE, limit=1,
        gold_dir=tmp_path / "gold", test_dir=tmp_path / "test",
    )
    assert n == 1


def test_sample_head_and_stratified(tmp_path):
    out = tmp_path / "tasks.jsonl"
    import_swebench_verified(
        out, fixture_path=SAMPLE,
        gold_dir=tmp_path / "gold", test_dir=tmp_path / "test",
    )
    tasks = load_tasks(out)
    assert len(sample_tasks(tasks, 1, strategy="head")) == 1
    strat = sample_tasks(tasks, 2, strategy="stratified", seed=0)
    assert len(strat) == 2
    # both repo groups represented when n covers them
    assert {t.metadata.repo_group for t in strat} == {"astropy", "django"}
