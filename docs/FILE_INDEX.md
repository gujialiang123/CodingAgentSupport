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
| `workspace.py` | `Workspace`: git-backed checkout (`from_template` for fixtures, `from_git` for real repos); apply/reverse patches, final diff, run pytest. |
| `patch_utils.py` | Unified-diff parsing → `DiffMetrics` (files_touched, loc_added/deleted) + changed files. |
| `run_manager.py` | `run_single`: orchestrates one (task, agent, condition) run end-to-end. |

### `src/se_support/agents/` — agent scaffolds

| Path | Purpose |
|---|---|
| `base.py` | `AgentRunner` protocol (swappable scaffolds, proposal §7.1). |
| `mock_agent.py` | `MockAgent`: deterministic, no-LLM agent (gold/empty/broken/patch) for pipeline validation. |
| `chat_client.py` | `ChatClient` protocol; `OpenAIChatClient` (vLLM/API) + `ScriptedChatClient` (offline tests). |
| `llm_agent.py` | `LLMAgent`: controllable bash-loop agent; model-agnostic; condition-aware (gates hook). |

### `src/se_support/isolation/` — provenance firewall & sandbox (EP-01)

| Path | Purpose |
|---|---|
| `policy.py` | `SandboxPolicy` (network-off, fs-confined by default); `confirmatory()` vs `open()`. |
| `sandbox.py` | `build_sandbox_argv`: wrap agent commands with bubblewrap (`--unshare-net`, fs-confined) or `unshare` fallback. |
| `scrub.py` | `scrub_git_history` (flatten to base commit, drop remotes/reflogs/future objects); `scrubbed_task_dict` (drop gold/official-test fields). |
| `manifest.py` | `VisibleInputManifest` + artifact hashing: record and hash every agent-visible input. |

### `src/se_support/support/` — support conditions (T4)

| Path | Purpose |
|---|---|
| `condition.py` | `SupportCondition` + `CONDITIONS` (C0–C6) toggling context/tests/gates/harness/memory. |
| `bundle.py` | `SupportBundle`/`build_bundle` (EP-02): frozen, hashed, validated support artifacts generated before the agent runs; C0 empty, C6 = union of C1–C5, C2 tests marked `declared_unimplemented`. |
| `harness.py` | `HarnessStateMachine` (EP-04): enforced C4 workflow DISCOVER→DIAGNOSE→PATCH→VALIDATE→SUBMIT; edit permission by state, required records, transition/rejection logging. |
| `gate_policy.py` | Frozen C3 gate policy (EP-07): versioned blocking/advisory gates, base-vs-patch advisory delta (legacy warnings excluded), revision budget; official tests never a gate. |
| `gates.py` | Low-level gate runners (compileall blocking; ruff/bandit advisory). |

### `src/se_support/support/repro_tests/` — C2 reproduction tests (EP-03)

| Path | Purpose |
|---|---|
| `schema.py` | `HelperTestArtifact`, `ReproTestClass` (T0–T4), `ReproTestResults` (B/J/H/A/S separation). |
| `generator.py` | K=3 blind candidate generator (issue-only prompt; model-agnostic via ChatClient). |
| `validator.py` | Run a candidate on base/gold workspaces; classify T0–T4. |
| `provenance.py` | Assertion-literal traceability to the issue; suspicious/forbidden-literal audit. |
| `audit.py` | Run the hidden semantic-audit (S) test to catch hard-coded solutions. |
| `injector.py` | Freeze (hash) + read-only reconstruct of the helper so agent edits can't alter eval. |
| `__init__.py` | `build_helper_test` orchestrator: generate → gold-blind select → freeze → classify → audit. |
| `prompts.py` | `build_system_prompt`: base prompt + condition-driven additions, sourced from the frozen bundle when present. |
| `context_pack.py` | C1 context generator (repo file map + test hints), lexical/leak-free. |
| `memory.py` | C5 repo-memory generator (AGENTS.md-style, from repo contents). |
| `gates.py` | C3 deterministic gates (compileall blocking; ruff/bandit advisory). |

### `src/se_support/datasets/` — importers & sampling (T2)

| Path | Purpose |
|---|---|
| `swebench_importer.py` | SWE-bench Verified → TaskSpec JSONL; pure record mapping (tested offline) + optional `datasets` download. |
| `task_sampler.py` | `sample_tasks` (head / stratified-by-repo, seeded) + load/write JSONL. |

### `src/se_support/evaluation/` — correctness scoring

| Path | Purpose |
|---|---|
| `local_eval.py` | `evaluate_patch`: offline evaluator (apply patch, compileall, run F2P/P2P) → `EvalResult`. |
| `swebench_eval.py` | `evaluate_with_docker`: official SWE-bench Docker harness wrapper (authoritative F2P/P2P) → `EvalResult`. |

### `src/se_support/quality/` — patch quality cards

| Path | Purpose |
|---|---|
| `quality_card.py` | `build_card` / `recompute_card_from_run_dir` (EP-08): correctness + locality + process metrics; Q-levels capped at Q2 automatically (Q3+ needs human review). |
| `trajectory.py` | Extract process/trajectory metrics (turns, commands, gate failures, harness rejections, stop reason) offline from run logs. |

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
| `test_importer.py` | SWE-bench importer + sampler on a SWE-bench-shaped fixture (offline, no download). |
| `test_swebench_eval.py` | SWE-bench Docker evaluator's pure helpers (report parsing, predictions) offline. |
| `test_isolation.py` | EP-01 red-team: provenance scrub, git-history flatten, bwrap fs/network confinement, manifest. |
| `test_bundle.py` | EP-02 frozen SupportBundle: C0 empty, C6=union hashes, validation, determinism. |
| `test_harness.py` | EP-04 enforced C4: state machine + agent edit-revert / submit-gating enforcement. |
| `test_gate_policy.py` | EP-07 frozen C3 gate policy: blocking pass/fail, advisory base-vs-patch delta, no official tests as gates. |
| `test_quality_card.py` | EP-08 quality card v1: Q-level caps, process metrics, offline recompute. |
| `test_repro_tests.py` | EP-03 C2 pipeline: fail-before/pass-after, no official literal, semantic audit catches hard-code, frozen read-only, T0–T4. |
| `fixtures/repro_demo/` | Runnable synthetic repo (base bug + gold + hardcoded-bad + helper + semantic audit) for EP-03. |
| `fixtures/astropy__astropy-13033/` | Canonical C2 reference fixture (problem statement, helper, semantic audit, expected results). |
| `fixtures/swebench_sample.jsonl` | Two SWE-bench-shaped raw records for importer tests. |
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
