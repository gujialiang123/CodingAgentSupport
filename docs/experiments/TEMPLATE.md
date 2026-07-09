# Experiment NNN: <title>

- **experiment_id:** `<must match runs/{experiment_id}/>`
- **date:** `YYYY-MM-DD`
- **author:** `<name>`
- **status:** planned | running | done | abandoned

## 1. Purpose

What question does this run answer? Which RQ/hypothesis (e.g. RQ2, H3)?

## 2. Setup

| Field | Value |
|---|---|
| Dataset | e.g. SWE-bench Verified (pilot_50) |
| Tasks | count + selection/sampling method |
| Agent | e.g. mini_swe_agent |
| Model | **pinned** snapshot string |
| Conditions | e.g. C0_minimal, C6_full_stack |
| Seeds | e.g. [0] |
| Max turns / wall time | |
| Commit | git SHA of the code used |

Exact command(s) run:

```bash
# e.g.
python -m se_support run --tasks data/tasks/pilot_50.jsonl \
  --agent mini_swe_agent --condition C0_minimal --output runs/001_smoke ...
```

## 3. Where the logs live

- Raw run artifacts: `runs/<experiment_id>/`
- Eval results: `results/eval/<experiment_id>.jsonl`
- Quality cards: `results/quality_cards/<experiment_id>.jsonl`
- Aggregated tables/figures: `results/tables/<experiment_id>/`

## 4. Results

| Metric | C0 | C6 | Δ |
|---|---|---|---|
| Resolution rate | | | |
| Median files_touched | | | |
| Median loc changed | | | |
| ... | | | |

## 5. Findings / Notes

Interpretation, surprises, anomalies, follow-ups. Note any deviations from the
protocol and why.

## 6. Risks / TODOs

Open issues, tasks whose environment failed, metrics not yet computed.
