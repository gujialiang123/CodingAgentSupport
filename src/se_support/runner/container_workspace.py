"""Agent workspace backed by the SWE-bench instance container (P1).

Runs the agent **inside** the task's official Docker image, where the repository
lives at ``/testbed`` with its dependencies installed (conda env ``testbed``). This
lets the agent actually run the repo's tests, lint/type tools, and the C2 helper —
the capability a bare ``git clone`` lacks.

Isolation:
* ``docker run --network none`` -> no network reaches the agent;
* the agent only sees the container filesystem (host is not mounted);
* the container HEAD is SWE-bench's synthetic base commit, so the gold patch /
  official ``test_patch`` / future fix are not present.

Interface parity: exposes ``run_sandboxed``, ``is_dirty``, ``revert_all``,
``final_diff``, ``scrub`` and ``path`` so :class:`~se_support.agents.llm_agent.LLMAgent`
works unchanged. Official evaluation still runs via the harness afterwards.
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

from se_support.runner.run_dir import CommandRecord, RunDirectory

TESTBED = "/testbed"
_ACTIVATE = "source /opt/miniconda3/bin/activate testbed 2>/dev/null; cd /testbed"


def docker_host_env(env: dict | None = None) -> dict:
    e = dict(os.environ)
    e.setdefault("DOCKER_HOST", f"unix:///run/user/{os.getuid()}/docker.sock")
    if env:
        e.update(env)
    return e


def instance_image_name(instance_id: str, namespace: str = "swebench",
                        arch: str = "x86_64") -> str:
    """SWE-bench instance image name (encodes '__' -> '_1776_')."""
    enc = instance_id.replace("__", "_1776_")
    return f"{namespace}/sweb.eval.{arch}.{enc}:latest"


class ContainerWorkspace:
    def __init__(self, container_id: str, run_dir: RunDirectory | None,
                 env: dict, path: Path | None = None) -> None:
        self.cid = container_id
        self.run_dir = run_dir
        self.env = env
        # ``path`` is a host-side dir for artifacts (e.g. copied-out helper);
        # the agent's real cwd is /testbed inside the container.
        self.path = path or Path("/testbed")

    # -- lifecycle ------------------------------------------------------------
    @classmethod
    def start(
        cls,
        instance_id: str,
        run_dir: RunDirectory | None = None,
        *,
        namespace: str = "swebench",
        env: dict | None = None,
        idle_timeout: int = 7200,
    ) -> ContainerWorkspace:
        e = docker_host_env(env)
        image = instance_image_name(instance_id, namespace)
        proc = subprocess.run(
            ["docker", "run", "-d", "--network", "none", image,
             "sleep", str(idle_timeout)],
            capture_output=True, text=True, env=e,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"failed to start container for {instance_id}: {proc.stderr}")
        cid = proc.stdout.strip()
        return cls(cid, run_dir, e)

    def close(self) -> None:
        subprocess.run(["docker", "rm", "-f", self.cid],
                       capture_output=True, text=True, env=self.env)

    def __enter__(self) -> ContainerWorkspace:
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # -- exec helpers ---------------------------------------------------------
    def _exec(self, inner: str, check: bool = False) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["docker", "exec", self.cid, "bash", "-lc", inner],
            capture_output=True, text=True, env=self.env,
        )

    def _testbed(self, cmd: str, check: bool = False) -> subprocess.CompletedProcess:
        return self._exec(f"{_ACTIVATE}; {cmd}", check=check)

    # -- interface parity with Workspace --------------------------------------
    def scrub(self) -> None:
        """Flatten git history inside /testbed (defense-in-depth; base state kept)."""
        self._testbed(
            "git reflog expire --expire=now --all 2>/dev/null; "
            "git gc --prune=now -q 2>/dev/null; true"
        )

    def run_sandboxed(self, bash_command: str, policy=None, step: int | None = None):
        """Run an agent bash command inside the container at /testbed. Returns
        (proc, backend). ``policy`` is accepted for interface parity; network
        isolation is provided by the container (``--network none``)."""
        t0 = time.time()
        proc = self._testbed(bash_command)
        dur = time.time() - t0
        if self.run_dir is not None:
            self.run_dir.append_command(
                CommandRecord(
                    step=step, command=bash_command, exit_code=proc.returncode,
                    duration_sec=round(dur, 4), stdout_preview=proc.stdout[:2000],
                    meta={"stderr_preview": proc.stderr[:2000], "sandbox": "container"},
                )
            )
        return proc, "container"

    def is_dirty(self) -> bool:
        proc = self._testbed("git status --porcelain")
        return bool(proc.stdout.strip())

    def revert_all(self) -> None:
        self._testbed("git checkout -- . 2>/dev/null; git clean -fdq 2>/dev/null; true")

    def final_diff(self) -> str:
        proc = self._testbed(
            "git add -A -- . ':(exclude)**/__pycache__/**' ':(exclude)**/*.pyc' 2>/dev/null; "
            "git diff --cached HEAD"
        )
        return proc.stdout

    # -- C2 helper injection --------------------------------------------------
    def inject_file(self, container_path: str, content: str) -> None:
        """Write ``content`` to ``container_path`` inside the container."""
        import base64

        b64 = base64.b64encode(content.encode()).decode()
        self._exec(f"echo {b64} | base64 -d > {container_path}")

    def run_pytest(self, node_ids: list[str]) -> tuple[int, int]:
        """Run pytest node ids inside the container. Returns (passed, total)."""
        if not node_ids:
            return (0, 0)
        proc = self._testbed("python -m pytest -q --no-header -p no:cacheprovider "
                             + " ".join(node_ids))
        total = len(node_ids)
        if proc.returncode == 0:
            return (total, total)
        import re

        m = re.search(r"(\d+) passed", proc.stdout)
        return (int(m.group(1)) if m else 0, total)

    # -- gate + repo-reading helpers (for C3/C1/C5 inside the container) -------
    def gate_exec_fn(self):
        """An executor for gate_policy that runs argv inside /testbed."""
        import shlex

        def run(argv: list[str]) -> tuple[int, str]:
            cmd = " ".join(shlex.quote(a) for a in argv)
            proc = self._testbed(cmd)
            return proc.returncode, (proc.stdout + proc.stderr)
        return run

    def list_repo_files(self, max_files: int = 60) -> list[str]:
        proc = self._testbed(f"git ls-files 2>/dev/null | head -n {max_files}")
        return [x for x in proc.stdout.splitlines() if x.strip()]

    def has_file(self, name: str) -> bool:
        proc = self._testbed(f"test -f {name} && echo yes || echo no")
        return "yes" in proc.stdout

