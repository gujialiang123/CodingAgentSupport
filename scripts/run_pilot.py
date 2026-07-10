"""Run a C0 vs C6 pilot on real SWE-bench tasks and report a results table.

For each task in a TaskSpec JSONL, runs the controllable LLM agent under each
condition, evaluates via the official SWE-bench Docker harness, and prints a
per-condition summary. Intended for small pilots (a handful of tasks).

Usage:
    python -m scripts.run_pilot --tasks data/tasks/pilot.jsonl \
        --model Qwen/Qwen2.5-Coder-7B-Instruct --base-url http://localhost:8000/v1 \
        --experiment-id pilot01 --conditions C0_minimal C6_full_stack --max-turns 30
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from se_support.agents import LLMAgent, OpenAIChatClient
from se_support.datasets import load_tasks
from se_support.runner.run_manager import run_single


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", required=True)
    ap.add_argument("--model", default="Qwen/Qwen2.5-Coder-7B-Instruct")
    ap.add_argument("--base-url", default="http://localhost:8000/v1")
    ap.add_argument("--api-key", default="EMPTY")
    ap.add_argument("--experiment-id", default="pilot")
    ap.add_argument("--conditions", nargs="+", default=["C0_minimal", "C6_full_stack"])
    ap.add_argument("--max-turns", type=int, default=30)
    ap.add_argument("--output", default="runs")
    ap.add_argument("--results", default=None, help="Path to write results JSONL.")
    ap.add_argument("--swebench-python", default="/home/jgu7/miniconda3/envs/swebench/bin/python")
    ap.add_argument("--dataset-name", default="SWE-bench/SWE-bench_Verified")
    args = ap.parse_args()

    tasks = load_tasks(Path(args.tasks))
    docker_env = {"DOCKER_HOST": f"unix:///run/user/{os.getuid()}/docker.sock"}
    rows: list[dict] = []

    for task in tasks:
        for cond in args.conditions:
            client = OpenAIChatClient(
                model=args.model, base_url=args.base_url, api_key=args.api_key
            )
            agent = LLMAgent(client, max_turns=args.max_turns)
            print(f"\n=== {task.task_id} | {cond} ===", flush=True)
            try:
                outcome = run_single(
                    task=task, agent=agent, condition=cond,
                    runs_root=Path(args.output), experiment_id=args.experiment_id,
                    model=args.model, evaluator="docker",
                    docker_python_exe=args.swebench_python, docker_env=docker_env,
                    dataset_name=args.dataset_name,
                )
                ev = outcome.eval_result
                row = {
                    "task_id": task.task_id, "condition": cond,
                    "resolved": ev.resolved, "patch_applies": ev.patch_applies,
                    "f2p": f"{ev.fail_to_pass_passed}/{ev.fail_to_pass_total}",
                    "p2p": f"{ev.pass_to_pass_passed}/{ev.pass_to_pass_total}",
                    "quality": str(outcome.quality_card.quality_level),
                    "files_touched": outcome.quality_card.locality.files_touched,
                    "run_dir": str(outcome.run_dir),
                }
            except Exception as exc:  # noqa: BLE001 - keep going, record failure
                row = {"task_id": task.task_id, "condition": cond,
                       "resolved": None, "error": repr(exc)}
            print(json.dumps(row), flush=True)
            rows.append(row)

    # Summary.
    print("\n===== PILOT SUMMARY =====")
    for cond in args.conditions:
        crows = [r for r in rows if r["condition"] == cond]
        resolved = sum(1 for r in crows if r.get("resolved"))
        errored = sum(1 for r in crows if r.get("error"))
        print(f"{cond}: resolved {resolved}/{len(crows)} (errors={errored})")

    if args.results:
        Path(args.results).parent.mkdir(parents=True, exist_ok=True)
        with open(args.results, "w") as fh:
            for r in rows:
                fh.write(json.dumps(r) + "\n")
        print(f"\nresults -> {args.results}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
