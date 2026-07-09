# Experiment Protocol

This document records the **decisions** for how the SE-Support Study is run:
datasets, agents, models, conditions, and metrics. It complements the proposal
(which is the full rationale) by stating what we *actually do*.

---

## 1. Core research question

> Coding agents fail not only because the model is weak, but because they lack
> structured software-engineering support.

We hold the **agent and model fixed** and toggle five support structures as
experimental conditions (C0–C6). The main comparison is **agent-vs-agent across
conditions**; the human "gold" patch is a *measuring stick* (localization,
test oracle, quality ceiling), not the main opponent.

## 2. Datasets

| Dataset | Role | Notes |
|---|---|---|
| **SWE-bench Verified** | Primary causal ablation | 500 human-filtered Python tasks; has gold patch + FAIL_TO_PASS/PASS_TO_PASS; Docker-reproducible. |
| **SWE-bench Lite** / SWE-Gym Lite | Dev / smoke test only | cheap & fast; never a source of paper claims. |
| **SWE-bench Live** | Freshness / anti-contamination check | issues created after 2024; used post-pilot. |
| **AIDev** | Failure-taxonomy grounding (RQ1) | real agentic PRs; **qualitative only**, not causal (conditions not controlled). |

Scale-up: 10 tasks (smoke) → 50 (pilot) → 120 (main).

## 3. Agents (scaffolds)

| Agent | Role | Why |
|---|---|---|
| **mini-SWE-agent** | Primary controllable scaffold | ~100-line, bash-only, model-agnostic (litellm); we can inject/remove support layers. |
| **Agentless-style pipeline** | Secondary robustness scaffold | localize→repair→validate; cheap; shows results aren't scaffold-specific. |
| **Copilot CLI** | Optional ecological validation | closed internals → **not** used for main causal claims. |

We **do not build an agent from scratch**. We build the *support layer* that
wraps a fixed agent and toggles conditions — that layer is the contribution.

## 4. Models & compute

- **Main causal runs:** one **pinned API model snapshot** (record exact
  version string in `RunSpec.model`). Fixed model = clean causal attribution.
- **Robustness (optional):** one self-hosted open-weight model (e.g.
  Qwen3-Coder-Next 80B via vLLM) re-running C0/C6, to show support effects are
  not model-specific.
- **Compute plan (cost-saving staged approach):**
  1. **Plumbing:** mock agent (deterministic), 0 model cost.
  2. **Smoke:** small open model on a 24 GB GPU (e.g. RTX 4090) via vLLM — for
     debugging the loop only; **do not** treat its pass rate as a result.
  3. **Real runs:** switch `model` to the pinned API snapshot (one-line config
     change — mini-SWE-agent is model-agnostic).
- SWE-bench Docker evaluation is **CPU-only**; GPUs are only for serving a
  local LLM.

## 5. Support conditions (C0–C6)

Implemented as a `SupportCondition` config that toggles layers around the same
fixed agent. Two mechanisms:

- **Prompt/artifact injection** (C1 context, C5 memory): generate artifacts and
  add them to the agent prompt. Toggle = inject or not.
- **Loop/tool interception** (C2 tests, C3 gates, C4 harness): wrap the agent
  loop — run gates and feed results back, enforce workflow phases, run generated
  tests during validation.

See `PROJECT_PROPOSAL.md` §6 for the full per-condition specification.

## 6. Experiments (staged)

| Stage | Design | Purpose |
|---|---|---|
| 0 Smoke | 10 tasks × {C0,C6} × 1 agent | pipeline works end-to-end |
| 1 Pilot | 50 tasks × {C0,C6} × 1 agent | is there signal? stabilise quality card + codebook |
| 2 Main | 120 tasks × C0–C6 × 1 agent | core causal ablation |
| 3 Robustness | C0/C2/C4/C6 × 2nd agent, 2–3 seeds | generality |
| 4 External | SWE-bench Live 50 + optional Copilot CLI | freshness / ecological validity |

Every task appears in every condition (paired comparisons; McNemar for binary).

## 7. Metrics we actually use

### Must (pilot, fully automated)
- **Correctness (from official eval):** patch_applies, build_success,
  fail_to_pass passed/total, pass_to_pass passed/total, resolved.
- **Locality (from diff + gold):** files_touched, loc_added, loc_deleted,
  gold_file_overlap, unrelated_file_change_suspected.
- **Test adequacy:** tests_added, repro_test_fail_before/pass_after (with C2).

### Should (main run, mature tools)
- lint_new_warnings (`ruff`), type_new_warnings (`mypy`, if repo configured),
  new_security_warnings (`bandit`, advisory), complexity_delta (`radon`),
  changed_line_coverage_delta (`coverage.py`).

### Human annotation (200–300 patches, RQ1/RQ3)
- quality_level Q0–Q5, failure_modes F01–F14, would-reviewer-reject + reason.
- Report inter-annotator agreement (Cohen's kappa / Krippendorff's alpha).

### Deferred (v0 skips)
- mutation testing, architecture/import-graph analysis, duplication detection.

## 8. Iron rules

1. **Fix and pin the model** for a given experiment; never change it mid-run.
2. **All quality metrics are deltas** (post-patch − pre-patch).
3. **Missing tool = `null` (unavailable), never `0`.**
4. **Record raw data richly** (full transcript, per-command logs, intermediate
   patches, base_commit/env) so new metrics are recomputed offline — never
   re-run an experiment just to add a metric.
5. **The headline analysis** compares quality metrics **among patches with equal
   pass/fail**, to show pass-rate alone hides quality differences.
