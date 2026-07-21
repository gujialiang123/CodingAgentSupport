"""Sandbox policy (EP-01).

A frozen description of what an agent's shell commands are allowed to touch.
Defaults deny network and confine the filesystem to the workspace, which is the
required posture for confirmatory runs (EXPERIMENT_PLAN_2026-07-21.md §6).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SandboxPolicy:
    """Filesystem + network policy for agent command execution."""

    enable_sandbox: bool = True
    allow_network: bool = False
    # Read-only system paths made visible inside the sandbox so tooling works.
    ro_binds: tuple[str, ...] = (
        "/usr", "/bin", "/lib", "/lib64", "/sbin", "/etc/alternatives",
        "/etc/ssl", "/opt/conda", "/home/jgu7/miniconda3",
    )
    # Environment variables to set inside the sandbox.
    env: dict[str, str] = field(default_factory=lambda: {
        "PATH": "/usr/bin:/bin:/usr/local/bin:/home/jgu7/miniconda3/bin",
        "HOME": "/work",
        "LANG": "C.UTF-8",
    })
    die_with_parent: bool = True

    @classmethod
    def confirmatory(cls) -> SandboxPolicy:
        """Strict policy for confirmatory experiments: no network, fs-confined."""
        return cls(enable_sandbox=True, allow_network=False)

    @classmethod
    def open(cls) -> SandboxPolicy:
        """No sandbox (development/smoke only; never for confirmatory runs)."""
        return cls(enable_sandbox=False, allow_network=True)
