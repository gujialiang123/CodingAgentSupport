# Experiment Configurations (reproducibility log)

A durable record of every experiment's configuration, cohort, model/endpoint,
exact command, and rationale, so runs can be reproduced and analyzed later.
Raw per-run artifacts live under `runs/<experiment_id>/` (git-ignored, but each is
self-contained and replayable); result tables under `results/<experiment_id>.jsonl`;
narrative logs under `docs/experiments/NNN_*.md`.

> **Secrets:** API keys are NEVER committed. They are passed via `--api-key` on the
> command line / environment only. Where a key was used it is shown as `<KEY>` here.

## Common infrastructure

- Repo: `gujialiang123/CodingAgentSupport`.
- Envs (conda): `se-support` (package/scheduler), `vllm` (local serving),
  `swebench` (official Docker eval, `swebench` 4.1.0).
- Docker: rootless, `DOCKER_HOST=unix:///run/user/$(id -u)/docker.sock`.
- Evaluation: official SWE-bench Docker harness (`evaluate_with_docker`).
- Isolation (confirmatory): bubblewrap sandbox (no network, fs-confined) + git
  history scrub + gold/official-test scrub + per-run manipulation check.
- Scheduler (EP-09): randomized order, resumable (deterministic run_id +
  `quality_card.json` marker), infra-only retries, optional concurrency
  (`--max-workers`, safe for API models).

## Datasets / cohorts

| File | Contents |
|---|---|
| `data/tasks/all500.jsonl` | Full SWE-bench Verified (500) imported TaskSpecs. |
| `data/tasks/pilot_requests.jsonl` | 2 small `psf/requests` tasks. |
| `data/tasks/formal_requests6.jsonl` | 6 `psf/requests` tasks (Exp 006). |
| `data/tasks/ablation5.jsonl` | 5 `psf/requests` tasks (Exp 007). |

(`data/` raw JSONL is git-ignored to keep the repo small; regenerate with the
`se-support import` + `sample` commands below.)

```bash
python -m se_support import swebench-verified --output data/tasks/all500.jsonl
# requests-only cohorts were selected by smallest PASS_TO_PASS count for speed.
```

## Experiments

### Exp 004 — pilot01 (first real C0 vs C6)
- Model: Qwen2.5-Coder-7B-Instruct (local vLLM, RTX 4090).
- Cohort: 2 `psf/requests`. Conditions: C0, C6. max_turns 25. Sandbox: OFF.
- Result: C0 0/2, C6 1/2 resolved. See `docs/experiments/004_*`.

### Exp 005 — feasib01 (integrated pipeline)
- Model: Qwen2.5-Coder-7B (local vLLM). Cohort: 2 tasks × {C0,C2,C4,C6}.
- Sandbox ON, C2 generation ON, Docker eval. All Q0 (plumbing result).

### Exp 006 — formal01 (formal-standard C0 vs C6, 7B)
- Model: Qwen2.5-Coder-7B (local vLLM). Cohort: 6 `psf/requests`. C0 vs C6.
  max_turns 30. Sandbox ON. 6/12 cells.
- Result: 0/6 resolved; C0 1/3 applying (Q1); C6 all timed out (harness hurt weak
  model). See `docs/experiments/006_*`.

### Exp 007 — ablation01 (full C0–C6 ablation, qwen3.7-plus via 302.ai)
- **Model:** `qwen3.7-plus` (reasoning model) via **302.ai**, OpenAI-compatible
  endpoint `https://api.302.ai/v1`, API key `<KEY>` (not committed).
- **Cohort:** `data/tasks/ablation5.jsonl` (5 `psf/requests`).
- **Conditions:** C0, C1, C2, C3, C4, C5, C6 (full OFAT ablation) → 5×7 = 35 runs.
- **Budgets:** max_turns 15, max_tokens 4096 (reasoning models need headroom).
- **Isolation:** sandbox ON (confirmatory). C2 helper generation ON (same model).
- **Concurrency:** `--max-workers 6` (API model, no local GPU bottleneck).
- **Command:**
  ```bash
  python -m scripts.run_feasibility \
    --tasks data/tasks/ablation5.jsonl \
    --conditions C0_minimal C1_context C2_tests C3_gates C4_harness C5_memory C6_full_stack \
    --model qwen3.7-plus --base-url https://api.302.ai/v1 --api-key <KEY> \
    --max-tokens 4096 --max-turns 15 --max-workers 6 \
    --experiment-id ablation01 --output runs/ablation01 --results results/ablation01.jsonl
  ```
- Results: `results/ablation01.jsonl`; narrative `docs/experiments/007_*`.
- **Resumable:** re-run the exact command to finish/extend (completed cells skip).

### Exp 008 — ablation02 (scaled C0–C6, 12 tasks × 5 repos)
- **Model:** `qwen3.7-plus` via 302.ai (`https://api.302.ai/v1`, key not committed).
- **Cohort:** `data/tasks/ablation12.jsonl` — 12 tasks across psf/requests(4),
  pytest(3), pylint(2), pallets/flask(1), pydata/xarray(2). Gold-eval pre-checked
  for the 4 new repos (plan §7.4).
- **Conditions:** C0–C6 → 12×7 = 84 runs. Budgets: **max_turns 25**, max_tokens 4096.
- Isolation ON, C2 gen ON, concurrency `--max-workers 6`.
- **Command:**
  ```bash
  python -m scripts.run_feasibility --tasks data/tasks/ablation12.jsonl \
    --conditions C0_minimal C1_context C2_tests C3_gates C4_harness C5_memory C6_full_stack \
    --model qwen3.7-plus --base-url https://api.302.ai/v1 --api-key <KEY> \
    --max-tokens 4096 --max-turns 25 --max-workers 6 \
    --experiment-id ablation02 --output runs/ablation02 --results results/ablation02.jsonl
  # analysis:
  python -m scripts.analyze --experiment-id ablation02 --output results/ablation02_analysis.md
  ```
- Results: `results/ablation02.jsonl` + `results/ablation02_analysis.md`; narrative
  `docs/experiments/008_*`. Resolution by condition: C0 .42, C1 .50, C2 .67,
  C3 .58, C4 .58, C5 .67, C6 .33 (single supports help; C6 worst).
