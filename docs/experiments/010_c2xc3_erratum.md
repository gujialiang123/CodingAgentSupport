# Experiment 010 — Erratum (integrity fix, protocol 0.3.0)

**Status:** the raw Experiment 010 (protocol pre-0.3.0) suffered two measurement
contaminations. This erratum reports the corrected numbers from offline
sanitization + official re-evaluation. Raw artifacts are preserved; corrected
values live in `results/exp010_c2xc3_sanitized.jsonl` and
`results/exp010_c2xc3_reeval.jsonl`.

## What was wrong

1. **Helper leaked into the patch.** The C2 helper was written into the git tree
   at `/testbed/se_support_helper_test.py` and swept into `final.patch` by
   `git add -A`. **All 42 C2/C2_C3 runs** included the helper file → inflated
   `files_touched`.
2. **Base-image `build/lib/` leaked into the patch (all conditions).** The
   `psf/requests` SWE-bench image ships an untracked `build/lib/` tree (~65 files)
   at container start. `git add -A` swept it into every `requests-1142` patch.
   When the official evaluator tried to `git apply` a patch that re-adds these
   already-present files, **application failed**, so **all 12 `requests-1142` runs
   (every condition, every seed) were scored `patch_applies=False`, `resolved=False`**
   — masking that the agent's real `requests/models.py` fix was correct.

## Corrections

Offline: strip reserved support/build-artifact/cache diff blocks (never touching
legitimate agent edits) and recompute locality. Official re-evaluation of the 12
contaminated non-applying `requests-1142` patches with the sanitized diff.

**Re-evaluation result: 12/12 `requests-1142` runs flip `False → True` resolved**
(applies `False → True`). The task is solved by every condition; contamination
had hidden it uniformly.

### Resolution (n=7 tasks × 3 seeds = 21 per condition)

| Condition | raw | **corrected** |
|-----------|-----|---------------|
| C0_minimal | 0.38 | **0.52** |
| C2_tests | 0.52 | **0.67** |
| C3_gates | 0.52 | **0.67** |
| C2_C3 | 0.52 | **0.67** |

Because `requests-1142` flips uniformly (+3 for every condition), the **relative**
support effect is preserved: C2 and C3 each still lift resolution over C0 by
**+0.15**, and there is still **no stacking** on resolution (all supported cells
= 0.67).

### Locality (mean files touched)

| Condition | raw (contaminated) | **corrected** |
|-----------|--------------------|---------------|
| C0_minimal | 10.3 | **1.0** |
| C2_tests | 11.3 | **1.1** |
| C3_gates | 10.7 | **1.4** |
| C2_C3 | 11.4 | **1.1** |

**The "C2 broadens edits / over-editing" claim is WITHDRAWN.** After removing the
helper artifact, C2 touches ~1.1 files vs C0's ~1.0 — no meaningful difference.
The raw 2.0-vs-1.1 gap was entirely the injected helper file.

### P2P regression (recomputed from corrected data)

Recomputed directly from `results/exp010_c2xc3_reeval.jsonl` + the sanitized
per-run evals (not the old denominators). Denominator = applying patches with a
usable PASS_TO_PASS result (`patch_applies` and P2P total > 0). A regression =
≥1 PASS_TO_PASS test failed. Machine-readable: `exp010_c2xc3_corrected_summary.json`.

| Condition | applying | P2P-usable | P2P-regressing | rate |
|-----------|----------|------------|----------------|------|
| C0_minimal | 20 | 17 | 4 | 0.24 |
| C2_tests | 21 | 18 | 3 | 0.17 |
| C3_gates | 21 | 18 | 4 | 0.22 |
| C2_C3 | 21 | 18 | 2 | **0.11** |

**C2_C3 had the lowest observed P2P-regression rate in this pilot** (2/18). With
n=7 tasks this is directional only — it is **not** proof that helper+gates
improves patch safety; it is a hypothesis to test on the new-task E1 cohort.

## Net effect on the study's claims

- **Held:** C2 and C3 each individually help; helper and gates do not stack on
  resolution.
- **Softened:** helper+gates had the *lowest observed* P2P-regression rate in
  this pilot (2/18); with n=7 this is directional, not a proven safety effect.
- **Withdrawn:** C2 causes broader edits / over-editing.
- **Newly corrected:** absolute resolution is higher for all conditions once
  `requests-1142` is evaluable; C0 rises 0.38 → 0.52.

The raw Experiment 010 is retained as a construct-validation / bug-discovery
pilot; the corrected numbers here are the citable ones, and any headline reruns
should use protocol 0.3.0.
