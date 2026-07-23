"""Freeze per-repository C5 memory once, BEFORE any evaluation task is seen (P5).

C5 memory is repository-scoped and must be frozen ahead of time so it cannot
smuggle in task-specific information. For each distinct repo in the cohort this
starts one instance container (any task from that repo), derives repo memory from
repo-wide files only (README/CONTRIBUTING/pyproject/tox/setup.cfg/conftest,
top-level layout) and writes ``<out>/<repo_slug>.md``.

Usage:
  python scripts/freeze_repo_memory.py --tasks data/tasks/ablation12.jsonl \
      --out data/repo_memory
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from se_support.datasets import load_tasks
from se_support.runner.container_workspace import ContainerWorkspace
from se_support.support.memory import build_repo_memory, repo_slug


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", required=True)
    ap.add_argument("--out", default="data/repo_memory")
    ap.add_argument("--namespace", default="swebench")
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    tasks = load_tasks(Path(args.tasks))
    docker_env = {"DOCKER_HOST": f"unix:///run/user/{os.getuid()}/docker.sock"}

    # One representative task per repo (memory is repo-scoped, task-agnostic).
    by_repo: dict[str, object] = {}
    for t in tasks:
        by_repo.setdefault(t.repo, t)

    for i, (repo, task) in enumerate(by_repo.items(), 1):
        dst = out / f"{repo_slug(repo)}.md"
        if dst.exists() and not args.overwrite:
            print(f"[{i}/{len(by_repo)}] {repo} -> cached ({dst.name})")
            continue
        instance_id = task.task_id.split("__", 1)[1] if "__" in task.task_id \
            else task.task_id
        cw = ContainerWorkspace.start(instance_id, None, namespace=args.namespace,
                                      env=docker_env)
        try:
            memory = build_repo_memory(repo, cw.path, reader=cw)
        finally:
            cw.close()
        dst.write_text(memory, encoding="utf-8")
        print(f"[{i}/{len(by_repo)}] {repo} -> {dst.name} ({len(memory)} chars)")

    print(f"\nFroze memory for {len(by_repo)} repos into {out}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
