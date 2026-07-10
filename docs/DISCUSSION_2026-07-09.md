# Design Discussion Log — 2026-07-09

A record of the decisions and open questions worked through with the team on
2026-07-09, so the reasoning behind the current design is not lost. This is a
discussion log, not a spec; the authoritative design lives in
`PROJECT_PROPOSAL.md` and `docs/experiment_protocol.md`.

---

## 1. What the project is

A **controlled-ablation study**: hold the agent + model **fixed** and toggle
five software-engineering "support structures" (C0–C6) to measure their causal
effect on (a) correctness and (b) patch quality beyond pass/fail. The support
structures are **our research constructs** — not provided by the dataset or by
any off-the-shelf agent.

## 2. Provenance — who provides what

| Source | Provides | Does NOT provide |
|---|---|---|
| **SWE-bench (dataset)** | tasks, repo snapshots, FAIL_TO_PASS/PASS_TO_PASS tests, gold patches, Docker eval env | any help given to the agent |
| **mini-SWE-agent (scaffold)** | a minimal bash loop (propose command → run → observe) | any structured support |
| **Us (researchers)** | the 5 support layers = the independent variables | — |

Takeaway: SWE-bench sets and grades the exam; the scaffold is the bare "worker
loop"; **the five support layers are ours to build.**

## 3. Datasets (decided)

- **Primary causal:** SWE-bench Verified (500 human-filtered Python tasks).
- **Dev/smoke:** SWE-bench Lite / small subsets.
- **Freshness / anti-contamination:** SWE-bench Live (post-pilot).
- **Real-world grounding (qualitative only):** AIDev.

Scale-up: 10 (smoke) → 50 (pilot) → 120 (main).

## 4. Agents (decided)

| Agent | Role |
|---|---|
| **mini-SWE-agent** style bash-loop | primary controllable scaffold → main causal claims |
| **Agentless** 3-step | secondary scaffold → robustness |
| **Copilot (SDK/CLI)** | **ecological validation only** — a real industrial agent; NOT used for main causal claims because its model version / internal prompts are not controlled |

## 5. Models & compute (decided)

- **Main causal runs:** one **pinned** model snapshot (API or a fixed local
  model). Fixed model = clean causal attribution.
- **Robustness (optional):** a second (e.g. open-weight) model re-running C0/C6.
- **Cost-saving staging:** mock agent (0 cost) → small local model on the RTX
  4090 via vLLM (debug only, pass rate not a result) → switch `model` to the
  pinned snapshot (one-line change; the agent is model-agnostic).
- **Disk:** SWE-bench Docker images are pulled per-instance and, with
  `--cache_level env`, **removed after each eval** — a pilot does not accumulate
  images. ~1.2 TB free is plenty. No extra disk needed.
- **Docker on this host is rootless** (`DOCKER_HOST=unix:///run/user/<uid>/docker.sock`).

## 6. The five support layers — what each is, and current status

| Layer | What it is | Raw material | Built by | Status |
|---|---|---|---|---|
| **C1 Context** | task-relevant repo navigation pack (file map, relevant files, symbols, API examples, build/test hints) | the repo | us | 🟡 weak v1 (file map + test hint only) |
| **C2 Tests** | auto-generated **reproduction test** (fail-before/pass-after) handed to the agent as a helper | issue text | us | 🔴 **not implemented (deferred)** |
| **C3 Gates** | deterministic checks on submit (syntax/lint/type/security/test); blocking vs advisory; results fed back | generic tools (ruff/mypy/bandit/pytest/compileall) | us | 🟢 real (compileall blocking; ruff/bandit advisory) |
| **C4 Harness** | enforced workflow: localize → diagnose → test plan → edit → validate | none (process constraint) | us | 🟡 soft (prompt rules only; no state-machine enforcement) |
| **C5 Memory** | repo-specific memory (AGENTS.md, build recipes, flaky tests, conventions, past failures) | repo contents + prior runs | us | 🟡 weak v1 (build/test commands + generic conventions) |

**Implication:** today's C6 is a "discounted C6" — C3 is solid, C1/C4/C5 are
functional-but-weak, **C2 is empty**. Results from it are a *lower bound* on the
true support effect.

## 7. C2 reproduction-test design (discussed, DEFERRED)

Decided design (to implement later, after the team researches the boundary):

- **Granularity:** one reproduction test **per task** (each bug is different).
- **Writer:** a **separate fixed LLM step in our infra** — NOT hand-written, and
  NOT written by the agent-under-test. It is prepared *before* the agent runs
  and handed to it as a helper.
- **Three distinct tests (never conflate):**
  1. official `FAIL_TO_PASS`/`PASS_TO_PASS` — human-derived, **hidden**, the grader;
  2. C2 reproduction test — auto-generated, **shown** to the agent, a helper;
  3. tests the agent adds itself — part of its own patch.

### The key concern: won't the generated test == the official test?

Worked example — `astropy__astropy-13033` ("TimeSeries: misleading exception
when required column check fails"):

- The **official hidden test** asserts an exact string the maintainer chose:
  `"... expected ['time', 'a'] as the first columns but found ['time', 'b']"`.
  This precise wording is an arbitrary implementation choice **and is not in the
  issue text**.
- A **good C2 test** (from the issue only) asserts *behavior/intent*: removing a
  required column raises `ValueError` and the message names the missing column /
  the old confusing message is gone. It cannot know the exact official string.

**Calibrating the boundary — what is OK vs not to show the model:**

| OK to show | Not OK (leakage / overfit) |
|---|---|
| generated only from the **issue text** | uses gold patch / official test_patch |
| passes **fail-before** (truly reproduces) | empty test / passes on base code |
| asserts behavior the issue describes | asserts exact strings/format the issue never gave |
| relatively loose | verbatim copy of the official grading test |

**Five guardrails to implement:** (1) provenance firewall — feed only the issue,
never the gold/official test; (2) fail-before validation; (3) prompt the
generator to test behavior, not brittle exact strings; (4) measure textual
overlap with the official test and flag near-duplicates as suspected
leakage/overfit; (5) grade with the hidden official test regardless — the
generated test is only a helper.

This also *is* a research object: hypothesis **H2** says repro tests help but
low-quality ones cause test-overfitting, so we log test quality (reproducing?,
overlap with official?, overfit?) to study which tests actually help.

**Status:** DESIGN AGREED, IMPLEMENTATION DEFERRED — the team will research the
boundary and decide the exact policy before we build it.

## 8. Copilot SDK — two separate questions

- **As the C2 test generator?** Not by default: it injects an uncontrolled model
  (version/prompt) into a controlled condition, contaminating causal claims. Use
  the pinned model instead. (Could be studied separately as an alternative.)
- **As a baseline agent?** Yes — this is exactly the proposal's "ecological
  validation subject" (§7.2). Wrap it as another `AgentRunner` (`copilot_adapter`)
  alongside mini-SWE-agent/Agentless. Treat as validation, not main causal
  evidence. Verify the real SDK surface (headless support, log capture) before
  building.

## 9. Immediate decision (today)

- **Do not add C2 (tests) or strengthen other layers yet.** Leave support as-is.
- **Run one C0 vs C6 pilot** on a few real SWE-bench Verified tasks with the
  fixed local model, Docker-evaluated, and report results.
- Revisit C2 after the team researches the test-generation boundary.
