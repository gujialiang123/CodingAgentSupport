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

from pathlib import Path

from se_support.runner.patch_utils import changed_files, diff_metrics
from se_support.schemas import EvalResult, PatchQualityCard, TaskSpec
from se_support.schemas.patch_quality_card import (
    FunctionalCorrectness,
    Locality,
    ProcessMetrics,
    QualityLevel,
)


def _gold_overlap(patch_files: list[str], gold_files: list[str]) -> float | None:
    if not gold_files:
        return None
    if not patch_files:
        return 0.0
    overlap = len(set(patch_files) & set(gold_files))
    return round(overlap / len(set(gold_files)), 4)


def _quality_level(ev: EvalResult) -> QualityLevel:
    """Automatic quality level. Caps at Q2 (EP-08 / plan §10.9): a resolved patch
    is 'functionally correct'; Q3+ ('engineering acceptable' and above) require a
    mature metric rubric and/or human judgment and must not be auto-assigned."""
    if not ev.patch_applies or not ev.build_success:
        return QualityLevel.Q0_invalid
    if not ev.resolved:
        return QualityLevel.Q1_plausible_failing
    return QualityLevel.Q2_functionally_correct


def build_card(
    task: TaskSpec,
    eval_result: EvalResult,
    final_diff: str,
    gold_diff: str | None = None,
    run_dir: Path | None = None,
) -> PatchQualityCard:
    dm = diff_metrics(final_diff)
    gold_files = changed_files(gold_diff) if gold_diff else []
    overlap = _gold_overlap(dm.files, gold_files)

    # Heuristic: a change touching files the gold patch never touched is
    # suspicious (over-broad). Only meaningful when we have a gold reference.
    # Descriptive only -- NOT ground-truth unrelatedness (plan §10.4).
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

    process = ProcessMetrics()
    if run_dir is not None:
        from se_support.quality.trajectory import extract_process_metrics

        process = extract_process_metrics(Path(run_dir))

    return PatchQualityCard(
        run_id=eval_result.run_id,
        task_id=task.task_id,
        resolved=eval_result.resolved,
        quality_level=_quality_level(eval_result),
        functional_correctness=fc,
        locality=loc,
        process=process,
    )


def recompute_card_from_run_dir(run_dir: Path) -> PatchQualityCard:
    """Rebuild a PatchQualityCard offline from a run directory's artifacts.

    Acceptance for EP-08: metrics are recomputable from saved artifacts without
    re-running the agent. Reads task.json, eval_result.json and final.patch.
    """
    import json

    from se_support.schemas import EvalResult, TaskSpec

    run_dir = Path(run_dir)
    task = TaskSpec.model_validate(json.loads((run_dir / "task.json").read_text()))
    eval_result = EvalResult.model_validate(json.loads((run_dir / "eval_result.json").read_text()))
    final_diff = (run_dir / "final.patch").read_text() if (run_dir / "final.patch").exists() else ""
    gold_diff = None
    gp = run_dir / ".." / ".."  # gold lives outside the run dir; skip unless provided
    _ = gp
    return build_card(task, eval_result, final_diff, gold_diff, run_dir=run_dir)

