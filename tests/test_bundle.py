"""Tests for the frozen SupportBundle (EP-02)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from se_support.schemas import TaskSpec
from se_support.support import build_bundle, get_condition
from se_support.support.bundle import (
    STATUS_DECLARED_UNIMPLEMENTED,
    STATUS_PRESENT,
    SupportArtifact,
    SupportBundle,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _task() -> TaskSpec:
    return TaskSpec.model_validate(json.loads((FIXTURES / "task_mini_repo.json").read_text()))


def test_c0_bundle_is_empty(tmp_path):
    b = build_bundle(_task(), "C0_minimal", FIXTURES / "mini_repo")
    assert b.artifacts == []
    b.validate_against_condition(get_condition("C0_minimal"))


def test_c1_only_context(tmp_path):
    b = build_bundle(_task(), "C1_context", FIXTURES / "mini_repo")
    layers = {a.layer for a in b.artifacts}
    assert layers == {"context"}
    assert b.artifact("context").status == STATUS_PRESENT
    assert "calc.py" in b.artifact("context").content


def test_c2_tests_declared_unimplemented():
    b = build_bundle(_task(), "C2_tests", FIXTURES / "mini_repo")
    art = b.artifact("tests")
    assert art is not None
    assert art.status == STATUS_DECLARED_UNIMPLEMENTED  # C2 deferred, recorded honestly


def test_c6_equals_union_of_c1_to_c5():
    b6 = build_bundle(_task(), "C6_full_stack", FIXTURES / "mini_repo")
    layers = {a.layer for a in b6.artifacts}
    assert layers == {"context", "tests", "gates", "harness", "memory"}
    # Content of C6's context/memory equals the single-condition bundles' content.
    b1 = build_bundle(_task(), "C1_context", FIXTURES / "mini_repo")
    b5 = build_bundle(_task(), "C5_memory", FIXTURES / "mini_repo")
    assert b6.artifact("context").hash == b1.artifact("context").hash
    assert b6.artifact("memory").hash == b5.artifact("memory").hash


def test_validate_rejects_mismatch():
    # A bundle claiming a context artifact must not validate against C0.
    bad = SupportBundle("t", "C0_minimal", [
        SupportArtifact(layer="context", filename="context_pack.md",
                        status=STATUS_PRESENT, hash="sha256:x", content="x"),
    ])
    with pytest.raises(AssertionError):
        bad.validate_against_condition(get_condition("C0_minimal"))


def test_bundle_write_and_manifest(tmp_path):
    b = build_bundle(_task(), "C6_full_stack", FIXTURES / "mini_repo")
    manifest_path = b.write(tmp_path / "support")
    assert manifest_path.exists()
    # Present artifacts are written; unimplemented tests artifact is not.
    assert (tmp_path / "support" / "context_pack.md").exists()
    assert (tmp_path / "support" / "gate_policy.json").exists()
    assert not (tmp_path / "support" / "helper_test.py").exists()
    manifest = json.loads(manifest_path.read_text())
    assert manifest["bundle_hash"].startswith("sha256:")
    # Manifest carries metadata only (no content inlined).
    for a in manifest["artifacts"]:
        assert a["content"] == ""


def test_bundle_hash_is_deterministic():
    a = build_bundle(_task(), "C6_full_stack", FIXTURES / "mini_repo")
    b = build_bundle(_task(), "C6_full_stack", FIXTURES / "mini_repo")
    assert a.bundle_hash == b.bundle_hash
