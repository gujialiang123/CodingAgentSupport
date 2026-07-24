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
# Read-only support mount: experiment inputs (e.g. C2 helper) the agent may read
# but must never mutate, and which never enters the repo git tree / final patch.
_SUPPORT_REL = ".se_support"
_SUPPORT_DIR = f"{TESTBED}/{_SUPPORT_REL}"
HELPER_MOUNT_PATH = f"{_SUPPORT_DIR}/helper_test.py"
# Legacy in-tree helper path (pre-integrity-fix); kept only for historical
# patch parsing / auditing. NEVER written for new runs.
LEGACY_HELPER_PATH = f"{TESTBED}/se_support_helper_test.py"
# Narrow allowlist of ephemeral paths that never count as an agent change and are
# excluded from the final patch.
_EPHEMERAL_GLOBS = (
    "**/__pycache__/**", "**/*.pyc", "**/.pytest_cache/**", "**/.mypy_cache/**",
    "**/.ruff_cache/**", "**/.coverage", "**/htmlcov/**", f"{_SUPPORT_REL}/**",
    "se_support_helper_test.py",
)
PATCH_EXTRACTOR_VERSION = "2"


def classify_git_state(porcelain: str, head: str = "", baseline_untracked=None,
                       strict_untracked: bool = True) -> dict:
    """Pure classifier for ``git status --porcelain=v1 -uall`` output.

    Modified/deleted TRACKED files are always suspicious; untracked files are
    benign at S0 (recorded as baseline) and only flagged at S1+ when they appear
    beyond the baseline. Extracted as a pure function so it is unit-testable
    without a container.
    """
    import hashlib

    tracked, untracked = [], []
    for ln in porcelain.splitlines():
        if not ln.strip():
            continue
        code, path = ln[:2], ln[3:].strip()
        (untracked if code == "??" else tracked).append(path)
    allow = (f"{_SUPPORT_REL}/", "se_support_helper_test.py")
    eph = ("__pycache__", ".pyc", ".pytest_cache", ".mypy_cache",
           ".ruff_cache", ".coverage", "htmlcov")

    def _allowed(p: str) -> bool:
        return p.startswith(allow) or any(e in p for e in eph)

    baseline = set(baseline_untracked or [])
    bad_tracked = [p for p in tracked if not _allowed(p)]
    bad_untracked = ([p for p in untracked if not _allowed(p) and p not in baseline]
                     if strict_untracked else [])
    unexplained = bad_tracked + bad_untracked
    return {
        "head": head,
        "porcelain_sha256": hashlib.sha256(porcelain.encode()).hexdigest(),
        "tracked_changes": tracked,
        "untracked_files": untracked,
        "base_untracked": sorted(baseline),
        "unexplained_changes": unexplained,
        "clean": not unexplained,
    }


def build_patch_manifest(patch: str, included_paths: list[str], globs: list[str]) -> dict:
    """Pure builder for the patch manifest incl. the helper-leak assertion."""
    import hashlib

    return {
        "extractor_version": PATCH_EXTRACTOR_VERSION,
        "included_paths": included_paths,
        "excluded_globs": globs,
        "patch_sha256": hashlib.sha256(patch.encode()).hexdigest(),
        "helper_leak": any(
            p == "se_support_helper_test.py" or p.startswith(f"{_SUPPORT_REL}/")
            for p in included_paths
        ),
    }


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


def _shell_grep_terms(terms: list[str]) -> list[str]:
    """Sanitize + single-quote query terms for a ``git grep -F`` invocation."""
    out: list[str] = []
    seen: set[str] = set()
    for t in terms:
        t = "".join(c for c in t if c.isalnum() or c in "_.-")
        if len(t) < 3 or t.lower() in seen:
            continue
        seen.add(t.lower())
        out.append(f"'{t}'")
    return out[:12]


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
        support_mount: Path | str | None = None,
    ) -> ContainerWorkspace:
        e = docker_host_env(env)
        image = instance_image_name(instance_id, namespace)
        argv = ["docker", "run", "-d", "--network", "none"]
        if support_mount is not None:
            # Read-only bind mount: the frozen support artifacts (e.g. the C2
            # helper) are experiment INPUT the agent may read but cannot mutate,
            # and which never enters the repo git tree / final patch.
            src = Path(support_mount).resolve()
            argv += ["--mount", f"type=bind,src={src},dst={_SUPPORT_DIR},readonly"]
        argv += [image, "sleep", str(idle_timeout)]
        proc = subprocess.run(argv, capture_output=True, text=True, env=e)
        if proc.returncode != 0:
            raise RuntimeError(f"failed to start container for {instance_id}: {proc.stderr}")
        cid = proc.stdout.strip()
        ws = cls(cid, run_dir, e)
        if support_mount is not None:
            # Keep the mount point out of git entirely (defense in depth alongside
            # the filtered patch extractor).
            ws._testbed(f"grep -qxF '{_SUPPORT_REL}/' .git/info/exclude 2>/dev/null || "
                        f"echo '{_SUPPORT_REL}/' >> .git/info/exclude; true")
        return ws

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

    def final_diff(self, extra_excludes=None) -> str:
        """Safe patch extraction (integrity fix).

        Builds the diff in a **temporary git index** (``GIT_INDEX_FILE``) seeded
        from HEAD so the repo's real index is never mutated, and excludes the
        read-only support mount, the legacy helper file, ephemeral caches, and any
        pre-existing base-image untracked paths (``extra_excludes``). The returned
        patch contains only the agent's real repository edits.
        """
        patch, _ = self.final_diff_with_manifest(extra_excludes=extra_excludes)
        return patch

    def final_diff_with_manifest(self, extra_excludes=None) -> tuple[str, dict]:
        """Return ``(patch, manifest)``; manifest records included/excluded paths."""
        globs = list(_EPHEMERAL_GLOBS) + [f"{p}" for p in (extra_excludes or [])]
        excludes = " ".join(f"':(exclude){g}'" for g in globs)
        # Use an isolated temp index so we never touch the real .git/index.
        script = (
            "export GIT_INDEX_FILE=/tmp/.se_final_index; rm -f $GIT_INDEX_FILE; "
            "git read-tree HEAD; "
            f"git add -A -- . {excludes} 2>/dev/null; "
            "git diff --cached --binary HEAD; "
            "rm -f $GIT_INDEX_FILE"
        )
        proc = self._testbed(script)
        patch = proc.stdout
        # Manifest: which paths the temp index actually staged (name-only).
        name_script = (
            "export GIT_INDEX_FILE=/tmp/.se_names_index; rm -f $GIT_INDEX_FILE; "
            "git read-tree HEAD; "
            f"git add -A -- . {excludes} 2>/dev/null; "
            "git diff --cached --name-status HEAD; "
            "rm -f $GIT_INDEX_FILE"
        )
        names = self._testbed(name_script).stdout
        included = [ln.split("\t", 1)[-1].strip()
                    for ln in names.splitlines() if ln.strip()]
        manifest = build_patch_manifest(patch, included, globs)
        return patch, manifest

    # -- integrity: git-state snapshots + helper hashing ----------------------
    def git_state(self, baseline_untracked=None, strict_untracked: bool = True) -> dict:
        """Structured snapshot of the repo working-tree state (integrity check).

        Distinguishes two kinds of dirt:
        * **modified/deleted TRACKED** files -> always suspicious (image tampering
          or support/setup mutation of real source);
        * **untracked** files -> at container start (S0) these are benign base-image
          artifacts (e.g. a shipped ``build/lib/`` tree). They are recorded as the
          baseline and excluded from the agent patch. New untracked files that
          appear *after* S0 (``strict_untracked=True`` with a baseline) mean our
          own setup created files and ARE flagged.
        """
        porcelain = self._testbed("git status --porcelain=v1 -uall").stdout
        head = self._testbed("git rev-parse HEAD 2>/dev/null").stdout.strip()
        return classify_git_state(porcelain, head, baseline_untracked, strict_untracked)

    def helper_sha256(self) -> str | None:
        """SHA-256 of the mounted helper as seen inside the container (or None)."""
        proc = self._exec(f"sha256sum {HELPER_MOUNT_PATH} 2>/dev/null | cut -d' ' -f1")
        out = proc.stdout.strip()
        return out or None

    # -- C2 helper injection --------------------------------------------------
    def inject_file(self, container_path: str, content: str) -> None:
        """Write ``content`` to ``container_path`` inside the container.

        Deprecated for the C2 helper (now delivered via a read-only mount); kept
        for other uses. Never use this to place the helper in the git tree.
        """
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

    def read_file(self, relpath: str, max_bytes: int = 20000) -> str:
        """Read a repo file's text (C1 v2 retrieval). Empty string on error."""
        safe = relpath.replace("'", "")
        proc = self._testbed(f"head -c {max_bytes} '{safe}' 2>/dev/null")
        return proc.stdout if proc.returncode == 0 else ""

    def grep_files(self, terms: list[str], max_files: int = 40) -> list[str]:
        """Repo files containing any of ``terms`` (fixed-string, case-insensitive).

        One ``git grep`` call inside the container -> cheap. Returns relative paths.
        """
        pats = " ".join(f"-e {t}" for t in _shell_grep_terms(terms))
        if not pats:
            return []
        proc = self._testbed(
            f"git grep -l -I -F -i {pats} 2>/dev/null | head -n {max_files}"
        )
        return [x for x in proc.stdout.splitlines() if x.strip()]

