"""EvalResult: functional-correctness outcome of one run (section 9.4).

Produced by applying the final patch to a clean checkout and running the
official evaluator + deterministic gates. These are the *correctness* metrics
(RQ2). Non-functional quality lives in PatchQualityCard.
"""

from __future__ import annotations

from se_support.schemas.base import SEModel


class EvalResult(SEModel):
    run_id: str
    patch_applies: bool = False
    build_success: bool = False
    fail_to_pass_passed: int = 0
    fail_to_pass_total: int = 0
    pass_to_pass_passed: int = 0
    pass_to_pass_total: int = 0
    resolved: bool = False
    full_tests_status: str | None = None  # "pass" | "fail" | "partial" | None
    gate_results_path: str | None = None
    eval_log_path: str | None = None
