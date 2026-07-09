# Project Proposal: SE-Support Study

**Working title:** *What Support Do Coding Agents Need? A Controlled Study of Context, Tests, Gates, Harnesses, and Memory in AI Software Engineering*  
**Short project name:** `se-support-study`  
**Target venues:** ICSE / FSE / ASE / MSR  
**Audience:** research team + Copilot CLI / coding agents implementing the infrastructure  
**Version:** v0.1  
**Date:** 2026-07-09

---

## 0. Executive Summary

This project studies why AI coding agents fail and what kinds of software-engineering support make them produce higher-quality code. The central claim is not simply that larger models improve coding performance. The claim is that coding-agent reliability depends on a **support stack**: structured repository context, executable tests, deterministic gates, controlled harnesses, repository memory, and review-like validation.

The project will build a reproducible experimental framework that runs repository-level software-engineering tasks under controlled support conditions. We will measure not only whether a patch passes benchmark tests, but also whether it is local, maintainable, reviewable, tested, and safe from obvious regressions.

The first implementation target is a pilot:

```text
50 SWE-bench Verified tasks
+ 20 SWE-Gym Lite tasks
× 2 core conditions: C0 Minimal vs C6 Full-stack
× 1 open agent scaffold
+ optional Copilot CLI ecological-validation runs
```

The full target is:

```text
100–150 tasks
× 7 support conditions
× 2 agent scaffolds
+ 50–100 Copilot CLI / Copilot coding-agent validation tasks
```

The expected paper contribution is fourfold:

1. A taxonomy of repository-level coding-agent failure modes and patch-quality gaps.
2. A controlled ablation study of support structures: context, tests, gates, harnesses, and memory.
3. A patch-quality evaluation framework beyond pass/fail resolution rate.
4. A simple support-aware baseline agent that is competitive in correctness and stronger in reviewability/maintainability.

---

## 1. Motivation

Current coding-agent evaluation is dominated by pass/fail resolution rate on benchmark tasks. This is necessary but insufficient. A patch that passes tests may still be too broad, brittle, poorly tested, architecturally inconsistent, hard to review, or subtly unsafe. In real software engineering, code quality depends on process and validation, not only on generation.

The core research bet is:

> Coding agents fail not only because the model is weak, but because the agent lacks structured software-engineering support.

This project asks which supports matter, how they interact, and whether they improve engineering quality beyond benchmark pass rate.

---

## 2. Background and Related Work

This section should be used to position the paper, not as an exhaustive literature review.

### 2.1 SWE-bench and SWE-bench Verified

SWE-bench evaluates whether an AI system can resolve real GitHub issues by generating patches against repository snapshots. SWE-bench Verified is a 500-instance human-filtered subset intended to make evaluation more reliable. It is the best primary comparability benchmark for this project.

Reference:
- SWE-bench Verified official page: https://www.swebench.com/verified.html
- OpenAI SWE-bench Verified announcement: https://openai.com/index/introducing-swe-bench-verified/
- HuggingFace dataset: https://huggingface.co/datasets/SWE-bench/SWE-bench_Verified

### 2.2 SWE-Gym

SWE-Gym contains 2,438 real-world Python software-engineering tasks, each with codebase, executable runtime, unit tests, and natural-language task description. It is suitable for pilot development, larger-scale experiments, and training/verifier extensions.

Reference:
- Paper: https://arxiv.org/html/2412.21139v2
- Repo: https://github.com/SWE-Gym/SWE-Gym

### 2.3 SWE-bench Live

SWE-bench Live is designed as a fresher, contamination-resistant benchmark. It contains issue-resolution tasks from real GitHub issues created since 2024 and provides Docker images for reproducible execution. Use it for external validation after the pilot.

Reference:
- Paper: https://arxiv.org/html/2505.23419v2
- Microsoft Research page: https://www.microsoft.com/en-us/research/publication/swe-bench-goes-live/
- Repo: https://github.com/microsoft/SWE-bench-Live

### 2.4 Agentless and SWE-agent

Agentless shows that a simple localization → repair → patch validation pipeline can be a strong baseline. SWE-agent shows that agent-computer interface design affects agent behavior and performance. This project differs by treating such supports as experimental factors and measuring both correctness and patch quality.

References:
- Agentless: https://arxiv.org/abs/2407.01489
- SWE-agent: https://arxiv.org/abs/2405.15793

### 2.5 SWT-Bench

SWT-Bench evaluates issue-reproduction test generation. Its fail-before/pass-after criterion is directly relevant to our generated-test support condition.

References:
- SWT-Bench official page: https://swtbench.com/
- Paper: https://arxiv.org/html/2406.12952v3

### 2.6 AIDev

AIDev provides large-scale real-world agentic pull request data from GitHub. It is not suitable for causal ablation, but it is useful for grounding the failure taxonomy and comparing agentic PRs with human PRs.

Reference:
- Paper: https://arxiv.org/html/2602.09185v1

### 2.7 GitHub Copilot CLI

Copilot CLI is a terminal-native coding assistant / agent that can plan, edit code, run tests, and interact with GitHub workflows. It should be used in two ways: as an implementation accelerator and, optionally, as a real-world coding-agent condition. Do not rely on Copilot CLI as the only experimental subject because model version, internal prompts, and logs may not be fully controlled.

References:
- Copilot CLI official overview: https://docs.github.com/en/copilot/how-tos/copilot-cli/use-copilot-cli/overview
- Copilot CLI product page: https://github.com/features/copilot/cli
- Copilot CLI best practices: https://docs.github.com/en/copilot/how-tos/copilot-cli/cli-best-practices

---

## 3. Research Questions

### RQ1: Failure and quality gaps

**RQ1. What failure modes and quality gaps distinguish AI-generated patches from human-written patches in repository-level software-engineering tasks?**

Operationalization:
- Compare AI patches from controlled runs with human reference patches and real-world human/agentic PR samples.
- Build a qualitative taxonomy of failures.
- Measure how often each failure occurs by agent, condition, task type, and pass/fail status.

Expected output:
- A coding-agent failure taxonomy.
- A patch-quality codebook.
- A small human-validated annotation dataset.

### RQ2: Correctness effects of support structures

**RQ2. Which support structures improve coding-agent success rates, and which failure modes do they reduce?**

Support factors:
- Context support.
- Test support.
- Gate support.
- Harness/process support.
- Memory/repository-instruction support.

Primary metrics:
- Patch applies.
- Build succeeds.
- FAIL_TO_PASS tests pass.
- PASS_TO_PASS tests remain passing.
- Full test suite pass rate where feasible.
- Resolution rate.

Expected output:
- Effect sizes for each support condition.
- Failure-mode reduction by support type.
- Interaction hypotheses for larger runs.

### RQ3: Code-quality effects beyond pass rate

**RQ3. Do support structures improve non-functional patch quality, such as maintainability, locality, security, test adequacy, and reviewability?**

Quality dimensions:
- Functional correctness.
- Regression safety.
- Locality/minimality.
- Maintainability.
- Architecture consistency.
- Reliability/security.
- Test adequacy.
- Reviewability.

Expected output:
- Patch Quality Card per run.
- Comparison of passing patches across support conditions.
- Evidence that pass rate alone misses important patch-quality variation.

### RQ4: General support-aware baseline

**RQ4. Can a simple support-aware baseline achieve competitive correctness while producing higher-quality and more reviewable patches?**

Baseline name options:
- `SE-Guarded Agent`
- `Support-Aware Agentless`
- `Guarded Coding Agent`
- `SE-Support Baseline`

Expected output:
- A reproducible baseline pipeline.
- Ablations showing which steps matter.
- Comparison against minimal agent, Agentless-style pipeline, SWE-agent/mini-SWE-agent, and optional Copilot CLI runs.

---

## 4. Hypotheses

### H1: Structured context helps localization more than raw long context.

Agents benefit from curated task-relevant context: repo map, symbols, relevant files, API examples, and build/test instructions. Blindly increasing context length may add distractors.

### H2: Reproduction tests improve correctness but can induce test overfitting.

Fail-before/pass-after generated tests should reduce incomplete fixes and brittle patches. However, low-quality generated tests may make the agent optimize for the wrong behavior.

### H3: Gates improve precision more than generation ability.

Lint, type checks, static analysis, security checks, and test gates may not make the agent generate better first patches. They should reduce the probability that bad patches are submitted.

### H4: Structured harnesses improve process quality.

A localization → plan → test → edit → validate workflow should reduce premature editing, irrelevant changes, and failed-test neglect.

### H5: Repository memory improves adaptation to project conventions.

Repo-specific instructions, build recipes, known fragile tests, coding conventions, and previous failed attempts should reduce repeated environment errors and style/architecture violations.

### H6: Full-stack support improves code quality beyond pass rate.

The strongest result would be that two conditions have similar resolution rate but different maintainability, test adequacy, and reviewability.

---

## 5. Datasets

### 5.1 Stage 1: Pilot dataset

Use:

```text
30–50 SWE-bench Verified tasks
20 SWE-Gym Lite tasks
```

Selection criteria:
- Python only.
- Reproducible local/Docker environment.
- Clear issue description.
- Non-trivial code change; exclude docs-only tasks.
- Exclude tasks whose environment setup repeatedly fails.
- Stratify by repository, gold patch size, number of files touched, and issue type.

Purpose:
- Validate infrastructure.
- Test logging and metrics.
- Build first failure taxonomy.
- Decide whether full experiment has signal.

### 5.2 Stage 2: Main ablation dataset

Use:

```text
100–150 SWE-bench Verified tasks
50–100 SWE-Gym Lite / SWE-Gym tasks
```

Purpose:
- Main causal ablation.
- Support-condition comparisons.
- Statistical modeling.

### 5.3 Stage 3: Freshness validation

Use:

```text
50–100 SWE-bench Live tasks
```

Purpose:
- Check whether results generalize to fresher, less contamination-prone tasks.

### 5.4 Stage 4: Real-world PR grounding

Use:

```text
AIDev curated subset
```

Purpose:
- Taxonomy grounding.
- Human-vs-agent PR structure comparison.
- Review-comment analysis.

Do not use AIDev for causal support ablation because support conditions are not controlled.

---

## 6. Support Conditions

The main experiment uses one-factor-at-a-time ablations plus a full-stack condition. This avoids the cost of a full factorial design while preserving causal interpretability.

| Condition | Context | Tests | Gates | Harness | Memory | Purpose |
|---|---|---|---|---|---|---|
| C0 Minimal | Low | Low | Low | Low | Low | Baseline |
| C1 +Context | High | Low | Low | Low | Low | Is structured context useful? |
| C2 +Tests | Low | High | Low | Low | Low | Are generated/repro tests useful? |
| C3 +Gates | Low | Low | High | Low | Low | Do deterministic checks improve patch acceptance quality? |
| C4 +Harness | Low | Low | Low | High | Low | Does structured process help? |
| C5 +Memory | Low | Low | Low | Low | High | Do repo instructions and memory help? |
| C6 Full-stack | High | High | High | High | High | Upper-bound combined support |

### 6.1 C0 Minimal

Agent receives:
- Issue description.
- Repository checkout.
- Basic shell/edit permissions.
- Official final evaluation only after patch generation.

Agent does not receive:
- Prebuilt repo map.
- Generated reproduction test.
- Special gates beyond final eval.
- Structured phase constraints.
- Repo memory or AGENTS.md.

### 6.2 C1 +Context

Add a structured context pack:

```text
context_pack.md
repo_card.md
symbol_map.json
relevant_files.json
api_usage_examples.md
build_and_test_notes.md
```

The context pack must not include the gold patch.

Context pack contents:
- Repository architecture summary.
- Test command hints inferred from repo files.
- Top-k relevant files/functions from lexical retrieval and symbol search.
- Similar API usage examples from the repository.
- Known conventions from config files.

### 6.3 C2 +Tests

Add test support:
- Generate a reproduction test from issue description.
- Run generated test on base commit.
- Prefer tests that fail-before and pass-after human/gold patch where available.
- Add generated tests to a separate experimental test directory.
- Use generated tests during patch validation.

Important:
- The official benchmark tests remain hidden from the agent where possible.
- Generated tests must be logged and evaluated for quality.
- If a generated test does not fail on base code, mark it as non-reproducing.

### 6.4 C3 +Gates

Add deterministic gates. Gate availability is repo-dependent.

Default Python gates:
- Patch applies cleanly.
- `python -m compileall` for syntax.
- Repo unit tests or selected tests.
- Full test suite when feasible.
- `ruff` if repo has config or if we use a conservative default.
- `mypy` or `pyright` only if repo has configuration.
- `bandit` or `semgrep` for security warnings, reported but not always blocking.
- Coverage for changed lines where feasible.

Gate output:

```json
{
  "gate_name": "pytest_selected",
  "command": "...",
  "exit_code": 0,
  "duration_sec": 12.3,
  "stdout_path": "...",
  "stderr_path": "...",
  "status": "pass"
}
```

Blocking policy:
- Syntax/build failures: blocking.
- Failing existing tests: blocking.
- Lint/type/security warnings: initially non-blocking but recorded; later ablate blocking vs advisory gates.

### 6.5 C4 +Harness

Use a structured workflow:

1. Read issue.
2. Localize relevant files/functions.
3. Write diagnosis.
4. Write test plan.
5. Edit code.
6. Run validation.
7. Revise at most N times.
8. Produce final patch and validation report.

Rules:
- No code edit before localization step is complete.
- No final answer without validation summary.
- If tests fail, agent must classify failure before making another edit.
- Limit irrelevant broad refactors.

### 6.6 C5 +Memory

Add repository-specific memory:

```text
AGENTS.md
repo_card.md
known_build_recipes.md
known_flaky_tests.md
coding_conventions.md
previous_failures.md
```

Memory types:
- Build/test recipes.
- Project layout.
- Style and naming conventions.
- Previous failed approaches on similar tasks.
- Common fragile modules.

Important:
- Memory should be generated from repository contents and previous experimental runs.
- Do not leak gold patches.
- Version and hash memory artifacts.

### 6.7 C6 Full-stack

Combine:
- Structured context.
- Generated tests.
- Deterministic gates.
- Structured harness.
- Repo memory.

This condition represents the proposed support-aware baseline.

---

## 7. Agent Scaffolds

### 7.1 Open controllable agent: required

Use at least one open, controllable scaffold for causal claims.

Candidates:
- Agentless-style pipeline.
- mini-SWE-agent.
- SWE-agent.
- OpenHands.

Implementation should define a common `AgentRunner` interface so agents can be swapped.

```python
class AgentRunner(Protocol):
    def run(self, task: TaskSpec, condition: SupportCondition, run_dir: Path) -> AgentRunResult:
        ...
```

### 7.2 Copilot CLI: optional but valuable

Use Copilot CLI in two ways:

1. **Implementation accelerator:** ask it to build infrastructure, tests, importers, metrics, and analysis scripts.
2. **Ecological validation subject:** run selected tasks using Copilot CLI or Copilot coding-agent workflow to test whether real industrial agents show similar support effects.

Important constraints:
- Do not rely on Copilot CLI for main causal claims unless logs and versioning are sufficient.
- Do not make PRs to upstream open-source repositories.
- Use private forks or local benchmark checkouts.
- Capture model/tool version, prompt, command transcript, patch, and validation logs whenever possible.
- Do not assume non-interactive CLI flags exist; implement a manual adapter first, then automate after verifying local CLI behavior.

---

## 8. Experimental Design

### 8.1 Pilot design

```text
50 tasks
× 2 conditions: C0 Minimal, C6 Full-stack
× 1 open agent
= 100 runs
```

Optional:

```text
20–50 tasks
× 2 Copilot conditions: default, full-stack instructions
= 40–100 Copilot runs
```

Pilot success criteria:
- At least 90% tasks can be set up reproducibly.
- Runner saves complete logs and patches.
- Evaluation can classify pass/fail.
- Patch Quality Card can be produced for at least 80% of runs.
- Qualitative codebook stabilizes after first 50–100 patch annotations.

### 8.2 Main design

```text
120 tasks
× 7 conditions
× 2 agent scaffolds
= 1,680 runs
```

If compute is constrained:

```text
100 tasks
× 7 conditions
× 1 agent
= 700 runs
```

Add second agent only for C0, C2, C4, C6.

### 8.3 Randomization and pairing

- Every task should appear in every condition for paired comparisons.
- Randomize run order to avoid temporal/model drift.
- Record model versions and date.
- If model versions change mid-study, treat version as a covariate or separate block.

### 8.4 Repetition

LLM runs are stochastic. Preferred:
- Pilot: 1 run per condition.
- Main: 2–3 seeds for key conditions C0, C2, C4, C6.
- Report pass@1 and pass@k-like metrics separately.

Do not mix repeated sampling with support effects without reporting sample counts.

---

## 9. Data Contracts

### 9.1 TaskSpec

Create `schemas/task_spec.schema.json` and corresponding Python dataclass/Pydantic model.

```json
{
  "task_id": "swebench__django__12345",
  "dataset": "swebench_verified",
  "repo": "django/django",
  "base_commit": "abc123",
  "issue_title": "...",
  "issue_body": "...",
  "test_command": "pytest ...",
  "setup_command": "...",
  "docker_image": "...",
  "gold_patch_path": "data/gold_patches/...diff",
  "fail_to_pass_tests": ["..."],
  "pass_to_pass_tests": ["..."],
  "metadata": {
    "language": "python",
    "gold_files_touched": 2,
    "gold_loc_changed": 35,
    "repo_group": "django"
  }
}
```

### 9.2 RunSpec

```json
{
  "run_id": "uuid",
  "task_id": "...",
  "agent": "agentless_style",
  "model": "...",
  "condition": "C2_tests",
  "seed": 0,
  "max_turns": 50,
  "max_wall_time_sec": 3600,
  "max_cost_usd": null,
  "created_at": "2026-07-09T00:00:00Z"
}
```

### 9.3 AgentRunResult

```json
{
  "run_id": "uuid",
  "status": "completed",
  "patch_path": "runs/.../final.patch",
  "transcript_path": "runs/.../transcript.jsonl",
  "commands_path": "runs/.../commands.jsonl",
  "support_artifacts_dir": "runs/.../support/",
  "final_message_path": "runs/.../final_message.md",
  "duration_sec": 1234.5,
  "error": null
}
```

### 9.4 EvalResult

```json
{
  "run_id": "uuid",
  "patch_applies": true,
  "build_success": true,
  "fail_to_pass_passed": 4,
  "fail_to_pass_total": 4,
  "pass_to_pass_passed": 122,
  "pass_to_pass_total": 122,
  "resolved": true,
  "full_tests_status": "pass",
  "gate_results_path": "runs/.../gate_results.json",
  "eval_log_path": "runs/.../eval.log"
}
```

### 9.5 PatchQualityCard

```json
{
  "run_id": "uuid",
  "task_id": "...",
  "resolved": true,
  "quality_level": "Q3_engineering_acceptable",
  "functional_correctness": {
    "patch_applies": true,
    "build_success": true,
    "official_resolved": true,
    "regression_failures": 0
  },
  "locality": {
    "files_touched": 2,
    "loc_added": 34,
    "loc_deleted": 12,
    "gold_file_overlap": 0.5,
    "unrelated_file_change_suspected": false
  },
  "maintainability": {
    "complexity_delta": 1,
    "duplication_delta": 0,
    "lint_new_warnings": 0,
    "type_new_warnings": 0
  },
  "security_reliability": {
    "new_security_warnings": 0,
    "error_handling_concern": false,
    "resource_cleanup_concern": false
  },
  "test_adequacy": {
    "tests_added": 1,
    "repro_test_fail_before": true,
    "repro_test_pass_after": true,
    "changed_line_coverage_delta": 0.12
  },
  "reviewability": {
    "has_validation_report": true,
    "description_diff_consistent": true,
    "human_rating": null
  },
  "failure_modes": [],
  "notes": ""
}
```

---

## 10. Code Quality Definition

### 10.1 Definition

Patch-level code quality is the degree to which a patch:

1. Correctly resolves the issue.
2. Preserves existing behavior.
3. Minimizes unnecessary changes.
4. Fits the architecture and abstractions of the repository.
5. Is maintainable and readable.
6. Avoids obvious reliability/security problems.
7. Includes or is supported by adequate tests.
8. Is reviewable by a human maintainer.

### 10.2 Quality levels

| Level | Name | Definition |
|---|---|---|
| Q0 | Invalid patch | Does not apply, does not build, or has syntax/runtime setup failure. |
| Q1 | Plausible but failing | Looks relevant but does not pass target evaluation. |
| Q2 | Functionally correct | Passes official target tests and preserves existing tests, but quality unknown or weak. |
| Q3 | Engineering acceptable | Correct, local, no obvious maintainability/security problems. |
| Q4 | Review-ready | Correct, well-tested, documented/validated, consistent with repo style and architecture. |
| Q5 | Human-quality or better | Comparable to or better than human patch in simplicity, robustness, and validation. |

### 10.3 Automated metrics

Correctness:
- Patch applies.
- Build/syntax success.
- FAIL_TO_PASS success.
- PASS_TO_PASS preservation.
- Full test suite status.

Locality:
- Files touched.
- Functions/classes touched.
- Lines added/deleted.
- Diff size.
- Overlap with human patch files/functions.
- Unrelated file changes.

Maintainability:
- Cyclomatic complexity delta.
- Function length delta.
- Duplication delta.
- Lint warnings delta.
- Type-check warnings delta.
- Dead code / unreachable code indicators.

Architecture consistency:
- New dependency edges.
- Cross-layer imports.
- Public API changes without caller/test updates.
- Copy-pasted logic instead of reuse.

Security/reliability:
- Static security warnings.
- Missing input validation.
- Exception swallowing.
- Resource cleanup issues.
- Concurrency/async misuse.

Test adequacy:
- Tests added.
- Test files touched.
- Generated test fail-before/pass-after.
- Coverage of changed lines.
- Mutation-lite score where feasible.

Reviewability:
- Final validation summary exists.
- Patch explanation matches diff.
- Reviewer Likert score.
- Human intervention required.

---

## 11. Failure Taxonomy

Initial codebook:

| Code | Failure mode | Description |
|---|---|---|
| F01 | Requirement misunderstanding | Misread issue or solved a different problem. |
| F02 | Fault localization failure | Edited wrong file/function or missed true fault location. |
| F03 | Incomplete fix | Handles main case but misses edge cases. |
| F04 | Brittle/test-overfit fix | Hard-coded or overly specific to visible tests. |
| F05 | Over-broad patch | Unnecessary refactor or unrelated changes. |
| F06 | API/protocol misuse | Misuses internal API, lifecycle, async/concurrency, or error semantics. |
| F07 | Architecture violation | Breaks abstraction, layering, or dependency direction. |
| F08 | Regression introduction | Breaks existing behavior. |
| F09 | Missing/inadequate validation | No useful tests or no fail-before/pass-after evidence. |
| F10 | Low maintainability | Duplicate code, complexity increase, poor naming/style. |
| F11 | Security/reliability issue | Input validation, auth, resource, exception, or safety issue. |
| F12 | Process failure | Premature edit, ignores test failure, loops, or stops too early. |
| F13 | Environment/tool failure | Build/test environment misused or not reproducible. |
| F14 | Explanation mismatch | Final explanation does not match actual patch. |

Annotation fields:

```json
{
  "patch_id": "...",
  "annotator": "...",
  "main_failure_mode": "F02",
  "secondary_failure_modes": ["F09", "F12"],
  "quality_level": "Q1",
  "would_reviewer_reject": true,
  "reviewer_reject_reason": "Edited parser but issue is in serializer validation.",
  "severity": "high",
  "confidence": 4,
  "notes": "..."
}
```

Annotation protocol:
- Two annotators independently label an initial 50-patch calibration set.
- Resolve disagreements and update codebook.
- Compute agreement on main failure mode and quality level.
- Target agreement: Cohen's kappa or Krippendorff's alpha reported, not necessarily optimized artificially.
- Annotate 200–300 patches for paper-quality analysis.

---

## 12. System Architecture

Recommended repository layout:

```text
se-support-study/
  README.md
  PROJECT_PROPOSAL.md
  pyproject.toml
  Makefile
  .gitignore

  configs/
    default.yaml
    agents/
      agentless_style.yaml
      mini_swe_agent.yaml
      copilot_cli_manual.yaml
    conditions/
      C0_minimal.yaml
      C1_context.yaml
      C2_tests.yaml
      C3_gates.yaml
      C4_harness.yaml
      C5_memory.yaml
      C6_full_stack.yaml

  schemas/
    task_spec.schema.json
    run_spec.schema.json
    eval_result.schema.json
    patch_quality_card.schema.json
    annotation.schema.json

  src/se_support/
    __init__.py
    cli.py
    config.py
    logging.py

    datasets/
      __init__.py
      swebench_importer.py
      swegym_importer.py
      swebench_live_importer.py
      task_filter.py
      task_sampler.py

    agents/
      __init__.py
      base.py
      agentless_style.py
      mini_swe_agent_adapter.py
      swe_agent_adapter.py
      copilot_cli_adapter.py
      mock_agent.py

    support/
      __init__.py
      context_pack.py
      repo_card.py
      retrieval.py
      test_generation.py
      gates.py
      harness.py
      memory.py
      prompts.py

    runner/
      __init__.py
      workspace.py
      executor.py
      run_manager.py
      patch_utils.py
      docker_utils.py
      command_logger.py

    evaluation/
      __init__.py
      swebench_eval.py
      generic_eval.py
      gate_eval.py
      test_result_parser.py

    quality/
      __init__.py
      patch_quality_card.py
      diff_metrics.py
      complexity_metrics.py
      lint_metrics.py
      type_metrics.py
      security_metrics.py
      coverage_metrics.py
      reviewability.py
      gold_overlap.py

    annotation/
      __init__.py
      sample_patches.py
      export_for_labeling.py
      agreement.py

    analysis/
      __init__.py
      aggregate_runs.py
      stats_models.py
      plots.py
      tables.py

  scripts/
    import_swebench_verified.py
    run_pilot.py
    run_condition.py
    evaluate_runs.py
    compute_quality_cards.py
    export_annotation_sample.py
    analyze_pilot.py

  data/
    raw/
    tasks/
    gold_patches/
    support_artifacts/

  runs/
    .gitkeep

  results/
    tables/
    figures/
    quality_cards/
    annotations/

  docs/
    codebook.md
    experiment_protocol.md
    copilot_cli_protocol.md
    paper_outline.md

  tests/
    unit/
    integration/
    fixtures/
```

---

## 13. CLI Design

Use a single project CLI:

```bash
python -m se_support --help
```

Required subcommands:

```bash
# Import tasks
python -m se_support import swebench-verified \
  --output data/tasks/swebench_verified.jsonl \
  --limit 50

# Sample pilot tasks
python -m se_support sample \
  --input data/tasks/swebench_verified.jsonl \
  --output data/tasks/pilot_50.jsonl \
  --strategy stratified \
  --n 50

# Prepare support artifacts
python -m se_support prepare-support \
  --tasks data/tasks/pilot_50.jsonl \
  --condition C1_context \
  --output data/support_artifacts/C1_context

# Run an experiment
python -m se_support run \
  --tasks data/tasks/pilot_50.jsonl \
  --agent agentless_style \
  --condition C0_minimal \
  --output runs/pilot_C0_agentless \
  --max-workers 4

# Evaluate patches
python -m se_support evaluate \
  --runs runs/pilot_C0_agentless \
  --output results/eval/pilot_C0_agentless.jsonl

# Compute patch quality cards
python -m se_support quality \
  --runs runs/pilot_C0_agentless \
  --eval results/eval/pilot_C0_agentless.jsonl \
  --output results/quality_cards/pilot_C0_agentless.jsonl

# Export annotation sample
python -m se_support export-annotations \
  --quality-cards results/quality_cards/*.jsonl \
  --n 100 \
  --output results/annotations/sample_100.jsonl

# Analyze pilot
python -m se_support analyze \
  --eval results/eval/*.jsonl \
  --quality results/quality_cards/*.jsonl \
  --output results/tables
```

---

## 14. Implementation Tickets for Copilot CLI

### Ticket T0: Initialize repository

Goal:
- Create Python package with `pyproject.toml`, CLI entry point, tests, lint config, and basic docs.

Acceptance criteria:
- `python -m se_support --help` works.
- `pytest` passes.
- `ruff check .` passes or is configured.
- CI workflow exists for unit tests.

### Ticket T1: Define schemas and data models

Goal:
- Implement TaskSpec, RunSpec, AgentRunResult, EvalResult, PatchQualityCard.

Acceptance criteria:
- JSON schemas exist.
- Pydantic/dataclass models validate fixtures.
- Unit tests cover valid and invalid examples.

### Ticket T2: Implement task importer skeleton

Goal:
- Implement importers for SWE-bench Verified and SWE-Gym Lite.

Acceptance criteria:
- Importer produces JSONL TaskSpec records.
- Importer can run in dry-run mode without downloading huge assets.
- Unit tests use small fixtures.

### Ticket T3: Implement workspace and patch utilities

Goal:
- Create isolated workspace per run.
- Checkout base repo snapshot or use placeholder fixture in tests.
- Apply and reverse patches.
- Compute diff metrics.

Acceptance criteria:
- Can create run workspace.
- Can apply a sample patch.
- Can collect final diff.
- Logs all commands.

### Ticket T4: Implement support-condition system

Goal:
- Represent C0–C6 as configuration objects.
- Generate support artifacts depending on condition.

Acceptance criteria:
- `prepare-support` produces condition-specific artifact directory.
- C0 produces no extra artifacts except metadata.
- C1 produces context-pack placeholders at minimum.
- C5 produces AGENTS.md/repo memory placeholders at minimum.

### Ticket T5: Implement gates

Goal:
- Implement deterministic gate runner.

Acceptance criteria:
- Can run syntax gate on Python project.
- Can run configured test command.
- Can record stdout/stderr/exit code/duration.
- Can mark blocking vs advisory gates.

### Ticket T6: Implement mock agent and manual agent adapter

Goal:
- Implement a mock agent for integration tests and a manual adapter for human/Copilot CLI runs.

Acceptance criteria:
- Mock agent writes a known patch.
- Manual adapter can pause and ask user to provide patch path.
- Run manager treats both as AgentRunner implementations.

### Ticket T7: Implement agentless-style baseline skeleton

Goal:
- Implement a simple localization → repair → validation structure.

Acceptance criteria:
- Localizer can retrieve files using lexical search.
- Repair step can be stubbed or call a pluggable LLM provider.
- Validation step runs gates.
- All prompts and outputs are logged.

### Ticket T8: Implement quality metrics v1

Goal:
- Produce PatchQualityCard with automated metrics.

Acceptance criteria:
- Computes LOC added/deleted, files touched, patch applies.
- Computes gold file overlap if gold patch is available.
- Runs optional lint/type/security tools if installed; otherwise records unavailable.
- Outputs valid PatchQualityCard JSONL.

### Ticket T9: Implement annotation export

Goal:
- Sample patches for qualitative labeling.

Acceptance criteria:
- Exports patch diff, issue text, evaluation result, quality card, and annotation fields.
- Supports stratified sampling by pass/fail and condition.

### Ticket T10: Implement analysis scripts

Goal:
- Aggregate run results and produce pilot tables.

Acceptance criteria:
- Table: resolution rate by condition.
- Table: gate failures by condition.
- Table: patch size/locality by condition.
- Basic bootstrap confidence intervals.

---

## 15. Copilot CLI Work Protocol

Use Copilot CLI as a careful engineering assistant. Each Copilot session should follow this protocol:

1. Read `PROJECT_PROPOSAL.md`.
2. Work on one ticket at a time.
3. Before editing, produce a short plan.
4. Keep changes minimal and testable.
5. Add or update tests for every new module.
6. Run local tests before finishing.
7. Summarize changed files, commands run, and remaining risks.
8. Do not change experiment definitions without explicit approval.
9. Do not add external services or paid APIs unless requested.
10. Do not push to public upstream repositories.

Recommended first Copilot CLI task:

```text
Read PROJECT_PROPOSAL.md. Implement Ticket T0 and T1 only.
Create a Python package named se_support with a working CLI,
Pydantic models for TaskSpec, RunSpec, AgentRunResult, EvalResult,
and PatchQualityCard, JSON schema export, fixtures, and unit tests.
Do not implement dataset downloads yet. Keep the code minimal and clean.
Run pytest and ruff before summarizing.
```

---

## 16. Evaluation Procedure

For each run:

1. Create workspace.
2. Checkout base commit or load benchmark Docker image.
3. Generate support artifacts based on condition.
4. Run agent.
5. Save transcript, commands, patch, support artifacts.
6. Apply final patch to clean checkout.
7. Run official evaluator.
8. Run deterministic gates.
9. Compute quality metrics.
10. Produce Patch Quality Card.
11. Archive all logs.

Run directory format:

```text
runs/{experiment_id}/{run_id}/
  task.json
  run_spec.json
  condition.yaml
  support/
  workspace_snapshot_info.json
  transcript.jsonl
  commands.jsonl
  final.patch
  final_message.md
  eval_result.json
  gate_results.json
  quality_card.json
  logs/
```

---

## 17. Statistical Analysis Plan

### 17.1 Correctness analysis

Primary model:

```text
resolved ~ context + tests + gates + harness + memory + agent + model + (1 | task) + (1 | repo)
```

If sample size is small, use paired comparisons instead:
- C0 vs C1.
- C0 vs C2.
- C0 vs C3.
- C0 vs C4.
- C0 vs C5.
- C0 vs C6.

Report:
- Absolute resolution-rate gain.
- Odds ratio where applicable.
- Bootstrap confidence intervals.
- McNemar test for paired binary outcomes.

### 17.2 Quality analysis

For continuous metrics:

```text
metric_delta ~ condition + resolved + patch_size + agent + (1 | task) + (1 | repo)
```

For ordinal quality levels:

```text
quality_level ~ condition + agent + resolved + (1 | task)
```

Report:
- Median and interquartile range.
- Bootstrap confidence intervals.
- Passing-patch-only analysis.
- All-patch analysis.

### 17.3 Failure-mode analysis

For each failure mode:

```text
failure_mode_present ~ condition + agent + task_difficulty + (1 | repo)
```

Report:
- Failure-mode prevalence by condition.
- Top failure modes for failed vs passing-but-low-quality patches.
- Which support condition most reduces each failure mode.

### 17.4 Multiple comparisons

Use Holm-Bonferroni or Benjamini-Hochberg correction for families of tests. Emphasize effect sizes over p-values.

---

## 18. Threats to Validity

### Internal validity

Risk:
- Conditions may accidentally differ in multiple ways.

Mitigation:
- Define C0–C6 strictly.
- Version and hash prompts/support artifacts.
- Keep one-factor conditions isolated.

### Construct validity

Risk:
- Code quality is hard to measure.

Mitigation:
- Use multiple metrics.
- Separate correctness from maintainability/reviewability.
- Use human annotation for architecture/reviewability.

### External validity

Risk:
- SWE-bench/SWE-Gym are Python-heavy and benchmark-specific.

Mitigation:
- Add SWE-bench Live validation.
- Add AIDev real-world PR grounding.
- Later add Java/JS tasks if needed.

### Contamination

Risk:
- Public benchmarks may appear in model training.

Mitigation:
- Use SWE-bench Live for freshness.
- Report dates, model versions, and benchmark versions.
- Avoid overclaiming from static datasets alone.

### Reproducibility

Risk:
- Proprietary models and Copilot CLI behavior may change.

Mitigation:
- Use open scaffold for main causal claims.
- Log model/tool version and full prompts.
- Treat Copilot CLI as ecological validation rather than sole evidence.

---

## 19. Milestones

### Week 1: Infrastructure skeleton

Deliverables:
- Repo skeleton.
- Schemas and data models.
- CLI skeleton.
- Mock agent.
- Gate runner v0.
- Unit tests.

### Week 2: Dataset and runner pilot

Deliverables:
- SWE-bench Verified importer.
- SWE-Gym Lite importer or placeholder.
- Workspace manager.
- Patch apply/evaluation skeleton.
- 5–10 toy/fixture runs.

### Week 3: Support conditions v1

Deliverables:
- C0, C1, C3, C5 implemented.
- Context pack generator v1.
- Repo card generator v1.
- AGENTS.md/memory generator v1.

### Week 4: Tests and harness support

Deliverables:
- C2 generated-test pipeline v1.
- C4 structured harness v1.
- C6 full-stack condition.
- End-to-end runs on 10 real tasks.

### Week 5: Pilot run

Deliverables:
- 50-task pilot C0 vs C6.
- Evaluation results.
- Patch Quality Cards.
- Initial analysis tables.

### Week 6: Qualitative codebook

Deliverables:
- 80–100 patch annotation sample.
- Codebook v1.
- Inter-annotator calibration.

### Weeks 7–8: Full ablation expansion

Deliverables:
- 100–150 task main run.
- C0–C6 condition results.
- Quality metrics v2.

### Weeks 9–10: Copilot and external validation

Deliverables:
- Copilot CLI protocol.
- 50-task Copilot validation if feasible.
- SWE-bench Live sample if feasible.

### Weeks 11–12: Paper analysis package

Deliverables:
- Tables and figures.
- Failure taxonomy results.
- Baseline comparison.
- Paper outline and first draft.

---

## 20. Initial Paper Outline

### Title

*What Support Do Coding Agents Need? A Controlled Study of Context, Tests, Gates, Harnesses, and Memory in AI Software Engineering*

### Abstract draft

AI coding agents are increasingly evaluated by whether they can resolve repository-level GitHub issues, but passing benchmark tests is not equivalent to producing maintainable, reviewable software. This paper studies coding-agent reliability as a software-engineering support problem. We define a support stack consisting of structured context, reproduction tests, deterministic gates, structured harnesses, and repository memory. Across repository-level tasks from SWE-bench Verified and SWE-Gym, we systematically ablate these supports and measure both functional correctness and patch quality. We further develop a taxonomy of coding-agent failure modes and introduce a support-aware baseline that combines localization, context construction, test generation, patch generation, validation gates, and review-style reporting. Our results show which supports improve resolution rate, which reduce specific failure modes, and which improve engineering quality beyond pass/fail evaluation.

### Sections

1. Introduction.
2. Background and related work.
3. Support-stack framework.
4. Experimental design.
5. Patch-quality framework.
6. RQ1 failure taxonomy.
7. RQ2 correctness ablation.
8. RQ3 quality analysis.
9. RQ4 support-aware baseline.
10. Discussion.
11. Threats to validity.
12. Conclusion.

---

## 21. Immediate Next Step

Start with Ticket T0 and T1 only. Do not attempt the full experiment immediately.

The first successful commit should contain:

```text
README.md
PROJECT_PROPOSAL.md
pyproject.toml
src/se_support/
  __init__.py
  cli.py
  schemas.py
schemas/
  task_spec.schema.json
  run_spec.schema.json
  eval_result.schema.json
  patch_quality_card.schema.json
tests/
  test_schemas.py
  fixtures/
```

First command target:

```bash
pytest
python -m se_support --help
python -m se_support schemas export --output schemas/
```

First Copilot CLI instruction:

```text
Read PROJECT_PROPOSAL.md. Implement only Ticket T0 and T1.
Keep the code minimal. Create typed data models, JSON schemas, a basic CLI,
fixtures, and unit tests. Do not implement dataset downloads or real agent calls yet.
Run pytest and report the result.
```

---

## 22. Non-goals for v0

Do not implement in v0:
- Full SWE-bench Docker evaluation.
- Full Copilot CLI automation.
- Real LLM API integrations.
- A web annotation UI.
- Multi-language support.
- Public PR automation.
- Full factorial ablation.

These are later-stage extensions.

---

## 23. Definition of Done for Pilot

The pilot is done when:

1. At least 50 real tasks are imported.
2. C0 and C6 can be run end-to-end with one open agent or mock-to-real agent bridge.
3. Every run produces patch, transcript, command log, eval result, and quality card.
4. Resolution-rate table is generated.
5. Patch-quality table is generated.
6. At least 80 patches are sampled for annotation.
7. Failure taxonomy v1 is produced.
8. The team can decide whether to expand to full C0–C6 ablation.

---

## 24. Key Design Principle

Do not build a benchmark-only system. Build a system that explains coding-agent behavior.

The paper should not merely say:

> Full-stack support gets higher pass rate.

It should say:

> Different software-engineering supports address different agent failure modes. Tests help agents reproduce bugs, gates prevent bad patches from being submitted, structured harnesses reduce process failures, context improves localization, and memory helps repository adaptation. Together, they shift coding agents from plausible code generation toward reviewable software contribution.

