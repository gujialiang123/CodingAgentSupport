"""SWE-bench Verified importer (T2).

Converts SWE-bench-shaped records into :class:`TaskSpec` JSONL. The record→TaskSpec
mapping is pure and unit-tested against a small fixture (no download). Pulling the
real dataset requires the optional ``datasets`` package (extra ``.[data]``) and is
imported lazily, so the rest of the toolkit has no heavy dependency.

SWE-bench Verified record fields used:
``instance_id, repo, base_commit, patch, test_patch, problem_statement,
FAIL_TO_PASS, PASS_TO_PASS, environment_setup_commit, version`` -- where
FAIL_TO_PASS / PASS_TO_PASS are JSON-encoded lists of pytest node ids.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from se_support.schemas import TaskSpec

DATASET_NAME = "SWE-bench/SWE-bench_Verified"
DATASET_ID = "swebench_verified"


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return []
        try:
            parsed = json.loads(value)
            return [str(v) for v in parsed] if isinstance(parsed, list) else [value]
        except json.JSONDecodeError:
            return [value]
    return [str(value)]


def _title_from_problem(problem: str) -> str:
    for line in problem.splitlines():
        line = line.strip()
        if line:
            return line[:200]
    return ""


def record_to_taskspec(
    record: dict[str, Any],
    gold_dir: Path,
    test_dir: Path,
    dataset: str = DATASET_ID,
) -> TaskSpec:
    """Map one SWE-bench record to a TaskSpec, writing gold/test patches to disk."""
    instance_id = record["instance_id"]
    repo = record["repo"]
    gold_dir.mkdir(parents=True, exist_ok=True)
    test_dir.mkdir(parents=True, exist_ok=True)

    gold_path = gold_dir / f"{instance_id}.patch"
    gold_path.write_text(record.get("patch", "") or "", encoding="utf-8")

    test_patch = record.get("test_patch", "") or ""
    test_path = None
    if test_patch:
        tp = test_dir / f"{instance_id}.test.patch"
        tp.write_text(test_patch, encoding="utf-8")
        test_path = str(tp)

    problem = record.get("problem_statement", "") or ""
    return TaskSpec(
        task_id=f"{dataset}__{instance_id}",
        dataset=dataset,
        repo=repo,
        base_commit=record["base_commit"],
        issue_title=_title_from_problem(problem),
        issue_body=problem,
        gold_patch_path=str(gold_path),
        test_patch_path=test_path,
        environment_setup_commit=record.get("environment_setup_commit"),
        version=str(record.get("version")) if record.get("version") is not None else None,
        fail_to_pass_tests=_as_list(record.get("FAIL_TO_PASS")),
        pass_to_pass_tests=_as_list(record.get("PASS_TO_PASS")),
        metadata={
            "language": "python",
            "repo_group": repo.split("/")[0],
        },
    )


def iter_records(
    *,
    limit: int | None = None,
    fixture_path: Path | None = None,
    split: str = "test",
) -> Iterable[dict[str, Any]]:
    """Yield raw SWE-bench records.

    * If ``fixture_path`` is given, read newline-delimited JSON records (offline).
    * Otherwise load the real dataset via the optional ``datasets`` package.
    """
    if fixture_path is not None:
        n = 0
        for line in Path(fixture_path).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)
            n += 1
            if limit is not None and n >= limit:
                return
        return

    try:
        from datasets import load_dataset
    except ImportError as exc:  # pragma: no cover - requires optional extra
        raise ImportError(
            "loading the real SWE-bench dataset requires the 'datasets' package; "
            "install `.[data]` or pass a fixture_path for offline use."
        ) from exc
    ds = load_dataset(DATASET_NAME, split=split)
    for i, record in enumerate(ds):
        if limit is not None and i >= limit:
            return
        yield record


def import_swebench_verified(
    output_jsonl: Path,
    *,
    limit: int | None = None,
    fixture_path: Path | None = None,
    gold_dir: Path | None = None,
    test_dir: Path | None = None,
) -> int:
    """Import records into a TaskSpec JSONL file. Returns the number written."""
    from se_support.config import data_dir

    output_jsonl = Path(output_jsonl)
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    gold_dir = gold_dir or (data_dir() / "gold_patches")
    test_dir = test_dir or (data_dir() / "test_patches")

    count = 0
    with output_jsonl.open("w", encoding="utf-8") as fh:
        for record in iter_records(limit=limit, fixture_path=fixture_path):
            task = record_to_taskspec(record, gold_dir, test_dir)
            fh.write(task.model_dump_json() + "\n")
            count += 1
    return count
