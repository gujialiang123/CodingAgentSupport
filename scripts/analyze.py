"""Generate analysis tables for an experiment (EP-10).

Usage:
    python -m scripts.analyze --experiment-id ablation02 \
        --runs runs --output results/ablation02_analysis.md
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from se_support.analysis import analyze, format_report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--experiment-id", required=True)
    ap.add_argument("--runs", default="runs")
    ap.add_argument("--baseline", default="C0_minimal")
    ap.add_argument("--output", default=None, help="Markdown output path.")
    ap.add_argument("--json", default=None, help="Optional JSON output path.")
    args = ap.parse_args()

    exp_dir = Path(args.runs) / args.experiment_id / args.experiment_id
    report = analyze(exp_dir, args.experiment_id, baseline=args.baseline)
    md = format_report(report)
    print(md)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(md)
    if args.json:
        Path(args.json).write_text(json.dumps(report.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
