"""ManipulationCheck: did a condition apply exactly its intended treatment?

Every confirmatory run must be able to *prove* that its support condition changed
the intended mechanism and nothing else (EXPERIMENT_PLAN_2026-07-21.md §8 E0 and
the go/no-go checklists). This record is produced before/around the agent run and
stored as ``manipulation.json`` so that runs with a failed manipulation check can
be excluded or flagged rather than silently trusted.
"""

from __future__ import annotations

from pydantic import Field

from se_support.schemas.base import SEModel


class ManipulationCheck(SEModel):
    run_id: str
    condition: str = Field(..., description="Condition id whose treatment is checked.")
    # Which support artifacts were actually present for this run.
    context_present: bool = False
    tests_present: bool = False
    gates_present: bool = False
    harness_present: bool = False
    memory_present: bool = False
    # Provenance / isolation guarantees verified for this run.
    no_gold_in_visible_inputs: bool | None = Field(
        None, description="Verified that agent-visible inputs contain no gold/official-test data."
    )
    network_disabled: bool | None = Field(
        None, description="Verified that the agent had no network access."
    )
    support_manifest_hash: str | None = Field(
        None, description="Hash of the frozen support bundle actually mounted."
    )
    passed: bool = Field(
        False, description="Overall: did the condition apply exactly its intended treatment?"
    )
    notes: str = ""
