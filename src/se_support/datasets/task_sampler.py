"""Task sampling for building pilot/main task lists.

Supports ``head`` (first N) and ``stratified`` (proportional by a key, default
repository group) sampling with a fixed seed for reproducibility.
"""

from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path

from se_support.schemas import TaskSpec


def load_tasks(jsonl_path: Path) -> list[TaskSpec]:
    tasks = []
    for line in Path(jsonl_path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            tasks.append(TaskSpec.model_validate_json(line))
    return tasks


def sample_tasks(
    tasks: list[TaskSpec],
    n: int,
    strategy: str = "stratified",
    seed: int = 0,
    stratify_key: str = "repo_group",
) -> list[TaskSpec]:
    if n >= len(tasks):
        return list(tasks)
    if strategy == "head":
        return tasks[:n]
    if strategy != "stratified":
        raise ValueError(f"unknown strategy: {strategy}")

    rng = random.Random(seed)
    groups: dict[str, list[TaskSpec]] = defaultdict(list)
    for t in tasks:
        key = getattr(t.metadata, stratify_key, None) or "unknown"
        groups[str(key)].append(t)

    for g in groups.values():
        rng.shuffle(g)

    # Proportional allocation, then round-robin fill to hit exactly n.
    selected: list[TaskSpec] = []
    order = sorted(groups)
    idx = {k: 0 for k in order}
    while len(selected) < n:
        progressed = False
        for k in order:
            if len(selected) >= n:
                break
            if idx[k] < len(groups[k]):
                selected.append(groups[k][idx[k]])
                idx[k] += 1
                progressed = True
        if not progressed:
            break
    return selected


def write_tasks(tasks: list[TaskSpec], output_jsonl: Path) -> int:
    output_jsonl = Path(output_jsonl)
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with output_jsonl.open("w", encoding="utf-8") as fh:
        for t in tasks:
            fh.write(t.model_dump_json() + "\n")
    return len(tasks)


def _load_raw(jsonl_path: Path) -> list[dict]:  # kept for potential JSON reuse
    return [json.loads(x) for x in Path(jsonl_path).read_text().splitlines() if x.strip()]
