# Experiment 003: SWE-bench Docker evaluation validated

- **experiment_id:** `docker_eval_check`
- **date:** 2026-07-09
- **author:** gujialiang123
- **status:** done

## 1. Purpose

Bring up the **authoritative** SWE-bench Verified evaluation path (official
Docker harness) and prove it works end-to-end through our
`evaluate_with_docker` wrapper. This is the correctness oracle real experiments
will use. Not a research result.

## 2. Setup

| Field | Value |
|---|---|
| Docker | rootless, `DOCKER_HOST=unix:///run/user/1007/docker.sock`, data dir `~/.local/share/docker` |
| Harness | `swebench` 4.1.0 in conda env `swebench` |
| Dataset | SWE-bench/SWE-bench_Verified (test split) |
| Task | `astropy__astropy-13033` (F2P=1, P2P=20) |
| Patch | **gold** (human reference) — sanity oracle |
| Image | pulled from `swebench` namespace, `--cache_level env` |

Validated two ways:

```bash
# 1) raw harness, gold predictions
conda activate swebench
DOCKER_HOST=unix:///run/user/$(id -u)/docker.sock \
python -m swebench.harness.run_evaluation \
  --dataset_name SWE-bench/SWE-bench_Verified -i astropy__astropy-13033 \
  -p gold --run_id goldcheck --max_workers 1 --cache_level env --namespace swebench

# 2) our wrapper (se_support.evaluation.evaluate_with_docker) on the gold patch
```

## 3. Where the logs live

- Harness logs + report: work dir passed to `evaluate_with_docker`
  (`harness.log`, `logs/run_evaluation/<run_id>/...`).
- `EvalResult` is returned and (in real runs) written to `eval_result.json`.

## 4. Results

| Path | resolved | F2P | P2P |
|---|---|---|---|
| raw harness (gold) | True | 1/1 | 20/20 |
| our wrapper (gold) | True | 1/1 | 20/20 |

Wall time ~90 s (image pull dominated). **Disk:** with `--cache_level env` the
instance image is removed after evaluation — free space stayed at ~1.2 TB, so a
pilot does not accumulate images.

## 5. Findings / Notes

- The official Docker oracle works on this host via **rootless Docker** (system
  daemon needs sudo; rootless does not). Env `swebench` is separate from
  `se-support` and invoked by interpreter path (`--python-exe`).
- Predictions must be **JSONL** (one dict per line), not a JSON array — fixed in
  `write_predictions`.
- Report parser reads the per-instance `report.json`
  (`patch_successfully_applied`, `resolved`, `tests_status.*`).

## 6. Risks / TODOs

- Wire `evaluate_with_docker` into `run_single` as the evaluator for real
  (non-fixture) tasks, selectable from the CLI.
- Each instance pull is a few GB and ~1-2 min; budget time for a 50-task pilot.
- Consider `--cache_level instance` only if re-evaluating the same tasks often.
