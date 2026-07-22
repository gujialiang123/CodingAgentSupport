"""Context pack generator (C1) -- v1.

Produces a small, task-relevant context string from the workspace: a repository
file map and inferred test command hints. Deliberately lexical/structural (no
LLM, no gold patch) so it is cheap and leak-free. Richer retrieval (symbol map,
API examples) is future work.
"""

from __future__ import annotations

from pathlib import Path

from se_support.schemas import TaskSpec

_SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".ruff_cache", "node_modules"}
_MAX_FILES = 60


def build_context_pack(task: TaskSpec, workspace_path: Path, reader=None) -> str:
    files: list[str] = []
    if reader is not None and hasattr(reader, "list_repo_files"):
        files = reader.list_repo_files(_MAX_FILES)
    else:
        for p in sorted(workspace_path.rglob("*")):
            if any(part in _SKIP_DIRS for part in p.parts):
                continue
            if p.is_file():
                files.append(str(p.relative_to(workspace_path)))
            if len(files) >= _MAX_FILES:
                break

    lines = ["## Repository context (auto-generated)", ""]
    lines.append(f"Repository: {task.repo}")
    if task.test_command:
        lines.append(f"Test command hint: `{task.test_command}`")
    lines.append("")
    lines.append("Files:")
    lines += [f"- {f}" for f in files]
    if len(files) >= _MAX_FILES:
        lines.append(f"- ... (truncated at {_MAX_FILES} files)")
    return "\n".join(lines) + "\n"
