# Forensics — `psf/requests-1142` "66–68 changed files" (integrity fix)

## Question

Experiment 010 (and 009A) reported ~66–68 changed files for `requests-1142`
across **every** condition, including C0. Was this the agent (e.g. running a
whole-repo formatter), a dirty base image, or an experiment-setup mutation?

## Method

The integrity-fix run flow captures a git-state snapshot **S0** immediately after
the container starts, before any support setup or agent action
(`integrity/git_state_s0.json`). A live C2 run on `requests-1142` was inspected.

## Finding

**The SWE-bench base image for `psf__requests-1142` ships an untracked
`build/lib/requests/` tree (~65 files) in the working directory at container
start.** S0 shows:

```
clean (tracked): True   # zero modified/deleted tracked source files
untracked files: 65     # build/lib/requests/**  (a shipped build output)
```

These files are present **before the agent runs and before any support setup** —
they are part of the pristine image, identical across all conditions. They are
not agent behavior.

### Why it produced 66–68 "changed files"

The pre-integrity extractor ran `git add -A` and diffed against HEAD. Since
`build/lib/**` is untracked (not in the base commit), `git add -A` staged all ~65
files plus the agent's real edit (`requests/models.py`) plus, for C2/C6, the
injected helper — giving ~66–68 files in `final.patch` for every condition.

### Why every `requests-1142` run also failed to apply

When the official evaluator `git apply`-ed a patch that **re-adds** files already
present in its own (identical) base image, application failed
(`patch_applies=False`), so the agent's genuine `requests/models.py` fix was
never scored. All 12 runs (4 conditions × 3 seeds) were false negatives.

## Decision

`build/lib/**` is a **pre-existing base-image build artifact**, not agent output.
Correct handling (now implemented, protocol 0.3.0):

1. **Retain the runs** — do not mark them infrastructure_failure. The image state
   is uniform and benign; only tracked-source mutation or *new* post-S0 untracked
   files are treated as infrastructure failures.
2. **Exclude the base-image untracked set from the agent patch** (recorded at S0
   as `base_untracked` and passed as extra excludes to the extractor).
3. **Re-evaluate** the historical patches with the sanitized diff.

## Result after the fix

Live re-run (protocol 0.3.0): S0 clean (65 untracked, 0 tracked changes), S1
clean, `final.patch = [requests/models.py]` only, `files_touched = 1`,
`resolved = True`. Official re-evaluation of all 12 historical `requests-1142`
runs: `applies False→True`, `resolved False→True` for **12/12**. See
`010_c2xc3_erratum.md`.
