# E1 C2×C3 analysis plan (pre-registered, protocol 0.3.1)

Frozen **before** observing any E1 agent outcome. No metric, comparison, budget,
prompt, model, or condition may change after results are seen.

## Experimental unit

The independent generalization unit is the **task**, not the seed. The primary E1
block uses **one seed per (task, condition)**; three seeds on one task are
repeated measurements (Phase 7 stability), never three independent tasks.

## Conditions

`C0_minimal`, `C2_tests`, `C3_gates`, `C2_C3` — a 2×2 (helper × gates) on new
T3/T4 tasks. C1/C4/C5/C6 are **not** in E1.

## Primary outcome & comparisons

- **Primary outcome:** official SWE-bench `resolved`.
- **Primary paired comparisons** (task-level, seed 0): C2 vs C0, C3 vs C0,
  C2_C3 vs C0. Each uses an **exact McNemar test** on discordant task pairs plus a
  **paired bootstrap CI** for the resolution-rate difference
  (`analysis/aggregate.paired_contrast`).
- **Factorial interpretation:** helper main effect, gate main effect,
  helper × gate interaction (from the four cell resolution rates).
- No uncorrected fishing across many metrics; the three paired comparisons above
  are the confirmatory family.

## Secondary outcomes (descriptive)

`patch_applies`, F2P passed/total, P2P passed/total, P2P regression (denominator =
applying + P2P total > 0, via `p2p_regression_stats`), empty patch, timeout,
infrastructure failure, files touched / changed LOC, token/turn/command/wall-time
cost. Quality metrics reported separately over: all generated patches / applying
patches / resolved patches.

## Mechanism outcomes (structured, per run)

**C2 (helper):** helper available; agent viewed helper; agent executed helper;
helper execution count; helper result at base; helper result after final patch;
helper-pass / official-fail overfit cases.

**C3 (gates):** gates executed; blocking gate failures; advisory warnings;
revision triggered; patch before/after revision; whether revision changed the
official outcome; whether revision introduced a regression.

These are extracted offline from `commands.jsonl`, `gate_results.json`,
`state_transitions.json`, and the helper artifact (recomputable from run dirs).

## Aggregation guards (enforced in code + tested)

`analysis/aggregate.load_runs` refuses to pool across:
- mixed `protocol_version` (`allow_mixed_protocol`);
- mixed `model` (`allow_mixed_model`);
- mixed `condition_version` (`allow_mixed_condition_version`);
- and **excludes** runs flagged `infrastructure_failure` from agent statistics.
Seed-level rows are never treated as independent tasks (pairing is by task at
seed 0; stability uses task-clustered analysis).

## Reporting

Report **task-level paired transitions**, not only aggregate percentages:
`C0 fail → support pass`, `C0 pass → support fail`, `both pass`, `both fail`, for
each support vs C0. With ~20 tasks × 1 seed this is a **pilot**: report effect
directions and CIs, not definitive significance.

## Interpretation caveats

- C2 efficacy is estimated **conditional on a valid (T3/T4) helper**; helper
  coverage (T0–T4 over the 40 candidates) is reported separately and must not be
  folded into the conditional estimate.
- Do not generalize conditional C2 efficacy to all 500 SWE-bench Verified tasks
  without reporting coverage.
