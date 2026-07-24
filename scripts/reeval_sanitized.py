"""Re-evaluate sanitized patches for contaminated runs (P6 reprocessing).

Some historical runs failed to apply purely because the contaminated patch tried
to (re)add pre-existing base-image files (e.g. psf/requests ``build/lib/``), so
the agent's real edit was never scored. This script sanitizes each selected run's
patch and re-runs the OFFICIAL SWE-bench Docker evaluator, writing a derived
(sanitized) result WITHOUT touching the raw run.

Selection: by default only re-evaluates runs whose raw ``patch_applies`` is False
AND whose patch was contaminated (that is where the outcome can change).

Usage:
  python scripts/reeval_sanitized.py --runs-root runs --experiment exp010_c2xc3 \
      --out results/exp010_c2xc3_reeval.jsonl \
      --swebench-python /home/jgu7/miniconda3/envs/swebench/bin/python
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from audit_support_contamination import sanitize_patch  # noqa: E402  (same dir)

from se_support.datasets import load_tasks
from se_support.evaluation import evaluate_with_docker
from se_support.schemas import TaskSpec


def _task_index(task_files: list[str]) -> dict[str, TaskSpec]:
    idx: dict[str, TaskSpec] = {}
    for tf in task_files:
        for t in load_tasks(Path(tf)):
            idx[t.task_id] = t
    return idx


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-root", default="runs")
    ap.add_argument("--experiment", required=True)
    ap.add_argument("--tasks", nargs="+",
                    default=["data/tasks/ablation_t34.jsonl", "data/tasks/ablation12.jsonl"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--swebench-python",
                    default="/home/jgu7/miniconda3/envs/swebench/bin/python")
    ap.add_argument("--only-nonapplying", action="store_true", default=True)
    ap.add_argument("--all-contaminated", action="store_true",
                    help="re-eval every contaminated run, not just non-applying ones")
    args = ap.parse_args()

    tasks = _task_index(args.tasks)
    docker_env = {"DOCKER_HOST": f"unix:///run/user/{os.getuid()}/docker.sock"}
    exp_root = Path(args.runs_root) / args.experiment / args.experiment

    out_rows = []
    for spec_path in sorted(exp_root.glob("*/run_spec.json")):
        rd = spec_path.parent
        spec = json.loads(spec_path.read_text())
        fp = rd / "final.patch"
        ev_path = rd / "eval_result.json"
        if not fp.exists() or not ev_path.exists():
            continue
        raw_ev = json.loads(ev_path.read_text())
        patch = fp.read_text(encoding="utf-8", errors="replace")
        sanitized, kept, removed = sanitize_patch(patch)
        if not removed:
            continue  # not contaminated
        if not args.all_contaminated and raw_ev.get("patch_applies") is True:
            continue  # applied already -> sanitization won't change resolution
        task = tasks.get(spec["task_id"])
        if task is None:
            print(f"skip {spec['task_id']}: task not in indices")
            continue
        run_id = spec["run_id"]
        res = evaluate_with_docker(
            task, sanitized, rd / "docker_eval_sanitized", run_id=run_id,
            python_exe=args.swebench_python, env=docker_env,
        )
        row = {
            "run_id": run_id, "task_id": spec["task_id"],
            "condition": spec["condition"], "seed": spec["seed"],
            "raw_patch_applies": raw_ev.get("patch_applies"),
            "raw_resolved": raw_ev.get("resolved"),
            "sanitized_patch_applies": res.patch_applies,
            "sanitized_resolved": res.resolved,
            "removed_paths": removed,
        }
        out_rows.append(row)
        rd.joinpath("integrity").mkdir(exist_ok=True)
        rd.joinpath("integrity", "eval_sanitized.json").write_text(
            res.model_dump_json(indent=2), encoding="utf-8")
        print(f"{spec['task_id']} {spec['condition']} seed{spec['seed']}: "
              f"applies {raw_ev.get('patch_applies')}->{res.patch_applies} "
              f"resolved {raw_ev.get('resolved')}->{res.resolved}")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w") as f:
        for row in out_rows:
            f.write(json.dumps(row) + "\n")
    changed = sum(1 for r in out_rows
                  if r["raw_resolved"] != r["sanitized_resolved"])
    print(f"\nre-evaluated {len(out_rows)} runs; resolution changed for {changed}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
