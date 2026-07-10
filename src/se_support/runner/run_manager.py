"""Run orchestration: execute one (task, agent, condition) run end-to-end.

Sequence (mirrors PROJECT_PROPOSAL.md section 16):
1. create the run directory, persist task.json + run_spec.json,
2. build the agent workspace from the base state,
3. run the agent (it edits the workspace + writes transcript/commands),
4. capture the final diff -> final.patch,
5. evaluate the patch on a clean checkout -> eval_result.json,
6. compute the patch quality card -> quality_card.json.

Everything is written to disk so metrics can be recomputed later without
re-running the agent.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path

from se_support.agents.base import AgentRunner
from se_support.evaluation import evaluate_patch, evaluate_with_docker
from se_support.quality import build_card
from se_support.runner.run_dir import (
    FILE_EVAL,
    FILE_FINAL_PATCH,
    FILE_QUALITY,
    FILE_RUN_SPEC,
    FILE_TASK,
    RunDirectory,
)
from se_support.runner.workspace import Workspace
from se_support.schemas import EvalResult, PatchQualityCard, RunSpec, TaskSpec


@dataclass
class RunOutcome:
    run_id: str
    run_dir: Path
    eval_result: EvalResult
    quality_card: PatchQualityCard


def _load_gold_diff(task: TaskSpec) -> str | None:
    from se_support.config import repo_root

    if not task.gold_patch_path:
        return None
    p = Path(task.gold_patch_path)
    if not p.is_absolute():
        p = repo_root() / p
    return p.read_text(encoding="utf-8") if p.exists() else None


def run_single(
    task: TaskSpec,
    agent: AgentRunner,
    condition: str,
    runs_root: Path,
    experiment_id: str,
    model: str = "mock",
    seed: int = 0,
    run_id: str | None = None,
    evaluator: str = "auto",
    docker_python_exe: str | None = None,
    docker_env: dict | None = None,
    dataset_name: str = "SWE-bench/SWE-bench_Verified",
) -> RunOutcome:
    """Execute one run end-to-end.

    Workspace + evaluator are chosen by ``evaluator`` (``auto`` picks by task):
    * fixture tasks (``local_repo_path`` set) -> copy template + local evaluator.
    * real tasks (``repo`` + ``base_commit``) -> git clone + official Docker eval.
    """
    run_id = run_id or uuid.uuid4().hex[:12]
    rd = RunDirectory.create(runs_root, experiment_id, run_id)

    run_spec = RunSpec(
        run_id=run_id, task_id=task.task_id, agent=getattr(agent, "name", "agent"),
        model=model, condition=condition, seed=seed,
    )
    rd.write_model(FILE_TASK, task)
    rd.write_model(FILE_RUN_SPEC, run_spec)

    mode = _resolve_mode(task, evaluator)

    # Build the agent workspace from the base state.
    if mode == "fixture":
        agent_ws = Workspace.from_template(_template(task), rd.path / "agent_workspace", rd)
    else:
        agent_ws = Workspace.from_git(
            task.repo, task.base_commit, rd.path / "agent_workspace", rd
        )

    agent.run(task, condition, agent_ws, rd)
    final_diff = agent_ws.final_diff()
    rd.write_text(FILE_FINAL_PATCH, final_diff)

    # Evaluate.
    if mode == "fixture":
        eval_result = evaluate_patch(task, final_diff, rd.path / "eval_workspace", rd)
    else:
        eval_result = evaluate_with_docker(
            task, final_diff, rd.path / "docker_eval", run_id=run_id,
            dataset_name=dataset_name, python_exe=docker_python_exe, env=docker_env,
        )
    eval_result.run_id = run_id
    rd.write_model(FILE_EVAL, eval_result)

    # Quality card (offline, from artifacts).
    card = build_card(task, eval_result, final_diff, _load_gold_diff(task))
    rd.write_model(FILE_QUALITY, card)

    return RunOutcome(run_id=run_id, run_dir=rd.path, eval_result=eval_result, quality_card=card)


def _resolve_mode(task: TaskSpec, evaluator: str) -> str:
    if evaluator == "local":
        return "fixture"
    if evaluator == "docker":
        return "real"
    # auto
    return "fixture" if task.local_repo_path else "real"


def _template(task: TaskSpec) -> Path:
    from se_support.config import repo_root

    if not task.local_repo_path:
        raise ValueError("run_single (local mode) requires TaskSpec.local_repo_path")
    p = Path(task.local_repo_path)
    return p if p.is_absolute() else repo_root() / p
