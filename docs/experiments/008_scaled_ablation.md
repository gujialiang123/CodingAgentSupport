# Experiment 008: Scaled C0–C6 ablation (12 tasks × 5 repos, qwen3.7-plus)

- **experiment_id:** `ablation02`
- **date:** 2026-07-21
- **author:** gujialiang123
- **status:** done (84/84 cells)

## 1. Purpose

Strengthen the Exp 007 signal on a **larger, more diverse cohort** and test the
Exp 007 hypothesis that C6's deficit was a tight-turn-budget artifact. Still a
**pilot** (12 tasks, 1 seed, 1 model) — directional, not a statistical result,
but the analysis now emits paired McNemar + bootstrap CIs (EP-10).

## 2. Setup

| Field | Value |
|---|---|
| Dataset | SWE-bench Verified |
| Cohort | **12 tasks across 5 repos** (`data/tasks/ablation12.jsonl`): psf/requests ×4, pytest ×3, pylint ×2, pallets/flask ×1, pydata/xarray ×2 |
| Conditions | C0–C6 (all seven) → 12×7 = **84 runs** |
| Model | qwen3.7-plus via 302.ai (`https://api.302.ai/v1`, key not committed) |
| Budgets | **max_turns 25** (up from 15 in Exp 007), max_tokens 4096 |
| Isolation | sandbox ON; C2 helper gen ON; official Docker eval |
| Scheduler | EP-09 randomized, resumable, **--max-workers 6** |
| Pre-check | gold-eval verified for the 4 new repos (plan §7.4 exclusion rule) |

Exact command: `docs/EXPERIMENT_CONFIGS.md` (Exp 008). Analysis:
`python -m scripts.analyze --experiment-id ablation02` → `results/ablation02_analysis.md`.

## 3. Where the logs live

- Raw runs: `runs/ablation02/ablation02/<run_id>/` (git-ignored; self-contained).
- Results: `results/ablation02.jsonl`; analysis `results/ablation02_analysis.{md,json}`.

## 4. Results

### Resolution by condition (n=12 each)

| condition | resolved | rate | applying | ≥Q2 | Δ vs C0 | 95% CI | McNemar p |
|---|---|---|---|---|---|---|---|
| C0 minimal | 5 | 0.42 | 10 | 5 | — | — | — |
| C1 +context | 6 | 0.50 | 11 | 6 | +0.08 | [0.00, +0.25] | 1.000 |
| C2 +tests | **8** | **0.67** | 11 | 8 | +0.25 | [0.00, +0.50] | 0.250 |
| C3 +gates | 7 | 0.58 | 11 | 7 | +0.17 | [0.00, +0.42] | 0.500 |
| C4 +harness | 7 | 0.58 | 9 | 7 | +0.17 | [-0.17, +0.50] | 0.625 |
| C5 +memory | **8** | **0.67** | **12** | 8 | +0.25 | [0.00, +0.50] | 0.250 |
| C6 full-stack | 4 | 0.33 | 7 | 4 | -0.08 | [-0.42, +0.25] | 1.000 |

### Resolved by repo × condition

```
repo(n)       C0  C1  C2  C3  C4  C5  C6
pallets(1)    1   1   1   1   1   1   1
psf(4)        2   3   3   2   3   3   1
pydata(2)     1   1   2   2   2   2   1
pylint(2)     0   0   0   0   0   0   0
pytest(3)     1   1   2   2   1   2   1
```

## 5. Findings (directional; n=12, no stats claim)

1. **Every single support (C1–C5) ≥ C0; none hurt.** C2 tests and C5 memory are
   top (0.67 vs C0 0.42, +0.25), C3/C4 next (+0.17), C1 smallest (+0.08). All
   paired discordances favor the treatment (b≥c) except C4 (3 vs 1) and C6. This
   **replicates and sharpens Exp 007**.
2. **C6 full-stack is again the worst (0.33 < C0 0.42).** Raising the turn budget
   15→25 did **not** rescue C6 — so the deficit is not purely a budget artifact.
   Stacking all five supports over-constrains this model (harness bookkeeping +
   gate revisions + a T0 helper + a long context compete), and C6 also has the
   lowest *applying* rate (7/12). This is the study's central kind of result:
   **more support is not monotonically better; interactions matter.**
3. **C5 memory reached 12/12 applying** — repo recipes/conventions reliably keep
   edits legal even when they don't always resolve.
4. **Difficulty is repo-dependent:** pylint (2 tasks) is unsolved by every
   condition; psf/pytest/pydata show the support lift. Supports help most where
   the task is within reach.
5. **Isolation held on all 84 cells** (100% manipulation-passed, network off,
   no gold in agent-visible inputs).

## 6. Caveats

- **n=12, 1 seed, 1 model.** McNemar p-values are all > 0.05 (expected at this n);
  treat as effect-size *direction*, not significance. CIs that touch 0 are not
  "no effect", just underpowered.
- C2 helpers were T0 (bare clone lacks deps) — C2's gain is **not** attributable
  to a validated helper yet; re-run with in-container helper validation.
- Single repo family bias reduced but not eliminated (still Python web/tools).

## 7. Conclusion / next

Two independent pilots (Exp 007 n=5, Exp 008 n=12) now agree: **single supports
help; full-stack C6 underperforms for this model at these budgets.** This is a
strong, testable hypothesis for the main study. Next: scale to the 50/120-task
cohorts with multiple seeds and a larger turn budget on a bigger machine; add
in-container C2 validation; run the paired stats at powered n. Pipeline + analysis
are turn-key (`docs/HANDOFF.md`, `scripts/analyze.py`).
