"""Analysis package (EP-10): aggregate runs into paired tables + statistics."""

from se_support.analysis.aggregate import (
    AnalysisReport,
    ConditionSummary,
    PairedContrast,
    analyze,
    format_report,
    load_runs,
    mcnemar_exact,
    paired_contrast,
    summarize_by_condition,
)

__all__ = [
    "AnalysisReport",
    "ConditionSummary",
    "PairedContrast",
    "analyze",
    "format_report",
    "load_runs",
    "mcnemar_exact",
    "paired_contrast",
    "summarize_by_condition",
]
