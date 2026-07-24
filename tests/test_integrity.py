"""Tests for the experiment-integrity fixes (helper isolation, clean-tree,
safe patch extraction). Pure-function tests here; the live read-only mount and
git-index extractor are covered by the integrity smoke run (docs 011)."""

from __future__ import annotations

from se_support.runner.container_workspace import (
    build_patch_manifest,
    classify_git_state,
)


def test_s0_untracked_build_dir_is_benign():
    # SWE-bench base image ships an untracked build/lib tree -> not a failure at S0.
    porcelain = "\n".join(f"?? build/lib/requests/{n}.py" for n in ("a", "b", "c"))
    s0 = classify_git_state(porcelain, strict_untracked=False)
    assert s0["clean"] is True
    assert len(s0["untracked_files"]) == 3
    assert s0["tracked_changes"] == []


def test_s1_new_untracked_beyond_baseline_is_flagged():
    base = ["build/lib/requests/a.py"]
    # a new untracked file (not in baseline) appears -> infrastructure failure.
    porcelain = "?? build/lib/requests/a.py\n?? support_leaked_file.py"
    s1 = classify_git_state(porcelain, baseline_untracked=base, strict_untracked=True)
    assert s1["clean"] is False
    assert "support_leaked_file.py" in s1["unexplained_changes"]
    assert "build/lib/requests/a.py" not in s1["unexplained_changes"]


def test_modified_tracked_file_is_always_flagged():
    s = classify_git_state(" M requests/models.py", strict_untracked=False)
    assert s["clean"] is False
    assert "requests/models.py" in s["unexplained_changes"]


def test_support_and_ephemeral_paths_are_allowed():
    porcelain = (
        "?? .se_support/helper_test.py\n"
        "?? requests/__pycache__/models.cpython-311.pyc\n"
        "?? .pytest_cache/v/cache/lastfailed"
    )
    s = classify_git_state(porcelain, strict_untracked=True)
    assert s["clean"] is True


def test_patch_manifest_flags_helper_leak():
    m = build_patch_manifest("diff...", ["requests/models.py",
                                         "se_support_helper_test.py"], [])
    assert m["helper_leak"] is True


def test_patch_manifest_flags_mounted_helper_leak():
    m = build_patch_manifest("diff...", [".se_support/helper_test.py"], [])
    assert m["helper_leak"] is True


def test_patch_manifest_clean_agent_edit():
    m = build_patch_manifest("diff...", ["requests/models.py"], ["**/*.pyc"])
    assert m["helper_leak"] is False
    assert m["included_paths"] == ["requests/models.py"]
    assert m["patch_sha256"]


def _write_run(root, run_id, cond, protocol="0.3.0", resolved=True, infra=False):
    import json as _json
    d = root / run_id
    d.mkdir(parents=True)
    (d / "run_spec.json").write_text(_json.dumps({
        "run_id": run_id, "task_id": "repo__x-1", "condition": cond, "seed": 0,
        "protocol_version": protocol, "agent": "a", "model": "m",
    }))
    (d / "eval_result.json").write_text(_json.dumps(
        {"run_id": run_id, "resolved": resolved, "patch_applies": True}))
    (d / "quality_card.json").write_text(_json.dumps(
        {"run_id": run_id, "task_id": "repo__x-1", "quality_level": "Q2_functionally_correct"}))
    if infra:
        (d / "integrity").mkdir()
        (d / "integrity" / "status.json").write_text(
            _json.dumps({"status": "infrastructure_failure", "stage": "S0"}))


def test_load_runs_excludes_infra_failures(tmp_path):
    from se_support.analysis.aggregate import load_runs

    _write_run(tmp_path, "r1", "C0_minimal")
    _write_run(tmp_path, "r2", "C0_minimal", infra=True)
    rows = load_runs(tmp_path)
    assert len(rows) == 1
    assert rows[0].task_id == "repo__x-1"


def test_load_runs_rejects_mixed_protocol(tmp_path):
    import pytest

    from se_support.analysis.aggregate import load_runs

    _write_run(tmp_path, "r1", "C0_minimal", protocol="0.3.0")
    _write_run(tmp_path, "r2", "C0_minimal", protocol="2026-07-21")
    with pytest.raises(ValueError, match="mixed protocol"):
        load_runs(tmp_path)
    assert len(load_runs(tmp_path, allow_mixed_protocol=True)) == 2


# -- Phase 1A: helper-hash hard invariant -------------------------------------
from se_support.runner.run_manager import _helper_integrity_violation  # noqa: E402


def test_helper_integrity_valid_unchanged():
    assert _helper_integrity_violation("abc", "abc", "abc") is None


def test_helper_integrity_null_host():
    assert _helper_integrity_violation(None, None, None) == "helper_host_sha_missing"
    assert _helper_integrity_violation("", "x", "x") == "helper_host_sha_missing"


def test_helper_integrity_before_mismatch():
    r = _helper_integrity_violation("hostsha", "othersha", "othersha")
    assert r is not None and "before_mismatch" in r


def test_helper_integrity_after_mismatch():
    r = _helper_integrity_violation("abc", "abc", "tampered")
    assert r is not None and "after_mismatch" in r


def test_p2p_regression_stats_denominators():
    from se_support.analysis.aggregate import p2p_regression_stats

    evals = [
        {"patch_applies": True, "pass_to_pass_passed": 15, "pass_to_pass_total": 15},
        {"patch_applies": True, "pass_to_pass_passed": 14, "pass_to_pass_total": 15},  # reg
        {"patch_applies": True, "pass_to_pass_passed": 0, "pass_to_pass_total": 0},  # missing
        {"patch_applies": False, "pass_to_pass_passed": 0, "pass_to_pass_total": 0},  # excluded
    ]
    s = p2p_regression_stats(evals)
    assert s["applying"] == 3
    assert s["p2p_usable"] == 2
    assert s["p2p_regressing"] == 1
    assert s["p2p_missing"] == 1
    assert s["p2p_regression_rate"] == 0.5


def test_load_runs_rejects_mixed_model(tmp_path):
    import pytest

    from se_support.analysis.aggregate import load_runs

    # same protocol, different model -> rejected unless allowed.
    d1 = tmp_path / "r1"
    d1.mkdir()
    d2 = tmp_path / "r2"
    d2.mkdir()
    import json as _json
    for d, mdl in ((d1, "qwen3-coder-30b-a3b-instruct"), (d2, "qwen3.7-plus")):
        (d / "run_spec.json").write_text(_json.dumps({
            "run_id": d.name, "task_id": "repo__x-1", "condition": "C0_minimal",
            "seed": 0, "protocol_version": "0.3.1", "model": mdl,
            "condition_version": "0.2.0", "agent": "a"}))
        (d / "eval_result.json").write_text(_json.dumps(
            {"run_id": d.name, "resolved": True, "patch_applies": True}))
        (d / "quality_card.json").write_text(_json.dumps(
            {"run_id": d.name, "task_id": "repo__x-1", "quality_level": "Q2_functionally_correct"}))
    with pytest.raises(ValueError, match="mixed models"):
        load_runs(tmp_path)
    assert len(load_runs(tmp_path, allow_mixed_model=True)) == 2
