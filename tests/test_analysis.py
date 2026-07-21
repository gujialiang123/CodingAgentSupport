"""Tests for the analysis package (EP-10)."""

from __future__ import annotations

from se_support.analysis import (
    mcnemar_exact,
    paired_contrast,
    summarize_by_condition,
)
from se_support.analysis.aggregate import AnalysisReport, RunRow, format_report


def _rows() -> list[RunRow]:
    # 3 tasks; C6 resolves all 3, C0 resolves 1 -> C6 should beat C0.
    rows = []
    for i, tid in enumerate(["t1", "t2", "t3"]):
        rows.append(RunRow(tid, "C0_minimal", 0, resolved=(i == 0),
                           patch_applies=True, quality="Q0_invalid"))
        rows.append(RunRow(tid, "C6_full_stack", 0, resolved=True,
                           patch_applies=True, quality="Q2_functionally_correct"))
    return rows


def test_summarize_by_condition():
    s = {x.condition: x for x in summarize_by_condition(_rows())}
    assert s["C0_minimal"].resolved == 1
    assert s["C6_full_stack"].resolved == 3
    assert s["C6_full_stack"].resolution_rate == 1.0


def test_mcnemar_exact_symmetry_and_bounds():
    assert mcnemar_exact(0, 0) == 1.0
    assert mcnemar_exact(5, 0) < 0.1     # all discordant one way -> small p
    assert mcnemar_exact(2, 2) == 1.0    # balanced -> p=1
    assert 0.0 <= mcnemar_exact(3, 1) <= 1.0


def test_paired_contrast_direction():
    c = paired_contrast(_rows(), "C6_full_stack", "C0_minimal", n_boot=1000)
    assert c.n_pairs == 3
    assert c.only_treat == 2   # C6 resolved t2,t3 where C0 did not
    assert c.only_base == 0
    assert c.delta_rate > 0     # C6 > C0
    assert c.boot_lo <= c.delta_rate <= c.boot_hi


def test_format_report_runs():
    from se_support.analysis import analyze  # noqa: F401
    report = AnalysisReport(
        experiment_id="x",
        condition_summaries=summarize_by_condition(_rows()),
        contrasts=[paired_contrast(_rows(), "C6_full_stack", "C0_minimal", n_boot=200)],
        warnings=["small cohort"],
    )
    md = format_report(report)
    assert "Resolution by condition" in md
    assert "McNemar p" in md
    assert "C6_full_stack" in md
