# Run Directory Specification

Every run writes a self-contained directory. This is the contract that makes
**post-hoc metric recomputation** possible: we store enough raw input + output
that a future script can compute new metrics without re-running the agent.

## Layout

```
runs/{experiment_id}/{run_id}/
    task.json                 # TaskSpec (the run input)
    run_spec.json             # RunSpec (pinned model / condition / seed)
    condition.yaml            # resolved support-condition config (later ticket)
    support/                  # injected support artifacts (context pack, AGENTS.md, ...)
    intermediate_patches/     # diff after each edit attempt (0001.diff, 0002.diff, ...)
    transcript.jsonl          # one TranscriptEvent per line (every agent step)
    commands.jsonl            # one CommandRecord per line (every shell command)
    final.patch               # final unified diff
    final_message.md          # agent's final summary message
    eval_result.json          # EvalResult (correctness)
    gate_results.json         # raw gate outputs
    quality_card.json         # PatchQualityCard (non-functional quality)
    logs/                     # large stdout/stderr dumps referenced by path
```

Canonical filenames are constants in `se_support/runner/run_dir.py` — always use
them rather than hard-coding strings.

## JSONL stream schemas

Fixed so producers and future metric consumers agree. Defined as Pydantic
models in `run_dir.py`.

### `transcript.jsonl` — `TranscriptEvent`

| Field | Type | Meaning |
|---|---|---|
| `ts` | str (ISO-8601 UTC) | timestamp |
| `step` | int | 0-based step index |
| `role` | str | `system` / `user` / `assistant` / `tool` |
| `content` | str | raw text of the step |
| `tokens_in` / `tokens_out` | int? | token usage if known |
| `meta` | object | free-form extras (model params, tool name, ...) |

### `commands.jsonl` — `CommandRecord`

| Field | Type | Meaning |
|---|---|---|
| `ts` | str | timestamp |
| `step` | int? | transcript step that issued the command |
| `command` | str | the shell command |
| `exit_code` | int? | process exit code |
| `duration_sec` | float? | wall-clock duration |
| `stdout_path` / `stderr_path` | str? | path under `logs/` for large output |
| `stdout_preview` | str | truncated inline stdout for quick reads |
| `meta` | object | free-form extras |

## Rules for what to capture

1. **Store paths, not blobs, for heavy data.** Large stdout goes to `logs/…`;
   the JSONL keeps only a preview + path.
2. **Always record `base_commit` + repo** (in `task.json`) and the exact
   **`model`** string (in `run_spec.json`) so the environment is reconstructable.
3. **Keep every intermediate patch**, not only the final one — process-quality
   metrics need them.
4. **Never overwrite; append.** JSONL streams are append-only during a run.
5. **Compress on archive.** `transcript.jsonl` / `commands.jsonl` may be gzipped
   after a run; readers should tolerate `.jsonl` and `.jsonl.gz` (future work).
