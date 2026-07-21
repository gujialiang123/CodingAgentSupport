"""Read-only injection + freezing of the helper test (EP-03, plan §5.5).

The helper test is frozen (hashed) at generation time and, whenever it runs, is
reconstructed from the frozen source rather than read from the agent's editable
workspace. Any attempt by the agent to delete/weaken/replace its workspace copy
therefore cannot change evaluation. This module provides the freeze + verified
reconstruct primitives.
"""

from __future__ import annotations

from pathlib import Path

from se_support.isolation.manifest import hash_text
from se_support.support.repro_tests.schema import HelperTestArtifact


def freeze(artifact: HelperTestArtifact) -> HelperTestArtifact:
    """Attach the content hash to the artifact (idempotent)."""
    return artifact.model_copy(update={"frozen_hash": hash_text(artifact.test_source)})


def verify_frozen(artifact: HelperTestArtifact) -> bool:
    """True if the artifact's source still matches its frozen hash."""
    return artifact.frozen_hash is not None and \
        hash_text(artifact.test_source) == artifact.frozen_hash


def materialize(
    artifact: HelperTestArtifact, dest_dir: Path, filename: str = "helper_test.py"
) -> Path:
    """Write the FROZEN helper source to ``dest_dir`` (used by the evaluator).

    Reconstructs from the frozen artifact, not from any workspace copy the agent
    may have modified. Refuses to write if the frozen hash does not verify.
    """
    if artifact.frozen_hash is not None and not verify_frozen(artifact):
        raise ValueError("helper artifact hash mismatch; refusing to materialize")
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    path = dest_dir / filename
    path.write_text(artifact.test_source, encoding="utf-8")
    return path
