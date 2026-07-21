"""Isolated per-run workspace backed by a real git repo.

For offline/fixture tasks the workspace is seeded from ``TaskSpec.local_repo_path``
(copied, then ``git init`` + an initial "base" commit). Real SWE-bench tasks will
instead ``git checkout`` ``repo@base_commit`` -- the same interface applies.

Responsibilities:
* materialise the base repository state,
* let an agent edit files,
* produce the final unified diff (``git diff`` vs base),
* apply/reverse patches,
* run selected pytest node ids and report pass counts.

All shell commands can be tee'd into a :class:`RunDirectory` command log.
"""

from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path

from se_support.runner.run_dir import CommandRecord, RunDirectory


class Workspace:
    def __init__(self, path: Path, run_dir: RunDirectory | None = None) -> None:
        self.path = Path(path)
        self.run_dir = run_dir

    # -- construction ---------------------------------------------------------
    @classmethod
    def from_template(
        cls,
        template_dir: Path,
        dest: Path,
        run_dir: RunDirectory | None = None,
    ) -> Workspace:
        dest = Path(dest)
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(template_dir, dest)
        ws = cls(dest, run_dir)
        ws._git("init", "-q")
        ws._git("config", "user.email", "runner@se-support.local")
        ws._git("config", "user.name", "se-support-runner")
        ws._git("add", "-A")
        ws._git("commit", "-qm", "base")
        return ws

    @classmethod
    def from_git(
        cls,
        repo: str,
        base_commit: str,
        dest: Path,
        run_dir: RunDirectory | None = None,
        remote_base: str = "https://github.com",
    ) -> Workspace:
        """Clone ``repo`` and check out ``base_commit`` (real SWE-bench tasks).

        Uses fetch-by-SHA (shallow) with a full-clone fallback. Requires network;
        heavy repos take time. Official test evaluation still runs via the
        SWE-bench Docker harness (later ticket); this materialises the base state
        for the agent to edit.
        """
        dest = Path(dest)
        if dest.exists():
            shutil.rmtree(dest)
        dest.mkdir(parents=True)
        url = f"{remote_base}/{repo}.git"
        ws = cls(dest, run_dir)
        ws._git("init", "-q")
        ws._git("config", "user.email", "runner@se-support.local")
        ws._git("config", "user.name", "se-support-runner")
        ws._git("remote", "add", "origin", url)
        fetched = ws._git("fetch", "--depth", "1", "origin", base_commit, check=False)
        if fetched.returncode != 0:
            # Fallback: unshallow fetch of the commit.
            ws._git("fetch", "origin", base_commit)
        ws._git("checkout", "-q", base_commit)
        # Re-anchor a local base commit so final_diff() works against it.
        ws._git("checkout", "-q", "-B", "se_support_base")
        return ws

    # -- git helpers ----------------------------------------------------------
    def _run(self, *cmd: str, step: int | None = None, check: bool = True):
        t0 = time.time()
        proc = subprocess.run(
            list(cmd), cwd=self.path, capture_output=True, text=True
        )
        dur = time.time() - t0
        if self.run_dir is not None:
            self.run_dir.append_command(
                CommandRecord(
                    step=step,
                    command=" ".join(cmd),
                    exit_code=proc.returncode,
                    duration_sec=round(dur, 4),
                    stdout_preview=proc.stdout[:2000],
                    meta={"stderr_preview": proc.stderr[:2000]},
                )
            )
        if check and proc.returncode != 0:
            raise RuntimeError(
                f"command failed ({proc.returncode}): {' '.join(cmd)}\n{proc.stderr}"
            )
        return proc

    def _git(self, *args: str, check: bool = True):
        return self._run("git", *args, check=check)

    def scrub(self) -> None:
        """Flatten git history so the agent cannot recover future commits (EP-01)."""
        from se_support.isolation import scrub_git_history

        scrub_git_history(self.path)

    def run_sandboxed(self, bash_command: str, policy, step: int | None = None):
        """Run an agent bash command under the sandbox policy (EP-01).

        Unlike :meth:`_run` (used for orchestrator git ops), this wraps the
        command with bubblewrap/unshare so the agent has no network and cannot
        escape the workspace. Returns (proc, backend).
        """
        from se_support.isolation import build_sandbox_argv

        argv, backend = build_sandbox_argv(["bash", "-lc", bash_command], self.path, policy)
        t0 = time.time()
        # When sandboxed with bwrap the cwd is /work; else run in self.path.
        cwd = None if backend == "bwrap" else self.path
        proc = subprocess.run(argv, cwd=cwd, capture_output=True, text=True)
        dur = time.time() - t0
        if self.run_dir is not None:
            self.run_dir.append_command(
                CommandRecord(
                    step=step,
                    command=bash_command,
                    exit_code=proc.returncode,
                    duration_sec=round(dur, 4),
                    stdout_preview=proc.stdout[:2000],
                    meta={"stderr_preview": proc.stderr[:2000], "sandbox": backend},
                )
            )
        return proc, backend

    # -- patch operations -----------------------------------------------------
    def apply_patch(self, diff_text: str, check: bool = True) -> bool:
        if not diff_text.strip():
            return True
        patch_file = self.path / ".se_support_apply.patch"
        patch_file.write_text(diff_text, encoding="utf-8")
        proc = self._git("apply", "--whitespace=nowarn", str(patch_file.name), check=False)
        patch_file.unlink(missing_ok=True)
        if check and proc.returncode != 0:
            raise RuntimeError(f"patch did not apply:\n{proc.stderr}")
        return proc.returncode == 0

    def final_diff(self) -> str:
        # Diff working tree against base, excluding Python caches that agent/gate
        # commands create (they would otherwise pollute the patch and break apply).
        self._git(
            "add", "-A", "--", ".",
            ":(exclude)**/__pycache__/**", ":(exclude)**/*.pyc",
        )
        proc = self._git("diff", "--cached", "HEAD")
        return proc.stdout

    # -- test execution -------------------------------------------------------
    def run_pytest(self, node_ids: list[str], step: int | None = None) -> tuple[int, int]:
        """Run the given pytest node ids. Returns (passed, total)."""
        if not node_ids:
            return (0, 0)
        proc = self._run(
            "python", "-m", "pytest", "-q", "--no-header", "-p", "no:cacheprovider",
            *node_ids, step=step, check=False,
        )
        # Count passed nodes by re-running per-node for robustness is expensive;
        # instead parse the summary. A zero exit code means all passed.
        total = len(node_ids)
        if proc.returncode == 0:
            return (total, total)
        # Parse "N passed" from output for partial success.
        passed = _parse_passed(proc.stdout)
        return (passed, total)


def _parse_passed(pytest_stdout: str) -> int:
    import re

    m = re.search(r"(\d+) passed", pytest_stdout)
    return int(m.group(1)) if m else 0
