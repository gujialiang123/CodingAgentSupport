"""se_support: controlled-ablation framework for coding-agent support structures.

This package implements the infrastructure for the SE-Support Study (see
``PROJECT_PROPOSAL.md``). The current milestone (T0 + T1) provides:

* Typed data models / data contracts (``se_support.schemas``).
* JSON-schema export for those models.
* Run-directory + JSONL logging conventions (``se_support.runner.run_dir``)
  designed so that new metrics can be recomputed from raw logs *without*
  re-running expensive experiments.
* A minimal CLI entry point (``python -m se_support``).
"""

__version__ = "0.1.0"

__all__ = ["__version__"]
