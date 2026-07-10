# Experiment 004: First real C0 vs C6 pilot (SWE-bench Verified)

- **experiment_id:** `pilot01`
- **date:** 2026-07-09
- **author:** gujialiang123
- **status:** done

## 1. Purpose

The **first real end-to-end experiment**: run the controllable LLM agent on
real SWE-bench Verified tasks under the two extreme conditions (C0 minimal vs C6
full-stack), score with the official Docker harness, and see whether a support
signal exists. This is a smoke pilot (2 tasks, weak 7B model, "discounted" C6
with C2 tests not implemented) — a *lower bound* on the support effect, not a
paper result.

## 2. Setup

| Field | Value |
|---|---|
| Dataset | SWE-bench Verified |
| Tasks | 2 from `psf/requests` (small, fast repo): `requests-1142`, `requests-1724` |
| Agent | controllable LLM bash-loop (`LLMAgent`) |
| Model | Qwen/Qwen2.5-Coder-7B-Instruct (local vLLM, 4090, max_model_len 16384) |
| Conditions | C0_minimal, C6_full_stack |
| Max turns | 25 |
| Workspace | `Workspace.from_git` (clone repo@base_commit) |
| Evaluation | **official SWE-bench Docker harness** (`evaluate_with_docker`) |

Command:

```bash
# vLLM server (env: vllm) on the 4090, then:
python -m scripts.run_pilot --tasks data/tasks/pilot_requests.jsonl \
  --model Qwen/Qwen2.5-Coder-7B-Instruct --base-url http://localhost:8000/v1 \
  --experiment-id pilot01 --conditions C0_minimal C6_full_stack --max-turns 25 \
  --output runs/pilot01 --results results/pilot01.jsonl
```

## 3. Where the logs live

- Raw run artifacts: `runs/pilot01/pilot01/<run_id>/` (git-ignored) — full
  `transcript.jsonl`, `commands.jsonl`, `final.patch`, `eval_result.json`,
  `quality_card.json`, `docker_eval/harness.log`.
- Results table: `results/pilot01.jsonl`.

## 4. Results

| Task | Cond | resolved | patch_applies | F2P | P2P | quality |
|---|---|---|---|---|---|---|
| requests-1142 | C0 | False | False | 0/0 | 0/0 | Q0_invalid |
| requests-1142 | C6 | False | True | 0/1 | 5/5 | Q1_plausible_failing |
| requests-1724 | C0 | False | False | 0/0 | 0/0 | Q0_invalid |
| requests-1724 | C6 | **True** | True | 6/6 | 79/79 | Q2_functionally_correct |

**Summary:** C0 resolved **0/2**; C6 resolved **1/2**. Under C0 both patches were
empty/non-applying; under C6 both applied and one fully resolved.

## 5. Findings / Notes

- **A directional support signal exists even in this minimal pilot.** With no
  support (C0) the 7B agent failed to produce a usable patch on both tasks; with
  full-stack support (C6) it produced applying patches on both and resolved one.
- **Interpretable failure mode under C0** (from the transcript): without the
  context pack, the agent could not orient in the repo — it wandered off trying
  to edit `requests` in global `site-packages`, looped on errors, and timed out
  with an empty patch (failure modes F13 environment/tool, F02 localization).
  The C1 context (file map) + C5 memory (build/test hints) + C4 harness rules in
  C6 kept it inside the repository.
- Confirms the **full real pipeline** works: git clone of the base commit →
  condition-aware agent → official Docker evaluation → quality card → logs.

## 6. Caveats (do not over-read)

- n=2, single weak model, single seed — **no statistical claim**.
- C6 is "discounted": **C2 (reproduction tests) is not implemented**, and
  C1/C4/C5 are weak v1. The true support effect is likely larger.
- `psf/requests` tasks were chosen for speed; not representative of the harder
  django/sympy majority.

## 7. Next steps

- Scale to a proper pilot (e.g. 50 stratified tasks) with a pinned stronger
  model once the team finalizes the model choice.
- Implement C2 and strengthen C4 enforcement, then re-run to measure the delta.
- Add paired-comparison stats (McNemar) and quality-card aggregation.
