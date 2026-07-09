"""Dataset importers and task sampling.

Importers produce dataset-agnostic :class:`~se_support.schemas.TaskSpec` JSONL.
Real dataset loading needs the optional ``datasets`` package (extra ``.[data]``);
the pure record→TaskSpec mapping and sampling work offline.
"""

from se_support.datasets.swebench_importer import (
    DATASET_ID,
    DATASET_NAME,
    import_swebench_verified,
    iter_records,
    record_to_taskspec,
)
from se_support.datasets.task_sampler import load_tasks, sample_tasks, write_tasks

__all__ = [
    "DATASET_ID",
    "DATASET_NAME",
    "import_swebench_verified",
    "iter_records",
    "record_to_taskspec",
    "load_tasks",
    "sample_tasks",
    "write_tasks",
]
