# Experiment 012 — Protocol 0.3.1 preflight / implementation audit

Preflight audit before the Qwen open-weight E1 study. Baseline: `main @ 669be6c`
(protocol 0.3.0), work branch `experiment/protocol-031-qwen-e1`.

## Repository state

- HEAD descends from `669be6c` ✓
- `pytest` green (all tests) ✓; `ruff check .` clean ✓
- 302.ai API reachable; new model `qwen3-coder-30b-a3b-instruct` responds
  (non-reasoning instruct model, returns `content` directly).

## Integrity mechanisms present at 0.3.0 (audited)

| Mechanism | Location | Behavior |
|-----------|----------|----------|
| Helper resolved before container start; read-only mount | `run_manager.run_single`, `container_workspace.start(support_mount=…)` | Helper at `/testbed/.se_support/helper_test.py`, `readonly` bind mount; not in git tree |
| Clean-tree snapshots S0/S1/S2 | `_run_body`, `container_workspace.git_state()` | S0 records base-image untracked as baseline; modified-tracked or new-post-S0 untracked ⇒ `infrastructure_failure` |
| Safe patch extraction | `container_workspace.final_diff_with_manifest()` | Isolated `GIT_INDEX_FILE`; excludes support/build/cache + base-image untracked; `patch_manifest.json`; helper-leak assertion |
| Provenance | `_write_provenance` | `integrity/provenance.json` (versions, SHAs, image, commit) |
| Analysis guards | `analysis/aggregate.load_runs` | Excludes `infrastructure_failure`; refuses mixed `protocol_version` unless `--allow-mixed-protocol` |

## Gaps identified (addressed in Phase 1)

1. **Helper-hash was recorded but not enforced.** `helper_unchanged` was written
   but a mismatch did not fail the run. → **Fixed (1A):** `_helper_integrity_violation`
   now marks `infrastructure_failure`/`HELPER_INTEGRITY` before official eval;
   `PROTOCOL_VERSION` bumped 0.3.0 → **0.3.1**.
2. **Exp 010 P2P used stale denominators** (`4/14`, `2/15`) predating the 12
   `requests-1142` re-evaluations. → **Fixed (1C):** recomputed from corrected
   data (`p2p_regression_stats`, `exp010_c2xc3_corrected_summary.json`).
3. **Integrity smoke covered only one cell** (`C2_tests`). → Phase 1B four-cell
   smoke.

## Model-provenance caveat (documented, accepted per user directive)

The user directed E1 to run against the **302.ai hosted API** model
`qwen3-coder-30b-a3b-instruct` (same endpoint/key), not a self-served vLLM
checkpoint. Weight-file SHAs / exact HF revision are therefore **not verifiable
from the API**. This is recorded as a provenance limitation in
`docs/MODEL_FREEZE_QWEN3_CODER_E1.md`; the model **ID** is pinned and the server
`model` field is asserted on every call. Any future publication-grade weight-level
reproducibility would require self-hosting the pinned checkpoint.
