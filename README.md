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

Implemented so far:

- **T0/T1** — typed data contracts (`se_support.schemas`) + JSON-schema export.
- **T3/T6** — git-backed `Workspace`, `MockAgent`, offline evaluator, quality
  card v0, wired into an end-to-end `run` command.
- **T4 (v1)** — `SupportCondition` system (C0–C6) toggling
  context/tests/gates/harness/memory via prompt injection + loop hooks.
- **Controllable `LLMAgent`** — a model-agnostic bash-loop agent that runs
  against any OpenAI-compatible endpoint (local vLLM now, pinned API later),
  validated end-to-end on a local RTX 4090 with Qwen2.5-Coder-7B.
- **T2** — SWE-bench Verified importer (real dataset → TaskSpec JSONL) + task
  sampler; verified against the real 500-task dataset.
- Run-directory + JSONL logging so metrics can be recomputed from raw logs
  **without re-running experiments**.
- Unit + end-to-end tests (offline, no GPU); `pytest` and `ruff` green.

Docker-based official evaluation for real SWE-bench tasks and a mini-SWE-agent
adapter are the next steps.

## Import real tasks

```bash
pip install -e ".[data]"                       # brings in huggingface `datasets`
python -m se_support import swebench-verified \
  --output data/tasks/swebench_verified.jsonl --limit 50
python -m se_support sample -i data/tasks/swebench_verified.jsonl \
  -o data/tasks/pilot_50.jsonl --n 50 --strategy stratified
```

## Run the pipeline

```bash
# Mock (no model needed): gold resolves, empty/broken do not
python -m se_support run --task tests/fixtures/task_mini_repo.json \
  --mock-mode gold --condition C6_full_stack

# Real LLM against a local vLLM server (env: vllm)
#   CUDA_VISIBLE_DEVICES=0 python -m vllm.entrypoints.openai.api_server \
#     --model Qwen/Qwen2.5-Coder-7B-Instruct --max-model-len 8192 --port 8000
python -m se_support run --task tests/fixtures/task_mini_repo.json \
  --agent llm --model Qwen/Qwen2.5-Coder-7B-Instruct \
  --base-url http://localhost:8000/v1 --condition C6_full_stack --max-turns 15
```

See [`docs/experiments/`](docs/experiments/) for logged runs (001 mock, 002 real 4090).

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
