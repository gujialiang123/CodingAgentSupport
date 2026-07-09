"""PatchQualityCard v0 computation (offline, re-runnable).

Inputs are already-recorded artifacts, so this can be re-run to back-fill new
metrics without touching the agent:

* ``eval_result`` -- correctness (from the evaluator).
* ``final_diff``  -- the agent's patch text (for locality).
* ``gold_diff``   -- optional human patch (for gold-file overlap).

Metrics not yet implemented (lint/type/security/complexity/coverage) are left as
``None`` = **unavailable**, per the protocol's "missing != 0" rule.
"""

from __future__ import annotations

from se_support.runner.patch_utils import changed_files, diff_metrics
from se_support.schemas import EvalResult, PatchQualityCard, TaskSpec
from se_support.schemas.patch_quality_card import (
    FunctionalCorrectness,
    Locality,
    QualityLevel,
)


def _gold_overlap(patch_files: list[str], gold_files: list[str]) -> float | None:
    if not gold_files:
        return None
    if not patch_files:
        return 0.0
    overlap = len(set(patch_files) & set(gold_files))
    return round(overlap / len(set(gold_files)), 4)


def _quality_level(ev: EvalResult, unrelated: bool) -> QualityLevel:
    if not ev.patch_applies or not ev.build_success:
        return QualityLevel.Q0_invalid
    if not ev.resolved:
        return QualityLevel.Q1_plausible_failing
    # Resolved. Distinguish "engineering acceptable" from bare "functionally
    # correct" using the only signal we have in v0: locality cleanliness.
    if unrelated:
        return QualityLevel.Q2_functionally_correct
    return QualityLevel.Q3_engineering_acceptable


def build_card(
    task: TaskSpec,
    eval_result: EvalResult,
    final_diff: str,
    gold_diff: str | None = None,
) -> PatchQualityCard:
    dm = diff_metrics(final_diff)
    gold_files = changed_files(gold_diff) if gold_diff else []
    overlap = _gold_overlap(dm.files, gold_files)

    # Heuristic: a change touching files the gold patch never touched is
    # suspicious (over-broad). Only meaningful when we have a gold reference.
    unrelated = bool(gold_files) and any(f not in gold_files for f in dm.files)

    fc = FunctionalCorrectness(
        patch_applies=eval_result.patch_applies,
        build_success=eval_result.build_success,
        official_resolved=eval_result.resolved,
        regression_failures=max(
            0, eval_result.pass_to_pass_total - eval_result.pass_to_pass_passed
        ),
    )
    loc = Locality(
        files_touched=dm.files_touched,
        loc_added=dm.loc_added,
        loc_deleted=dm.loc_deleted,
        gold_file_overlap=overlap,
        unrelated_file_change_suspected=unrelated,
    )

    return PatchQualityCard(
        run_id=eval_result.run_id,
        task_id=task.task_id,
        resolved=eval_result.resolved,
        quality_level=_quality_level(eval_result, unrelated),
        functional_correctness=fc,
        locality=loc,
    )
