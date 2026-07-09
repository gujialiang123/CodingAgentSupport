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
| `workspace.py` | `Workspace`: git-backed per-run checkout; apply/reverse patches, final diff, run pytest node ids. |
| `patch_utils.py` | Unified-diff parsing → `DiffMetrics` (files_touched, loc_added/deleted) + changed files. |
| `run_manager.py` | `run_single`: orchestrates one (task, agent, condition) run end-to-end. |

### `src/se_support/agents/` — agent scaffolds

| Path | Purpose |
|---|---|
| `base.py` | `AgentRunner` protocol (swappable scaffolds, proposal §7.1). |
| `mock_agent.py` | `MockAgent`: deterministic, no-LLM agent (gold/empty/broken/patch) for pipeline validation. |
| `chat_client.py` | `ChatClient` protocol; `OpenAIChatClient` (vLLM/API) + `ScriptedChatClient` (offline tests). |
| `llm_agent.py` | `LLMAgent`: controllable bash-loop agent; model-agnostic; condition-aware (gates hook). |

### `src/se_support/support/` — support conditions (T4)

| Path | Purpose |
|---|---|
| `condition.py` | `SupportCondition` + `CONDITIONS` (C0–C6) toggling context/tests/gates/harness/memory. |
| `prompts.py` | `build_system_prompt`: base prompt + condition-driven additions (context/memory/harness). |
| `context_pack.py` | C1 context generator (repo file map + test hints), lexical/leak-free. |
| `memory.py` | C5 repo-memory generator (AGENTS.md-style, from repo contents). |
| `gates.py` | C3 deterministic gates (compileall blocking; ruff/bandit advisory). |

### `src/se_support/evaluation/` — correctness scoring

| Path | Purpose |
|---|---|
| `local_eval.py` | `evaluate_patch`: offline evaluator (apply patch, compileall, run F2P/P2P) → `EvalResult`. |

### `src/se_support/quality/` — patch quality cards

| Path | Purpose |
|---|---|
| `quality_card.py` | `build_card`: offline, re-runnable `PatchQualityCard` v0 (functional correctness + locality + gold overlap). |

## `schemas/` — generated

Exported `*.schema.json` (one per model in `EXPORTED_MODELS`). Regenerate with
`python -m se_support schemas export`. Committed so schema changes are visible
in diffs.

## `tests/`

| Path | Purpose |
|---|---|
| `test_schemas.py` | Every model: valid-fixture round-trip, invalid raises, schema export. |
| `test_run_dir.py` | Run-directory creation + JSONL round-trip. |
| `test_pipeline.py` | End-to-end mock-agent pipeline on the fixture repo (gold resolves, empty/broken do not). |
| `test_llm_agent.py` | Controllable LLM agent + conditions via ScriptedChatClient (offline, no GPU). |
| `fixtures/*.valid.json` | One valid example per model (also mirrors proposal §9). |
| `fixtures/mini_repo/` | Tiny buggy repo (calc + tests) used as an offline task. |
| `fixtures/mini_repo_gold.patch` | Gold patch that fixes the mini-repo bug. |
| `fixtures/task_mini_repo.json` | TaskSpec pointing at the mini-repo fixture. |

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
