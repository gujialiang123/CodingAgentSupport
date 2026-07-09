# Experiment 001: Mock pipeline smoke test

- **experiment_id:** `smoke`
- **date:** 2026-07-09
- **author:** gujialiang123
- **status:** done

## 1. Purpose

Validate the end-to-end pipeline (workspace → agent → patch → eval → quality
card → logs) with **zero model cost** before plugging in any real LLM. Not a
research result — a plumbing check.

## 2. Setup

| Field | Value |
|---|---|
| Dataset | fixture (`tests/fixtures/mini_repo`) |
| Tasks | 1 (`fixture__mini_repo__subtract_bug`) |
| Agent | `mock_agent` (gold / empty / broken) |
| Model | none (deterministic) |
| Conditions | C0_minimal, C6_full_stack |
| Seeds | [0] |

Commands:

```bash
python -m se_support run --task tests/fixtures/task_mini_repo.json \
  --mock-mode gold   --condition C6_full_stack --experiment-id smoke --output runs/smoke
python -m se_support run --task tests/fixtures/task_mini_repo.json \
  --mock-mode empty  --condition C0_minimal   --experiment-id smoke --output runs/smoke
python -m se_support run --task tests/fixtures/task_mini_repo.json \
  --mock-mode broken --condition C0_minimal   --experiment-id smoke --output runs/smoke
```

## 3. Where the logs live

- Raw run artifacts: `runs/smoke/smoke/<run_id>/` (git-ignored; regenerate with
  the commands above).
- Each run dir contains: `task.json`, `run_spec.json`, `transcript.jsonl`,
  `commands.jsonl`, `final.patch`, `final_message.md`, `eval_result.json`,
  `quality_card.json`.

## 4. Results

| Mock mode | resolved | F2P | P2P | quality_level |
|---|---|---|---|---|
| gold | True | 1/1 | 1/1 | Q3_engineering_acceptable |
| empty | False | 0/1 | 1/1 | Q1_plausible_failing |
| broken | False | 0/1 | 1/1 | Q1_plausible_failing |

Broken run additionally flags `locality.unrelated_file_change_suspected=true`
and `gold_file_overlap=0.0`, confirming locality metrics work.

## 5. Findings / Notes

- Pipeline is correct end-to-end without any LLM: gold resolves, empty/broken do
  not. Unavailable quality metrics are recorded as `null` (not `0`), per protocol.
- Automated as `tests/test_pipeline.py`.

## 6. Risks / TODOs

- Real dataset importer (T2), gates (T5), harness/context/memory support layers
  (T4) and a real mini-SWE-agent adapter are still pending.
- Eval currently uses the local (no-Docker) evaluator; SWE-bench Docker eval is a
  later ticket behind the same `EvalResult` contract.
