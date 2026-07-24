# Experiment 011 — Integrity smoke (protocol 0.3.0)

One-task validation that the integrity fixes work end-to-end in a live container
before any large rerun. Task: `psf/requests-1142` (T4 helper), condition
`C2_tests`, 1 seed, in-container.

## Checks and results

| Check | Result |
|-------|--------|
| S0 clean (no modified tracked files at container start) | PASS (65 untracked `build/lib`, 0 tracked changes) |
| S0 base-image untracked recorded as baseline | PASS (65 paths) |
| S1 clean (support setup did not mutate the repo) | PASS (0 unexplained) |
| Helper mounted read-only at `/testbed/.se_support/helper_test.py` | PASS (readable) |
| Helper **cannot** be written | PASS (`echo >> helper` → "Read-only file system") |
| Helper **cannot** be deleted | PASS (`rm helper` → "Read-only file system") |
| Helper SHA-256 before == after | PASS (unchanged) |
| `final.patch` excludes the helper | PASS (`helper_leak=false`) |
| `final.patch` excludes base-image `build/lib` | PASS (only `requests/models.py`) |
| Real git index not mutated (temp `GIT_INDEX_FILE`) | PASS (by construction) |
| Official evaluation runs on the sanitized patch | PASS |
| `files_touched` correct | PASS (**1**, was 67 pre-fix) |
| Task resolves | PASS (`resolved=True`) |

## Artifacts (per run dir)

- `integrity/git_state_s0.json`, `git_state_s1.json`, `git_state_s2.json`
- `integrity/patch_manifest.json` (included/excluded paths, patch sha, helper_leak)
- `integrity/helper_hash.json` (host + container before/after)
- `integrity/provenance.json` (protocol/condition/extractor/gate versions, SHAs, image)

## Conclusion

The read-only helper mount, clean-tree S0/S1/S2 invariants, and safe filtered
patch extraction all behave as specified. The repository is ready for a
protocol-0.3.0 C2×C3 rerun. Do not mix 0.3.0 results with earlier (contaminated)
runs.
