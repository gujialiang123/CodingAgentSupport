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
| _(none yet)_ | | | |
