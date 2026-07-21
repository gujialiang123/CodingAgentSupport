"""Pre-run C2 helper generation in the isolated generator zone (A1, plan §6.1).

For a task under C2/C6, this builds base + gold workspaces, derives the forbidden
official-literal set from the official ``test_patch`` (used only to *reject* leaks,
never shown to the generator), then runs the blind K-candidate pipeline and returns
a frozen, classified :class:`HelperTestArtifact`.

Environment note: fail-before/pass-after validation needs the task's runtime deps.
A bare git checkout may lack them, in which case candidates classify as T0/invalid
(recorded honestly); full validation for real repos runs inside the task's Docker
image (future wiring). The generation + provenance/leakage audit + freezing always
work offline.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from se_support.schemas import TaskSpec
from se_support.support.context_pack import build_context_pack
from se_support.support.repro_tests import build_helper_test
from se_support.support.repro_tests.schema import HelperTestArtifact

_STRING_LIT_RE = re.compile(r"""(['"])(.{20,}?)\1""")


def forbidden_literals_from_test_patch(test_patch_path: str | None) -> list[str]:
    """Long string literals added by the official test patch (leak-detection set)."""
    if not test_patch_path:
        return []
    p = Path(test_patch_path)
    if not p.exists():
        return []
    lits: list[str] = []
    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.startswith("+"):
            for _q, body in _STRING_LIT_RE.findall(line):
                lits.append(body)
    return lits


def _build_base_ws(task: TaskSpec, dest: Path) -> Path:
    from se_support.config import repo_root
    from se_support.runner.workspace import Workspace

    if task.local_repo_path:
        src = Path(task.local_repo_path)
        if not src.is_absolute():
            src = repo_root() / src
        Workspace.from_template(src, dest)
    else:
        Workspace.from_git(task.repo, task.base_commit, dest)
    return dest


def _apply_gold(base_dest: Path, gold_dest: Path, task: TaskSpec) -> Path | None:
    from se_support.config import repo_root

    if not task.gold_patch_path:
        return None
    gp = Path(task.gold_patch_path)
    if not gp.is_absolute():
        gp = repo_root() / gp
    if not gp.exists():
        return None
    if gold_dest.exists():
        shutil.rmtree(gold_dest)
    shutil.copytree(base_dest, gold_dest)
    proc = subprocess.run(["git", "apply", str(gp)], cwd=gold_dest,
                          capture_output=True, text=True)
    return gold_dest if proc.returncode == 0 else None


def generate_helper_for_task(
    task: TaskSpec,
    client,
    workdir: Path,
    k: int = 3,
    generator_model: str | None = None,
) -> HelperTestArtifact:
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    base = _build_base_ws(task, workdir / "gen_base")
    gold = _apply_gold(base, workdir / "gen_gold", task)

    repo_context = build_context_pack(task, base)
    forbidden = forbidden_literals_from_test_patch(task.test_patch_path)

    problem = task.issue_body or task.issue_title
    return build_helper_test(
        task_id=task.task_id, problem_statement=problem, repo_context=repo_context,
        client=client, base_workspace=base, gold_workspace=gold,
        forbidden_literals=forbidden, generator_model=generator_model, k=k,
    )
