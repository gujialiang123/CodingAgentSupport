"""Provenance scrubbing (EP-01).

Two firewalls that stop future-solution / gold information reaching the agent:

* :func:`scrub_git_history` flattens the workspace git repo to a single "base"
  commit, removing remotes, reflogs and the object store of *future* commits, so
  the agent cannot recover the upstream fix via ``git log``/``fetch``/reflog.
* :func:`scrubbed_task_dict` returns only the agent-safe fields of a TaskSpec.
  Gold and official-test fields (``gold_patch_path``, ``test_patch_path``,
  ``fail_to_pass_tests``, ``pass_to_pass_tests``, ``environment_setup_commit``)
  are dropped so they never land in an agent-visible file.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from se_support.schemas import TaskSpec

# TaskSpec fields the agent is allowed to see.
AGENT_VISIBLE_FIELDS = (
    "task_id",
    "dataset",
    "repo",
    "base_commit",
    "issue_title",
    "issue_body",
    "test_command",
    "setup_command",
)

# TaskSpec fields that must NEVER appear in agent-visible inputs.
FORBIDDEN_FIELDS = (
    "gold_patch_path",
    "test_patch_path",
    "fail_to_pass_tests",
    "pass_to_pass_tests",
    "environment_setup_commit",
)


def scrubbed_task_dict(task: TaskSpec) -> dict:
    """Return only the agent-safe fields of a task (no gold/official-test data)."""
    full = task.model_dump()
    return {k: full[k] for k in AGENT_VISIBLE_FIELDS if k in full}


def assert_no_forbidden_fields(data: dict) -> None:
    """Raise if any forbidden (gold/official-test) field is present/non-empty."""
    leaked = [f for f in FORBIDDEN_FIELDS if data.get(f)]
    if leaked:
        raise AssertionError(f"agent-visible input leaks forbidden fields: {leaked}")


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)


def scrub_git_history(workspace_path: Path) -> None:
    """Flatten the repo to a single base commit; drop remotes/reflogs/future objects."""
    workspace_path = Path(workspace_path)
    gitdir = workspace_path / ".git"
    if gitdir.exists():
        shutil.rmtree(gitdir)
    _git(workspace_path, "init", "-q")
    _git(workspace_path, "config", "user.email", "runner@se-support.local")
    _git(workspace_path, "config", "user.name", "se-support-runner")
    _git(workspace_path, "add", "-A")
    _git(workspace_path, "commit", "-qm", "base")
    # Expire any reflog and prune unreachable objects, just in case.
    _git(workspace_path, "reflog", "expire", "--expire=now", "--all")
    _git(workspace_path, "gc", "--prune=now", "-q")
