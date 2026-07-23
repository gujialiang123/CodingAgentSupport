"""Frozen support bundle (EP-02).

A :class:`SupportBundle` is the complete set of support artifacts for one
(task, condition), generated **before** the agent runs, hashed, and written to
``support/`` so it can be mounted read-only and audited. This makes C6 provably
equal to the union of C1-C5 and C0 provably empty
(EXPERIMENT_PLAN_2026-07-21.md §14 EP-02).

Each of the five support layers maps to one artifact:

| layer   | condition flag | artifact              | status when enabled            |
|---------|----------------|-----------------------|--------------------------------|
| context | C1 / C6        | ``context_pack.md``   | present                        |
| tests   | C2 / C6        | ``helper_test.py``    | **declared_unimplemented** (C2 deferred) |
| gates   | C3 / C6        | ``gate_policy.json``  | present                        |
| harness | C4 / C6        | ``harness_policy.json``| present                       |
| memory  | C5 / C6        | ``repo_memory.md``    | present                        |

The ``tests`` layer is currently deferred (see DISCUSSION_2026-07-09.md); the
bundle records it as ``declared_unimplemented`` so manipulation checks and
analysis never silently treat C2/C6 as having a helper test.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import Field

from se_support.config import CONDITION_VERSION
from se_support.isolation.manifest import hash_text
from se_support.schemas.base import SEModel
from se_support.schemas.task_spec import TaskSpec
from se_support.support.condition import SupportCondition, get_condition
from se_support.support.context_pack import (
    build_context_pack,
    build_context_pack_v2,
    build_random_context_pack,
)
from se_support.support.memory import build_memory

LAYERS = ("context", "tests", "gates", "harness", "memory")

STATUS_PRESENT = "present"
STATUS_ABSENT = "absent"
STATUS_DECLARED_UNIMPLEMENTED = "declared_unimplemented"


class SupportArtifact(SEModel):
    layer: str = Field(..., description="One of context/tests/gates/harness/memory.")
    filename: str
    status: str = Field(..., description="present | absent | declared_unimplemented.")
    hash: str | None = None
    content: str = Field("", description="Artifact text (empty when absent).")


class SupportBundleManifest(SEModel):
    """Serialisable, content-free summary of a bundle (goes to support/manifest.json)."""

    task_id: str
    condition: str
    condition_version: str = CONDITION_VERSION
    bundle_hash: str
    artifacts: list[SupportArtifact] = Field(default_factory=list)


def _gate_policy_artifact() -> SupportArtifact:
    from se_support.support.gate_policy import GatePolicy

    content = json.dumps(GatePolicy().to_dict(), indent=2, sort_keys=True)
    return SupportArtifact(
        layer="gates", filename="gate_policy.json", status=STATUS_PRESENT,
        hash=hash_text(content), content=content,
    )


def _harness_policy_artifact() -> SupportArtifact:
    policy = {
        "states": ["DISCOVER", "DIAGNOSE", "PATCH", "VALIDATE", "SUBMIT"],
        "edits_allowed_in": ["PATCH", "VALIDATE"],
        "submit_requires_validation_record": True,
        "enforced": False,
        "note": "prompt-level in v0.1; state-machine enforcement is EP-04.",
    }
    content = json.dumps(policy, indent=2, sort_keys=True)
    return SupportArtifact(
        layer="harness", filename="harness_policy.json", status=STATUS_PRESENT,
        hash=hash_text(content), content=content,
    )


def _context_artifact(
    task: TaskSpec, workspace_path: Path, reader=None, variant: str = "v2"
) -> SupportArtifact:
    if variant == "random":
        content = build_random_context_pack(task, workspace_path, reader=reader)
    elif variant == "v1":
        content = build_context_pack(task, workspace_path, reader=reader)
    else:
        content = build_context_pack_v2(task, workspace_path, reader=reader)
    return SupportArtifact(
        layer="context", filename="context_pack.md", status=STATUS_PRESENT,
        hash=hash_text(content), content=content,
    )


def _memory_artifact(task: TaskSpec, workspace_path: Path, reader=None) -> SupportArtifact:
    content = build_memory(task, workspace_path, reader=reader)
    return SupportArtifact(
        layer="memory", filename="repo_memory.md", status=STATUS_PRESENT,
        hash=hash_text(content), content=content,
    )


def _tests_artifact(helper_artifact=None) -> SupportArtifact:
    """C2 helper test artifact.

    If a validated (T3/T4) frozen helper is provided it is carried as ``present``;
    otherwise the layer is honestly ``declared_unimplemented`` (no helper generated).
    """
    from se_support.support.repro_tests.schema import CONFIRMATORY_CLASSES

    if helper_artifact is not None and helper_artifact.classification in CONFIRMATORY_CLASSES:
        return SupportArtifact(
            layer="tests", filename="helper_test.py", status=STATUS_PRESENT,
            hash=helper_artifact.frozen_hash or hash_text(helper_artifact.test_source),
            content=helper_artifact.test_source,
        )
    return SupportArtifact(
        layer="tests", filename="helper_test.py",
        status=STATUS_DECLARED_UNIMPLEMENTED, hash=None, content="",
    )


class SupportBundle:
    """The frozen support artifacts for one (task, condition)."""

    def __init__(self, task_id: str, condition: str, artifacts: list[SupportArtifact]) -> None:
        self.task_id = task_id
        self.condition = condition
        self.artifacts = artifacts

    @property
    def bundle_hash(self) -> str:
        parts = sorted(f"{a.layer}:{a.status}:{a.hash or ''}" for a in self.artifacts)
        return hash_text("\n".join(parts))

    def artifact(self, layer: str) -> SupportArtifact | None:
        for a in self.artifacts:
            if a.layer == layer:
                return a
        return None

    def manifest(self) -> SupportBundleManifest:
        # Manifest carries metadata only (content stripped) plus the bundle hash.
        meta = [a.model_copy(update={"content": ""}) for a in self.artifacts]
        return SupportBundleManifest(
            task_id=self.task_id, condition=self.condition,
            bundle_hash=self.bundle_hash, artifacts=meta,
        )

    def write(self, support_dir: Path) -> Path:
        support_dir = Path(support_dir)
        support_dir.mkdir(parents=True, exist_ok=True)
        for a in self.artifacts:
            if a.status == STATUS_PRESENT and a.content:
                (support_dir / a.filename).write_text(a.content, encoding="utf-8")
        manifest_path = support_dir / "manifest.json"
        manifest_path.write_text(self.manifest().model_dump_json(indent=2) + "\n")
        return manifest_path

    def validate_against_condition(self, condition: SupportCondition) -> None:
        """Assert the bundle's present artifacts exactly match the condition flags."""
        flags = {
            "context": condition.context, "tests": condition.tests,
            "gates": condition.gates, "harness": condition.harness,
            "memory": condition.memory,
        }
        for layer, enabled in flags.items():
            art = self.artifact(layer)
            if enabled:
                assert art is not None, f"{condition.id}: missing enabled layer {layer}"
                assert art.status != STATUS_ABSENT, f"{condition.id}: {layer} absent"
            else:
                assert art is None, f"{condition.id}: unexpected artifact for disabled {layer}"


def build_bundle(
    task: TaskSpec, condition_id: str, workspace_path: Path, helper_artifact=None,
    reader=None,
) -> SupportBundle:
    """Generate the frozen support bundle for a condition (before the agent runs).

    ``helper_artifact`` is an optional pre-generated, validated C2 helper (EP-03);
    when present and valid it populates the tests layer for C2/C6. ``reader`` is an
    optional container reader so C1/C5 read the repo inside the instance image.
    """
    cond = get_condition(condition_id)
    artifacts: list[SupportArtifact] = []
    if cond.context:
        variant = "random" if condition_id == "C1_random" else "v2"
        artifacts.append(
            _context_artifact(task, workspace_path, reader=reader, variant=variant)
        )
    if cond.tests:
        artifacts.append(_tests_artifact(helper_artifact))
    if cond.gates:
        artifacts.append(_gate_policy_artifact())
    if cond.harness:
        artifacts.append(_harness_policy_artifact())
    if cond.memory:
        artifacts.append(_memory_artifact(task, workspace_path, reader=reader))
    bundle = SupportBundle(task.task_id, condition_id, artifacts)
    bundle.validate_against_condition(cond)
    return bundle
