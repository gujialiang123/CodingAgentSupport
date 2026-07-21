"""Schemas for C2 reproduction-test support (EP-03, plan §5).

The five test classes B/J/H/A/S are never collapsed; this module models the
researcher-generated **helper** test (H) artifact and its T0-T4 validity class.
"""

from __future__ import annotations

from enum import Enum

from pydantic import Field

from se_support.schemas.base import SEModel


class ReproTestClass(str, Enum):
    """Validity classification of a frozen helper candidate (plan §5.3)."""

    T0_invalid = "T0_invalid"                      # cannot collect/import/execute
    T1_non_reproducing = "T1_non_reproducing"      # passes on base commit
    T2_incompatible_oracle = "T2_incompatible_oracle"  # fails on base AND on gold
    T3_valid_reproduction = "T3_valid_reproduction"    # fails on base, passes on gold
    T4_decoupled_valid = "T4_decoupled_valid"      # T3 + audit finds no leakage/overfit


CONFIRMATORY_CLASSES = {ReproTestClass.T3_valid_reproduction, ReproTestClass.T4_decoupled_valid}


class HelperTestArtifact(SEModel):
    """A frozen, hashed C2 helper reproduction test (class H)."""

    task_id: str
    test_source: str
    run_command: str = "python -m pytest helper_test.py"
    generator_model: str | None = None
    prompt_hash: str | None = None
    candidate_index: int = 0
    frozen_hash: str | None = None
    # Validation outcomes (offline diagnostics; gold used only to classify).
    collected: bool | None = None
    fail_before: bool | None = None       # fails on the base commit
    pass_after_gold: bool | None = None   # passes once the gold patch is applied
    classification: ReproTestClass = ReproTestClass.T0_invalid
    # Provenance / audit.
    issue_provenance_ok: bool | None = None
    suspicious_literals: list[str] = Field(default_factory=list)
    audit_passed: bool | None = None      # hidden semantic audit (S) passed on gold
    notes: str = ""


class ReproTestResults(SEModel):
    """Per-run results kept separate for the five test classes (plan §5.1)."""

    run_id: str
    # B/J come from the evaluator; H/A/S recorded here.
    helper_passed: bool | None = None        # H
    agent_tests_added: int = 0               # A
    semantic_audit_passed: bool | None = None  # S
    notes: str = ""
