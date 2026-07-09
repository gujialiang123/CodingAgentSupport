# CodingAgentSupport (SE-Support Study)

A controlled-ablation framework for studying **which software-engineering
support structures make AI coding agents produce more correct and higher-quality
code**. See [`PROJECT_PROPOSAL.md`](PROJECT_PROPOSAL.md) for the full research
design.

The central idea: hold the agent and model **fixed**, and toggle five support
structures on/off as experimental conditions (C0–C6):

| Condition | Adds | Question |
|---|---|---|
| C0 minimal | nothing | baseline |
| C1 context | structured context pack | does curated context help? |
| C2 tests | generated reproduction tests | do repro tests help? |
| C3 gates | deterministic lint/type/test/security gates | do gates improve quality? |
| C4 harness | enforced localize→plan→edit→validate workflow | does process help? |
| C5 memory | repo memory (AGENTS.md, build recipes, ...) | does memory help? |
| C6 full-stack | all of the above | combined upper bound |

We measure both **functional correctness** (SWE-bench pass/fail) and
**non-functional patch quality** (locality, maintainability, test adequacy,
reviewability). The human reference ("gold") patch is used as a measuring
stick, not the main opponent — the main comparison is agent-vs-agent across
conditions.

## Status

Milestones **T0 + T1** (data contracts) and **T3 + T6** (workspace + mock
pipeline) are implemented:

- Typed data contracts (`se_support.schemas`) + JSON-schema export.
- Run-directory + JSONL logging conventions (`se_support.runner.run_dir`)
  designed so new metrics can be recomputed from raw logs **without re-running
  experiments**.
- Git-backed `Workspace`, deterministic `MockAgent`, offline evaluator, and a
  `PatchQualityCard` v0 builder wired into an end-to-end `run` command.
- Minimal CLI (`python -m se_support`).
- Unit + end-to-end tests with a fixture repo; `pytest` and `ruff` green.

Dataset importers (T2), gates (T5), support layers C1–C6 (T4) and real agent
adapters (mini-SWE-agent, Agentless) are stubbed for later tickets.

## Run the mock pipeline (no model needed)

```bash
# gold patch resolves the fixture task; empty/broken do not
python -m se_support run --task tests/fixtures/task_mini_repo.json \
  --mock-mode gold --condition C6_full_stack --experiment-id smoke
# -> resolved=True ... quality=Q3_engineering_acceptable
```

See [`docs/experiments/001_smoke_mock_pipeline.md`](docs/experiments/001_smoke_mock_pipeline.md).

## Quick start

```bash
# 1. Create the environment (conda)
conda env create -f environment.yml      # creates env "se-support"
conda activate se-support
pip install -e ".[dev]"                   # if not already installed

# 2. Verify
python -m se_support --help
pytest
ruff check .

# 3. Export JSON schemas from the Pydantic models (single source of truth)
python -m se_support schemas export --output schemas/
```

## Repository layout

See [`docs/FILE_INDEX.md`](docs/FILE_INDEX.md) for a file-by-file description.
Key directories:

```
src/se_support/      # the Python package
  schemas/           # data contracts (TaskSpec, RunSpec, EvalResult, ...)
  runner/            # run-directory layout + structured logging
schemas/             # exported *.schema.json (generated)
tests/               # unit tests + fixtures
docs/                # experiment protocol, run-dir spec, per-experiment logs
runs/                # experiment outputs (git-ignored except .gitkeep)
results/             # tables/figures/quality cards (git-ignored except .gitkeep)
```

## Documentation

- [`docs/FILE_INDEX.md`](docs/FILE_INDEX.md) — what every file/dir is for.
- [`docs/experiment_protocol.md`](docs/experiment_protocol.md) — datasets,
  agents, models, conditions, and metrics we actually use, plus rules.
- [`docs/run_directory_spec.md`](docs/run_directory_spec.md) — exact on-disk
  contract for each run (the basis for post-hoc metric recomputation).
- [`docs/experiments/`](docs/experiments/) — one file per experiment recording
  its **purpose, setup, results, and log locations**.
