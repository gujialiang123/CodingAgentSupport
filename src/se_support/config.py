"""Project-wide constants and path configuration.

Centralises the on-disk layout so every module agrees on where tasks, runs,
results and schemas live. Paths are resolved relative to the repository root
(the parent of ``src/``) unless overridden by the ``SE_SUPPORT_ROOT`` env var.
"""

from __future__ import annotations

import os
from pathlib import Path

# Support conditions defined in PROJECT_PROPOSAL.md section 6.
SUPPORT_CONDITIONS: tuple[str, ...] = (
    "C0_minimal",
    "C1_context",
    "C2_tests",
    "C3_gates",
    "C4_harness",
    "C5_memory",
    "C6_full_stack",
)


def repo_root() -> Path:
    """Return the repository root directory."""
    env = os.environ.get("SE_SUPPORT_ROOT")
    if env:
        return Path(env).resolve()
    # src/se_support/config.py -> repo root is three parents up.
    return Path(__file__).resolve().parents[2]


def schemas_dir() -> Path:
    return repo_root() / "schemas"


def runs_dir() -> Path:
    return repo_root() / "runs"


def results_dir() -> Path:
    return repo_root() / "results"


def data_dir() -> Path:
    return repo_root() / "data"
