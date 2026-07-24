# Experiment 014 — E1 helper feasibility (40 new candidates)

Blind C2 helper generation + container validation on the 40 new E1 candidate
tasks, using the frozen Qwen model `qwen3-coder-30b-a3b-instruct` (K=3 candidates
each). This is the **helper-coverage** result; it is reported separately from and
must not be folded into the conditional C2 efficacy estimate.

## Method

For each task: generate 3 blind candidates (issue + base repo/tests only; never
gold/official tests/PR/future history), select one that collects and fails on the
base commit with issue provenance and no forbidden literal, freeze it, then apply
the gold patch in a fresh container to classify pass-after, and run a
leakage/decoupling audit. All in the SWE-bench instance container. No gold
feedback is fed back into the generator.

## Result: T0–T4 distribution (n=40)

| Class | n | meaning |
|-------|---|---------|
| T4_decoupled_valid | 7 | T3 + no leakage/overfit flag |
| T3_valid_reproduction | 1 | fails on base, passes on gold |
| T2_incompatible_oracle | 18 | fails on base AND on gold |
| T1_non_reproducing | 5 | passes on base (no repro) |
| T0_invalid | 5 | cannot collect/execute |
| ERROR | 4 | image could not be pulled/run |

**Usable (T3/T4): 8/40 = 20%.** (Excluding the 4 un-pullable images: 8/36 = 22%.)

## Interpretation — coverage is repository-structural

The 8 valid helpers come from only **3 repositories** — xarray (2),
scikit-learn (3), astropy (3) — all "library-like" packages whose behavior is
testable in a short standalone pytest module. The dominant failure mode is
**T2 (18/40)**: the generated test fails on base *and* still fails after the gold
patch. Inspection shows this is largely **framework harness dependence** — e.g.
Django checks need app/settings bootstrapping that a standalone helper does not
provide, so the test fails for setup reasons both before and after the fix.
django, sympy, sphinx contribute almost entirely T0–T2.

- **4 ERROR** tasks are all **matplotlib**: their images fail to load under
  rootless Docker (`failed to register layer: Lchown .../build/qhull-... invalid
  argument` — a subuid-range limitation of this host), so they cannot be run here
  at all.

**Headline coverage finding:** blind single-model helper generation yields a
container-valid reproduction test for only ~20% of a repository-diverse
SWE-bench Verified frame, concentrated in library-style projects. Framework-heavy
repos (Django/Sphinx/SymPy) and un-pullable images (matplotlib) are effectively
out of reach for standalone helper tests with this model/pipeline. This is a real
constraint on how broadly a helper-conditioned C2 result can generalize.

## Cohort for the E1 experiment

Because only **8** tasks reached T3/T4, the planned "20 T3/T4" cannot be met on
this frame. The E1 C2×C3 experiment therefore uses **all 8** valid-helper tasks
(`data/partitions/e1_t34.jsonl`), a smaller pilot. A 4-task stability subset
(`data/partitions/e1_stability_subset.jsonl`) is preselected by seeded hash before
any agent outcome is observed.

- Frozen helpers: `data/helpers/e1/<task_id>.json` (8 usable; all classes retained).
- Deviation from plan (20→8) is driven purely by helper coverage, not by agent
  performance; task order is a fixed seeded hash.

C2 efficacy from this cohort is **conditional on a valid helper** and, given only
3 repositories, must not be generalized to all 500 SWE-bench Verified tasks.
