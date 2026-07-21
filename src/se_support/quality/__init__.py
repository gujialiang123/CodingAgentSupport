"""Quality: PatchQualityCard computation.

``build_card`` computes the v0 card (functional correctness + locality) from a
run's artifacts. It is intentionally an **offline, re-runnable** function taking
already-recorded inputs (EvalResult + final diff + optional gold diff), so new
metrics can be back-filled without re-running the agent.
"""

from se_support.quality.quality_card import build_card, recompute_card_from_run_dir

__all__ = ["build_card", "recompute_card_from_run_dir"]
