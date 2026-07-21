"""Visible-input manifest and artifact hashing (EP-01).

Every run records exactly what the agent was allowed to see and a hash of each
visible artifact, so provenance can be audited after the fact
(EXPERIMENT_PLAN_2026-07-21.md §6.4: "Every run stores a scrubbed-input manifest
and hashes of all visible artifacts.").
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from pydantic import Field

from se_support.schemas.base import SEModel


def hash_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def hash_file(path: Path) -> str:
    return hash_bytes(Path(path).read_bytes())


def hash_text(text: str) -> str:
    return hash_bytes(text.encode("utf-8"))


class ArtifactHash(SEModel):
    name: str
    kind: str = Field(..., description="'support_artifact' | 'scrubbed_task' | 'workspace'")
    hash: str
    size_bytes: int | None = None


class VisibleInputManifest(SEModel):
    """The complete set of agent-visible inputs for one run, with hashes."""

    run_id: str
    condition: str
    base_commit: str
    scrubbed_task_hash: str
    sandbox_backend: str = Field(..., description="'bwrap' | 'unshare' | 'none'.")
    network_allowed: bool = False
    artifacts: list[ArtifactHash] = Field(default_factory=list)

    def add_artifact(self, name: str, kind: str, content: bytes) -> None:
        self.artifacts.append(
            ArtifactHash(name=name, kind=kind, hash=hash_bytes(content), size_bytes=len(content))
        )
