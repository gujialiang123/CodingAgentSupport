"""Local evaluator (offline analogue of the SWE-bench official eval).

Given a task and the agent's final patch, it:
1. builds a *clean* workspace from the base state,
2. applies the patch,
3. checks build (``compileall``),
4. runs FAIL_TO_PASS and PASS_TO_PASS pytest node ids,
5. returns an :class:`EvalResult`.

Real SWE-bench evaluation (Docker) will replace this via the same EvalResult
contract; the local path lets the whole pipeline run with no external assets.
"""

from __future__ import annotations

from pathlib import Path

from se_support.config import repo_root
from se_support.runner.run_dir import RunDirectory
from se_support.runner.workspace import Workspace
from se_support.schemas import EvalResult, TaskSpec


def evaluate_patch(
    task: TaskSpec,
    final_diff: str,
    eval_workspace_dir: Path,
    run_dir: RunDirectory | None = None,
) -> EvalResult:
    if not task.local_repo_path:
        raise ValueError(
            "local evaluator requires TaskSpec.local_repo_path; "
            "Docker/official eval is a later ticket."
        )
    template = Path(task.local_repo_path)
    if not template.is_absolute():
        template = repo_root() / template

    ws = Workspace.from_template(template, eval_workspace_dir, run_dir)

    patch_applies = ws.apply_patch(final_diff, check=False)

    # Build check: compile all python files.
    build_ok = ws._run(
        "python", "-m", "compileall", "-q", ".", check=False
    ).returncode == 0

    f2p_passed = f2p_total = p2p_passed = p2p_total = 0
    if patch_applies:
        f2p_passed, f2p_total = ws.run_pytest(task.fail_to_pass_tests)
        p2p_passed, p2p_total = ws.run_pytest(task.pass_to_pass_tests)

    resolved = (
        patch_applies
        and build_ok
        and f2p_total > 0
        and f2p_passed == f2p_total
        and p2p_passed == p2p_total
    )

    full_status = None
    if patch_applies:
        full_status = "pass" if resolved else ("partial" if f2p_passed else "fail")

    return EvalResult(
        run_id=run_dir.path.name if run_dir else task.task_id,
        patch_applies=patch_applies,
        build_success=build_ok,
        fail_to_pass_passed=f2p_passed,
        fail_to_pass_total=f2p_total,
        pass_to_pass_passed=p2p_passed,
        pass_to_pass_total=p2p_total,
        resolved=resolved,
        full_tests_status=full_status,
    )
