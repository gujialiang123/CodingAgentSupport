"""PatchQualityCard: non-functional patch quality (section 9.5 / 10).

This is the heart of RQ3 -- quality *beyond* pass/fail. Design notes:

* Every automatically-measured metric that depends on an external tool is
  ``Optional``; ``None`` means **unavailable** (tool not installed / not
  applicable) and must never be conflated with ``0``. See docs/experiment_protocol.md.
* Metrics are deltas (post-patch minus pre-patch) where noted, so they reflect
  the impact of *this* patch rather than absolute repo state.
* Cards are produced by an offline, re-runnable script from the run directory,
  so new fields can be back-filled without re-running experiments.
"""

from __future__ import annotations

from enum import Enum

from pydantic import Field

from se_support.schemas.base import SEModel


class QualityLevel(str, Enum):
    Q0_invalid = "Q0_invalid"
    Q1_plausible_failing = "Q1_plausible_failing"
    Q2_functionally_correct = "Q2_functionally_correct"
    Q3_engineering_acceptable = "Q3_engineering_acceptable"
    Q4_review_ready = "Q4_review_ready"
    Q5_human_quality = "Q5_human_quality"


class FunctionalCorrectness(SEModel):
    patch_applies: bool = False
    build_success: bool = False
    official_resolved: bool = False
    regression_failures: int = 0


class Locality(SEModel):
    files_touched: int = 0
    loc_added: int = 0
    loc_deleted: int = 0
    gold_file_overlap: float | None = None
    unrelated_file_change_suspected: bool = False


class Maintainability(SEModel):
    complexity_delta: float | None = None
    duplication_delta: float | None = None
    lint_new_warnings: int | None = None
    type_new_warnings: int | None = None


class SecurityReliability(SEModel):
    new_security_warnings: int | None = None
    error_handling_concern: bool = False
    resource_cleanup_concern: bool = False


class TestAdequacy(SEModel):
    tests_added: int = 0
    repro_test_fail_before: bool | None = None
    repro_test_pass_after: bool | None = None
    changed_line_coverage_delta: float | None = None


class Reviewability(SEModel):
    has_validation_report: bool = False
    description_diff_consistent: bool | None = None
    human_rating: int | None = None


class ProcessMetrics(SEModel):
    """Trajectory/process outcomes derived from the run logs (EP-08).

    All fields are recomputable offline from transcript.jsonl / commands.jsonl /
    state_transitions.json, so they can be back-filled without re-running.
    """

    turns: int = 0
    commands_run: int = 0
    failed_commands: int = 0
    edits_made: int | None = None
    gate_failures: int = 0
    gate_revisions: int = 0
    harness_rejections: int = 0
    localized_before_edit: bool | None = None
    sandbox_backend: str | None = None
    stop_reason: str | None = None  # "submitted" | "timeout" | "error"


class PatchQualityCard(SEModel):
    run_id: str
    task_id: str
    resolved: bool = False
    quality_level: QualityLevel = QualityLevel.Q0_invalid
    functional_correctness: FunctionalCorrectness = Field(default_factory=FunctionalCorrectness)
    locality: Locality = Field(default_factory=Locality)
    maintainability: Maintainability = Field(default_factory=Maintainability)
    security_reliability: SecurityReliability = Field(default_factory=SecurityReliability)
    test_adequacy: TestAdequacy = Field(default_factory=TestAdequacy)
    reviewability: Reviewability = Field(default_factory=Reviewability)
    process: ProcessMetrics = Field(default_factory=ProcessMetrics)
    failure_modes: list[str] = Field(default_factory=list)
    notes: str = ""
