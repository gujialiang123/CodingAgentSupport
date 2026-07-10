"""SWE-bench official Docker evaluator (Ticket A / T-eval).

Wraps the official ``swebench.harness.run_evaluation`` so a run's ``final.patch``
is scored in the real, reproducible per-instance Docker environment (the
authoritative FAIL_TO_PASS / PASS_TO_PASS judgement).

Flow:
1. write a predictions file ``[{instance_id, model_name_or_path, model_patch}]``,
2. invoke the harness (subprocess) for that single instance,
3. read the per-instance report JSON it produces,
4. map it to :class:`~se_support.schemas.EvalResult`.

Requirements: Docker reachable (on this host: rootless, ``DOCKER_HOST=
unix:///run/user/<uid>/docker.sock``) and the ``swebench`` package (installed in
the ``swebench`` conda env). The harness pulls prebuilt images from the
``swebench`` namespace by default.

The instance_id is recovered from ``TaskSpec.task_id`` (``<dataset>__<instance>``).
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from se_support.schemas import EvalResult, TaskSpec

DEFAULT_DATASET = "SWE-bench/SWE-bench_Verified"
MODEL_TAG = "se_support"


def instance_id_from_task(task: TaskSpec) -> str:
    """Recover the SWE-bench instance_id from a TaskSpec.task_id."""
    prefix = f"{task.dataset}__"
    if task.task_id.startswith(prefix):
        return task.task_id[len(prefix):]
    return task.task_id


def write_predictions(task: TaskSpec, patch_text: str, path: Path) -> str:
    instance_id = instance_id_from_task(task)
    pred = {
        "instance_id": instance_id,
        "model_name_or_path": MODEL_TAG,
        "model_patch": patch_text,
    }
    path.write_text(json.dumps(pred) + "\n", encoding="utf-8")
    return instance_id


def _find_report(work_dir: Path, run_id: str, instance_id: str) -> dict | None:
    # Prefer the detailed per-instance report (has tests_status); fall back to
    # the top-level summary written as <model>.<run_id>.json in cwd.
    candidates = [
        work_dir / "logs" / "run_evaluation" / run_id / MODEL_TAG / instance_id / "report.json",
        work_dir / f"{MODEL_TAG}.{run_id}.json",
    ]
    for c in candidates:
        if c.exists():
            return json.loads(c.read_text())
    return None


def _eval_from_report(report: dict, instance_id: str, run_id: str) -> EvalResult:
    # Top-level summary report shape:
    # {"resolved_ids": [...], "unresolved_ids": [...], "error_ids": [...], ...}
    # Per-instance report shape: {instance_id: {"resolved": bool,
    #   "tests_status": {"FAIL_TO_PASS": {"success": [...], "failure": [...]},
    #                    "PASS_TO_PASS": {...}}, "patch_successfully_applied": bool}}
    inst = report.get(instance_id, report)
    resolved = bool(
        inst.get("resolved", instance_id in report.get("resolved_ids", []))
    )
    applied = bool(inst.get("patch_successfully_applied", False))

    status = inst.get("tests_status", {})
    f2p = status.get("FAIL_TO_PASS", {})
    p2p = status.get("PASS_TO_PASS", {})
    f2p_pass = len(f2p.get("success", []))
    f2p_total = f2p_pass + len(f2p.get("failure", []))
    p2p_pass = len(p2p.get("success", []))
    p2p_total = p2p_pass + len(p2p.get("failure", []))

    return EvalResult(
        run_id=run_id,
        patch_applies=applied,
        build_success=applied,  # harness only reaches tests if the image built
        fail_to_pass_passed=f2p_pass,
        fail_to_pass_total=f2p_total,
        pass_to_pass_passed=p2p_pass,
        pass_to_pass_total=p2p_total,
        resolved=resolved,
        full_tests_status="pass" if resolved else "fail",
    )


def evaluate_with_docker(
    task: TaskSpec,
    patch_text: str,
    work_dir: Path,
    run_id: str,
    *,
    dataset_name: str = DEFAULT_DATASET,
    split: str = "test",
    namespace: str = "swebench",
    timeout: int = 1800,
    python_exe: str | None = None,
    env: dict | None = None,
) -> EvalResult:
    """Evaluate one patch via the official Docker harness. Returns EvalResult.

    ``python_exe`` should point at the interpreter of the ``swebench`` conda env
    when calling from another env. ``env`` may set ``DOCKER_HOST``.
    """
    work_dir = Path(work_dir).resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    preds = work_dir / "predictions.jsonl"
    instance_id = write_predictions(task, patch_text, preds)

    py = python_exe or "python"
    cmd = [
        py, "-m", "swebench.harness.run_evaluation",
        "--dataset_name", dataset_name,
        "--split", split,
        "-i", instance_id,
        "-p", str(preds),
        "--run_id", run_id,
        "--max_workers", "1",
        "--cache_level", "env",
        "--namespace", namespace,
        "--timeout", str(timeout),
    ]
    run_env = dict(os.environ)
    if env:
        run_env.update(env)

    proc = subprocess.run(cmd, cwd=work_dir, capture_output=True, text=True, env=run_env)
    (work_dir / "harness.log").write_text(proc.stdout + "\n---STDERR---\n" + proc.stderr)

    report = _find_report(work_dir, run_id, instance_id)
    if report is None:
        raise RuntimeError(
            f"swebench harness produced no report (exit {proc.returncode}); "
            f"see {work_dir / 'harness.log'}"
        )
    result = _eval_from_report(report, instance_id, run_id)
    result.eval_log_path = str(work_dir / "harness.log")
    return result
