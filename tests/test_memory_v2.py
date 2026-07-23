"""Tests for C5 v2 repository-scoped memory (plan P5)."""

from __future__ import annotations

import json
from pathlib import Path

from se_support.schemas import TaskSpec
from se_support.support.memory import build_memory, build_repo_memory, repo_slug

FIXTURES = Path(__file__).parent / "fixtures"


def _task() -> TaskSpec:
    return TaskSpec.model_validate(
        json.loads((FIXTURES / "task_mini_repo.json").read_text())
    )


def test_repo_slug():
    assert repo_slug("psf/requests") == "psf__requests"


def test_repo_memory_is_repo_scoped_not_task_scoped():
    mem = build_repo_memory("local/mini_repo", FIXTURES / "mini_repo")
    # repo-level structure present
    assert "Repository memory" in mem
    assert "Common failure recovery" in mem
    # must NOT leak the task's issue text or task-specific commands
    assert "subtract() returns wrong result" not in mem
    assert "calc.subtract(5, 3)" not in mem


def test_build_memory_prefers_frozen_cache(tmp_path):
    frozen = tmp_path / f"{repo_slug('local/mini_repo')}.md"
    frozen.write_text("FROZEN REPO MEMORY", encoding="utf-8")
    out = build_memory(_task(), FIXTURES / "mini_repo", cache_dir=tmp_path)
    assert out == "FROZEN REPO MEMORY"


def test_build_memory_derives_when_no_cache():
    out = build_memory(_task(), FIXTURES / "mini_repo")
    assert "Repository memory" in out
    # no task issue leakage even in the derived path
    assert "returns 8 instead of 2" not in out
