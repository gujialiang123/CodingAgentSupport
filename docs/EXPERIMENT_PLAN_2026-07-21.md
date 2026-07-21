# CodingAgentSupport — Experimental Execution Plan

**Document status:** Proposed protocol v1.0  
**Repository:** `gujialiang123/CodingAgentSupport`  
**Repository baseline reviewed:** `main` at `73c5266`, after Experiment 004 (`pilot01`)  
**Date:** 2026-07-21  
**Intended location in the repository:** `docs/EXPERIMENT_PLAN_2026-07-21.md`

---

## 0. Executive decision

The repository has already demonstrated the complete mechanical path from a real SWE-bench task to an agent patch and official Docker evaluation. It is therefore past the “can the pipeline run?” stage. It is **not yet ready for the 50-task or 120-task research runs**, because several experimental constructs are still weak or absent:

- C1 currently provides a weak repository inventory rather than task-relevant context.
- C2 reproduction-test support is not implemented.
- C3 has a usable first implementation, but its gate policy and feedback/revision semantics need to be frozen.
- C4 is primarily a prompt instruction rather than a runner-enforced workflow.
- C5 is generic and overlaps with ordinary environment information.
- The quality card is sufficient for plumbing, but not for claims about maintainability, test adequacy, or reviewability.

The next research milestone should therefore be a **construct-hardening milestone**, followed by a small C2 × C3 micro-study, and only then the full C0–C6 pilot.

The recommended sequence is:

1. Prove information isolation and artifact provenance.
2. Implement a frozen support-artifact interface.
3. Implement and validate C2 using a canonical SWE-bench example.
4. Turn C4 into an enforced state machine.
5. Strengthen C1, C3, C5, trajectory logging, and quality metrics.
6. Run a 20-task C2 × C3 micro-study.
7. Run a 50-task C0–C6 pilot.
8. Freeze the protocol and run a 120-task main study.
9. Freeze a cost-effective support-aware baseline and evaluate it on a held-out set.

No paper-level result should be claimed from the existing two-task pilot. Its value is that it validates the engineering path and exposes useful failure modes.

---

## 1. Current repository state

### 1.1 What is already usable

The following components should be retained and extended rather than rewritten:

- Typed task, run, evaluation, and quality-card schemas.
- SWE-bench Verified importer and task sampler.
- Git-backed task workspace creation.
- A controllable bash-loop `LLMAgent` against an OpenAI-compatible endpoint.
- `SupportCondition` definitions for C0–C6.
- Official SWE-bench Docker evaluation.
- Per-run transcripts, commands, patches, evaluation results, and quality-card logging.
- Mock and local-model smoke-test paths.
- Experiment documentation convention under `docs/experiments/`.

### 1.2 What Experiment 004 established

Experiment 004 ran two real `psf/requests` SWE-bench Verified tasks under C0 and the current C6 using Qwen2.5-Coder-7B. C0 produced no usable patch on either task, while C6 produced applying patches and resolved one task. This establishes:

- the real task → agent → patch → Docker judge path works;
- support conditions can alter agent behavior;
- trajectory logs contain interpretable failures;
- the current local 7B model is useful for plumbing but too weak for substantive conclusions;
- the current C6 is not the intended full treatment because C2 is absent and C1/C4/C5 are weak.

### 1.3 Protocol change introduced by this document

The existing protocol moves from a 10-task smoke directly to a 50-task C0-vs-C6 pilot. This plan inserts two prerequisites:

- **Construct readiness:** every condition must pass a manipulation check.
- **C2 × C3 micro-study:** test support and gate support must first be separated experimentally.

This avoids spending a large run budget on conditions whose meanings are still unstable.

---

## 2. Research objective and RQs

### 2.1 Core objective

Hold the coding-agent scaffold and model fixed, intervene on software-engineering support, and estimate how each support structure changes:

1. functional correctness;
2. regression risk;
3. patch quality beyond benchmark pass/fail;
4. agent process and failure modes;
5. cost and efficiency.

### 2.2 Research questions

#### RQ1 — Failure and quality differences

**What failure modes and quality gaps characterize coding-agent patches, and how do they differ across support conditions and from human reference patches?**

#### RQ2 — Causal effects on correctness

**Which support structures improve repository-level task resolution, and which failure modes do they reduce?**

#### RQ3 — Quality beyond resolution

**Which support structures improve locality, maintainability, test adequacy, reliability, and reviewability among all patches and among functionally correct patches?**

#### RQ4 — General baseline

**Can a simple, frozen, support-aware baseline achieve competitive resolution while producing safer and more reviewable patches on held-out tasks?**

---

## 3. Experimental unit and invariants

### 3.1 Unit of analysis

The primary unit is a **task-condition run**:

```text
one SWE-bench task
× one frozen support condition
× one frozen agent scaffold
× one frozen model snapshot
× one random seed / sampling configuration
```

Every task in a confirmatory cohort appears in every compared condition. Paired comparisons are therefore the default.

### 3.2 Variables held constant within an experiment

The following must be identical across conditions:

- base repository commit;
- problem statement;
- model provider, exact snapshot/version, decoding parameters, and context limit;
- agent scaffold and tool surface;
- total turn, token, command, wall-clock, and output budgets;
- filesystem and network policy;
- public repository contents;
- official evaluator version and Docker image digest;
- retry policy;
- task order randomization procedure.

The support condition is the intended independent variable. Any additional difference must be logged as a protocol deviation.

### 3.3 What all agents are always allowed to do

C0 must be a realistic minimal coding agent, not a deliberately disabled one. In every condition the agent can:

- read the issue;
- inspect the base repository;
- edit files inside its workspace;
- execute shell commands inside the allowed environment;
- inspect and run the repository’s existing public tests;
- add its own tests;
- submit a patch.

The treatment conditions add structured support; they do not remove basic software-development capabilities from C0.

---

## 4. Locked definitions of C0–C6

### C0 — Minimal

**Treatment:** none beyond the shared base environment.

**Visible to the agent:** issue, base repository, standard shell/edit tools, existing public tests.

**Not included:** generated context pack, helper reproduction test, automatic submit-time gates, enforced workflow state machine, repository memory.

### C1 — Task-specific context support

**Construct:** selected and structured task-relevant context.

**Artifact should include:**

- top relevant files and symbols;
- symbol definitions and selected references/callers;
- relevant existing tests and fixtures;
- short file/symbol summaries with provenance;
- a fixed token budget.

**Generation input:** issue + scrubbed base repository only.

**Must not include:**

- gold files or functions supplied directly from the benchmark;
- official test names or test patch;
- task solution hints from future commits;
- repository-wide memory or generic build instructions that belong in C5.

**Manipulation check:** offline gold-file recall may be measured after artifact generation, but gold information is never used to construct the artifact or shown to the agent.

### C2 — Executable reproduction support

**Construct:** an issue-derived, frozen, executable helper test supplied before the agent edits code.

**The agent receives:**

- the helper test source;
- the exact command that runs it;
- its failure output on the base commit;
- read-only access to the frozen artifact.

**The helper test is not the final judge.** It is a treatment artifact. Passing it does not establish correctness.

The detailed C2 protocol is specified in Section 5.

### C3 — Automatic validation gates

**Construct:** deterministic checks that the runner automatically executes when the agent attempts to submit, with results returned to the agent under a fixed revision policy.

Recommended gate sequence:

1. patch integrity and syntax/import checks — blocking;
2. deterministic repository-native public smoke/regression tests — blocking when the base is known clean;
3. repository-configured lint and type checks — blocking or advisory according to a frozen per-repository policy;
4. security/reliability checks — advisory unless a repository-native policy makes them blocking.

**C3-only must not run the C2 helper test.** C6 may include the helper test in its validation sequence.

The official SWE-bench judge remains hidden and is never a C3 gate.

### C4 — Enforced engineering workflow

**Construct:** a runner-enforced process, not merely a prompt reminder.

Required states:

```text
DISCOVER → DIAGNOSE → PATCH → VALIDATE → SUBMIT
```

Minimum enforcement:

- edits are rejected during DISCOVER and DIAGNOSE;
- transition to PATCH requires a structured localization and diagnosis record;
- transition to SUBMIT requires a validation record or an explicit, logged inability to validate;
- all rejected actions and state transitions are logged;
- C4 does not itself provide C1 context, C2 tests, C3 gates, or C5 memory.

### C5 — Repository memory

**Construct:** task-independent, repository-specific knowledge prepared before evaluation-task execution.

The same frozen artifact is used for every task from the same repository. It may contain:

- install/build/test recipes;
- repository conventions;
- module-boundary descriptions;
- fixture and test-layout conventions;
- compatibility constraints;
- known repository-level pitfalls derived from base documentation and configuration.

It must not contain:

- current-task localization or diagnosis;
- gold-derived information;
- outputs from previous evaluation tasks;
- patches or failures from the evaluation set.

Cross-task experience memory can be studied later as a separate construct; it should not be mixed into the confirmatory C5.

### C6 — Full support stack

C6 combines the frozen implementations of C1, C2, C3, C4, and C5. It is not a separate hand-tuned prompt. Its artifacts and policies must equal the union of the individual conditions.

---

## 5. C2 test boundary and implementation protocol

### 5.1 Five distinct test classes

Every run must distinguish these classes in storage and analysis:

| Code | Test class                                    |                       Agent visibility | Role                                   |
| ---- | --------------------------------------------- | -------------------------------------: | -------------------------------------- |
| B    | Base/public repository tests                  |              visible in all conditions | ordinary regression evidence           |
| J    | Official SWE-bench judge tests                |                                 hidden | primary benchmark correctness          |
| H    | Researcher-generated helper reproduction test |                  visible only in C2/C6 | treatment/support                      |
| A    | Agent-authored tests                          | visible because the agent creates them | agent output and process measure       |
| S    | Independent semantic audit tests              |                                 hidden | secondary generalization/overfit audit |

Never collapse these into a single `tests_passed` field.

### 5.2 Information boundary for helper-test generation

The helper-test generator may use:

- the problem statement as the only source of the expected behavioral oracle;
- the scrubbed base repository and public tests to learn imports, fixtures, APIs, and test style.

It must not access:

- the gold patch;
- the official `test_patch`;
- FAIL_TO_PASS/PASS_TO_PASS test identifiers;
- solution PRs, future commits, review comments after resolution, or network search;
- outputs from agents evaluated on the same task.

Rule for every assertion:

> The expected behavior must be traceable to the issue. Base-repository information may determine how the test is expressed, but not invent the expected result.

### 5.3 Candidate generation and freezing

For each candidate task:

1. Generate `K=3` independent candidates using a frozen generator model, prompt, and decoding configuration.
2. Do not return execution feedback from the gold patch or official tests to the generator.
3. Select a candidate using gold-blind rules:
   - it collects and runs;
   - it fails on the base commit for an issue-relevant reason;
   - its assertions have issue provenance;
   - it is minimal and does not enforce unsupported formatting or implementation choices.
4. Freeze that candidate before checking the gold patch.
5. Run the frozen candidate against the gold patch only as an offline validity diagnostic.
6. Do not switch to another candidate because of the gold result.

Classify the result:

- **T0 Invalid:** cannot collect, import, or execute.
- **T1 Non-reproducing:** passes on the base commit.
- **T2 Incompatible oracle:** fails on base and also fails on the gold patch.
- **T3 Valid reproduction:** fails on base and passes on gold.
- **T4 Decoupled valid reproduction:** T3 plus human/automatic audit finds no unsupported exact oracle or apparent solution/test leakage.

Confirmatory C2 analyses use T3/T4 tasks. T0–T2 rates remain reportable results; they must never be silently discarded.

### 5.4 Canonical example: `astropy__astropy-13033`

The issue concerns a misleading `TimeSeries` exception when an additional required column such as `flux` is removed.

The hidden official judge checks a maintainer-chosen exact message format resembling:

```python
assert str(exc.value) == (
    "TimeSeries object is invalid - expected ['time', 'a'] "
    "as the first columns but found ['time', 'b']"
)
```

That exact wording and fixture choice must not be shown to the agent.

A suitable visible helper test checks only issue-level semantics:

```python
def test_error_identifies_removed_required_column():
    time = Time(np.arange(3), format="jd")
    ts = TimeSeries(time=time, data={"flux": [1.0, 2.0, 3.0]})
    ts._required_columns = ["time", "flux"]

    with pytest.raises(ValueError) as exc:
        ts.remove_column("flux")

    assert "flux" in str(exc.value)
```

A hidden semantic audit can vary the column name to catch a hard-coded solution:

```python
@pytest.mark.parametrize("required_name", ["flux", "quality", "error"])
def test_reports_arbitrary_removed_required_column(required_name):
    ...
    assert required_name in str(exc.value)
```

Interpretation:

- H pass + J pass + S pass: benchmark and semantic success.
- H pass + J fail + S pass: likely semantically acceptable patch rejected by an over-specific official oracle; inspect manually.
- H pass + J fail + S fail: likely helper-test overfit.
- H fail + J pass: helper may be misaligned or the patch solved the task by a different valid behavior; inspect manually.

### 5.5 Read-only injection

The helper test must be mounted outside the editable patch workspace or reconstructed from its frozen hash every time it runs. Attempts to delete, weaken, or replace it must be logged and must not alter the evaluator’s copy.

Helper-test files are excluded from:

- agent changed-LOC counts;
- agent tests-added counts;
- patch locality metrics;
- maintainability metrics.

### 5.6 Semantic-audit scope

Hand-design hidden S tests for:

- all tasks in the 20-task C2 micro-study;
- a stratified 40-task subset in the main study;
- all motivating examples used in the paper.

S tests should be created from the issue and base repository without access to agent patches. Their purpose is not to replace the official benchmark but to diagnose helper overfitting and judge overspecification.

---

## 6. Information-isolation architecture

Before any confirmatory run, use three separate trust zones.

### 6.1 Artifact-generator zone

Visible:

- issue;
- scrubbed base repository;
- public base tests.

Hidden:

- gold patch;
- official test patch and test identifiers;
- future git history;
- agent outputs;
- network.

### 6.2 Agent zone

Visible:

- issue;
- scrubbed base repository;
- artifacts authorized by the assigned condition.

Hidden:

- task records containing gold/test-patch fields;
- official evaluator files;
- host run directories and artifacts from other conditions;
- future git history and remotes;
- network.

### 6.3 Evaluator zone

Visible after the agent terminates:

- final patch;
- official SWE-bench evaluator and test patch;
- gold patch for descriptive comparisons;
- hidden semantic-audit tests.

The agent never receives evaluator output during generation. C3 feedback comes from public, predeclared gates only.

### 6.4 Required red-team checks

Automated tests must verify that an agent command cannot:

- traverse from the workspace into the run/task metadata directory;
- read gold or official-test fields;
- inspect another condition’s artifacts;
- use `git log`, remotes, reflogs, or object storage to recover future commits;
- access the network;
- mutate read-only support artifacts;
- communicate through persistent files across task-condition runs.

Every run stores a scrubbed-input manifest and hashes of all visible artifacts.

---

## 7. Dataset and sampling plan

### 7.1 Dataset roles

- **SWE-bench Verified:** primary causal study.
- **SWE-bench Lite or small Verified subsets:** engineering smoke only; no paper claims.
- **SWE-bench Live:** freshness/generalization check after protocol freeze.
- **AIDev:** optional qualitative grounding for RQ1; not causal evidence.

Do not add more benchmarks until the Verified adapter, C2 policy, and quality pipeline are stable.

### 7.2 Cohorts

#### D0 — Engineering development set

- 10 tasks.
- Used for sandbox, runner, model, and manipulation debugging.
- Permanently excluded from confirmatory estimates.

#### D1 — C2 feasibility set

- 30 candidate Verified tasks.
- Stratified across issue types and task complexity.
- Target: at least 20 frozen T3/T4 helper-test artifacts.
- All T0–T2 outcomes are retained to quantify helper-generation coverage.

#### P1 — Full pilot set

- 50 T3/T4-eligible Verified tasks.
- Every task runs under C0–C6.
- Used to test treatment strength, instrumentation, variance, and annotation codebook.
- Not the source of the final headline claim.

#### M1 — Main causal set

- 120 T3/T4-eligible Verified tasks drawn from a larger pre-sampled candidate frame.
- Every task runs under C0–C6.
- Eligibility selection occurs before any evaluated agent run.
- Report task-feature differences between eligible and ineligible candidates.

#### H1 — Held-out generalization set

- 50 untouched tasks.
- Prefer SWE-bench Live after the adapter is validated; otherwise use an untouched Verified holdout.
- Used only after the support-aware baseline and analysis code are frozen.

### 7.3 Stratification dimensions

Upgrade the current repository-proportional sampler to balance, where metadata permits:

- repository;
- gold files touched: 1 versus multiple;
- gold patch size: small, medium, large;
- number of FAIL_TO_PASS and PASS_TO_PASS tests;
- issue category: exception/message, state/value behavior, API compatibility, edge case, cross-file behavior;
- estimated environment/evaluation cost;
- task age;
- public-test availability.

Gold-derived features may be used for offline sampling strata, but never placed in agent-visible artifacts.

### 7.4 Exclusion rules

Pre-register exclusions before agent runs:

- Docker/evaluator cannot reproduce the gold resolution after a fixed retry policy;
- base environment is irreparably flaky;
- task requires prohibited external services;
- helper artifact is T0–T2 for an all-support confirmatory cohort;
- licensing or artifact availability prevents reproducibility.

Do not exclude tasks because an evaluated agent fails, times out, or produces an inconvenient result.

---

## 8. Experimental stages

### E0 — Construct and manipulation smoke

**Purpose:** prove each condition changes exactly its intended mechanism.

**Design:**

```text
10 D0 tasks × selected conditions and adversarial fixtures
```

Required checks:

- C1 artifact is task-specific and generated without gold fields.
- C2 helper is frozen, read-only, base-failing, and independent from J.
- C3 automatically runs only declared public gates and returns feedback.
- C4 rejects edits before required state transitions.
- C5 is byte-identical across tasks in the same repository.
- C6 equals the composition of C1–C5.
- C0 contains none of the support artifacts.

No correctness comparison is reported from E0.

### E1 — C2 × C3 micro-study

**Purpose:** separate two mechanisms:

- helper tests may improve diagnosis/generation;
- gates may detect and reject bad submissions.

**Design:**

```text
20 D1 tasks
× {C0, C2, C3, C2+C3}
× 1 frozen model/scaffold configuration
= 80 primary runs
```

Use two additional seeds on a 10-task subset if outcome instability is high.

Primary comparisons:

- C2 vs C0: effect of executable reproduction support.
- C3 vs C0: effect of automatic public validation.
- C2+C3 vs C2 and vs C3: complementarity.

Mechanism outcomes:

- time/turn to first correct localization;
- helper executions;
- public-test executions;
- revision after gate failure;
- helper overfit rate under S tests;
- official resolution and P2P regressions.

### E2 — Full 50-task C0–C6 pilot

**Design:**

```text
50 P1 tasks × 7 conditions × 1 seed = 350 runs
```

Condition order is randomized independently within each task. The scheduler should interleave conditions so model-service drift and machine load are not confounded with condition.

Pilot objectives:

- verify no floor/ceiling effect with the selected main model;
- estimate discordant-pair rates for power planning;
- quantify infrastructure failure rate;
- validate all automatic quality metrics;
- freeze the qualitative codebook;
- identify only protocol bugs, not tune toward favorable effects.

Go/no-go for E3:

- infrastructure failure below 5%;
- no detected information leakage;
- treatment manipulation success above 95%;
- quality-card fields complete or explicitly `null` in at least 95% of runs;
- sufficient condition discordance to support paired analysis;
- model, prompt, artifacts, and evaluator versions are frozen.

### E3 — Main causal study

#### Core ablation

```text
120 M1 tasks × C0–C6 × 1 seed = 840 runs
```

#### Targeted interaction additions

The seven-condition design cannot estimate general interactions. Add two pre-registered combinations on a 60-task stratified subset:

```text
C2+C3  — tests × gates
C1+C4  — context × enforced workflow
```

This adds 120 runs.

#### Stability subset

Repeat all seven conditions with two additional seeds on 30 tasks:

```text
30 tasks × 7 conditions × 2 extra seeds = 420 runs
```

Total planned E3 runs: 1,380.

### E4 — Qualitative failure and quality analysis

Select approximately 200 patches after outcomes are available using a predeclared stratified scheme:

- 100 AI failures across conditions and failure stages;
- 50 AI-resolved patches across conditions;
- 40 human gold patches for the same or matched tasks;
- up to 10 ecological examples from Copilot/AIDev, clearly separated from the causal sample.

Annotation process:

1. Open-code 40–60 patches and trajectories.
2. Freeze a codebook and decision rules.
3. Hide condition labels and model identity from annotators where feasible.
4. Double-code at least 30%; preferably all core RQ1 samples.
5. Report Cohen’s kappa or Krippendorff’s alpha.
6. Resolve disagreements through a documented adjudication process.

### E5 — RQ4 held-out baseline evaluation

Use P1 results to choose a **minimal cost-effective support stack** from the Pareto frontier of:

- official resolution;
- regression safety;
- reviewability/quality;
- token and wall-clock cost.

Freeze the chosen pipeline, prompts, models, and selection rule before H1.

Evaluate on 50 held-out tasks against:

- C0 with the same scaffold/model;
- the frozen support-aware baseline;
- an Agentless-style secondary scaffold where the adapter is mature;
- optional Copilot CLI default versus support-enabled configuration on a smaller ecological subset.

Copilot results are ecological validation, not the source of the primary causal claim, unless the exact model/version, system configuration, and tool surface can be frozen and independently reproduced.

---

## 9. Model and agent protocol

### 9.1 Primary scaffold

Use the repository’s controllable bash-loop `LLMAgent` as the primary scaffold after freezing its command grammar and tool interface. Do not change the scaffold during E2/E3.

### 9.2 Secondary scaffold

Implement an Agentless-style localize → repair → validate adapter after the primary experiment is stable. Use it for selected robustness conditions, not to expand scope before E3.

### 9.3 Main model selection

The current Qwen2.5-Coder-7B run is a plumbing result. Select the main pinned model using D0 only.

Pre-register a selection rule such as:

- exact snapshot/version is available for the whole experiment;
- model reliably follows the command protocol;
- C0 produces non-empty/applying patches often enough to avoid a floor effect;
- D0 resolution is neither essentially zero nor saturated;
- model cost permits the planned paired design;
- full raw responses and usage metadata can be stored.

Do not choose or change the model after observing P1 condition effects.

### 9.4 Budgets

Fix and record:

- maximum turns;
- maximum input/output tokens;
- maximum shell commands;
- per-command timeout;
- total wall-clock limit;
- maximum automatic-gate revisions;
- context-pack token budget;
- helper-test size/runtime budget.

Support conditions may change how the budget is used, but must not silently receive a larger total budget.

---

## 10. Outcomes and code-quality definition

### 10.1 Primary endpoint

**Official SWE-bench `resolved`**, evaluated in the official Docker harness.

Pre-register C6 vs C0 as the headline contrast. C1–C5 vs C0 are component contrasts.

### 10.2 Correctness and regression outcomes

Store separately:

- patch applies;
- build/import succeeds;
- F2P passed/total;
- P2P passed/total;
- official resolved;
- H helper passed;
- S semantic audit passed;
- number and type of new regression failures.

### 10.3 Process and trajectory outcomes

Add structured metrics derived from the transcript:

- files/symbols inspected before first edit;
- turn and time to first edit;
- turn and time to first test;
- whether localization preceded editing;
- number of edits and reverted edits;
- public/helper/agent-test executions;
- validation attempts;
- gate failures and revisions;
- repeated failed commands;
- out-of-workspace or prohibited-access attempts;
- stop reason;
- token, command, and wall-clock cost.

### 10.4 Patch locality

Report raw dimensions:

- files, functions, and LOC touched;
- diff entropy/distribution across files;
- gold-file and gold-function overlap;
- dependency distance from issue-relevant symbols where available.

Do not treat “file not touched by the gold patch” as ground-truth unrelatedness. Gold overlap is descriptive; human review or a task-relevance rubric is needed before labeling a change unrelated.

### 10.5 Maintainability

Measure deltas only:

- new lint warnings under a repository-compatible configuration;
- new type warnings when the repository already supports type checking;
- changed-function complexity delta;
- function-size and nesting delta;
- dead/unreachable-code signals where reliable;
- convention violations identified by human annotation.

Do not run a generic linter configuration and interpret all legacy warnings as agent-caused quality problems.

### 10.6 Test adequacy

Keep H helper tests separate from A agent-authored tests. For agent-authored tests record:

- tests added or modified;
- whether each test fails on base and passes on the agent patch;
- changed-line coverage where feasible;
- whether tests exercise the changed behavior;
- whether tests are brittle or implementation-specific under annotation.

### 10.7 Reliability and security

Report only tool-compatible deltas:

- newly introduced static security warnings;
- exception/resource-cleanup problems;
- input-validation or concurrency risks under human annotation.

A missing/unavailable tool result is `null`, never zero.

### 10.8 Reviewability

Human reviewers score, on a frozen rubric:

- clarity of the patch’s intent;
- minimality and focus;
- consistency with repository abstractions;
- sufficiency of tests/validation evidence;
- confidence to approve;
- would reject, and primary reason.

### 10.9 Composite quality levels

Q0–Q5 may be retained as a secondary summary, but raw dimensions remain primary. The current automatic quality-card rule should not promote a patch to “engineering acceptable” solely because it passes tests and overlaps gold files.

Suggested interpretation:

- Q0: invalid/non-applying;
- Q1: plausible but functionally failing;
- Q2: functionally correct by official evaluation;
- Q3: correct with no major regression/maintainability/reviewability concern;
- Q4: review-ready with adequate validation;
- Q5: demonstrably improves on the human reference in one or more dimensions without trade-off.

Q3–Q5 require the mature metric rubric and/or human judgment.

---

## 11. RQ-specific analysis plan

### 11.1 RQ1

Data:

- all run trajectories and patches;
- stratified 200-patch annotation sample;
- matched human gold patches;
- optional AIDev/Copilot examples separated from causal data.

Analysis:

- develop a failure taxonomy;
- compare failure-mode prevalence by condition;
- compare process anti-patterns in resolved versus unresolved runs;
- compare AI and human patches on locality, tests, abstractions, and reviewability;
- use representative cases to explain causal quantitative findings.

Candidate top-level failure families:

- requirement misunderstanding;
- fault localization;
- incomplete/edge-case fix;
- API/protocol misuse;
- architecture violation;
- regression introduction;
- brittle/test-overfit solution;
- validation failure;
- environment/tool failure;
- premature stopping or unproductive loops.

### 11.2 RQ2

Primary paired contrasts:

- C6 vs C0 — headline full-stack effect;
- C1, C2, C3, C4, C5 vs C0 — component effects.

Mechanism mapping:

- C1 → localization and relevant-code discovery;
- C2 → reproducibility, diagnosis, and edge-case targeting;
- C3 → defect detection and bad-submission prevention;
- C4 → order of work, validation behavior, and loop reduction;
- C5 → setup efficiency and repository-convention adherence.

Use the C2×C3 and C1×C4 additions for interaction claims. Do not infer broad interaction effects from C6 alone.

### 11.3 RQ3

Analyze two populations:

1. all generated patches, including invalid and failing outputs;
2. officially resolved patches only.

The second analysis is essential: it tests whether two conditions with similar pass rates produce patches of different engineering quality.

Report correctness and quality separately rather than hiding trade-offs in one score.

### 11.4 RQ4

The baseline must be selected before the held-out evaluation. Report:

- held-out resolution and regression safety;
- quality dimensions among resolved patches;
- cost per resolved task and cost per review-ready task;
- robustness across repository/task strata;
- differences between the controllable research scaffold and ecological Copilot runs.

---

## 12. Statistical plan

### 12.1 Binary outcomes

For paired condition comparisons:

- exact McNemar test;
- paired absolute percentage-point difference;
- task-clustered bootstrap confidence interval;
- discordant-pair counts.

Pre-register C6 vs C0 as primary. Apply Holm correction to the five component comparisons against C0.

### 12.2 Multivariable model

Use a mixed-effects logistic model as a secondary analysis:

```text
resolved ~ condition + task_features + (1 | task) + (1 | repository)
```

Treat `condition` as categorical in the seven-condition study. Do not pretend the OFAT-plus-full-stack design identifies all five additive main effects and interactions.

For the targeted factorial subsets, estimate:

```text
resolved ~ tests * gates + (1 | task) + (1 | repository)
resolved ~ context * harness + (1 | task) + (1 | repository)
```

### 12.3 Continuous/count outcomes

Depending on distribution:

- paired permutation or Wilcoxon signed-rank tests;
- task-clustered bootstrap intervals;
- mixed-effects linear, ordinal, Poisson, or negative-binomial models.

Report effect sizes and intervals, not p-values alone.

### 12.4 Seed variation

For the stability subset, model seed/run variation hierarchically and report:

- probability that condition ranking changes across seeds;
- within-task variance;
- pass@1 and repeated-run success where relevant.

### 12.5 Missingness

Distinguish:

- agent failure;
- infrastructure failure;
- evaluator failure;
- metric unavailable;
- task excluded before running.

Only predeclared infrastructure failures may be retried. Never silently overwrite a failed run.

### 12.6 Pilot and power

Do not use pilot significance as the decision rule. Use P1 to estimate:

- discordant-pair rate;
- infrastructure loss;
- condition variance;
- prevalence of resolved patches for RQ3;
- annotation prevalence and agreement.

Any sample-size adjustment must be based on these design quantities, not whether the observed direction is favorable.

---

## 13. Reproducibility and run-record requirements

Each run directory should contain or reference immutable copies of:

```text
run_spec.json
visible_input_manifest.json
support/manifest.json
support/context_pack.md                 # when C1/C6
support/helper_test.*                   # when C2/C6
support/helper_validation.json          # when C2/C6
support/gate_policy.json                # when C3/C6
support/harness_policy.json             # when C4/C6
support/repo_memory.md                   # when C5/C6
prompt.txt / messages.jsonl
transcript.jsonl
commands.jsonl
state_transitions.jsonl
intermediate_patches/
final.patch
eval_result.json
semantic_audit_result.json              # when available
quality_card.json
provenance.json
```

Record:

- git commit of the research repository;
- task base commit;
- model exact identifier and response metadata;
- prompt and support-artifact hashes;
- evaluator/harness version;
- Docker image digest;
- operating-system/tool versions;
- all budgets;
- seed;
- start/end timestamps;
- retry/attempt number and reason.

Raw logs are append-only. Derived tables and quality cards must be reproducible offline from raw artifacts.

---

## 14. Engineering work packages

### EP-00 — Protocol and schema freeze

**Deliverables**

- add this plan to `docs/`;
- update `docs/experiment_protocol.md` to reference it;
- add condition-version and protocol-version fields to `RunSpec`;
- add treatment/manipulation fields to run results.

**Acceptance**

- exported JSON schemas updated;
- old run records remain readable or have an explicit migration.

### EP-01 — Sandbox and provenance firewall

**Likely modules**

```text
src/se_support/isolation/
  manifest.py
  scrub.py
  sandbox.py
  policy.py
```

**Deliverables**

- scrubbed task workspace;
- network-disabled execution;
- host/run-directory isolation;
- future-git-history removal;
- visible-input manifest and hashes;
- adversarial leakage tests.

**Acceptance**

- all Section 6.4 red-team checks pass;
- agent-visible inputs contain no gold, official-test, or F2P/P2P metadata.

### EP-02 — Frozen support bundle

**Likely modules**

```text
src/se_support/support/bundle.py
src/se_support/support/schema.py
```

**Deliverables**

- `SupportBundle` and `SupportArtifactManifest`;
- pre-run artifact generation;
- condition-to-artifact validation;
- artifact hashing and immutable mounting.

**Acceptance**

- C0 receives an empty support bundle;
- C6 bundle equals the declared composition of C1–C5;
- artifacts are generated before the agent starts.

### EP-03 — C2 reproduction-test pipeline

**Likely modules**

```text
src/se_support/support/repro_tests/
  schema.py
  generator.py
  validator.py
  provenance.py
  audit.py
  injector.py
```

**Deliverables**

- K-candidate blind generator;
- base and offline-gold validator;
- T0–T4 classification;
- assertion-provenance and suspicious-literal audit;
- read-only injection and execution logging;
- helper/official/agent/semantic test result separation.

**Canonical fixture**

```text
tests/fixtures/astropy__astropy-13033/
  README.md
  problem_statement.txt
  helper_test.py
  helper_artifact.json
  expected_base_result.json
  expected_gold_result.json
  semantic_audit_test.py
```

**Acceptance**

- helper fails on base, passes on gold, and contains no official exact-message oracle;
- hard-coded `flux` patch is rejected by the hidden semantic audit;
- helper modifications inside the agent workspace cannot change evaluation.

### EP-04 — C4 enforced harness

**Likely module**

```text
src/se_support/support/harness.py
```

**Deliverables**

- explicit workflow state machine;
- phase-specific tool permissions;
- structured phase artifacts;
- transition and rejected-action logging.

**Acceptance**

- attempted edits in DISCOVER/DIAGNOSE are rejected;
- SUBMIT without a validation record is rejected or explicitly marked under a frozen exception rule;
- C4-only does not receive C1/C2/C3/C5 content.

### EP-05 — C1 context v2

**Deliverables**

- issue-based retrieval over files/symbols/tests;
- structured context with source paths and lines;
- fixed token budget;
- deterministic or pinned generation path;
- optional same-token random-context negative control for manipulation testing.

**Acceptance**

- no gold input;
- pack differs by task but is reproducible for the same input/version;
- offline relevance metrics are emitted.

### EP-06 — C5 memory v2

**Deliverables**

- repository profiler over docs/config/tests;
- one frozen memory artifact per repository;
- clear separation from C1 and shared base environment.

**Acceptance**

- identical hash for every evaluation task from one repository;
- generated before evaluation-task execution;
- no prior evaluation trajectory or task-specific content.

### EP-07 — C3 gate policy v2

**Deliverables**

- repository-specific, versioned gate policy;
- blocking/advisory semantics;
- base-versus-patch delta calculation;
- fixed revision budget and feedback format;
- separate handling of helper tests in C6.

**Acceptance**

- official hidden tests are never executed during agent generation;
- repeated execution is deterministic;
- legacy repository warnings are not attributed to the patch.

### EP-08 — Quality card v1

**Deliverables**

- raw correctness, locality, maintainability, test, reliability, reviewability fields;
- base→patch deltas;
- agent-authored-test fail-before/pass-after analysis;
- trajectory mechanism metrics;
- revised Q0–Q5 logic.

**Acceptance**

- missing is `null`;
- helper tests are excluded from agent test/LOC metrics;
- gold non-overlap is not automatically labeled unrelated;
- metrics can be recomputed from saved artifacts.

### EP-09 — Experiment scheduler

**Deliverables**

- randomized task-condition schedule;
- resume/idempotency support;
- explicit infrastructure-only retries;
- run-attempt records;
- concurrency control for model and Docker workers;
- completeness dashboard.

**Acceptance**

- interrupted experiments resume without duplicating valid runs;
- no result is overwritten;
- condition order is reproducibly randomized.

### EP-10 — Analysis and annotation package

**Deliverables**

```text
src/se_support/analysis/
annotation/
  codebook.md
  schema.json
  adjudication.md
```

- paired result tables;
- McNemar and bootstrap analyses;
- quality analysis among resolved patches;
- interaction analysis;
- annotation sampler and blind packet generator;
- agreement calculation.

**Acceptance**

- analysis runs from raw run directories;
- no manual spreadsheet editing is required for primary tables;
- all figures/tables include cohort and missingness counts.

---

## 15. Go/no-go checklist

### Before E1

- [ ] Agent filesystem and network isolation passes adversarial tests.
- [ ] Gold patch, official test patch, and test identifiers are absent from agent-visible inputs.
- [ ] Frozen support-bundle interface is implemented.
- [ ] Canonical Astropy helper-test fixture passes its base/gold/semantic checks.
- [ ] B/J/H/A/S outcomes have separate schema fields.
- [ ] Main agent/model/budget configuration is recorded.

### Before E2

- [ ] At least 20 of 30 D1 tasks have T3/T4 helpers.
- [ ] C2 eligibility and failure reasons are reported.
- [ ] C3 and C4 manipulation checks pass in at least 95% of smoke runs.
- [ ] C1 and C5 provenance and token boundaries are frozen.
- [ ] Quality-card v1 can be recomputed offline.
- [ ] Randomized, resumable scheduler is operational.

### Before E3

- [ ] P1 infrastructure-failure rate is below 5%.
- [ ] No material leakage or condition-contamination incident remains unresolved.
- [ ] Main model snapshot, prompt, scaffold, tools, and evaluator are frozen.
- [ ] M1 task list and condition schedule are frozen and hashed.
- [ ] Primary/secondary outcomes and multiple-comparison policy are pre-registered.
- [ ] Annotation codebook has acceptable pilot agreement.

### Before E5

- [ ] Support-aware baseline selection rule is frozen.
- [ ] H1 has not been used for tuning or debugging.
- [ ] Analysis code produces final tables without H1-specific changes.

---

## 16. Immediate Copilot CLI execution order

Do not ask Copilot CLI to start the 50-task pilot yet. Execute the work packages in this order:

1. **EP-01:** implement and test the provenance firewall and sandbox contract.
2. **EP-02:** implement the frozen `SupportBundle` interface.
3. **EP-03:** implement C2 end-to-end using `astropy__astropy-13033` as the acceptance fixture.
4. **EP-04:** replace C4 prompt-only behavior with a state machine.
5. **EP-07:** freeze C3 gate semantics and revision policy.
6. **EP-05 / EP-06:** strengthen and separate C1 context and C5 memory.
7. **EP-08:** mature the quality card and trajectory metrics.
8. **EP-09:** add randomized scheduling, resume, and infrastructure-only retries.
9. Run E0 and E1.
10. Proceed to E2 only after the go/no-go checklist passes.

A suitable first Copilot CLI instruction is:

```text
Read PROJECT_PROPOSAL.md, docs/experiment_protocol.md,
docs/DISCUSSION_2026-07-09.md, and
 docs/EXPERIMENT_PLAN_2026-07-21.md.

Implement only EP-01 (Sandbox and provenance firewall).
Do not modify the scientific definitions of C0-C6 and do not start any
large experiment. First inspect the current TaskSpec, Workspace, LLMAgent,
run manager, and SWE-bench importer paths. Then produce:

1. a concise design note;
2. the scrubbed-visible-input manifest schema;
3. isolation/scrubbing implementation;
4. adversarial tests for host traversal, network access, future git history,
   gold/test-patch metadata, cross-run files, and read-only support artifacts;
5. backward-compatible schema updates;
6. documentation of assumptions and unresolved limitations.

Acceptance is the EP-01 checklist in the experiment plan. Run pytest and ruff.
Do not proceed to EP-02 until EP-01 tests pass.
```

---

## 17. Expected paper-level claims, contingent on results

The protocol is designed to support claims of the following form without assuming their direction in advance:

- Different support structures target different failure mechanisms.
- Executable reproduction support changes diagnosis and patch generation, while automatic gates change defect detection and submission precision.
- Structured relevant context may outperform merely adding more context tokens.
- An enforced process may improve validation and reduce unproductive behavior beyond prompt-only instructions.
- Repository memory may improve setup and convention adherence without supplying task answers.
- Benchmark resolution is necessary but insufficient: equally resolved patches may differ in regression safety, maintainability, tests, and reviewability.
- A relatively simple, support-aware pipeline may provide a competitive and reproducible baseline without requiring a more complex autonomous agent.

Negative or heterogeneous results remain valuable. For example, a helper test may improve resolution on well-specified issues but harm performance when its oracle is weak; gates may reduce invalid submissions while increasing cost; context may help localization but distract on small tasks. The design should preserve these trade-offs rather than optimize only for a single leaderboard score.

---

## 18. Repository documents used as the starting point

- `README.md`
- `PROJECT_PROPOSAL.md`
- `docs/experiment_protocol.md`
- `docs/DISCUSSION_2026-07-09.md`
- `docs/experiments/003_docker_eval_validation.md`
- `docs/experiments/004_pilot_c0_vs_c6.md`
- current implementations under `src/se_support/`

This document should become the execution-level protocol; the proposal remains the rationale, and individual experiment files remain the immutable record of what was actually run. 