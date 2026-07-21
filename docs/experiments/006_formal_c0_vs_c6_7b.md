# Experiment 006: Formal-standard C0 vs C6 with 7B

- **experiment_id:** `formal01`
- **date:** 2026-07-21
- **author:** gujialiang123
- **status:** done (6/12 cells; balanced 3×C0 + 3×C6)

## 1. Purpose

Run the **confirmatory standard** (full isolation + frozen bundles + enforced
harness/gates + official Docker eval + manipulation checks + randomized resumable
scheduler) with the 7B model and check whether results **match expectations**.
The 7B is a plumbing/feasibility model, not a research subject. The pre-registered
headline contrast is **C6 (full-stack) vs C0 (minimal)** (plan §10.1).

## 2. Setup

| Field | Value |
|---|---|
| Dataset | SWE-bench Verified |
| Cohort | 6 `psf/requests` tasks (small repo, fast clone) |
| Conditions | C0_minimal, C6_full_stack |
| Agent | controllable `LLMAgent`, max_turns 30 |
| Model | Qwen/Qwen2.5-Coder-7B-Instruct (local vLLM, 4090) |
| Isolation | bubblewrap ON (no network, fs-confined); history scrubbed |
| Evaluation | official SWE-bench Docker harness |
| Scheduler | EP-09 randomized + resumable; sandbox default-on |

Fairness fixes applied before this run (so the weak model is not trivially
crippled): base prompt discloses the no-network environment and requires
non-interactive edits; enforced harness accepts forward multi-step transitions
(atomic) so the model does not loop on single-step rejections.

Command (resumable — 6/12 done; re-run to finish the rest):

```bash
python -m scripts.run_feasibility --tasks data/tasks/formal_requests6.jsonl \
  --conditions C0_minimal C6_full_stack --model Qwen/Qwen2.5-Coder-7B-Instruct \
  --base-url http://localhost:8000/v1 --experiment-id formal01 --max-turns 30 \
  --output runs/formal01 --results results/formal01.jsonl
```

## 3. Where the logs live

- Raw runs: `runs/formal01/formal01/<run_id>/` (git-ignored; self-contained).
- Results: `results/formal01.jsonl`.

## 4. Results

| Cond | Task | resolved | applies | quality | turns | cmds | stop | manip_ok | net_off |
|---|---|---|---|---|---|---|---|---|---|
| C0 | 1724 | False | False | Q0 | 7 | 6 | submitted | ✅ | ✅ |
| C0 | 1921 | False | False | Q0 | 1 | 0 | submitted | ✅ | ✅ |
| C0 | 5414 | False | **True** | **Q1** | 2 | 1 | submitted | ✅ | ✅ |
| C6 | 1142 | False | False | Q0 | 30 | 0 | timeout | ✅ | ✅ |
| C6 | 1766 | False | False | Q0 | 30 | 9 | timeout | ✅ | ✅ |
| C6 | 1921 | False | False | Q0 | 30 | 1 | timeout | ✅ | ✅ |

**Per condition:** C0 — resolved 0/3, applying **1/3**, >Q0 **1/3**.
C6 — resolved 0/3, applying **0/3**, >Q0 **0/3**.

## 5. Do the results match expectations?

**Yes, on all three axes:**

1. **Resolution ~0 for 7B.** 0/6 resolved. Expected: a 7B model on *full*
   SWE-bench Verified (not Lite), under isolation, is known to score near zero.
   This is the correct sanity result, not a pipeline defect — the mock-agent gold
   path and Experiment 003 both confirm the pipeline returns `resolved=True` when
   the patch is correct.
2. **The pipeline registers differentiated quality.** Not everything is identical
   Q0: C0 on `requests-5414` produced an **applying** patch (Q1). The quality card,
   Docker eval, and process metrics all discriminate.
3. **Isolation held on every cell.** Manipulation checks passed; network disabled;
   no gold/official-test data in agent-visible inputs; sandbox engaged.

**Additional, informative finding (heterogeneous treatment effect):** the
**enforced harness (C6) hurt the weak model.** All three C6 cells **timed out** at
30 turns having run 0–9 commands — the 7B spent its budget negotiating the state
machine (emitting mis-ordered `NEXT_STATE` directives) instead of editing code. C0
(no harness) let the model act immediately (submits in 1–7 turns) and produced the
only applying patch. This is exactly the kind of condition-dependent effect the
study is designed to surface: a process scaffold that may help a capable model can
*reduce* effective work for a model that cannot follow the protocol. It should be
re-checked with the capable pinned model (where the harness is expected to help).

## 6. Caveats

- n=6 (3 per condition), single weak model, single seed — **no statistical claim**.
- 7B is a plumbing model; absolute resolution is not meaningful.
- The harness result is a hypothesis-generating observation, not a finding.

## 7. Conclusion

The confirmatory-standard pipeline runs correctly end-to-end and the 7B results
match expectations (≈0 resolution, differentiated quality, isolation intact). The
run is **ready to repeat with a capable pinned model** on a bigger-GPU machine
(`docs/HANDOFF.md`); the same command resumes/extends this experiment. Carry the
"enforced harness may hurt weak models" observation into the main study's
C4/C6 analysis.
