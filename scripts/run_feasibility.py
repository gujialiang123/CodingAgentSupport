"""Feasibility experiment driver (E1-style, 7B) via the EP-09 scheduler.

Runs the fully-integrated confirmatory pipeline (isolation + frozen bundles +
C2 generation + harness + gates + Docker eval) on a small real SWE-bench cohort
across conditions, using a local vLLM model. Not a research result -- a
feasibility check that every construct runs end-to-end together.

Usage:
    python -m scripts.run_feasibility --tasks data/tasks/pilot_requests.jsonl \
      --conditions C0_minimal C2_tests C4_harness C6_full_stack \
      --model Qwen/Qwen2.5-Coder-7B-Instruct --base-url http://localhost:8000/v1 \
      --experiment-id feasib01 --max-turns 20
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from se_support.agents import LLMAgent, OpenAIChatClient
from se_support.datasets import load_tasks
from se_support.experiment import run_experiment
from se_support.isolation import SandboxPolicy


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", required=True)
    ap.add_argument("--conditions", nargs="+",
                    default=["C0_minimal", "C2_tests", "C4_harness", "C6_full_stack"])
    ap.add_argument("--model", default="Qwen/Qwen2.5-Coder-7B-Instruct")
    ap.add_argument("--base-url", default="http://localhost:8000/v1")
    ap.add_argument("--api-key", default="EMPTY")
    ap.add_argument("--experiment-id", default="feasib")
    ap.add_argument("--max-turns", type=int, default=20)
    ap.add_argument("--seeds", type=int, nargs="+", default=[0])
    ap.add_argument("--output", default="runs")
    ap.add_argument("--results", default=None)
    ap.add_argument("--no-sandbox", action="store_true")
    ap.add_argument("--in-container", action="store_true",
                    help="Run the agent inside the SWE-bench instance image (P1).")
    ap.add_argument("--max-tokens", type=int, default=1024,
                    help="Completion token budget per turn (raise for reasoning models).")
    ap.add_argument("--max-workers", type=int, default=1,
                    help="Concurrent cells (safe for API models; each cell isolated).")
    ap.add_argument("--swebench-python", default="/home/jgu7/miniconda3/envs/swebench/bin/python")
    ap.add_argument("--dataset-name", default="SWE-bench/SWE-bench_Verified")
    ap.add_argument("--helper-cache-dir", default=None,
                    help="Dir of pre-frozen container-validated C2 helpers "
                         "(<task_id>.json); reused read-only for C2/C2+C3 (P4).")
    args = ap.parse_args()

    tasks = load_tasks(Path(args.tasks))
    docker_env = {"DOCKER_HOST": f"unix:///run/user/{os.getuid()}/docker.sock"}

    def make_client():
        return OpenAIChatClient(model=args.model, base_url=args.base_url,
                                api_key=args.api_key, max_tokens=args.max_tokens)

    def agent_factory():
        return LLMAgent(make_client(), max_turns=args.max_turns)

    # In container mode the container provides isolation (--network none); the
    # host bwrap sandbox is not applied to container exec.
    sandbox = None if (args.no_sandbox or args.in_container) else SandboxPolicy.confirmatory()

    run_experiment(
        experiment_id=args.experiment_id, tasks=tasks, conditions=args.conditions,
        agent_factory=agent_factory, seeds=args.seeds, runs_root=Path(args.output),
        model=args.model, evaluator="docker", sandbox_policy=sandbox,
        generator_client=make_client(),  # C2 helper generation
        docker_python_exe=args.swebench_python, docker_env=docker_env,
        dataset_name=args.dataset_name,
        results_path=Path(args.results) if args.results else None,
        max_workers=args.max_workers, in_container=args.in_container,
        helper_cache_dir=Path(args.helper_cache_dir) if args.helper_cache_dir else None,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
