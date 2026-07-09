"""Deterministic gates (C3) -- v1.

Runs checks against the current workspace state and reports structured results.
Blocking gates (syntax/build) must pass for a patch to be accepted; advisory
gates (lint/security) are recorded but do not block. The official FAIL_TO_PASS
tests are intentionally **not** a gate -- they stay hidden from the agent.

Each gate result matches the shape in PROJECT_PROPOSAL.md §6.4.
"""

from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path
from typing import Any


def _run(cmd: list[str], cwd: Path) -> tuple[int, str, float]:
    t0 = time.time()
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return proc.returncode, (proc.stdout + proc.stderr), time.time() - t0


def _gate(name: str, cmd: list[str], cwd: Path, blocking: bool) -> dict[str, Any]:
    code, out, dur = _run(cmd, cwd)
    return {
        "gate_name": name,
        "command": " ".join(cmd),
        "exit_code": code,
        "duration_sec": round(dur, 4),
        "blocking": blocking,
        "status": "pass" if code == 0 else "fail",
        "output_preview": out[:2000],
    }


def run_gates(workspace_path: Path) -> list[dict[str, Any]]:
    """Run the default Python gate set against the workspace."""
    results: list[dict[str, Any]] = []
    # Blocking: syntax/build.
    results.append(_gate("compileall", ["python", "-m", "compileall", "-q", "."],
                         workspace_path, blocking=True))
    # Advisory: lint (only if ruff is installed).
    if shutil.which("ruff"):
        results.append(_gate("ruff", ["ruff", "check", "."], workspace_path, blocking=False))
    # Advisory: security (only if bandit is installed).
    if shutil.which("bandit"):
        results.append(_gate("bandit", ["bandit", "-q", "-r", "."],
                             workspace_path, blocking=False))
    return results


def blocking_failures(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [r for r in results if r["blocking"] and r["status"] != "pass"]
