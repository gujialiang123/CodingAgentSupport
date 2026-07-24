# Experiment 012 — Four-cell integrity smoke (protocol 0.3.1)

Extends the single-cell Exp 011 smoke to all four E1 conditions, and doubles as
the scaffold-compatibility check for the new model `qwen3-coder-30b-a3b-instruct`.
Task `psf/requests-1142` (T4 helper), 1 seed, in-container.

## Scaffold fix discovered here (pre-E1)

The first four-cell attempt produced **empty patches for every condition**. Root
cause: the Qwen3-Coder instruct model emits its whole plan as **many ```bash```
blocks in one message** (up to 39) and then stops; the scaffold executed only the
**first** block per message, so the model exhausted its plan without editing and
submitted empty. This is a scaffold/model-format mismatch, not an integrity or
efficacy result.

**Fix (model-agnostic, applied before any E1 run):** the agent now executes **all**
bash blocks in a message in order (capped at 10) and feeds back the combined
output; a message containing bash blocks is never treated as a SUBMIT. Base prompt
updated to match. After the fix the model produces real patches.

## Results (4/4 integrity PASS)

| Condition | S0 clean | S1 clean | helper leak | helper host==before==after | applies | resolved | files |
|-----------|----------|----------|-------------|----------------------------|---------|----------|-------|
| C0_minimal | ✓ | ✓ | none | n/a | ✓ | false | 5* |
| C2_tests | ✓ | ✓ | none | ✓ | ✓ | **true** | 2 |
| C3_gates | ✓ | ✓ | none | n/a | ✓ | false | 1 |
| C2_C3 | ✓ | ✓ | none | ✓ | ✓ | **true** | 2 |

*C0's 5 files are legitimate **agent-created** scratch scripts (`apply_fix.py`,
`test_fix.py`, `verify_fix.py`, `final_verification.py`) plus `requests/models.py`
— real agent output, correctly captured (not support/build contamination). This
is a locality signal to watch, not a leak.

### Per-condition integrity checks (all satisfied)

- **All cells:** S0 and S1 clean (base-image `build/lib` recorded as baseline, not
  agent output); `final.patch` contains only agent changes; real git index
  untouched (isolated `GIT_INDEX_FILE`); official evaluator consumed the patch;
  quality card computed from the sanitized patch; no support/cache artifact in
  `files_touched`.
- **C2 / C2_C3:** helper readable, write/delete fail (read-only mount verified in
  Exp 011), host==before==after SHA-256, helper absent from `final.patch`.
- **C3 / C2_C3:** gate results logged; gate baseline did not dirty S1; no
  gate-generated file entered `final.patch`.

## Acceptance

**4/4 cells pass every integrity check.** The scaffold is compatible with the new
model and protocol 0.3.1 is ready for the D0 qualification and E1 study. (This is
an integrity/compatibility smoke, not an efficacy result.)
