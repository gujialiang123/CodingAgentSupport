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
def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(argv, cwd=cwd, capture_output=True, text=True)


def _gate_compileall(cwd: Path) -> tuple[bool, int, str]:
    p = _run(["python", "-m", "compileall", "-q", "."], cwd)
    return (p.returncode == 0, 0 if p.returncode == 0 else 1, (p.stdout + p.stderr)[:500])


def _gate_ruff(cwd: Path) -> tuple[bool, int, str]:
    import shutil

    if not shutil.which("ruff"):
        return (True, -1, "ruff unavailable")
    p = _run(["ruff", "check", "--output-format=json", "."], cwd)
    try:
        n = len(json.loads(p.stdout or "[]"))
    except json.JSONDecodeError:
        n = -1
    return (True, n, (p.stdout or p.stderr)[:500])


def _gate_bandit(cwd: Path) -> tuple[bool, int, str]:
    import shutil

    if not shutil.which("bandit"):
        return (True, -1, "bandit unavailable")
    p = _run(["bandit", "-q", "-r", "-f", "json", "."], cwd)
    try:
        n = len(json.loads(p.stdout or "{}").get("results", []))
    except json.JSONDecodeError:
        n = -1
    return (True, n, "")


_RUNNERS = {
    "compileall": _gate_compileall,
    "ruff": _gate_ruff,
    "bandit": _gate_bandit,
}


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


def compute_baseline(workspace_path: Path, policy: GatePolicy | None = None) -> dict[str, int]:
    """Advisory warning counts on the BASE tree (call before the agent edits)."""
    policy = policy or GatePolicy()
    baseline: dict[str, int] = {}
    for g in policy.gates:
        if g.kind == "advisory":
            _, count, _ = _RUNNERS[g.runner](Path(workspace_path))
            baseline[g.name] = count
    return baseline


def run_policy(
    workspace_path: Path,
    baseline: dict[str, int] | None = None,
    policy: GatePolicy | None = None,
) -> list[GateResult]:
    """Run the gate policy on the patched tree; advisory gates report delta."""
    policy = policy or GatePolicy()
    baseline = baseline or {}
    results: list[GateResult] = []
    for g in policy.gates:
        passed, count, preview = _RUNNERS[g.runner](Path(workspace_path))
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
