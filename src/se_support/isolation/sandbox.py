"""Sandboxed command execution (EP-01).

Wraps an agent shell command with **bubblewrap** (`bwrap`) so that, for
confirmatory runs, the command:

* sees only the workspace (bound at ``/work``) plus read-only system paths, so it
  cannot traverse into the run/task metadata directory or another condition's
  artifacts;
* has **no network** (``--unshare-net``), so it cannot fetch the upstream fix or
  reach any service.

If ``bwrap`` is unavailable the code falls back to ``unshare -r -n`` (network
isolation only, no filesystem confinement) and records that the weaker mode was
used; callers doing confirmatory runs should treat that as a manipulation-check
failure. With ``enable_sandbox=False`` the command runs unwrapped (dev/smoke).
"""

from __future__ import annotations

import shutil
from pathlib import Path

from se_support.isolation.policy import SandboxPolicy


def sandbox_available() -> str | None:
    """Return the strongest available sandbox backend name, or None."""
    if shutil.which("bwrap"):
        return "bwrap"
    if shutil.which("unshare"):
        return "unshare"
    return None


def build_sandbox_argv(
    inner_cmd: list[str],
    workspace: Path,
    policy: SandboxPolicy,
) -> tuple[list[str], str]:
    """Return (argv, backend) to run ``inner_cmd`` under the given policy.

    ``workspace`` is bound at ``/work`` and is the working directory. ``backend``
    is one of ``"bwrap"``, ``"unshare"`` or ``"none"``.
    """
    workspace = Path(workspace).resolve()

    if not policy.enable_sandbox:
        return inner_cmd, "none"

    backend = sandbox_available()
    if backend == "bwrap":
        argv = ["bwrap"]
        for ro in policy.ro_binds:
            if Path(ro).exists():
                argv += ["--ro-bind", ro, ro]
        argv += ["--bind", str(workspace), "/work", "--chdir", "/work"]
        argv += ["--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp"]
        if not policy.allow_network:
            argv += ["--unshare-net"]
        if policy.die_with_parent:
            argv += ["--die-with-parent"]
        for k, v in policy.env.items():
            argv += ["--setenv", k, v]
        argv += ["--"]
        argv += inner_cmd
        return argv, "bwrap"

    if backend == "unshare":
        # Weaker: network isolation only, no filesystem confinement.
        argv = ["unshare", "--user", "--map-root-user"]
        if not policy.allow_network:
            argv += ["--net"]
        argv += ["--"] + inner_cmd
        return argv, "unshare"

    # No sandbox backend available.
    return inner_cmd, "none"
