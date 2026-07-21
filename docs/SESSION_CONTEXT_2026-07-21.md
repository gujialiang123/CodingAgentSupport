# Session Context Log — 2026-07-21

A durable, human-readable record of the decisions and dialogue driving this
session's work, so future analysis/reproduction has the *why*, not just the code.
Complements `DISCUSSION_2026-07-09.md` (earlier design) and
`EXPERIMENT_CONFIGS.md` (exact run configs).

## Starting point

Session resumed at `main@73c5266` (after Exp 004). The user provided a detailed
`EXPERIMENT_PLAN_2026-07-21.md` and asked to build the experimental constructs to
"formal experiment" standard, then run feasibility with 7B, then move big-model
runs to a bigger-GPU machine.

## Key decisions this session

1. **Adopt the execution plan.** Committed `EXPERIMENT_PLAN_2026-07-21.md` as the
   execution-level protocol; `experiment_protocol.md` references it.

2. **Construct-hardening first** (plan §16 order). Implemented, each with tests:
   - EP-00 protocol/schema freeze (+ `ManipulationCheck`).
   - EP-01 sandbox + provenance firewall (bubblewrap: no network, fs-confined;
     git-history scrub; gold/official-test scrub; hashed visible-input manifest).
   - EP-02 frozen `SupportBundle` (C0 empty; C6 = union of C1–C5; C2 honestly
     `declared_unimplemented` until a valid helper exists).
   - EP-04 enforced C4 harness state machine (edits reverted outside PATCH/VALIDATE;
     SUBMIT gated; later: forward multi-step transitions so weak models don't loop).
   - EP-07 frozen C3 gate policy (blocking/advisory, base-vs-patch delta so legacy
     warnings aren't blamed on the patch, revision budget).
   - EP-08 quality card v1 (process/trajectory metrics; Q auto-capped at Q2;
     offline recompute).

3. **C2 boundary — the plan already answered it.** The user initially deferred C2
   pending research, then clarified that the plan's §5 *is* the conclusion.
   Implemented EP-03: five test classes B/J/H/A/S, T0–T4 classification, K=3 blind
   generation (issue-only), provenance/leakage audit, hidden semantic audit (S),
   frozen read-only injection. Canonical `astropy__astropy-13033` fixture + runnable
   synthetic `repro_demo` fixture.

4. **Turn-key integration (A1–A4 + EP-09).** C2 generation in a pre-run generator
   zone; sandbox default-on; per-run manipulation checks; randomized, resumable,
   later **concurrent** scheduler.

5. **7B is plumbing only.** Feasibility runs (Exp 005/006) confirmed the pipeline
   but 7B resolved ~0 on full SWE-bench Verified — expected. Fairness fixes were
   added (disclose no-network env; forbid interactive editors; forgiving harness
   transitions) so weak-model failure is honest, not an artifact. Finding carried
   forward: the enforced harness can *cost* budget for weak models.

6. **Capable model via 302.ai.** The user supplied an OpenAI-compatible endpoint
   (`https://api.302.ai/v1`, model `qwen3.7-plus`). Verified `OpenAIChatClient`
   works against it (it returns `reasoning_content` + `content`; we use `content`).
   Added `--max-tokens` (reasoning headroom) and `--max-workers` (concurrency, safe
   for API models). The user also asked for **more tasks and more conditions than
   just 3 tasks / C0+C6** — so Exp 007 ran **5 tasks × all 7 conditions (C0–C6)**.

7. **Reproducibility mandate.** The user asked to save all configs and context in
   the repo. Added `EXPERIMENT_CONFIGS.md` (per-experiment config + exact command,
   keys redacted) and this file. API keys are never committed.

## Experiment 007 headline (see `docs/experiments/007_*`)

qwen3.7-plus, 5 `psf/requests` tasks, C0–C6 (35 runs), sandbox on, Docker eval:
resolution by condition — C0 3/5, C1 3/5, C2 4/5, C3 2/5, C4 4/5, C5 4/5, C6 2/5.
Directional signal (n=5, no stats): single supports (C2/C4/C5) tend to beat C0;
C6 full-stack was worst under the tight 15-turn budget (over-constrained). To be
re-tested at scale with larger budgets and in-container C2 helper validation.

## Open items for the bigger-GPU / scale session

- Scale cohort (more tasks, more repos beyond `psf/requests`), add seeds, raise
  the turn budget; re-check whether C6 recovers.
- In-container C2 helper validation + agent execution (deps available).
- EP-05/EP-06 (strengthen C1/C5), EP-10 (analysis: McNemar/bootstrap, annotation).
- Human annotation for RQ1/RQ3.
