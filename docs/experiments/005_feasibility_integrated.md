# Experiment 005: Integrated-pipeline feasibility (7B, C0/C2/C4/C6)

- **experiment_id:** `feasib01`
- **date:** 2026-07-21
- **author:** gujialiang123
- **status:** done

## 1. Purpose

Validate that the **fully integrated confirmatory pipeline** (after the construct-
hardening work packages EP-00…EP-08 + A1–A4/EP-09) runs end-to-end across
conditions on real SWE-bench tasks: information isolation, frozen support bundles,
C2 helper generation, enforced harness, gates, official Docker evaluation, quality
cards with process metrics, per-run manipulation checks, and the randomized
**resumable** scheduler. This is a **feasibility/plumbing** check — **not** a
research result. The 7B model is for plumbing only.

## 2. Setup

| Field | Value |
|---|---|
| Dataset | SWE-bench Verified |
| Tasks | 2 × `psf/requests` (`requests-1142`, `requests-1724`) |
| Conditions | C0_minimal, C2_tests, C4_harness, C6_full_stack |
| Agent | controllable `LLMAgent` (bash-loop) |
| Model | Qwen/Qwen2.5-Coder-7B-Instruct (local vLLM, 4090) |
| Isolation | bubblewrap sandbox ON (no network, fs-confined) |
| C2 | helper generated pre-run (generator zone) via same model |
| Evaluation | official SWE-bench Docker harness (rootless Docker) |
| Scheduler | EP-09 (randomized, resumable, infra-retry); max_turns 8–15 |

Command (resumable — re-running resumes):

```bash
python -m scripts.run_feasibility --tasks data/tasks/pilot_requests.jsonl \
  --conditions C0_minimal C2_tests C4_harness C6_full_stack \
  --model Qwen/Qwen2.5-Coder-7B-Instruct --base-url http://localhost:8000/v1 \
  --experiment-id feasib01 --max-turns 8 --output runs/feasib01 \
  --results results/feasib01.jsonl
```

## 3. Where the logs live

- Raw runs: `runs/feasib01/feasib01/<run_id>/` (git-ignored; each self-contained:
  transcript, commands, scrubbed_task, visible_input_manifest, support bundle +
  helper_artifact, manipulation.json, docker_eval, quality_card).
- Results: `results/feasib01.jsonl`.

## 4. Results

| Condition | Task | resolved | applies | quality | sandbox | manip_ok | net_off | helper |
|---|---|---|---|---|---|---|---|---|
| C0 | requests-1142 | False | False | Q0 | bwrap | ✅ | ✅ | – |
| C0 | requests-1724 | False | False | Q0 | bwrap | ✅ | ✅ | – |
| C2 | requests-1142 | False | False | Q0 | bwrap | ✅ | ✅ | T0 |
| C2 | requests-1724 | False | False | Q0 | bwrap | ✅ | ✅ | T0 |
| C4 | requests-1142 | False | False | Q0 | bwrap | ✅ | ✅ | – |
| C4 | requests-1724 | False | False | Q0 | bwrap | ✅ | ✅ | – |
| C6 | requests-1142 | False | False | Q0 | (none)* | ✅ | ✅ | T0 |
| C6 | requests-1724 | False | False | Q0 | (none)* | ✅ | ✅ | T0 |

\* C6 `sandbox_backend` is `none` in process metrics only because the agent ran
**no bash commands** under harness before the turn budget; the sandbox policy was
still applied (manipulation `network_disabled=True`).

## 5. Findings

- **The integrated confirmatory pipeline runs end-to-end across all conditions.**
  Every cell produced a complete, isolated, logged run and an official Docker
  evaluation. Manipulation checks passed; network was disabled and no gold/official
  -test data reached agent-visible inputs in any cell.
- **The EP-09 scheduler works**: randomized order + resume (verified by killing and
  re-launching — completed cells were skipped) + per-cell isolation.
- **7B resolves nothing here (all Q0).** Expected and honest: under the sandbox the
  agent operates in a *bare git clone without the repo's dependencies* and a small
  turn budget, so it cannot run the repo tests and mostly fails to produce an
  applying patch. This is a **plumbing** result, not a measure of support effects.
- **C2 helper = T0 for `requests`**: a bare clone lacks dependencies, so fail-before
  /pass-after validation cannot execute (generation + provenance + freeze still
  work). Documented in `docs/HANDOFF.md` §5.1 — validation must run inside the
  task's Docker image.

## 6. Conclusion / next steps

Feasibility is confirmed: the pipeline is ready to run at scale **once a capable
pinned model is available** (bigger-GPU machine or hosted API). Before publication-
grade runs, address the known limitations in `docs/HANDOFF.md` (C2 validation +
agent execution inside the task container; EP-05/06 construct strengthening;
EP-10 analysis package; human annotation). No support-effect claim is made from
this run.
