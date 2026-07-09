# File Index

A file-by-file description of the repository, so anyone can find where a
responsibility lives. Update this when adding or removing files.

## Top level

| Path | Purpose |
|---|---|
| `PROJECT_PROPOSAL.md` | Full research proposal (RQs, design, tickets). The source of truth for scope. |
| `README.md` | Project overview + quick start. |
| `pyproject.toml` | Package metadata, dependencies, `se-support` entry point, ruff & pytest config. |
| `environment.yml` | Conda environment spec (`se-support`, Python 3.11). |
| `.gitignore` | Ignores caches and large regenerable outputs (`runs/`, `results/`, `data/raw/`). |

## `src/se_support/` — the package

| Path | Purpose |
|---|---|
| `__init__.py` | Package docstring + version. |
| `__main__.py` | Enables `python -m se_support`. |
| `cli.py` | argparse CLI. Implements `schemas export/list`; stubs `import/run/evaluate/quality`. |
| `config.py` | On-disk paths (`runs/`, `results/`, `schemas/`, `data/`) and the `SUPPORT_CONDITIONS` list. |
| `logging.py` | Human/diagnostic stderr logger (distinct from structured experiment logging). |

### `src/se_support/schemas/` — data contracts (T1)

| Path | Purpose |
|---|---|
| `base.py` | `SEModel` base: forbids unknown fields, validates on assignment, `json_schema()` helper. |
| `task_spec.py` | `TaskSpec` (+`TaskMetadata`): one repository-level task = run input. |
| `run_spec.py` | `RunSpec`: parameters of one run (pinned model, condition, seed). |
| `agent_run_result.py` | `AgentRunResult` (+`RunStatus`): pointers to raw artifacts on disk. |
| `eval_result.py` | `EvalResult`: functional-correctness outcome (RQ2). |
| `patch_quality_card.py` | `PatchQualityCard` (+nested + `QualityLevel`): non-functional quality (RQ3). |
| `__init__.py` | Re-exports models; `EXPORTED_MODELS` map; `export_schemas()`. |

### `src/se_support/runner/` — execution & logging

| Path | Purpose |
|---|---|
| `__init__.py` | Subpackage docstring. |
| `run_dir.py` | `RunDirectory` layout + `TranscriptEvent`/`CommandRecord` JSONL contracts. The basis for post-hoc metric recomputation. |

## `schemas/` — generated

Exported `*.schema.json` (one per model in `EXPORTED_MODELS`). Regenerate with
`python -m se_support schemas export`. Committed so schema changes are visible
in diffs.

## `tests/`

| Path | Purpose |
|---|---|
| `test_schemas.py` | Every model: valid-fixture round-trip, invalid raises, schema export. |
| `test_run_dir.py` | Run-directory creation + JSONL round-trip. |
| `fixtures/*.valid.json` | One valid example per model (also mirrors proposal §9). |

## `docs/`

| Path | Purpose |
|---|---|
| `FILE_INDEX.md` | This file. |
| `experiment_protocol.md` | Datasets, agents, models, conditions, metrics we actually use; the rules. |
| `run_directory_spec.md` | Exact on-disk contract per run. |
| `experiments/README.md` | How experiment log files are named/organised. |
| `experiments/TEMPLATE.md` | Copy for each new experiment (purpose/setup/results/logs). |

## `runs/`, `results/`, `data/`

| Path | Purpose |
|---|---|
| `runs/` | Per-run raw outputs (`runs/{experiment_id}/{run_id}/...`). Git-ignored except `.gitkeep`. |
| `results/` | Aggregated tables/figures/quality cards. Git-ignored except `.gitkeep`. |
| `data/` | Imported tasks, gold patches, downloaded assets (raw assets git-ignored). |
