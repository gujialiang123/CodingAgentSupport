# Experiment 007: Full C0–C6 ablation with qwen3.7-plus (302.ai)

- **experiment_id:** `ablation01`
- **date:** 2026-07-21
- **author:** gujialiang123
- **status:** done (35/35 cells)

## 1. Purpose

The first ablation with a **capable model**: run the full one-factor-at-a-time
support ablation (C0–C6) and see whether support structures move resolution and
patch quality in interpretable ways. This is a **small pilot** (5 tasks, single
model, single seed) — directional signal, **not** a statistical result.

## 2. Setup

| Field | Value |
|---|---|
| Dataset | SWE-bench Verified |
| Cohort | 5 `psf/requests` tasks (`data/tasks/ablation5.jsonl`) |
| Conditions | C0, C1, C2, C3, C4, C5, C6 (all seven) → 5×7 = 35 runs |
| Model | **qwen3.7-plus** (reasoning) via **302.ai** OpenAI-compatible API |
| Endpoint | `https://api.302.ai/v1` (API key not committed) |
| Budgets | max_turns 15, max_tokens 4096 |
| Isolation | bubblewrap sandbox ON (no network, fs-confined) |
| C2 | helper generated pre-run (same model) |
| Evaluation | official SWE-bench Docker harness |
| Scheduler | EP-09, randomized, resumable, **--max-workers 6** (concurrent) |

Exact command in `docs/EXPERIMENT_CONFIGS.md` (Exp 007). Resumable: re-running the
command extends/finishes the experiment.

## 3. Where the logs live

- Raw runs: `runs/ablation01/ablation01/<run_id>/` (git-ignored; self-contained:
  transcript, commands, scrubbed task, manifest, support bundle + helper_artifact,
  manipulation.json, docker_eval, quality_card).
- Results: `results/ablation01.jsonl` (committed).

## 4. Results

### Per condition (5 tasks each)

| Condition | resolved | applying | ≥Q2 | isolation ok |
|---|---|---|---|---|
| C0 minimal | 3/5 | 4/5 | 3/5 | 5/5 |
| C1 +context | 3/5 | **5/5** | 3/5 | 5/5 |
| C2 +tests | **4/5** | **5/5** | **4/5** | 5/5 |
| C3 +gates | 2/5 | **5/5** | 2/5 | 5/5 |
| C4 +harness | **4/5** | 4/5 | **4/5** | 5/5 |
| C5 +memory | **4/5** | **5/5** | **4/5** | 5/5 |
| C6 full-stack | 2/5 | 3/5 | 2/5 | 5/5 |

### Resolution grid (R=resolved, a=applies-only, .=Q0)

```
cond            1142  1724  1766  1921  2931
C0 minimal      R     .     R     R     a
C1 context      R     R     R     a     a
C2 tests        R     R     R     R     a
C3 gates        R     a     R     a     a
C4 harness      R     R     R     R     .
C5 memory       R     R     R     R     a
C6 full-stack   R     R     .     a     .
```

## 5. Findings (directional; n=5, no stats)

1. **The capable model actually resolves tasks** — 22/35 resolved overall (vs 0
   for 7B). The pipeline discriminates: Q0 / applies-only / resolved all appear.
2. **Single supports (C2 tests, C4 harness, C5 memory) reach the top (4/5)**,
   above C0 (3/5). C1 context lifts *applying* to 5/5 (better localization/edits)
   even where resolution matches C0.
3. **C6 full-stack is the *worst* (2/5), not the best.** Stacking all supports
   over-constrained this model within the 15-turn budget: harness state management
   + gate revisions + a (T0) helper competed for turns, and 2 C6 cells produced no
   applying patch. This mirrors the Exp 006 observation that the enforced harness
   can *cost* budget, now visible even for a strong model when combined with
   everything else at a tight turn limit.
4. **C3 gates alone also underperforms (2/5 resolved)** despite 5/5 applying —
   i.e. gates kept patches syntactically valid but the model spent revisions
   without fixing the bug within budget.
5. **Isolation held on all 35 cells** (manipulation passed, network disabled, no
   gold in agent-visible inputs).

## 6. Caveats (do not over-read)

- **n=5 tasks, 1 seed, 1 model, 1 repo (`psf/requests`)** — no statistical claim;
  a single task flipping changes a condition by 20%.
- `max_turns=15` is tight; the C6/C3 deficits may be budget artifacts. A larger
  turn budget is a pre-registered variable to vary in the main study.
- C2 helpers were T0 (bare clone lacks deps); C2's gain here is **not** from a
  validated helper — treat C2's number cautiously and re-run with in-container
  helper validation (`docs/HANDOFF.md` §5.1).

## 7. Conclusion / next

The full C0–C6 ablation runs end-to-end with a capable API model and yields
interpretable, differentiated results. Ready to scale (more tasks/repos, more
seeds, larger turn budget) on the same turn-key command. Key hypotheses to test
at scale: (a) single supports > C0; (b) whether C6 recovers with a larger budget;
(c) gates/harness budget cost. See `docs/HANDOFF.md` and `docs/EXPERIMENT_CONFIGS.md`.
