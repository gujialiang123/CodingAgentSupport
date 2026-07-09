"""Data contracts for the SE-Support Study.

Public models (each maps to one ``schemas/<name>.schema.json`` export):

* :class:`TaskSpec`         -- one repository-level task (run input).
* :class:`RunSpec`          -- parameters of one experimental run.
* :class:`AgentRunResult`   -- pointers to raw artifacts produced by a run.
* :class:`EvalResult`       -- functional-correctness outcome (RQ2).
* :class:`PatchQualityCard` -- non-functional quality (RQ3).
"""

from __future__ import annotations

from pathlib import Path

from se_support.schemas.agent_run_result import AgentRunResult, RunStatus
from se_support.schemas.base import SEModel
from se_support.schemas.eval_result import EvalResult
from se_support.schemas.patch_quality_card import PatchQualityCard, QualityLevel
from se_support.schemas.run_spec import RunSpec
from se_support.schemas.task_spec import TaskMetadata, TaskSpec

__all__ = [
    "SEModel",
    "TaskSpec",
    "TaskMetadata",
    "RunSpec",
    "AgentRunResult",
    "RunStatus",
    "EvalResult",
    "PatchQualityCard",
    "QualityLevel",
    "EXPORTED_MODELS",
    "export_schemas",
]

# Model -> exported schema filename. This is the single source of truth for
# `python -m se_support schemas export`.
EXPORTED_MODELS: dict[str, type[SEModel]] = {
    "task_spec": TaskSpec,
    "run_spec": RunSpec,
    "agent_run_result": AgentRunResult,
    "eval_result": EvalResult,
    "patch_quality_card": PatchQualityCard,
}


def export_schemas(output_dir: Path) -> list[Path]:
    """Write ``<name>.schema.json`` for every exported model. Returns paths."""
    import json

    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name, model in EXPORTED_MODELS.items():
        path = output_dir / f"{name}.schema.json"
        path.write_text(json.dumps(model.json_schema(), indent=2, sort_keys=True) + "\n")
        written.append(path)
    return written
