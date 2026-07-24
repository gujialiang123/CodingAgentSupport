# Handoff: running large-model experiments

This document is the context needed to resume the SE-Support Study on a
bigger-GPU machine and run the real confirmatory experiments. It complements
`EXPERIMENT_PLAN_2026-07-21.md` (the protocol) and
`CONSTRUCT_HARDENING_STATUS.md` (build status).

## 1. What is ready

The **fully integrated confirmatory pipeline runs end-to-end**:

```
import task -> git clone @ base_commit -> [C2 helper gen in generator zone]
-> frozen support bundle (C0-C6) -> agent (sandboxed, harness/gates enforced)
-> official SWE-bench Docker eval -> quality card (+process metrics) -> logs
```

with information isolation (bwrap: no network, fs-confined), provenance scrubbing
(no gold/official-test in agent-visible inputs), per-run manipulation checks, and
a randomized, **resumable** scheduler.

Construct hardening packages done: EP-00/01/02/03/04/07/08 + A1–A4/EP-09.
See `CONSTRUCT_HARDENING_STATUS.md`.

## 2. Environments (conda)

| Env | Purpose |
|---|---|
| `se-support` | the package, scheduler, agents, C2 pipeline (`pip install -e .[dev]`) |
| `vllm` | local model serving (vLLM OpenAI server) |
| `swebench` | official SWE-bench Docker evaluation harness (`swebench` 4.1.0) |

Docker is **rootless**: `export DOCKER_HOST=unix:///run/user/$(id -u)/docker.sock`.
The scheduler sets this automatically via the driver script.

## 3. The one thing to change for big runs: the model

Everything is model-agnostic via an OpenAI-compatible endpoint. To use a stronger
model, **only the endpoint/model id changes**:

- **Self-hosted** (needs ~80–96 GB VRAM for e.g. Qwen2.5-Coder-32B/Coder-Next):
  serve with vLLM and point `--base-url`/`--model` at it.
  ```bash
  CUDA_VISIBLE_DEVICES=0,1 python -m vllm.entrypoints.openai.api_server \
    --model <big-model> --served-model-name <big-model> \
    --tensor-parallel-size 2 --max-model-len 32768 --port 8000
  ```
- **Hosted API**: set `--base-url https://api.provider/v1 --api-key ...` and a
  **pinned snapshot** model id.

**Pin the model for the whole experiment** (record the exact snapshot). Select it
using D0 only (plan §9.3): it must follow the command protocol and avoid a C0
floor effect (C0 should produce non-empty/applying patches often enough).

## 4. How to run

```bash
conda activate se-support

# 1. Import + sample a cohort (plan §7)
python -m se_support import swebench-verified --output data/tasks/all500.jsonl
python -m se_support sample -i data/tasks/all500.jsonl -o data/tasks/pilot50.jsonl \
  --n 50 --strategy stratified

# 2. Run (randomized, resumable; re-run the same command to resume)
python -m scripts.run_feasibility --tasks data/tasks/pilot50.jsonl \
  --conditions C0_minimal C1_context C2_tests C3_gates C4_harness C5_memory C6_full_stack \
  --model <pinned-model> --base-url <endpoint> \
  --experiment-id main01 --max-turns 40 --output runs --results results/main01.jsonl
```

The scheduler skips already-completed cells, so interrupted runs resume safely.

## 5. Known limitations to address before publication-grade runs

1. ✅ **RESOLVED (P1).** The agent now runs **inside the SWE-bench instance
   container** (`--in-container`): `/testbed` with deps installed, `--network none`.
   It can run the repo's real tests, C3 gates, and the C2 helper. Use
   `--in-container` on the driver for publication-grade runs.
2. ✅ **RESOLVED (P2).** C2 helper validation now runs **inside base/gold
   containers**, so fail-before/pass-after actually execute — helpers reach
   T3/T4 (verified on psf__requests-2931: fail_before=True, pass_after_gold=True).
   Only T3/T4 helpers are injected; T0–T2 are recorded (not dropped).
3. ✅ **RESOLVED (P5, C1+C3+C5).** All three supports upgraded to v2 and now
   default (protocol/CONDITION_VERSION bumped to **0.2.0**):
   - **C1 v2** — issue-based retrieval (symbol/lexical scoring, top-k snippets
     with `path:line` provenance, related tests, fixed token budget) + a
     `C1_random` same-budget control.
   - **C3 v2** — repo-aware gates: syntax + import + **repo-native targeted tests**
     for changed modules (blocking; never the hidden official tests), with
     lint/type checks that run **only when the repo configures them** (no forcing
     unconfigured Ruff/Bandit). Verified live on psf/requests: ruff/flake8/mypy
     correctly skipped as "not configured by repo".
   - **C5 v2** — repository-scoped frozen memory (no task leakage), frozen once via
     `scripts/freeze_repo_memory.py`; `data/repo_memory/<repo>.md` for all 5
     cohort repos. Basic install/run-tests **operational access is now in the
     shared base prompt for ALL conditions**, so C5 measures memory, not access.
   Known limitation: the targeted-test file mapping is heuristic
   (`tests/test_<stem>.py`); repos with monolithic test files (e.g. requests'
   `tests/test_requests.py`) may not map, so targeted tests pass trivially there.
4. ✅ **DIAGNOSED (Exp 009A).** The enforced harness (C4) — not the turn budget —
   drives C6's deficit for this model. C6−C4 recovers resolution (0.39→0.58; +0.28
   after integrity re-eval) at 25 turns; doubling the budget (C6@50) does NOT
   recover resolution (0.39), only converts timeouts to submitted-but-wrong
   patches. Harness needs redesign, not more turns (`009A_budget_diagnosis.md`).
5. ✅ **RESOLVED (integrity fix, protocol 0.3.0).** Root cause: the C2 helper was
   written into the git tree at `/testbed/se_support_helper_test.py` and swept
   into `final.patch` by `git add -A` (contaminating 97/404 historical runs); the
   `psf/requests` base image also ships an untracked `build/lib/` tree that leaked
   in and made **every** `requests-1142` patch fail to apply. Fixes: (a) helper is
   resolved before container start and delivered as a **read-only bind mount** at
   `/testbed/.se_support/helper_test.py` (write/delete fail; hash verified
   before/after); (b) **clean-tree S0/S1/S2 snapshots** — modified-tracked or new
   post-S0 untracked ⇒ `infrastructure_failure` (excluded from stats), pre-existing
   base-image untracked recorded as baseline; (c) **safe patch extraction** in an
   isolated `GIT_INDEX_FILE` temp index excluding support/build/cache paths, with a
   hard no-leak assertion + `integrity/patch_manifest.json`; (d) full provenance in
   `integrity/provenance.json`. Historical audit + sanitize + re-eval:
   `scripts/audit_support_contamination.py`, `scripts/reeval_sanitized.py`. See
   `010_c2xc3_erratum.md`, `010_requests1142_forensics.md`, `011_integrity_smoke.md`.
   **Corrected Exp 010:** C0 0.52, C2/C3/C2_C3 0.67 (relative support effect +0.15
   preserved; over-editing claim withdrawn; files_touched ~1). Future headline
   runs must use protocol 0.3.0 and must not be mixed with earlier results.
6. **Analysis package (EP-10) not built**: McNemar/bootstrap paired tables,
   quality-among-resolved, annotation sampler. Needed to produce paper tables.
7. **Human annotation (E4)** needs annotators (codebook + double-coding + kappa).
8. **Q3+ quality levels** require the mature rubric/human review (auto-capped at Q2).

## 6. Where results and context live

- Raw runs: `runs/<experiment_id>/<run_id>/` (git-ignored; each is self-contained
  and replayable — see `docs/run_directory_spec.md`).
- Results tables: `results/<experiment_id>.jsonl`.
- Experiment logs (purpose/setup/results): `docs/experiments/NNN_*.md`.
- Metrics are recomputable offline from run dirs
  (`se_support.quality.recompute_card_from_run_dir`), so new metrics never require
  re-running.
