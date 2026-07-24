"""Build the E1 task partition: exclusion manifest + 40 new stratified candidates.

Deterministic and outcome-blind (plan Phase 3). Scans historical task manifests,
run directories, results, helper caches, and docs for every previously used task,
then samples 40 NEW SWE-bench Verified tasks with a fixed seed, stratified by
repository (>=8 repos, <=4 per repo where feasible).

Usage:
  python scripts/build_e1_cohort.py --pool data/tasks/all500.jsonl \
      --seed 20260724 --n 40
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

_TASK_RE = re.compile(r"swebench_verified__[A-Za-z0-9_.\-]+")


def collect_used_task_ids(repo_root: Path) -> dict[str, list[str]]:
    """Return {source: [task_ids]} for every previously-used task."""
    used: dict[str, set[str]] = {}

    def add(src: str, ids):
        used.setdefault(src, set()).update(i for i in ids if i)

    # 1. task manifests (every jsonl under data/tasks except the full pool)
    for p in (repo_root / "data" / "tasks").glob("*.jsonl"):
        if p.name == "all500.jsonl":
            continue
        ids = []
        for line in p.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                ids.append(json.loads(line).get("task_id"))
            except json.JSONDecodeError:
                pass
        add(f"tasks/{p.name}", ids)

    # 2. run_spec.json under runs/
    run_ids = []
    for spec in (repo_root / "runs").glob("*/*/*/run_spec.json"):
        try:
            run_ids.append(json.loads(spec.read_text()).get("task_id"))
        except (OSError, json.JSONDecodeError):
            pass
    add("runs", run_ids)

    # 3. helper caches
    add("data/helpers", [p.stem for p in (repo_root / "data" / "helpers").glob("*.json")
                         if p.stem != "_manifest"])

    # 4. results jsonl
    res_ids = []
    for p in (repo_root / "results").glob("*.jsonl"):
        for line in p.read_text().splitlines():
            try:
                r = json.loads(line)
                if r.get("task_id"):
                    res_ids.append(r["task_id"])
            except json.JSONDecodeError:
                pass
    add("results", res_ids)

    # 5. docs (task ids mentioned in markdown, e.g. manually inspected during debug)
    doc_ids = []
    for p in (repo_root / "docs").rglob("*.md"):
        doc_ids += _TASK_RE.findall(p.read_text(errors="replace"))
    add("docs", doc_ids)

    return {k: sorted(v) for k, v in used.items()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool", default="data/tasks/all500.jsonl")
    ap.add_argument("--seed", type=int, default=20260724)
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--max-per-repo", type=int, default=4)
    ap.add_argument("--out-dir", default="data/partitions")
    args = ap.parse_args()

    root = Path.cwd()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    used_by_src = collect_used_task_ids(root)
    used = sorted({i for ids in used_by_src.values() for i in ids})
    (out / "all_previously_used_tasks.json").write_text(
        json.dumps({"by_source": used_by_src, "all": used, "count": len(used)},
                   indent=2), encoding="utf-8")

    pool = [json.loads(ln) for ln in Path(args.pool).read_text().splitlines() if ln.strip()]
    excluded = set(used)
    eligible = [t for t in pool if t["task_id"] not in excluded]

    (out / "e1_exclusions.json").write_text(json.dumps({
        "excluded_count": len(excluded), "excluded": sorted(excluded),
        "pool_size": len(pool), "eligible_after_exclusion": len(eligible),
    }, indent=2), encoding="utf-8")

    # Deterministic stratified sampling: within each repo sort by a seeded hash,
    # then round-robin across repos (sorted) taking up to max_per_repo each until n.
    def h(task_id: str) -> str:
        return hashlib.sha256(f"{args.seed}:{task_id}".encode()).hexdigest()

    by_repo: dict[str, list] = {}
    for t in eligible:
        by_repo.setdefault(t["repo"], []).append(t)
    for repo in by_repo:
        by_repo[repo].sort(key=lambda t: h(t["task_id"]))

    selected: list = []
    repos_sorted = sorted(by_repo)
    taken = {r: 0 for r in repos_sorted}
    round_i = 0
    while len(selected) < args.n and round_i < args.max_per_repo:
        for repo in repos_sorted:
            if len(selected) >= args.n:
                break
            if taken[repo] < min(args.max_per_repo, len(by_repo[repo])) \
                    and taken[repo] == round_i:
                selected.append(by_repo[repo][taken[repo]])
                taken[repo] += 1
        round_i += 1

    selected.sort(key=lambda t: h(t["task_id"]))  # frozen task order
    with open(out / "e1_candidate40.jsonl", "w") as f:
        for t in selected:
            f.write(json.dumps(t) + "\n")

    import collections
    strata = collections.Counter(t["repo"] for t in selected)
    manifest = {
        "source_dataset": "SWE-bench/SWE-bench_Verified (data/tasks/all500.jsonl)",
        "sampling_seed": args.seed,
        "n_requested": args.n, "n_selected": len(selected),
        "max_per_repo": args.max_per_repo,
        "n_repositories": len(strata),
        "strata_by_repo": dict(strata),
        "excluded_count": len(excluded),
        "task_ids": [t["task_id"] for t in selected],
        "task_hashes": {t["task_id"]: h(t["task_id"]) for t in selected},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    (out / "e1_candidate40_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"excluded {len(excluded)} used tasks; eligible {len(eligible)}")
    print(f"selected {len(selected)} across {len(strata)} repos: {dict(strata)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
