"""Evaluation: functional-correctness scoring of patches.

* ``local_eval`` -- offline evaluator (no Docker), for fixtures/pipeline dev.
* ``swebench_eval`` -- official SWE-bench Docker harness wrapper, the
  authoritative evaluator for real tasks.

Both return the same :class:`~se_support.schemas.EvalResult`.
"""

from se_support.evaluation.local_eval import evaluate_patch
from se_support.evaluation.swebench_eval import evaluate_with_docker

__all__ = ["evaluate_patch", "evaluate_with_docker"]
