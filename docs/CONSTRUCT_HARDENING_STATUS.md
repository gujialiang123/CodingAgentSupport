# Construct-Hardening Status (Stage 1)

Tracks the engineering work packages from `EXPERIMENT_PLAN_2026-07-21.md` §14 and
the go/no-go checklists §15. Updated as packages land.

## Work packages

| EP | Package | Status | Notes |
|----|---------|--------|-------|
| EP-00 | Protocol/schema freeze | ✅ done | `protocol_version`/`condition_version`/`experiment_id` on RunSpec; `ManipulationCheck` schema. |
| EP-01 | Sandbox + provenance firewall | ✅ done | `se_support.isolation`: bwrap fs+network confinement, git-history flatten, scrubbed task, hashed manifest; red-team tests pass. |
| EP-02 | Frozen SupportBundle | ✅ done | `build_bundle`: C0 empty, C6 = union of C1–C5 (hash-verified), C2 `declared_unimplemented`. |
| EP-03 | C2 reproduction-test pipeline | ⏸️ **held** | Deferred by request pending research on the helper/official test boundary (see `DISCUSSION_2026-07-09.md`). |
| EP-04 | C4 enforced harness | ✅ done | `HarnessStateMachine`; agent reverts edits outside PATCH/VALIDATE and blocks premature SUBMIT; transitions logged. |
| EP-05 | C1 context v2 | ⬜ todo | Retrieval-based, budgeted context; v1 (file map + test hints) in place. |
| EP-06 | C5 memory v2 | ⬜ todo | Repository profiler, one frozen artifact per repo; v1 in place. |
| EP-07 | C3 gate policy v2 | ✅ done | Frozen `GatePolicy` (blocking/advisory), base-vs-patch delta (legacy warnings excluded), revision budget; official tests never a gate. |
| EP-08 | Quality card v1 | ✅ done | Process/trajectory metrics; Q-levels capped at Q2 automatically; offline recompute from run dir. |
| EP-09 | Experiment scheduler | ⬜ todo | Randomized, resumable schedule with infra-only retries (needed for E2/E3). |
| EP-10 | Analysis/annotation package | ⬜ todo | Paired tables, McNemar/bootstrap, annotation sampler (needed for E4/analysis). |

## Go/no-go — Before E1 (§15)

- [x] Agent filesystem and network isolation passes adversarial tests — EP-01
- [x] Gold patch / official test patch / test ids absent from agent-visible inputs — EP-01
- [x] Frozen support-bundle interface implemented — EP-02
- [ ] Canonical Astropy helper-test fixture passes base/gold/semantic checks — **EP-03 (held)**
- [ ] B/J/H/A/S outcomes have separate schema fields — **EP-03 (held)**
- [x] Main agent/model/budget configuration recorded — EP-00 / RunSpec

The only remaining Before-E1 items depend on C2 (EP-03), which is intentionally
held pending the team's research on the reproduction-test boundary. All stage-1
items that are **not** blocked by that decision are complete.

## Suggested next steps (unblocked)

1. EP-05 / EP-06 — strengthen and separate C1 context and C5 memory.
2. EP-09 — randomized, resumable experiment scheduler (prerequisite for E2/E3).
3. On the team's return: EP-03 (C2) using `astropy__astropy-13033` as the
   acceptance fixture, then run E0 (construct/manipulation smoke) and E1
   (C2 × C3 micro-study).
