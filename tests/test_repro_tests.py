"""EP-03 acceptance tests for the C2 reproduction-test pipeline (plan §5).

Uses the self-contained synthetic fixture ``tests/fixtures/repro_demo`` (same
structure as astropy__astropy-13033) so base-fail / gold-pass / semantic-audit
run fast and offline.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from se_support.agents import ScriptedChatClient
from se_support.support.repro_tests import (
    HelperTestArtifact,
    ReproTestClass,
    build_helper_test,
    freeze,
    materialize,
    run_semantic_audit,
    run_test_in_workspace,
    suspicious_literals,
    verify_frozen,
)
from se_support.support.repro_tests.provenance import contains_forbidden_literal

FIX = Path(__file__).parent / "fixtures" / "repro_demo"
PROBLEM = (FIX / "problem_statement.txt").read_text()
HELPER = (FIX / "helper_test.py").read_text()
AUDIT = (FIX / "semantic_audit_test.py").read_text()
# The official (hidden) exact message the helper must NOT contain.
OFFICIAL_LITERAL = "expected 'time' as the first column but found 'time'"


def _base_ws(tmp_path: Path) -> Path:
    ws = tmp_path / "base"
    shutil.copytree(FIX / "base", ws)
    return ws


def _apply(ws: Path, patch: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=ws, check=True)
    subprocess.run(["git", "config", "user.email", "x@x"], cwd=ws, check=True)
    subprocess.run(["git", "config", "user.name", "x"], cwd=ws, check=True)
    subprocess.run(["git", "add", "-A"], cwd=ws, check=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=ws, check=True)
    subprocess.run(["git", "apply", str(patch)], cwd=ws, check=True)


def _gold_ws(tmp_path: Path) -> Path:
    ws = tmp_path / "gold"
    shutil.copytree(FIX / "base", ws)
    _apply(ws, FIX / "gold.patch")
    return ws


def _bad_ws(tmp_path: Path) -> Path:
    ws = tmp_path / "bad"
    shutil.copytree(FIX / "base", ws)
    _apply(ws, FIX / "hardcoded_bad.patch")
    return ws


# -- helper fails on base, passes on gold (T3/T4) -----------------------------
def test_helper_fails_before_passes_after(tmp_path):
    base = _base_ws(tmp_path)
    assert run_test_in_workspace(base, HELPER).passed is False   # fail-before
    gold = _gold_ws(tmp_path)
    assert run_test_in_workspace(gold, HELPER).passed is True     # pass-after


def test_helper_contains_no_official_literal():
    assert OFFICIAL_LITERAL not in HELPER
    assert contains_forbidden_literal(HELPER, [OFFICIAL_LITERAL]) == []
    # And provenance audit does not flag the issue-level assertion ("flux").
    assert suspicious_literals(HELPER, PROBLEM) == []


# -- hidden semantic audit catches a hard-coded solution ----------------------
def test_semantic_audit_passes_gold_rejects_hardcode(tmp_path):
    gold = _gold_ws(tmp_path)
    assert run_semantic_audit(gold, AUDIT) is True     # correct fix passes audit
    bad = _bad_ws(tmp_path)
    assert run_semantic_audit(bad, AUDIT) is False     # hard-coded 'flux' caught


# -- a leaked official-literal helper is flagged ------------------------------
def test_provenance_flags_leaked_official_string():
    leaky = (
        "def test_x():\n"
        "    import mod\n"
        "    try:\n        mod.remove_required_column('flux')\n    except ValueError as e:\n"
        f"        assert str(e) == \"{OFFICIAL_LITERAL}\"\n"
    )
    assert suspicious_literals(leaky, PROBLEM)  # non-empty -> suspicious
    assert contains_forbidden_literal(leaky, [OFFICIAL_LITERAL]) == [OFFICIAL_LITERAL]


# -- frozen / read-only helper ------------------------------------------------
def test_frozen_helper_readonly(tmp_path):
    art = freeze(HelperTestArtifact(task_id="t", test_source=HELPER))
    assert verify_frozen(art)
    # Tampering with the source breaks verification and blocks materialize.
    tampered = art.model_copy(update={"test_source": HELPER + "\n# hacked\n"})
    assert verify_frozen(tampered) is False
    # Materialize reconstructs the FROZEN source regardless of any workspace copy.
    out = materialize(art, tmp_path / "support")
    assert out.read_text() == HELPER


# -- full pipeline with a scripted generator ----------------------------------
def test_build_helper_pipeline_t4(tmp_path):
    # Generator returns a leaky candidate first, then the good one; selection is
    # gold-blind and must reject the leaky one (forbidden literal) and pick good.
    leaky = f"```python\nimport pytest\nfrom mod import remove_required_column\n" \
            f"def test_x():\n    with pytest.raises(ValueError) as e:\n" \
            f"        remove_required_column('flux')\n" \
            f"    assert str(e.value) == \"{OFFICIAL_LITERAL}\"\n```"
    good = "```python\n" + HELPER + "\n```"
    client = ScriptedChatClient([leaky, good, good])
    art = build_helper_test(
        "demo", PROBLEM, "module mod with remove_required_column(name)", client,
        base_workspace=_base_ws(tmp_path), gold_workspace=_gold_ws(tmp_path),
        forbidden_literals=[OFFICIAL_LITERAL], k=3,
    )
    assert art.fail_before is True
    assert art.pass_after_gold is True
    assert art.classification == ReproTestClass.T4_decoupled_valid
    assert art.frozen_hash is not None


def test_build_helper_non_reproducing_is_t1(tmp_path):
    # A candidate that always passes (no real assertion of the bug) -> T1.
    trivial = "```python\ndef test_trivial():\n    assert True\n```"
    client = ScriptedChatClient([trivial, trivial, trivial])
    art = build_helper_test(
        "demo", PROBLEM, "ctx", client,
        base_workspace=_base_ws(tmp_path), gold_workspace=_gold_ws(tmp_path), k=3,
    )
    assert art.classification == ReproTestClass.T1_non_reproducing
