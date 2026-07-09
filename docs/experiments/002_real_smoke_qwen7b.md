# Experiment 002: Real 4090 smoke run (Qwen2.5-Coder-7B)

- **experiment_id:** `real_smoke`
- **date:** 2026-07-09
- **author:** gujialiang123
- **status:** done

## 1. Purpose

Validate the **real LLM loop** end-to-end on the local 4090: the controllable
`LLMAgent` talking to a local vLLM server, under two conditions (C0 vs C6),
producing a patch that is evaluated and turned into a quality card. Debugging
check only — 7B pass/fail is not a research result.

## 2. Setup

| Field | Value |
|---|---|
| Dataset | fixture (`tests/fixtures/mini_repo`) |
| Tasks | 1 (`fixture__mini_repo__subtract_bug`) |
| Agent | `llm_agent` (controllable bash-loop) |
| Model | Qwen/Qwen2.5-Coder-7B-Instruct (local vLLM, bf16) |
| Serving | `vllm.entrypoints.openai.api_server`, `--max-model-len 8192`, GPU util 0.90 |
| Conditions | C0_minimal, C6_full_stack |
| Max turns | 15 |

Server:

```bash
conda activate vllm
CUDA_VISIBLE_DEVICES=0 python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-Coder-7B-Instruct --max-model-len 8192 \
  --gpu-memory-utilization 0.90 --port 8000
```

Runs:

```bash
conda activate se-support
python -m se_support run --task tests/fixtures/task_mini_repo.json \
  --agent llm --model Qwen/Qwen2.5-Coder-7B-Instruct \
  --base-url http://localhost:8000/v1 --condition C0_minimal \
  --max-turns 15 --experiment-id real_smoke --output runs/real_smoke
# ...and again with --condition C6_full_stack
```

## 3. Where the logs live

`runs/real_smoke/real_smoke/<run_id>/` (git-ignored). Each has full
`transcript.jsonl`, `commands.jsonl`, `final.patch`, `eval_result.json`,
`quality_card.json` (+ `gate_results.json` for C6).

## 4. Results

| Condition | resolved | F2P | P2P | quality |
|---|---|---|---|---|
| C0_minimal | False | 0/1 | 1/1 | Q1 |
| C6_full_stack | False | 1/1 | 0/1 | Q1 |

## 5. Findings / Notes

- **The whole real-LLM pipeline works**: multi-turn bash loop, command
  execution in the workspace, gates on submit (C6), patch capture, F2P/P2P
  evaluation, and quality card — all logged and replayable.
- **Behavioural signal captured**: under C6 the 7B model ran
  `sed -i 's/a + b/a - b/g'`, an **over-broad edit** (failure mode F05) that
  fixed `subtract` but **broke `add`** — the evaluator correctly flagged the
  regression (P2P 0/1 → not resolved). This is precisely the kind of quality
  gap the study measures.
- 7B correctness is weak/erratic as expected; not a result, just plumbing proof.

## 6. Risks / TODOs

- Switch to a pinned strong model (API or larger local) for real experiments.
- Harness (C4) and gates (C3) enforcement should be tuned to discourage
  over-broad edits; worth checking whether harness reduces F05.
- Replace the fixture with real SWE-bench Verified tasks (T2 importer).
