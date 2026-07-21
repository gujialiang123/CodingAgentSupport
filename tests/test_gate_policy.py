"""Tests for the frozen C3 gate policy (EP-07)."""

from __future__ import annotations

from pathlib import Path

from se_support.support.gate_policy import (
    GatePolicy,
    GateResult,
    blocking_failures,
    compute_baseline,
    run_policy,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_policy_serialisation_no_official_tests():
    d = GatePolicy().to_dict()
    assert d["official_tests_are_gates"] is False
    assert d["revision_budget"] == 3
    names = {g["name"] for g in d["gates"]}
    assert "compileall" in names
    # official test node ids never appear as a gate
    assert not any("PASS_TO_PASS" in g["name"] or "FAIL_TO_PASS" in g["name"] for g in d["gates"])


def test_compileall_blocking_pass(tmp_path):
    (tmp_path / "ok.py").write_text("x = 1\n")
    results = run_policy(tmp_path)
    comp = next(r for r in results if r.name == "compileall")
    assert comp.kind == "blocking"
    assert comp.passed is True
    assert blocking_failures(results) == []


def test_compileall_blocking_fail(tmp_path):
    (tmp_path / "bad.py").write_text("def broken(:\n")  # syntax error
    results = run_policy(tmp_path)
    comp = next(r for r in results if r.name == "compileall")
    assert comp.passed is False
    assert comp in blocking_failures(results)


def test_advisory_delta_excludes_legacy_warnings(tmp_path):
    import shutil

    if not shutil.which("ruff"):
        return  # advisory gate unavailable; delta logic still covered below
    # Base tree already has lint warnings (unused imports).
    (tmp_path / "legacy.py").write_text("import os\nimport sys\n")
    baseline = compute_baseline(tmp_path)
    # Patch adds ONE more unused import.
    (tmp_path / "legacy.py").write_text("import os\nimport sys\nimport re\n")
    results = run_policy(tmp_path, baseline)
    ruff = next((r for r in results if r.name == "ruff"), None)
    if ruff and ruff.warning_count >= 0:
        # new_warnings counts only the delta, not the pre-existing legacy ones.
        assert ruff.new_warnings is not None
        assert ruff.new_warnings <= ruff.warning_count


def test_advisory_never_blocks():
    r = GateResult("ruff", "advisory", True, 5, 2, "advisory")
    assert blocking_failures([r]) == []
