"""Helper-test validator + T0-T4 classifier (EP-03, plan §5.3).

Runs a candidate helper test against a base-state workspace and (offline, for
classification only) against a gold-patched workspace, then classifies:

* T0 invalid       - cannot collect/import/execute
* T1 non-reproducing - passes on base
* T2 incompatible  - fails on base AND on gold
* T3 valid         - fails on base, passes on gold
* T4 decoupled     - T3 + semantic audit finds no leakage/overfit (set by caller)

Gold results are used ONLY to classify; a candidate is frozen *before* gold is
consulted (see generator/orchestrator), and is never switched based on gold.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from se_support.support.repro_tests.schema import ReproTestClass


class TestRunOutcome:
    def __init__(self, collected: bool, passed: bool, output: str) -> None:
        self.collected = collected
        self.passed = passed
        self.output = output


def run_test_in_workspace(
    workspace_path: Path, test_source: str, test_filename: str = "_c2_helper_test.py"
) -> TestRunOutcome:
    """Write ``test_source`` into the workspace and run it with pytest."""
    workspace_path = Path(workspace_path)
    test_path = workspace_path / test_filename
    test_path.write_text(test_source, encoding="utf-8")
    try:
        proc = subprocess.run(
            ["python", "-m", "pytest", "-q", "--no-header", "-p", "no:cacheprovider",
             test_filename],
            cwd=workspace_path, capture_output=True, text=True,
        )
    finally:
        test_path.unlink(missing_ok=True)
    out = proc.stdout + proc.stderr
    # pytest exit codes: 0 = all pass, 1 = tests failed, 2 = usage/collection error,
    # 5 = no tests collected. Only 0/1 mean the test actually ran.
    collected = proc.returncode in (0, 1)
    passed = proc.returncode == 0
    return TestRunOutcome(collected=collected, passed=passed, output=out)


def classify(collected: bool, fail_before: bool, pass_after_gold: bool | None) -> ReproTestClass:
    """Classify a helper candidate into T0-T3 (T4 is assigned after audit)."""
    if not collected:
        return ReproTestClass.T0_invalid
    if not fail_before:
        return ReproTestClass.T1_non_reproducing
    # fails on base
    if pass_after_gold is None:
        # No gold available; best we can say is it reproduces (treat as T3-eligible).
        return ReproTestClass.T3_valid_reproduction
    if pass_after_gold:
        return ReproTestClass.T3_valid_reproduction
    return ReproTestClass.T2_incompatible_oracle
