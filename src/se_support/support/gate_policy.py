"""Frozen C3 gate policy (EP-07).

Freezes the deterministic validation gates run when the agent submits under C3/C6
(EXPERIMENT_PLAN_2026-07-21.md §6.4, §14 EP-07):

* a **versioned** gate policy (blocking vs advisory, revision budget);
* **base-vs-patch delta** for advisory gates, so pre-existing (legacy) repository
  warnings are never attributed to the agent's patch;
* a fixed **revision budget** and a stable feedback format;
* the official hidden SWE-bench tests are **never** a gate.

Blocking gates (syntax/build) must pass on the patched tree. Advisory gates
(lint/security) are reported as *new* warnings (patch count minus baseline count)
and do not block by default.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from se_support.config import CONDITION_VERSION

GATE_POLICY_VERSION = f"c3/{CONDITION_VERSION}"


@dataclass(frozen=True)
class GateSpec:
    name: str
    kind: str  # "blocking" | "advisory"
    # A callable name resolved in this module (keeps the policy JSON-serialisable).
    runner: str


@dataclass(frozen=True)
class GatePolicy:
    version: str = GATE_POLICY_VERSION
    revision_budget: int = 3
    gates: tuple[GateSpec, ...] = (
        GateSpec("compileall", "blocking", "compileall"),
        GateSpec("ruff", "advisory", "ruff"),
        GateSpec("bandit", "advisory", "bandit"),
    )

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "revision_budget": self.revision_budget,
            "official_tests_are_gates": False,
            "helper_test_in_gate_sequence": False,
            "gates": [{"name": g.name, "kind": g.kind} for g in self.gates],
        }


# -- individual gate runners: return (passed, warning_count, preview) ---------
def _run(argv: list[str], cwd: Path) -> tuple[int, str]:
    try:
        p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True)
    except FileNotFoundError:
        return 127, "not found"
    return p.returncode, (p.stdout + p.stderr)


# An executor runs an argv list and returns (returncode, combined_output). The
# default runs on the host; a container workspace injects one that execs inside
# the instance image (so C3 gates run where the repo's deps live).
ExecFn = "callable"


def _host_exec(cwd: Path):
    def run(argv: list[str]) -> tuple[int, str]:
        return _run(argv, cwd)
    return run


def _gate_compileall(exec_fn) -> tuple[bool, int, str]:
    code, out = exec_fn(["python", "-m", "compileall", "-q", "."])
    return (code == 0, 0 if code == 0 else 1, out[:500])


def _gate_ruff(exec_fn) -> tuple[bool, int, str]:
    code, out = exec_fn(["ruff", "check", "--output-format=json", "."])
    if "not found" in out.lower() or "no such file" in out.lower():
        return (True, -1, "ruff unavailable")
    try:
        n = len(json.loads(out or "[]"))
    except json.JSONDecodeError:
        n = -1
    return (True, n, out[:500])


def _gate_bandit(exec_fn) -> tuple[bool, int, str]:
    code, out = exec_fn(["bandit", "-q", "-r", "-f", "json", "."])
    if "not found" in out.lower() or "no such file" in out.lower():
        return (True, -1, "bandit unavailable")
    try:
        n = len(json.loads(out or "{}").get("results", []))
    except json.JSONDecodeError:
        n = -1
    return (True, n, "")


_RUNNERS = {
    "compileall": _gate_compileall,
    "ruff": _gate_ruff,
    "bandit": _gate_bandit,
}


# -- C3 v2 (plan P5) ----------------------------------------------------------
# v2 adds a repo-aware gate set: syntax + import gates (blocking), repo-native
# targeted tests for the changed modules (blocking), and lint/type checks that
# run ONLY when the repository actually configures them (no forcing unconfigured
# Ruff/Bandit on every project). The hidden official SWE-bench tests are still
# never a gate. v2 runners receive a small context dict (changed files).

_CONFIG_FILES = ("pyproject.toml", "setup.cfg", "tox.ini", ".flake8",
                 "ruff.toml", ".ruff.toml", "mypy.ini")


def changed_files_from_diff(diff: str) -> list[str]:
    """Extract changed file paths from a unified diff (``+++ b/<path>`` lines)."""
    out: list[str] = []
    for ln in (diff or "").splitlines():
        if ln.startswith("+++ b/"):
            p = ln[6:].strip()
            if p and p != "/dev/null":
                out.append(p)
    return out


def detect_configured_tools(exec_fn) -> set[str]:
    """Which QA tools the repo actually configures (read repo config files)."""
    found: set[str] = set()
    blob = ""
    for f in _CONFIG_FILES:
        code, out = exec_fn(["cat", f])
        if code == 0 and out:
            blob += "\n" + out
            if f in (".flake8",):
                found.add("flake8")
            if f in ("ruff.toml", ".ruff.toml"):
                found.add("ruff")
            if f == "mypy.ini":
                found.add("mypy")
    low = blob.lower()
    for tool in ("ruff", "flake8", "mypy", "black", "isort"):
        if f"[{tool}]" in low or f"tool.{tool}" in low or f"[tool.{tool}]" in low \
                or f"\n{tool}" in low:
            found.add(tool)
    return found


def _changed_test_targets(changed_files: list[str]) -> list[str]:
    """Map changed source files to repo-native test files/dirs (best effort)."""
    targets: set[str] = set()
    for f in changed_files:
        if not f.endswith(".py"):
            continue
        base = f.rsplit("/", 1)[-1]
        stem = base[:-3]
        if base.startswith("test_") or base.endswith("_test.py"):
            targets.add(f)
            continue
        # common test-file naming next to or under tests/
        parts = f.split("/")
        pkg = parts[0] if parts else ""
        targets.add(f"tests/test_{stem}.py")
        if pkg:
            targets.add(f"{pkg}/tests/test_{stem}.py")
    return sorted(targets)


def _gate_import(exec_fn, ctx) -> tuple[bool, int, str]:
    """Blocking: every changed module must import without error."""
    changed = [f for f in ctx.get("changed_files", [])
               if f.endswith(".py") and "test" not in f.rsplit("/", 1)[-1]]
    if not changed:
        return (True, 0, "no changed modules")
    mods = [f[:-3].replace("/", ".") for f in changed]
    expr = "; ".join(f"__import__('{m}')" for m in mods[:20])
    code, out = exec_fn(["python", "-c", expr])
    return (code == 0, 0 if code == 0 else 1, out[:500])


def _gate_targeted_tests(exec_fn, ctx) -> tuple[bool, int, str]:
    """Blocking: repo-native existing tests for the changed modules must pass.

    Only tests that actually exist are run; if none map to the change, the gate
    passes (nothing to check). These are the repo's OWN public tests, never the
    hidden official SWE-bench test_patch.
    """
    targets = _changed_test_targets(ctx.get("changed_files", []))
    existing = []
    for t in targets:
        code, _ = exec_fn(["test", "-f", t])
        if code == 0:
            existing.append(t)
    if not existing:
        return (True, 0, "no repo-native tests map to the change")
    code, out = exec_fn(["python", "-m", "pytest", "-q", "--no-header",
                         "-p", "no:cacheprovider", *existing])
    return (code == 0, 0 if code == 0 else 1, out[-600:])


def _gate_ruff_configured(exec_fn, ctx) -> tuple[bool, int, str]:
    if "ruff" not in ctx.get("configured", set()):
        return (True, -1, "ruff not configured by repo")
    return _gate_ruff(exec_fn)


def _gate_flake8_configured(exec_fn, ctx) -> tuple[bool, int, str]:
    if "flake8" not in ctx.get("configured", set()):
        return (True, -1, "flake8 not configured by repo")
    code, out = exec_fn(["flake8", "--count", "."])
    if "not found" in out.lower():
        return (True, -1, "flake8 unavailable")
    tail = (out.strip().splitlines() or ["0"])[-1]
    try:
        n = int(tail.strip())
    except ValueError:
        n = -1
    return (True, n, out[:400])


def _gate_mypy_configured(exec_fn, ctx) -> tuple[bool, int, str]:
    if "mypy" not in ctx.get("configured", set()):
        return (True, -1, "mypy not configured by repo")
    code, out = exec_fn(["mypy", "."])
    if "not found" in out.lower():
        return (True, -1, "mypy unavailable")
    n = out.lower().count("error:")
    return (True, n, out[-400:])


_RUNNERS_V2 = {
    "compileall": lambda exec_fn, ctx: _gate_compileall(exec_fn),
    "import": _gate_import,
    "targeted_tests": _gate_targeted_tests,
    "ruff": _gate_ruff_configured,
    "flake8": _gate_flake8_configured,
    "mypy": _gate_mypy_configured,
}


def gate_policy_v2() -> GatePolicy:
    """C3 v2 policy: syntax+import+targeted-tests blocking; lint/type advisory
    (only when configured). Selected via ``run_policy(..., version='v2')``."""
    return GatePolicy(
        version=f"c3v2/{CONDITION_VERSION}",
        revision_budget=3,
        gates=(
            GateSpec("compileall", "blocking", "compileall"),
            GateSpec("import", "blocking", "import"),
            GateSpec("targeted_tests", "blocking", "targeted_tests"),
            GateSpec("ruff", "advisory", "ruff"),
            GateSpec("flake8", "advisory", "flake8"),
            GateSpec("mypy", "advisory", "mypy"),
        ),
    )


def compute_baseline_v2(
    workspace_path: Path, policy: GatePolicy | None = None, exec_fn=None,
    ctx: dict | None = None
) -> dict[str, int]:
    """Advisory baseline for a v2 policy (call on the BASE tree, before edits)."""
    policy = policy or gate_policy_v2()
    exec_fn = exec_fn or _host_exec(Path(workspace_path))
    ctx = dict(ctx or {})
    ctx.setdefault("configured", detect_configured_tools(exec_fn))
    ctx.setdefault("changed_files", [])
    baseline: dict[str, int] = {}
    for g in policy.gates:
        if g.kind == "advisory":
            _, count, _ = _RUNNERS_V2[g.runner](exec_fn, ctx)
            baseline[g.name] = count
    return baseline


def run_policy_v2(
    workspace_path: Path,
    changed_files: list[str],
    baseline: dict[str, int] | None = None,
    policy: GatePolicy | None = None,
    exec_fn=None,
) -> list[GateResult]:
    """Run the C3 v2 gate policy on the patched tree (repo-aware, targeted)."""
    policy = policy or gate_policy_v2()
    baseline = baseline or {}
    exec_fn = exec_fn or _host_exec(Path(workspace_path))
    ctx = {"changed_files": changed_files or [],
           "configured": detect_configured_tools(exec_fn)}
    results: list[GateResult] = []
    for g in policy.gates:
        passed, count, preview = _RUNNERS_V2[g.runner](exec_fn, ctx)
        if g.kind == "blocking":
            results.append(GateResult(
                g.name, g.kind, passed, count, None,
                "pass" if passed else "fail", preview,
            ))
        else:
            base = baseline.get(g.name, 0)
            new = None if count < 0 else max(0, count - max(0, base))
            results.append(GateResult(
                g.name, g.kind, True, count, new, "advisory", preview,
            ))
    return results


@dataclass
class GateResult:
    name: str
    kind: str
    passed: bool
    warning_count: int  # -1 = unavailable
    new_warnings: int | None  # advisory only: patch - baseline; None otherwise
    status: str  # "pass" | "fail" | "advisory"
    preview: str = ""

    def to_dict(self) -> dict:
        return {
            "gate_name": self.name, "kind": self.kind, "passed": self.passed,
            "warning_count": self.warning_count, "new_warnings": self.new_warnings,
            "status": self.status, "output_preview": self.preview,
        }


def compute_baseline(
    workspace_path: Path, policy: GatePolicy | None = None, exec_fn=None
) -> dict[str, int]:
    """Advisory warning counts on the BASE tree (call before the agent edits)."""
    policy = policy or GatePolicy()
    exec_fn = exec_fn or _host_exec(Path(workspace_path))
    baseline: dict[str, int] = {}
    for g in policy.gates:
        if g.kind == "advisory":
            _, count, _ = _RUNNERS[g.runner](exec_fn)
            baseline[g.name] = count
    return baseline


def run_policy(
    workspace_path: Path,
    baseline: dict[str, int] | None = None,
    policy: GatePolicy | None = None,
    exec_fn=None,
) -> list[GateResult]:
    """Run the gate policy on the patched tree; advisory gates report delta."""
    policy = policy or GatePolicy()
    baseline = baseline or {}
    exec_fn = exec_fn or _host_exec(Path(workspace_path))
    results: list[GateResult] = []
    for g in policy.gates:
        passed, count, preview = _RUNNERS[g.runner](exec_fn)
        if g.kind == "blocking":
            results.append(GateResult(
                g.name, g.kind, passed, count, None,
                "pass" if passed else "fail", preview,
            ))
        else:
            base = baseline.get(g.name, 0)
            new = None if count < 0 else max(0, count - max(0, base))
            results.append(GateResult(
                g.name, g.kind, True, count, new, "advisory", preview,
            ))
    return results


def blocking_failures(results: list[GateResult]) -> list[GateResult]:
    return [r for r in results if r.kind == "blocking" and not r.passed]


def format_feedback(failures: list[GateResult]) -> str:
    lines = ["Blocking gate(s) failed; fix before submitting:"]
    for f in failures:
        lines.append(f"- {f.name}: {f.preview[:300]}")
    return "\n".join(lines)
