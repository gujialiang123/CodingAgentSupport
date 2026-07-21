# Canonical C2 fixture: astropy__astropy-13033

Reference artifacts for the C2 reproduction-test boundary (EXPERIMENT_PLAN
_2026-07-21.md §5.4). The `helper_test.py` here is a *valid decoupled* helper (T4):
it fails on the base commit, passes on the gold patch, and asserts only the
issue-level behavior ("the message names the removed required column") — never the
maintainer's exact string.

`semantic_audit_test.py` (hidden, class S) parametrizes the column name so a patch
that hard-codes `flux` is caught.

These run against the real astropy repo. For fast, offline pipeline tests see
`tests/fixtures/repro_demo/`, a self-contained synthetic repo with the same
structure (base bug, gold patch, hardcoded-bad patch, helper, semantic audit).
