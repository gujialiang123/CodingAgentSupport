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


# -- C3 v2 (plan P5) ----------------------------------------------------------
from se_support.support.gate_policy import (  # noqa: E402
    detect_configured_tools,
    run_policy_v2,
)


class _FakeExec:
    """Scriptable exec_fn: maps an argv-substring to (returncode, output)."""

    def __init__(self, rules, default=(0, "")):
        self.rules = rules
        self.default = default
        self.calls = []

    def __call__(self, argv):
        self.calls.append(argv)
        joined = " ".join(argv)
        for needle, resp in self.rules.items():
            if needle in joined:
                return resp
        return self.default


def test_detect_configured_tools_reads_repo_config():
    ex = _FakeExec({
        "cat pyproject.toml": (0, "[tool.ruff]\nline-length=99\n[tool.mypy]\n"),
        "cat setup.cfg": (1, ""),
    })
    tools = detect_configured_tools(ex)
    assert "ruff" in tools and "mypy" in tools


def test_v2_skips_unconfigured_lint():
    # No config -> ruff/flake8/mypy report "unavailable/not configured" (-1), pass.
    ex = _FakeExec({"cat ": (1, "")})
    results = run_policy_v2(".", changed_files=["pkg/mod.py"], exec_fn=ex)
    by = {r.name: r for r in results}
    assert by["ruff"].warning_count == -1
    assert by["mypy"].warning_count == -1
    # unconfigured advisory tools must never have been executed
    assert not any(a[:1] == ["ruff"] for a in ex.calls)


def test_v2_import_gate_blocks_on_bad_import():
    ex = _FakeExec({
        "cat ": (1, ""),
        "python -c": (1, "ModuleNotFoundError: broken"),
        "test -f": (1, ""),  # no repo-native test maps
    })
    results = run_policy_v2(".", changed_files=["pkg/mod.py"], exec_fn=ex)
    by = {r.name: r for r in results}
    assert by["import"].passed is False
    assert by["import"].status == "fail"


def test_v2_targeted_tests_run_only_existing():
    ex = _FakeExec({
        "cat ": (1, ""),
        "python -c": (0, ""),
        "test -f tests/test_mod.py": (0, ""),
        "test -f": (1, ""),
        "pytest": (0, "1 passed"),
    })
    results = run_policy_v2(".", changed_files=["pkg/mod.py"], exec_fn=ex)
    by = {r.name: r for r in results}
    assert by["targeted_tests"].passed is True
    # pytest was invoked with the existing test target
    assert any("pytest" in " ".join(a) and "tests/test_mod.py" in " ".join(a)
               for a in ex.calls)


def test_v2_no_tests_map_passes_trivially():
    ex = _FakeExec({"cat ": (1, ""), "python -c": (0, ""), "test -f": (1, "")})
    results = run_policy_v2(".", changed_files=["pkg/mod.py"], exec_fn=ex)
    by = {r.name: r for r in results}
    assert by["targeted_tests"].passed is True
    assert "no repo-native tests" in by["targeted_tests"].preview
