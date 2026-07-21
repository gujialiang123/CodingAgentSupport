"""C2 reproduction-test support (EP-03, plan §5).

Pipeline: generate K blind candidates -> select gold-blind -> freeze -> classify
against base/gold (offline) -> provenance/leakage audit -> frozen HelperTestArtifact.
"""

from __future__ import annotations

from pathlib import Path

from se_support.support.repro_tests.audit import run_semantic_audit
from se_support.support.repro_tests.generator import (
    generate_candidates,
    prompt_hash,
)
from se_support.support.repro_tests.injector import freeze, materialize, verify_frozen
from se_support.support.repro_tests.provenance import (
    contains_forbidden_literal,
    has_issue_provenance,
    suspicious_literals,
)
from se_support.support.repro_tests.schema import (
    CONFIRMATORY_CLASSES,
    HelperTestArtifact,
    ReproTestClass,
    ReproTestResults,
)
from se_support.support.repro_tests.validator import classify, run_test_in_workspace

__all__ = [
    "HelperTestArtifact",
    "ReproTestClass",
    "ReproTestResults",
    "CONFIRMATORY_CLASSES",
    "generate_candidates",
    "run_test_in_workspace",
    "classify",
    "run_semantic_audit",
    "freeze",
    "materialize",
    "verify_frozen",
    "has_issue_provenance",
    "suspicious_literals",
    "build_helper_test",
    "select_candidate",
]


def select_candidate(
    candidates: list[str],
    base_workspace: Path,
    problem_statement: str,
    forbidden_literals: list[str],
) -> tuple[str | None, dict]:
    """Gold-blind selection (plan §5.3): first candidate that collects, fails on
    base, has issue provenance, and contains no forbidden official literal."""
    base_workspace = Path(base_workspace)
    fallback = None
    for cand in candidates:
        outcome = run_test_in_workspace(base_workspace, cand)
        if not outcome.collected:
            continue
        if fallback is None:
            fallback = cand  # at least it runs
        fails_before = not outcome.passed
        provenance_ok = has_issue_provenance(cand, problem_statement)
        forbidden = contains_forbidden_literal(cand, forbidden_literals)
        if fails_before and provenance_ok and not forbidden:
            return cand, {"collected": True, "fail_before": True, "provenance_ok": True}
    return fallback, {"collected": fallback is not None}


def build_helper_test(
    task_id: str,
    problem_statement: str,
    repo_context: str,
    client,
    base_workspace: Path,
    gold_workspace: Path | None = None,
    forbidden_literals: list[str] | None = None,
    generator_model: str | None = None,
    k: int = 3,
) -> HelperTestArtifact:
    """Run the full C2 pipeline and return a frozen, classified helper artifact."""
    forbidden_literals = forbidden_literals or []
    candidates = generate_candidates(problem_statement, repo_context, client, k=k)

    selected, _info = select_candidate(
        candidates, base_workspace, problem_statement, forbidden_literals
    )
    if selected is None:
        return HelperTestArtifact(
            task_id=task_id, test_source="", generator_model=generator_model,
            prompt_hash=prompt_hash(problem_statement, repo_context),
            classification=ReproTestClass.T0_invalid, notes="no runnable candidate",
        )

    artifact = HelperTestArtifact(
        task_id=task_id, test_source=selected, generator_model=generator_model,
        prompt_hash=prompt_hash(problem_statement, repo_context),
    )
    # Freeze BEFORE consulting gold (plan §5.3 step 4).
    artifact = freeze(artifact)

    # Validate on base.
    base_outcome = run_test_in_workspace(Path(base_workspace), selected)
    artifact.collected = base_outcome.collected
    artifact.fail_before = base_outcome.collected and not base_outcome.passed

    # Offline gold diagnostic ONLY for classification (never switch candidate).
    pass_after = None
    if gold_workspace is not None:
        gold_outcome = run_test_in_workspace(Path(gold_workspace), selected)
        pass_after = gold_outcome.collected and gold_outcome.passed
    artifact.pass_after_gold = pass_after

    cls = classify(artifact.collected, bool(artifact.fail_before), pass_after)

    # Provenance/leakage audit -> T4 upgrade.
    flagged = suspicious_literals(selected, problem_statement)
    forbidden = contains_forbidden_literal(selected, forbidden_literals)
    artifact.suspicious_literals = flagged
    artifact.issue_provenance_ok = not flagged and not forbidden
    if cls in CONFIRMATORY_CLASSES and artifact.issue_provenance_ok:
        cls = ReproTestClass.T4_decoupled_valid

    artifact.classification = cls
    return artifact
