# Protocol 0.3.1 freeze

Frozen definition for the Qwen open-weight E1 C2×C3 study. Runs under this freeze
are **not** poolable with any protocol < 0.3.1 or any other model checkpoint.

## Versions & commit

- `protocol_version = 0.3.1`
- `condition_version = 0.2.0`
- Freeze commit: recorded in each run's `integrity/provenance.json` (`base_commit`
  of the harness repo = `git rev-parse HEAD` on `experiment/protocol-031-qwen-e1`).

## Support definitions (frozen)

- **C0_minimal** — base prompt only. Shared operational access (may run the repo's
  tests with pytest) is available to ALL conditions.
- **C2_tests** — a frozen, container-validated T3/T4 helper reproduction test,
  delivered **read-only** at `/testbed/.se_support/helper_test.py`. Never in the
  git tree or final patch.
- **C3_gates** — C3 v2 repo-aware gates: blocking = compileall (syntax) + import
  of changed modules + repo-native targeted tests for changed modules; advisory =
  ruff/flake8/mypy **only when the repo configures them**. Revision budget 3. The
  official hidden tests are never a gate.
- **C2_C3** — C2 + C3 together.
- **Not run in E1:** C1, C4, C5, C6.

## Hidden / visible information policy

Visible to the agent: base repository, its dependencies (installed in the
container), public/base tests, repo-native lint/type/build tools, and — for
C2/C2_C3 — the read-only helper. Hidden: official `test_patch`,
FAIL_TO_PASS/PASS_TO_PASS ids, gold patch, any semantic hidden tests. Network is
disabled (`--network none`).

## Helper T0–T4 policy

Helpers are generated blind (issue + base repo/tests only; never gold/official
tests/PR/future history), frozen, then classified T0–T4 by container execution
(base-fail + gold-pass + leakage audit). Only **T3/T4** helpers are used for C2;
T0–T2 are reported as feasibility, never silently dropped. Helper-hash mismatch
at run time ⇒ `infrastructure_failure`/`HELPER_INTEGRITY`.

## Gate-policy version

`c3v2/0.2.0` (`gate_policy_v2`), extractor version `2`.

## Budgets

- Turns: 25; max output tokens: 4096; temperature 0.0; top_p default.
- Wall-time: harness default per run; official eval timeout 1800 s.
- Gate revision budget: 3.

## Retry & infrastructure-failure rules

- `infrastructure_failure` stages: `S0_CONTAINER_START`, `S1_PRE_AGENT`,
  `HELPER_INTEGRITY`. These are excluded from agent-performance statistics.
- Retry **only** infrastructure failures (bounded, `max_infra_retries`); never
  retry an ordinary agent failure.

## Official outcome definitions

- Primary: official SWE-bench `resolved` (FAIL_TO_PASS all pass + PASS_TO_PASS all
  pass under the official harness).
- Secondary: `patch_applies`, F2P/P2P counts, P2P regression (denominator =
  applying + P2P total > 0), empty patch, timeout, infra failure, files touched /
  LOC, token/turn/command/wall-time cost.

## Analyses

- Primary unit = **task** (seeds are repeated measurements, not independent tasks).
- Primary paired comparisons: C2 vs C0, C3 vs C0, C2_C3 vs C0 (exact McNemar +
  paired bootstrap CIs). Factorial: helper main effect, gate main effect,
  helper×gate interaction.
- No post-hoc metric fishing; no protocol changes after seeing results.

## Dataset partitions

- **D0** = the 12 development/diagnostic tasks (Exp 008–011). Permanently excluded
  from confirmatory effect estimates.
- **E1** = new tasks sampled from SWE-bench Verified with a fixed documented seed,
  excluding all previously used tasks. C2 efficacy is estimated **conditional on a
  valid (T3/T4) helper**; the 40-candidate feasibility estimates helper coverage.

## Model manifest

See `docs/MODEL_FREEZE_QWEN3_CODER_E1.md` / `configs/models/qwen3_coder_e1.yaml`.
Model ID `qwen3-coder-30b-a3b-instruct` via the 302.ai OpenAI-compatible endpoint;
server `model` field asserted per call. Weight-level SHAs not verifiable via API
(documented limitation).

## Rule

No change to prompts, budgets, model, conditions, or analysis after E1 results are
observed. Any such change starts a new protocol version.
