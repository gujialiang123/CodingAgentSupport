"""Audit + sanitize historical runs for support-artifact contamination (P6).

Before the integrity fix, the C2 helper (and, for psf/requests, the base image's
untracked ``build/lib/`` tree) could enter the agent's final patch via ``git add
-A``. This scanner finds affected runs and produces sanitized derived patches +
recomputed locality metrics, WITHOUT overwriting any raw artifact.

For each run under ``runs/<experiment>/**`` it:
  1. reads ``final.patch`` and splits it into per-file ``diff --git`` blocks;
  2. drops blocks for reserved support / build-artifact / cache paths;
  3. recomputes files_touched and added/deleted LOC from the sanitized patch;
  4. records provenance of the transformation.

Outputs (never overwrites raw):
  results/support_contamination_audit.jsonl
  docs/experiments/SUPPORT_CONTAMINATION_AUDIT.md
Optionally, per-experiment sanitized result JSONL via --sanitize-results.

Usage:
  python scripts/audit_support_contamination.py --runs-root runs \
      --out results/support_contamination_audit.jsonl \
      --sanitize-results results/exp010_c2xc3.jsonl
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

# Paths that must never be part of an agent patch (support inputs / build output).
_CONTAMINANT_RE = re.compile(
    r"^(se_support_helper_test\.py|\.se_support/|build/lib/|.*/__pycache__/|"
    r".*\.pyc$|\.pytest_cache/|\.mypy_cache/|\.ruff_cache/)"
)


def split_diff_blocks(patch: str) -> list[tuple[str, str]]:
    """Split a unified diff into (path_b, block_text) per file."""
    blocks: list[tuple[str, str]] = []
    if not patch.strip():
        return blocks
    parts = re.split(r"(?m)^(?=diff --git )", patch)
    for part in parts:
        if not part.strip():
            continue
        m = re.search(r"^diff --git a/.+ b/(.+)$", part, re.MULTILINE)
        path = m.group(1).strip() if m else ""
        blocks.append((path, part))
    return blocks


def sanitize_patch(patch: str) -> tuple[str, list[str], list[str]]:
    """Return (sanitized_patch, kept_paths, removed_paths)."""
    kept, removed, out = [], [], []
    for path, block in split_diff_blocks(patch):
        if path and _CONTAMINANT_RE.match(path):
            removed.append(path)
        else:
            kept.append(path)
            out.append(block)
    return "".join(out), kept, removed


def patch_loc(patch: str) -> tuple[int, int]:
    added = sum(1 for ln in patch.splitlines()
               if ln.startswith("+") and not ln.startswith("+++"))
    deleted = sum(1 for ln in patch.splitlines()
                 if ln.startswith("-") and not ln.startswith("---"))
    return added, deleted


def audit_run(run_dir: Path) -> dict | None:
    fp = run_dir / "final.patch"
    spec = run_dir / "run_spec.json"
    if not fp.exists() or not spec.exists():
        return None
    patch = fp.read_text(encoding="utf-8", errors="replace")
    sanitized, kept, removed = sanitize_patch(patch)
    s = json.loads(spec.read_text())
    a0, d0 = patch_loc(patch)
    a1, d1 = patch_loc(sanitized)
    helper_in = any(p == "se_support_helper_test.py" or p.startswith(".se_support/")
                    for p in removed)
    build_in = any(p.startswith("build/lib/") for p in removed)
    return {
        "run_id": s.get("run_id"), "task_id": s.get("task_id"),
        "condition": s.get("condition"), "seed": s.get("seed"),
        "experiment_id": s.get("experiment_id"),
        "protocol_version": s.get("protocol_version"),
        "files_before": len(kept) + len(removed), "files_after": len(kept),
        "removed_paths": removed, "helper_contaminated": helper_in,
        "build_artifact_contaminated": build_in,
        "loc_added_before": a0, "loc_added_after": a1,
        "loc_deleted_before": d0, "loc_deleted_after": d1,
        "run_dir": str(run_dir),
        "contaminated": bool(removed),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-root", default="runs")
    ap.add_argument("--out", default="results/support_contamination_audit.jsonl")
    ap.add_argument("--md", default="docs/experiments/SUPPORT_CONTAMINATION_AUDIT.md")
    ap.add_argument("--sanitize-results", nargs="*", default=[],
                    help="result JSONLs to rewrite with sanitized files_touched")
    args = ap.parse_args()

    rows = []
    for spec in sorted(Path(args.runs_root).glob("*/*/*/run_spec.json")):
        r = audit_run(spec.parent)
        if r is not None:
            rows.append(r)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")

    # Aggregate by experiment + condition.
    from collections import defaultdict
    agg = defaultdict(lambda: {"n": 0, "contam": 0, "helper": 0, "build": 0,
                               "files_before": 0, "files_after": 0})
    for r in rows:
        k = (r["experiment_id"], r["condition"])
        a = agg[k]
        a["n"] += 1
        a["contam"] += int(r["contaminated"])
        a["helper"] += int(r["helper_contaminated"])
        a["build"] += int(r["build_artifact_contaminated"])
        a["files_before"] += r["files_before"]
        a["files_after"] += r["files_after"]

    lines = ["# Support-artifact contamination audit", "",
             "Auto-generated by `scripts/audit_support_contamination.py`. Scans all",
             "historical runs for support/build-artifact paths that leaked into the",
             "agent's `final.patch` before the integrity fix (protocol 0.3.0).", "",
             "| experiment | condition | n | contaminated | helper | build/lib | "
             "mean files before | mean files after |",
             "|---|---|---|---|---|---|---|---|"]
    for (exp, cond), a in sorted(agg.items(), key=lambda x: (str(x[0][0]), x[0][1])):
        mb = a["files_before"] / a["n"] if a["n"] else 0
        ma = a["files_after"] / a["n"] if a["n"] else 0
        lines.append(f"| {exp} | {cond} | {a['n']} | {a['contam']} | {a['helper']} | "
                     f"{a['build']} | {mb:.1f} | {ma:.1f} |")
    total = len(rows)
    contam = sum(r["contaminated"] for r in rows)
    lines += ["", f"**Total runs scanned:** {total}; **contaminated:** {contam} "
              f"({100*contam/total:.0f}%).", "",
              "Sanitized patches remove only reserved support/build-artifact/cache",
              "blocks; all legitimate agent source edits are preserved. Raw patches",
              "and raw results are untouched. Resolution/F2P/P2P are unaffected by",
              "removing these non-source files (see erratum for re-evaluation)."]
    Path(args.md).parent.mkdir(parents=True, exist_ok=True)
    Path(args.md).write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Optionally rewrite result JSONLs with sanitized files_touched.
    by_key = {(r["experiment_id"], r["task_id"], r["condition"], r["seed"]): r
              for r in rows}
    for path in args.sanitize_results:
        src = Path(path)
        if not src.exists():
            continue
        out_rows = []
        for line in src.read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            exp = src.stem
            # results rows lack experiment_id; match on task/condition/seed.
            match = next((r for (e, t, c, s), r in by_key.items()
                          if t == row.get("task_id") and c == row.get("condition")
                          and s == row.get("seed")), None)
            if match:
                row["files_touched_raw"] = row.get("files_touched")
                row["files_touched"] = match["files_after"]
                row["sanitized"] = True
                row["removed_paths"] = match["removed_paths"]
            out_rows.append(row)
        dst = src.with_name(src.stem + "_sanitized.jsonl")
        with open(dst, "w") as f:
            for row in out_rows:
                f.write(json.dumps(row) + "\n")
        print(f"wrote {dst}")

    print(f"scanned {total} runs; {contam} contaminated -> {args.out}, {args.md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
