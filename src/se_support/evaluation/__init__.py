"""Evaluation: functional-correctness scoring of patches.

``local_eval`` provides an offline evaluator (no Docker) used for fixture runs
and pipeline validation. A SWE-bench Docker evaluator lands later behind the
same :class:`~se_support.schemas.EvalResult` contract.
"""

from se_support.evaluation.local_eval import evaluate_patch

__all__ = ["evaluate_patch"]
