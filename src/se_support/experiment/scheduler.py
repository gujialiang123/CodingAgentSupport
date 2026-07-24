"""Experiment scheduler (EP-09 / A3).

Drives a confirmatory experiment: tasks × conditions × seeds, in **randomized**
order (so model/service drift is not confounded with condition), **resumable**
(completed runs are skipped by a deterministic run id + completion marker), with
**infrastructure-only retries**. Sandbox isolation is **on by default**.

Each cell is one call to :func:`se_support.runner.run_manager.run_single`.
"""

from __future__ import annotations

import hashlib
import json
import random
import traceback
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from se_support.isolation import SandboxPolicy
from se_support.runner.run_manager import run_single
from se_support.schemas import TaskSpec


@dataclass
class Cell:
    task: TaskSpec
    condition: str
    seed: int

    @property
    def key(self) -> str:
        return f"{self.task.task_id}__{self.condition}__seed{self.seed}"

    @property
    def run_id(self) -> str:
        return hashlib.sha256(self.key.encode()).hexdigest()[:12]


def build_schedule(
    tasks: list[TaskSpec], conditions: list[str], seeds: list[int], rng_seed: int = 0
) -> list[Cell]:
    cells = [Cell(t, c, s) for t in tasks for c in conditions for s in seeds]
    random.Random(rng_seed).shuffle(cells)
    return cells


def _is_complete(run_dir: Path) -> bool:
    return (run_dir / "quality_card.json").exists()


def run_experiment(
    experiment_id: str,
    tasks: list[TaskSpec],
    conditions: list[str],
    agent_factory: Callable[[], object],
    *,
    seeds: list[int] | None = None,
    runs_root: Path = Path("runs"),
    model: str = "unknown",
    evaluator: str = "auto",
    sandbox_policy: SandboxPolicy | None = "default",
    generator_client=None,
    docker_python_exe: str | None = None,
    docker_env: dict | None = None,
    dataset_name: str = "SWE-bench/SWE-bench_Verified",
    rng_seed: int = 0,
    max_infra_retries: int = 1,
    resume: bool = True,
    results_path: Path | None = None,
    progress: bool = True,
    max_workers: int = 1,
    in_container: bool = False,
    helper_cache_dir: Path | None = None,
    memory_cache_dir: Path | None = None,
) -> list[dict]:
    """Run the full schedule and return per-cell result rows.

    ``sandbox_policy="default"`` uses the strict confirmatory policy; pass an
    explicit :class:`SandboxPolicy` or ``None`` (no sandbox) to override.
    ``agent_factory`` must build a fresh agent per run (agents hold per-run state).
    ``max_workers`` > 1 runs cells concurrently (safe: each cell has its own run
    dir + run_id; use for API models where there is no local GPU bottleneck).
    """
    if sandbox_policy == "default":
        sandbox_policy = SandboxPolicy.confirmatory()
    seeds = seeds or [0]
    runs_root = Path(runs_root)
    schedule = build_schedule(tasks, conditions, seeds, rng_seed)
    n = len(schedule)

    def _execute(cell: Cell) -> dict:
        run_dir = runs_root / experiment_id / cell.run_id
        if resume and _is_complete(run_dir):
            return _row_from_dir(cell, run_dir, skipped=True)
        for attempt in range(max_infra_retries + 1):
            try:
                agent = agent_factory()
                outcome = run_single(
                    task=cell.task, agent=agent, condition=cell.condition,
                    runs_root=runs_root, experiment_id=experiment_id,
                    model=model, seed=cell.seed, run_id=cell.run_id,
                    evaluator=evaluator, sandbox_policy=sandbox_policy,
                    generator_client=generator_client,
                    docker_python_exe=docker_python_exe, docker_env=docker_env,
                    dataset_name=dataset_name, in_container=in_container,
                    helper_cache_dir=helper_cache_dir,
                    memory_cache_dir=memory_cache_dir,
                )
                return _row_from_outcome(cell, outcome)
            except Exception as exc:  # noqa: BLE001 - infra retry / record
                if attempt < max_infra_retries:
                    continue
                return {"key": cell.key, "task_id": cell.task.task_id,
                        "condition": cell.condition, "seed": cell.seed,
                        "resolved": None, "error": f"{exc!r}\n{traceback.format_exc()[-800:]}"}

    rows: list[dict] = []
    if max_workers <= 1:
        for i, cell in enumerate(schedule, 1):
            if progress:
                print(f"[{i}/{n}] {cell.key}", flush=True)
            row = _execute(cell)
            rows.append(row)
            if progress:
                print("    " + json.dumps({k: row.get(k) for k in
                      ("resolved", "quality", "error")}), flush=True)
    else:
        from concurrent.futures import ThreadPoolExecutor, as_completed

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(_execute, cell): cell for cell in schedule}
            done = 0
            for fut in as_completed(futures):
                done += 1
                row = fut.result()
                rows.append(row)
                if progress:
                    print(f"[{done}/{n}] {row.get('key')} -> " + json.dumps(
                        {k: row.get(k) for k in ("resolved", "quality", "error")}),
                        flush=True)

    if results_path:
        results_path = Path(results_path)
        results_path.parent.mkdir(parents=True, exist_ok=True)
        with results_path.open("w") as fh:
            for r in rows:
                fh.write(json.dumps(r) + "\n")

    _print_summary(rows, conditions)
    return rows


def _row_from_outcome(cell: Cell, outcome) -> dict:
    ev = outcome.eval_result
    return {
        "key": cell.key, "task_id": cell.task.task_id, "condition": cell.condition,
        "seed": cell.seed, "resolved": ev.resolved, "patch_applies": ev.patch_applies,
        "f2p": f"{ev.fail_to_pass_passed}/{ev.fail_to_pass_total}",
        "p2p": f"{ev.pass_to_pass_passed}/{ev.pass_to_pass_total}",
        "quality": str(outcome.quality_card.quality_level),
        "files_touched": outcome.quality_card.locality.files_touched,
        "status": getattr(outcome, "status", "ok"),
        "run_dir": str(outcome.run_dir), "error": None,
    }


def _row_from_dir(cell: Cell, run_dir: Path, skipped: bool = False) -> dict:
    try:
        card = json.loads((run_dir / "quality_card.json").read_text())
        ev = json.loads((run_dir / "eval_result.json").read_text())
        return {
            "key": cell.key, "task_id": cell.task.task_id, "condition": cell.condition,
            "seed": cell.seed, "resolved": ev.get("resolved"),
            "quality": card.get("quality_level"), "run_dir": str(run_dir),
            "skipped": skipped, "error": None,
        }
    except Exception as exc:  # noqa: BLE001
        return {"key": cell.key, "condition": cell.condition, "resolved": None,
                "error": f"reload failed: {exc!r}"}


def _print_summary(rows: list[dict], conditions: list[str]) -> None:
    print("\n===== EXPERIMENT SUMMARY =====")
    for c in conditions:
        crows = [r for r in rows if r.get("condition") == c]
        resolved = sum(1 for r in crows if r.get("resolved"))
        errors = sum(1 for r in crows if r.get("error"))
        print(f"{c}: resolved {resolved}/{len(crows)} (errors={errors})")
