"""Repository memory generator (C5) -- v1.

Produces an AGENTS.md-style memory string from repository contents: build/test
recipes and detected conventions. v1 is intentionally minimal and generated
(never hand-authored per task, never leaking gold patches).
"""

from __future__ import annotations

from pathlib import Path

from se_support.schemas import TaskSpec

_CONVENTION_FILES = ("pyproject.toml", "setup.cfg", "tox.ini", "ruff.toml", ".ruff.toml")


def build_memory(task: TaskSpec, workspace_path: Path, reader=None) -> str:
    lines = ["## Repository memory (AGENTS.md, auto-generated)", ""]
    if task.setup_command:
        lines.append(f"- Setup: `{task.setup_command}`")
    if task.test_command:
        lines.append(f"- Run tests: `{task.test_command}`")

    if reader is not None and hasattr(reader, "has_file"):
        detected = [f for f in _CONVENTION_FILES if reader.has_file(f)]
    else:
        detected = [f for f in _CONVENTION_FILES if (workspace_path / f).exists()]
    if detected:
        lines.append(f"- Config/convention files present: {', '.join(detected)}")
    lines.append("- Keep changes minimal and consistent with existing style.")
    lines.append("- Do not modify unrelated files or tests you were not asked to change.")
    return "\n".join(lines) + "\n"
