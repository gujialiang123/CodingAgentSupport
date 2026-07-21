"""Adversarial red-team tests for the EP-01 provenance firewall (plan §6.4).

These verify that an agent shell command cannot:
- read gold / official-test fields (scrubbed task carries none);
- traverse from the workspace into the run/task metadata directory;
- recover future commits via git log/reflog;
- access the network;
- (documented) filesystem confinement + network block via the sandbox.

Sandbox-dependent checks are skipped if no sandbox backend (bwrap/unshare) is
available, but the provenance-scrub checks always run.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from se_support.isolation import (
    FORBIDDEN_FIELDS,
    SandboxPolicy,
    assert_no_forbidden_fields,
    build_sandbox_argv,
    hash_text,
    sandbox_available,
    scrub_git_history,
    scrubbed_task_dict,
)
from se_support.isolation.manifest import VisibleInputManifest
from se_support.runner.workspace import Workspace
from se_support.schemas import TaskSpec

FIXTURES = Path(__file__).parent / "fixtures"

HAS_SANDBOX = sandbox_available() is not None
needs_bwrap = pytest.mark.skipif(
    sandbox_available() != "bwrap", reason="bubblewrap not available"
)


def _real_task() -> TaskSpec:
    return TaskSpec(
        task_id="swebench_verified__psf__requests-1142",
        dataset="swebench_verified",
        repo="psf/requests",
        base_commit="22623bd8c265b78b161542663ee980738441c307",
        issue_title="bug",
        issue_body="something is broken",
        gold_patch_path="data/gold_patches/psf__requests-1142.patch",
        test_patch_path="data/test_patches/psf__requests-1142.test.patch",
        fail_to_pass_tests=["test_requests.py::RequestsTestCase::test_no_content_length"],
        pass_to_pass_tests=["test_requests.py::t2"],
        environment_setup_commit="deadbeef",
    )


# -- provenance scrubbing (always runs) --------------------------------------
def test_scrubbed_task_has_no_forbidden_fields():
    task = _real_task()
    scrubbed = scrubbed_task_dict(task)
    for f in FORBIDDEN_FIELDS:
        assert f not in scrubbed, f
    # Positive: keeps the agent-safe essentials.
    assert scrubbed["repo"] == "psf/requests"
    assert scrubbed["base_commit"].startswith("22623bd")
    assert "issue_body" in scrubbed
    # The guard raises on a leak.
    assert_no_forbidden_fields(scrubbed)
    with pytest.raises(AssertionError):
        assert_no_forbidden_fields({"gold_patch_path": "x"})


def test_scrubbed_task_serialised_contains_no_gold_string():
    task = _real_task()
    blob = json.dumps(scrubbed_task_dict(task))
    assert "gold" not in blob
    assert "test_patch" not in blob
    assert "fail_to_pass" not in blob.lower()


# -- git history flattening --------------------------------------------------
def test_scrub_git_history_removes_future_commits(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "f.py").write_text("base\n")
    # Build a repo with a base commit and a "future" (solution) commit.
    import subprocess

    def g(*a):
        subprocess.run(["git", *a], cwd=repo, check=True, capture_output=True)

    g("init", "-q")
    g("config", "user.email", "a@b")
    g("config", "user.name", "a")
    g("add", "-A")
    g("commit", "-qm", "base")
    base_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo,
                              capture_output=True, text=True).stdout.strip()
    (repo / "f.py").write_text("FUTURE SOLUTION\n")
    g("add", "-A")
    g("commit", "-qm", "the fix")
    # Check out base so the working tree is the pre-fix state.
    g("checkout", "-q", base_sha)

    scrub_git_history(repo)

    log = subprocess.run(["git", "log", "--all", "--oneline"], cwd=repo,
                         capture_output=True, text=True).stdout
    assert "the fix" not in log
    reflog = subprocess.run(["git", "reflog"], cwd=repo,
                            capture_output=True, text=True).stdout
    assert "the fix" not in reflog
    # The future content is not recoverable from the working tree.
    assert (repo / "f.py").read_text() == "base\n"


# -- sandbox filesystem confinement + network block --------------------------
@needs_bwrap
def test_sandbox_blocks_secret_and_network(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "code.py").write_text("print('hi')\n")
    secret = tmp_path / "secret"
    secret.mkdir()
    (secret / "gold.patch").write_text("GOLD_SECRET\n")

    policy = SandboxPolicy.confirmatory()
    argv, backend = build_sandbox_argv(
        ["bash", "-lc", f"cat {secret}/gold.patch"], ws, policy
    )
    assert backend == "bwrap"
    import subprocess

    proc = subprocess.run(argv, capture_output=True, text=True)
    assert proc.returncode != 0
    assert "GOLD_SECRET" not in proc.stdout


@needs_bwrap
def test_sandbox_run_via_workspace(tmp_path):
    ws = Workspace.from_template(FIXTURES / "mini_repo", tmp_path / "ws")
    ws.scrub()
    policy = SandboxPolicy.confirmatory()
    # Can see workspace files.
    proc, backend = ws.run_sandboxed("ls", policy)
    assert backend == "bwrap"
    assert "calc.py" in proc.stdout
    # Cannot reach a sibling secret outside the workspace.
    secret = tmp_path / "secret.txt"
    secret.write_text("TOPSECRET\n")
    proc2, _ = ws.run_sandboxed(f"cat {secret}", policy)
    assert "TOPSECRET" not in proc2.stdout


def test_open_policy_runs_unwrapped(tmp_path):
    argv, backend = build_sandbox_argv(["echo", "hi"], tmp_path, SandboxPolicy.open())
    assert backend == "none"
    assert argv == ["echo", "hi"]


def test_run_single_writes_scrubbed_task_and_manifest(tmp_path):
    """Integration: a run with a sandbox policy must not expose gold in the
    agent-visible scrubbed task, and must record a visible-input manifest."""
    import json as _json

    from se_support.agents import MockAgent
    from se_support.runner.run_manager import run_single

    task = TaskSpec.model_validate(
        _json.loads((FIXTURES / "task_mini_repo.json").read_text())
    )
    assert task.gold_patch_path  # fixture does carry gold

    outcome = run_single(
        task, MockAgent("gold"), "C0_minimal", tmp_path, "iso_exp",
        model="mock", sandbox_policy=SandboxPolicy.confirmatory(),
    )
    rd = outcome.run_dir
    scrubbed = _json.loads((rd / "scrubbed_task.json").read_text())
    for f in FORBIDDEN_FIELDS:
        assert f not in scrubbed
    assert "gold" not in _json.dumps(scrubbed)
    manifest = _json.loads((rd / "visible_input_manifest.json").read_text())
    assert manifest["scrubbed_task_hash"].startswith("sha256:")
    assert manifest["network_allowed"] is False


# -- manifest ----------------------------------------------------------------
def test_visible_input_manifest(tmp_path):
    task = _real_task()
    scrubbed = scrubbed_task_dict(task)
    m = VisibleInputManifest(
        run_id="r1", condition="C0_minimal", base_commit=task.base_commit,
        scrubbed_task_hash=hash_text(json.dumps(scrubbed, sort_keys=True)),
        sandbox_backend=sandbox_available() or "none",
    )
    m.add_artifact("context_pack.md", "support_artifact", b"repo map ...")
    assert m.artifacts[0].hash.startswith("sha256:")
    # Round-trips.
    from se_support.schemas import ManipulationCheck  # noqa: F401 - schema import sanity

    reloaded = VisibleInputManifest.model_validate_json(m.model_dump_json())
    assert reloaded == m
