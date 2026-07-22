# Experiment 009A: Full-stack budget & orchestration diagnosis (in-container)

- **experiment_id:** `exp009a_t25` (+ `exp009a_c6t50` for the 50-turn block)
- **date:** 2026-07-22
- **author:** gujialiang123
- **status:** 25-turn block done (144/144); C6@50 block running

## 1. Purpose

Exp 007/008 found **full-stack C6 underperforms single supports**. This diagnoses
*why*, per the plan's Priority 3, by decomposing the effect:

- **C4 @ 25** — harness overhead alone.
- **C6 @ 25** — reproduce the deficit.
- **C6−C4 @ 25** — full stack **without** the enforced harness (context+tests+
  gates+memory). If this recovers, the harness protocol is the main cost.
- **C6 @ 50** — does a bigger turn budget rescue C6? (budget vs. interaction).

First experiment run **in-container** (P1): the agent works inside the SWE-bench
instance image at `/testbed` with deps, so it runs real tests/gates. 3 seeds.

## 2. Setup

| Field | Value |
|---|---|
| Cohort | `data/tasks/ablation12.jsonl` (12 tasks × 5 repos) |
| Conditions | C0, C4, C6, C6_minus_C4 @ 25 turns; C6 @ 50 turns |
| Seeds | 0, 1, 2 |
| Model | qwen3.7-plus via 302.ai; max_tokens 4096 |
| Execution | **in-container** (`--in-container`), official Docker eval |
| Runs | 144 (25-turn block) + 36 (C6@50 block) |

Commands + config: `docs/EXPERIMENT_CONFIGS.md` (Exp 009A).

## 3. Results — 25-turn block (144 runs, 3 seeds)

| Condition | resolved | rate | applying | **timeout rate** |
|---|---|---|---|---|
| C0 minimal | 22/36 | **0.61** | 32/36 | 22% |
| C4 harness | 20/36 | 0.56 | 28/36 | **58%** |
| C6 full-stack | 14/36 | **0.39** | 21/36 | **67%** |
| C6−C4 (no harness) | 21/36 | **0.58** | 33/36 | 22% |

### Stability across seeds (highly consistent)

```
C0        seed0:8/12  seed1:7/12  seed2:7/12
C4        seed0:7/12  seed1:8/12  seed2:5/12
C6        seed0:4/12  seed1:4/12  seed2:6/12
C6−C4     seed0:7/12  seed1:7/12  seed2:7/12
```

## 4. Diagnosis (25-turn block)

1. **The enforced harness (C4) is the primary driver of C6's deficit.** Removing
   just the harness from the full stack (**C6−C4**) recovers resolution from
   **0.39 → 0.58** (+0.19), back to ~C0/single-support level. The other four
   supports stacked together (context+tests+gates+memory) do **not** hurt.
2. **The mechanism is turn-budget exhaustion via the state protocol.** Timeout
   rate tracks the harness exactly: harness-on conditions (C4 58%, C6 67%) time
   out far more than harness-off (C0 22%, C6−C4 22%). The agent spends its budget
   emitting/repairing `NEXT_STATE` directives instead of editing+testing code.
3. **Result is stable across 3 seeds** — not noise. C6 is 4/4/6, C6−C4 is 7/7/7.
4. **In-container matters:** with real deps the agent iterates on actual tests;
   resolution is much higher than the bare-clone Exp 007/008 (C0 .61 vs .42),
   confirming P1's value.

## 5. C6 @ 50 turns — RESULT

Completed (`exp009a_c6t50`, 12 tasks × 3 seeds = 36 runs, in-container).

| Condition | n | Resolved | Timeout | Mean turns |
|-----------|---|----------|---------|------------|
| C6 @ 25 turns | 36 | **0.39** | 67% | 23.0 |
| C6 @ 50 turns | 36 | **0.39** | 28% | 32.9 |

**Verdict: budget is NOT the driver.** Doubling the turn budget (25→50) left
resolution flat at **0.39** while cutting the timeout rate from 67% → 28%. In
other words, the extra turns only let the agent *stop timing out* — they convert
timeouts into **submitted-but-wrong** patches, not into correct ones. The
harness protocol churn consumes the added budget without producing correctness.

This matches decision rule (b) from plan P3: *C6@50 still low + timeout falls but
resolution does not recover → more turns won't help; the enforced harness
protocol itself must be redesigned.* Combined with C6−C4 recovering to 0.58 at
the **same** 25-turn budget, the harness — not the budget — is unambiguously the
bottleneck.

## 6. Caveats

- n=12 tasks/condition × 3 seeds; directional + mechanism evidence, not a powered
  significance test. But the seed stability + timeout-rate mechanism make the
  harness-overhead conclusion robust for this model/cohort.
- Single model (qwen3.7-plus). A stronger/faster model may tolerate the harness
  better — worth re-checking. The harness is expected to help *capable* models
  that follow the protocol cheaply.

## 7. Implication for the study

C4 (enforced harness) as currently implemented **trades correctness for process
compliance** under a fixed turn budget for this model, and — per §5 — **more
budget does not buy the correctness back** (it only trades timeouts for wrong
submissions). Options: (a) make the harness cheaper (fewer mandatory turns /
allow batching records+edits), or (b) treat harness as advisory rather than
enforced. Simply raising the budget (previously option (b)) is now **ruled out**
by the C6@50 result. This is a concrete, data-backed design finding for the main
study.
