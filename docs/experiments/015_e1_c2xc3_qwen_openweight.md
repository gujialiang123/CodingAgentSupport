# Experiment 015 — E1 primary C2×C3 (Qwen open-weight, protocol 0.3.1)

**First protocol-0.3.1 mechanism experiment.** New untouched cohort, frozen Qwen
model, integrity-clean pipeline. Pre-registered analysis:
`docs/E1_C2XC3_ANALYSIS_PLAN.md`. Raw: `results/exp015_e1_c2xc3_qwen_openweight.jsonl`;
summary: `results/exp015_e1_c2xc3_summary.json`.

## Design (as run)

- **Tasks:** 8 new T3/T4-helper tasks (`data/partitions/e1_t34.jsonl`) — xarray×2,
  scikit-learn×3, astropy×3. (Planned 20; only 8 reached T3/T4 — see Exp 014.)
- **Conditions:** C0_minimal, C2_tests, C3_gates, C2_C3. **1 seed.** 8×4 = 32 runs.
- **Fixed:** protocol 0.3.1, condition 0.2.0, model `qwen3-coder-30b-a3b-instruct`
  (302.ai), 25 turns, 900 s wall-cap, in-container, `--network none`, frozen
  helpers, C3 v2, official judge hidden. Integrity: 0 infrastructure failures.
- **Preflight:** xarray-4356 × 4 conditions passed 4/4 integrity checks before the
  full launch.

## Primary result — floor effect, no differentiation

| Condition | resolved |
|-----------|----------|
| C0_minimal | 1/8 (0.125) |
| C2_tests | 1/8 (0.125) |
| C3_gates | 1/8 (0.125) |
| C2_C3 | 1/8 (0.125) |

Only **one** task (`pydata/xarray-4629`) resolves, and it resolves under **all
four** conditions. Every paired comparison vs C0 has **0 discordant pairs**
(both_pass=1, both_fail=7), so exact McNemar **p = 1.0** for C2, C3, and C2_C3.
**No evidence of any support effect — but the experiment is uninformative at this
floor**, not evidence of absence.

### Task-level table (R=resolved, a=applies only, .=no patch/apply)

| task | C0 | C2 | C3 | C2_C3 |
|------|----|----|----|-------|
| astropy-13453 | a | a | . | . |
| astropy-14598 | a | a | . | a |
| astropy-8872 | a | a | a | . |
| xarray-4356 | a | a | a | a |
| xarray-4629 | **R** | **R** | **R** | **R** |
| sklearn-11310 | a | a | a | a |
| sklearn-13439 | a | a | a | a |
| sklearn-9288 | . | . | . | . |

## Manipulation checks — succeeded

- **C2:** the agent executed the read-only helper in **16/16** C2/C2_C3 runs
  (100%). The null result is not because the helper was ignored.
- **C3:** gates fired actively — **28 blocking failures → 28 revisions** across 16
  gated runs. The gate machinery works.

So the treatments were *delivered and used*; the model simply could not solve
these tasks, masking any effect.

## Secondary outcomes (descriptive only, floor-limited — do not over-read)

| Condition | applying | mean files touched | P2P regressing / usable |
|-----------|----------|--------------------|-------------------------|
| C0_minimal | 7/8 | 2.25 | 4/7 |
| C2_tests | 7/8 | 2.38 | 5/7 |
| C3_gates | **5/8** | 1.38 | 4/5 |
| C2_C3 | **5/8** | 1.00 | 2/5 |

- **Gates lowered the applying rate** (5/8 vs 7/8): under C3/C2_C3, two tasks
  ended with a non-applying patch — the revision cycle can leave the tree in a
  broken state at budget exhaustion. Hypothesis to test with a non-floored model.
- **Gates reduced files touched** (1.0–1.4 vs 2.25–2.38): C3 constrains edits.
- P2P differences are on n≤7 and not interpretable here.

## Interpretation & go/no-go

This is a **clean null under a floor**: integrity is perfect (0 infra failures,
helper used 100%, gates fired), but `qwen3-coder-30b-a3b-instruct` resolves only
1/8 of these hard 3-repo T3/T4 tasks, so the C2×C3 contrast is unpowered.

Against the 50-task go/no-go checklist:
- ✅ 4/4 integrity smoke; helper-hash hard failure; no support/build/cache leak;
  corrected P2P aggregation; one frozen model; E1 used only new tasks; infra
  failure rate 0%; manipulation success 100% (>95%); task-level analysis working.
- ❌ **"no unexplained floor/ceiling from the model"** — there IS a floor (1/8).

**Recommendation:** do **not** launch the 50-task pilot with this configuration.
The binding constraints are (1) helper coverage is only ~20% and concentrated in
3 library repos (Exp 014), and (2) the 30B model floors on those tasks. Options
before a powered study: use a stronger model (or higher budget) to lift the floor;
and/or broaden the valid-helper frame (framework-repo helper tooling, or an
easier difficulty stratum) so a ≥20-task, multi-repo T3/T4 cohort exists.

## Checkpoint

Per plan, stop here and present results **before** the additional-seed stability
block (Phase 7). Given the floor, a stability block on this model/cohort would add
little; it is deferred pending a model/cohort change.
