"""Semantic audit (class S) execution (EP-03, plan §5.4, §5.6).

The hidden semantic-audit test varies incidental details (e.g. the required-column
name) so that a patch which hard-codes a single case passes the helper (H) but
fails the audit (S). It is run by the evaluator on the agent's patched tree and is
never shown to the agent.
"""

from __future__ import annotations

from pathlib import Path

from se_support.support.repro_tests.validator import run_test_in_workspace


def run_semantic_audit(workspace_path: Path, audit_source: str) -> bool:
    """Run the hidden semantic-audit test on a (patched) workspace. True = passed."""
    outcome = run_test_in_workspace(
        Path(workspace_path), audit_source, test_filename="_c2_semantic_audit.py"
    )
    return outcome.collected and outcome.passed
