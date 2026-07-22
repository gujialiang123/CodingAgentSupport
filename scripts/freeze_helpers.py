"""Pre-generate + container-validate C2 helper tests, then freeze to disk (P2/P4).

For each task this runs :func:`generate_helper_in_container`, which:
  1. generates K blind candidates from the issue + scrubbed repo context,
  2. selects one that collects and FAILS on the base commit (in-container),
  3. freezes it BEFORE consulting gold,
  4. applies the gold patch in a fresh container to classify pass-after,
  5. assigns T0-T4 and runs a provenance/leakage audit for T4.

Every artifact is written to ``<out>/<task_id>.json`` regardless of class -- T0-T2
are the test-generation feasibility result and must never be silently dropped
(plan Priority 2). Only T3/T4 helpers are loaded by run_manager for C2/C2+C3.

Usage:
  python scripts/freeze_helpers.py --tasks data/tasks/ablation12.jsonl \
      --out data/helpers --model qwen3.7-plus \
      --base-url https://api.302.ai/v1 --api-key $API_KEY --k 3
"""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from pathlib import Path

from se_support.agents import OpenAIChatClient
from se_support.datasets import load_tasks
from se_support.support.repro_tests.pregen_container import generate_helper_in_container


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", required=True)
    ap.add_argument("--out", default="data/helpers")
    ap.add_argument("--model", default="qwen3.7-plus")
    ap.add_argument("--base-url", default="https://api.302.ai/v1")
    ap.add_argument("--api-key", default=os.environ.get("SE_API_KEY", "EMPTY"))
    ap.add_argument("--max-tokens", type=int, default=4096)
    ap.add_argument("--k", type=int, default=3, help="candidates per task")
    ap.add_argument("--namespace", default="swebench")
    ap.add_argument("--overwrite", action="store_true",
                    help="regenerate even if a frozen artifact already exists")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    tasks = load_tasks(Path(args.tasks))
    docker_env = {"DOCKER_HOST": f"unix:///run/user/{os.getuid()}/docker.sock"}
    client = OpenAIChatClient(model=args.model, base_url=args.base_url,
                              api_key=args.api_key, max_tokens=args.max_tokens)

    classes: Counter[str] = Counter()
    manifest = []
    for i, task in enumerate(tasks, 1):
        dst = out / f"{task.task_id}.json"
        if dst.exists() and not args.overwrite:
            art = json.loads(dst.read_text(encoding="utf-8"))
            cls = art.get("classification", "T0_invalid")
            classes[cls] += 1
            manifest.append({"task_id": task.task_id, "classification": cls, "cached": True})
            print(f"[{i}/{len(tasks)}] {task.task_id} -> {cls} (cached)")
            continue
        try:
            art = generate_helper_in_container(
                task, client, namespace=args.namespace, env=docker_env,
                k=args.k, generator_model=args.model,
            )
            dst.write_text(art.model_dump_json(indent=2), encoding="utf-8")
            cls = art.classification.value if hasattr(art.classification, "value") \
                else str(art.classification)
            classes[cls] += 1
            manifest.append({
                "task_id": task.task_id, "classification": cls,
                "fail_before": art.fail_before, "pass_after_gold": art.pass_after_gold,
                "issue_provenance_ok": art.issue_provenance_ok,
            })
            print(f"[{i}/{len(tasks)}] {task.task_id} -> {cls} "
                  f"(fail_before={art.fail_before} pass_after={art.pass_after_gold})")
        except Exception as exc:  # noqa: BLE001 - record + continue
            classes["ERROR"] += 1
            manifest.append({"task_id": task.task_id, "classification": "ERROR",
                             "error": repr(exc)})
            print(f"[{i}/{len(tasks)}] {task.task_id} -> ERROR: {exc!r}")

    (out / "_manifest.json").write_text(
        json.dumps({"classes": dict(classes), "tasks": manifest}, indent=2),
        encoding="utf-8",
    )
    t34 = classes.get("T3_valid_reproduction", 0) + classes.get("T4_decoupled_valid", 0)
    print("\n===== FREEZE SUMMARY =====")
    for k, v in sorted(classes.items()):
        print(f"  {k}: {v}")
    print(f"  T3+T4 (usable for C2): {t34}/{len(tasks)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
