# Experiment Logs

One Markdown file per experiment, recording its **purpose, setup, results, and
where the raw logs live**. This is the human-readable index on top of the
machine artifacts under `runs/` and `results/`.

## Conventions

- **Filename:** `NNN_short-name.md`, e.g. `001_smoke-c0-c6.md`. `NNN` is a
  zero-padded incrementing id.
- **`experiment_id`** used inside the file must match the directory name under
  `runs/{experiment_id}/` so logs and records line up.
- Copy [`TEMPLATE.md`](TEMPLATE.md) to start a new experiment.
- Fill **Purpose / Setup** *before* running; fill **Results / Findings** after.
- Never edit raw `runs/` artifacts by hand; this file interprets them.

## Index

| id | experiment_id | title | status |
|---|---|---|---|
| 001 | smoke | Mock pipeline smoke test | done |
| 002 | real_smoke | Real 4090 smoke run (Qwen2.5-Coder-7B) | done |
| 003 | docker_eval_check | SWE-bench Docker evaluation validated | done |
| 004 | pilot01 | First real C0 vs C6 pilot (SWE-bench Verified) | done |
| 005 | feasib01 | Integrated-pipeline feasibility (7B, C0/C2/C4/C6) | done |
| 006 | formal01 | Formal-standard C0 vs C6 with 7B | done (6/12) |
| 007 | ablation01 | Full C0–C6 ablation with qwen3.7-plus (302.ai) | done |
| 008 | ablation02 | Scaled C0–C6 ablation (12 tasks × 5 repos) | done |
| 009A | exp009a_t25 | Full-stack budget & orchestration diagnosis | DONE — harness (C4) is C6's deficit driver; budget (C6@50) does not recover resolution |
| 010 | exp010_c2xc3 | C2×C3 2×2 (helper tests × gates) on 7 T3/T4 tasks, 3 seeds, frozen helpers | DONE — C2 & C3 each lift resolution 0.38→0.52; no stacking on resolution; C2_C3 lowest P2P regression (safety benefit) |
