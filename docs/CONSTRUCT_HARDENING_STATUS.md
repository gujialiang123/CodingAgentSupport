# Construct-Hardening Status (Stage 1)

Tracks the engineering work packages from `EXPERIMENT_PLAN_2026-07-21.md` §14 and
the go/no-go checklists §15. Updated as packages land.

## Work packages

| EP | Package | Status | Notes |
|----|---------|--------|-------|
| EP-00 | Protocol/schema freeze | ✅ done | `protocol_version`/`condition_version`/`experiment_id` on RunSpec; `ManipulationCheck` schema. |
| EP-01 | Sandbox + provenance firewall | ✅ done | `se_support.isolation`: bwrap fs+network confinement, git-history flatten, scrubbed task, hashed manifest; red-team tests pass. |
| EP-02 | Frozen SupportBundle | ✅ done | `build_bundle`: C0 empty, C6 = union of C1–C5 (hash-verified), C2 `declared_unimplemented`. |
| EP-03 | C2 reproduction-test pipeline | ✅ done | `repro_tests/`: K=3 blind generator, T0–T4 classifier, provenance/leakage audit, semantic-audit (S), frozen read-only injection; canonical astropy-13033 fixture + runnable synthetic acceptance fixture. Full run-integration (per-task generation in the isolated generator zone) is the remaining wiring. |
| EP-04 | C4 enforced harness | ✅ done | `HarnessStateMachine`; agent reverts edits outside PATCH/VALIDATE and blocks premature SUBMIT; transitions logged. |
| EP-05 | C1 context v2 | ⬜ todo | Retrieval-based, budgeted context; v1 (file map + test hints) in place. |
| EP-06 | C5 memory v2 | ⬜ todo | Repository profiler, one frozen artifact per repo; v1 in place. |
| EP-07 | C3 gate policy v2 | ✅ done | Frozen `GatePolicy` (blocking/advisory), base-vs-patch delta (legacy warnings excluded), revision budget; official tests never a gate. |
| EP-08 | Quality card v1 | ✅ done | Process/trajectory metrics; Q-levels capped at Q2 automatically; offline recompute from run dir. |
| EP-09 | Experiment scheduler | ✅ done | `experiment/scheduler.py`: randomized, resumable (deterministic run_id + completion marker), infra-only retries, sandbox default-on. A1–A4 wired C2 generation, sandbox default, and per-run manipulation checks into `run_single`. Validated end-to-end in Experiment 005. |
| EP-10 | Analysis/annotation package | ⬜ todo | Paired tables, McNemar/bootstrap, annotation sampler (needed for E4/analysis). |

## Go/no-go — Before E1 (§15)

- [x] Agent filesystem and network isolation passes adversarial tests — EP-01
- [x] Gold patch / official test patch / test ids absent from agent-visible inputs — EP-01
- [x] Frozen support-bundle interface implemented — EP-02
- [x] Canonical Astropy helper-test fixture passes base/gold/semantic checks — EP-03
- [x] B/J/H/A/S outcomes have separate schema fields — EP-03 (`ReproTestResults`)
- [x] Main agent/model/budget configuration recorded — EP-00 / RunSpec

All Before-E1 construct items are now implemented. Remaining before running E1 is
operational: wire per-task helper generation into the isolated generator zone
(pre-run), and build the E0/E1 experiment drivers (EP-09 scheduler helps here).

## Suggested next steps (unblocked)

1. **Run large-model experiments** on a bigger-GPU machine — see `docs/HANDOFF.md`
   (the pipeline is turn-key; only the pinned model/endpoint changes).
2. EP-05 / EP-06 — strengthen and separate C1 context and C5 memory.
3. EP-10 — analysis/annotation package (paired McNemar/bootstrap, annotation sampler).
4. Address `docs/HANDOFF.md` §5 limitations (C2 validation + agent execution inside
   the task Docker image) before publication-grade runs.
