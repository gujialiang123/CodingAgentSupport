"""Run orchestration: execute one (task, agent, condition) run end-to-end.

Sequence (mirrors PROJECT_PROPOSAL.md section 16):
1. create the run directory, persist task.json + run_spec.json,
2. build the agent workspace from the base state,
3. run the agent (it edits the workspace + writes transcript/commands),
4. capture the final diff -> final.patch,
5. evaluate the patch on a clean checkout -> eval_result.json,
6. compute the patch quality card -> quality_card.json.

Everything is written to disk so metrics can be recomputed later without
re-running the agent.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path

from se_support.agents.base import AgentRunner
from se_support.evaluation import evaluate_patch, evaluate_with_docker
from se_support.quality import build_card
from se_support.runner.run_dir import (
    FILE_EVAL,
    FILE_FINAL_PATCH,
    FILE_QUALITY,
    FILE_RUN_SPEC,
    FILE_TASK,
    RunDirectory,
)
from se_support.runner.workspace import Workspace
from se_support.schemas import EvalResult, PatchQualityCard, RunSpec, TaskSpec


@dataclass
class RunOutcome:
    run_id: str
    run_dir: Path
    eval_result: EvalResult
    quality_card: PatchQualityCard


def _load_gold_diff(task: TaskSpec) -> str | None:
    from se_support.config import repo_root

    if not task.gold_patch_path:
        return None
    p = Path(task.gold_patch_path)
    if not p.is_absolute():
        p = repo_root() / p
    return p.read_text(encoding="utf-8") if p.exists() else None


def run_single(
    task: TaskSpec,
    agent: AgentRunner,
    condition: str,
    runs_root: Path,
    experiment_id: str,
    model: str = "mock",
    seed: int = 0,
    run_id: str | None = None,
    evaluator: str = "auto",
    docker_python_exe: str | None = None,
    docker_env: dict | None = None,
    dataset_name: str = "SWE-bench/SWE-bench_Verified",
    sandbox_policy=None,
    generator_client=None,
) -> RunOutcome:
    """Execute one run end-to-end.

    Workspace + evaluator are chosen by ``evaluator`` (``auto`` picks by task):
    * fixture tasks (``local_repo_path`` set) -> copy template + local evaluator.
    * real tasks (``repo`` + ``base_commit``) -> git clone + official Docker eval.

    When ``sandbox_policy`` is provided (EP-01) the workspace git history is
    flattened, a scrubbed (gold-free) task record + hashed visible-input manifest
    are written, and the agent's shell commands run under the sandbox.

    When ``generator_client`` is provided and the condition includes tests
    (C2/C6), a C2 helper is generated in a pre-run generator zone (A1/EP-03).
    """
    run_id = run_id or uuid.uuid4().hex[:12]
    rd = RunDirectory.create(runs_root, experiment_id, run_id)

    run_spec = RunSpec(
        run_id=run_id, task_id=task.task_id, agent=getattr(agent, "name", "agent"),
        model=model, condition=condition, seed=seed, experiment_id=experiment_id,
    )
    # The full task record (with gold/official-test fields) is evaluator-only.
    rd.write_model(FILE_TASK, task)
    rd.write_model(FILE_RUN_SPEC, run_spec)

    mode = _resolve_mode(task, evaluator)

    # Build the agent workspace from the base state.
    if mode == "fixture":
        agent_ws = Workspace.from_template(_template(task), rd.path / "agent_workspace", rd)
    else:
        agent_ws = Workspace.from_git(
            task.repo, task.base_commit, rd.path / "agent_workspace", rd
        )

    from se_support.support.condition import get_condition as _get_cond

    cond = _get_cond(condition)

    # A1/EP-03: generate the C2 helper (pre-run generator zone) for C2/C6.
    helper_artifact = None
    if cond.tests and generator_client is not None:
        try:
            from se_support.support.repro_tests.pregen import generate_helper_for_task

            helper_artifact = generate_helper_for_task(
                task, generator_client, rd.path / "gen_zone", generator_model=model
            )
            rd.write_json("support/helper_artifact.json", helper_artifact.model_dump())
        except Exception as exc:  # noqa: BLE001 - record, do not crash the run
            rd.write_json("support/helper_artifact_error.json", {"error": repr(exc)})

    # EP-02: generate the frozen support bundle before the agent starts, write it
    # to support/, and give it to the agent as its single source of support text.
    from se_support.support import build_bundle

    bundle = build_bundle(task, condition, agent_ws.path, helper_artifact=helper_artifact)
    bundle.write(rd.path / "support")
    if hasattr(agent, "support_bundle"):
        agent.support_bundle = bundle

    # EP-07: compute advisory-gate baseline on the BASE tree (before any edits)
    # so new warnings can be separated from pre-existing legacy warnings.
    if cond.gates and hasattr(agent, "gate_baseline"):
        from se_support.support.gate_policy import compute_baseline

        agent.gate_baseline = compute_baseline(agent_ws.path, getattr(agent, "gate_policy", None))

    # EP-01 provenance firewall: scrub history, write scrubbed task + manifest,
    # and run the agent's commands under the sandbox.
    if sandbox_policy is not None:
        _apply_isolation(task, condition, run_id, agent, agent_ws, rd, sandbox_policy)

    # A4/E0: manipulation check -- record whether the treatment was actually applied.
    _write_manipulation_check(
        run_id, condition, cond, bundle, sandbox_policy, rd
    )

    agent.run(task, condition, agent_ws, rd)
    final_diff = agent_ws.final_diff()
    rd.write_text(FILE_FINAL_PATCH, final_diff)

    # Evaluate.
    if mode == "fixture":
        eval_result = evaluate_patch(task, final_diff, rd.path / "eval_workspace", rd)
    else:
        eval_result = evaluate_with_docker(
            task, final_diff, rd.path / "docker_eval", run_id=run_id,
            dataset_name=dataset_name, python_exe=docker_python_exe, env=docker_env,
        )
    eval_result.run_id = run_id
    rd.write_model(FILE_EVAL, eval_result)

    # Quality card (offline, from artifacts) incl. trajectory/process metrics.
    card = build_card(task, eval_result, final_diff, _load_gold_diff(task), run_dir=rd.path)
    rd.write_model(FILE_QUALITY, card)

    return RunOutcome(run_id=run_id, run_dir=rd.path, eval_result=eval_result, quality_card=card)


def _apply_isolation(task, condition, run_id, agent, agent_ws, rd, sandbox_policy) -> None:
    import json

    from se_support.isolation import (
        VisibleInputManifest,
        assert_no_forbidden_fields,
        hash_text,
        sandbox_available,
        scrubbed_task_dict,
    )

    if sandbox_policy.enable_sandbox:
        agent_ws.scrub()

    scrubbed = scrubbed_task_dict(task)
    assert_no_forbidden_fields(scrubbed)
    scrubbed_blob = json.dumps(scrubbed, sort_keys=True)
    rd.write_json("scrubbed_task.json", scrubbed)

    backend = sandbox_available() if sandbox_policy.enable_sandbox else "none"
    manifest = VisibleInputManifest(
        run_id=run_id, condition=condition, base_commit=task.base_commit,
        scrubbed_task_hash=hash_text(scrubbed_blob),
        sandbox_backend=backend or "none",
        network_allowed=sandbox_policy.allow_network,
    )
    rd.write_model("visible_input_manifest.json", manifest)

    # Ensure the agent actually uses the sandbox policy.
    if hasattr(agent, "sandbox_policy"):
        agent.sandbox_policy = sandbox_policy


def _write_manipulation_check(run_id, condition, cond, bundle, sandbox_policy, rd) -> None:
    """A4/E0: record whether the condition applied exactly its intended treatment."""
    from se_support.schemas import ManipulationCheck

    def _present(layer: str) -> bool:
        art = bundle.artifact(layer)
        return art is not None and art.status == "present"

    # Expected-vs-actual: every enabled layer must be present (tests may be
    # declared_unimplemented -> present=False, which is honestly recorded).
    expected = {
        "context": cond.context, "tests": cond.tests, "gates": cond.gates,
        "harness": cond.harness, "memory": cond.memory,
    }
    actual = {layer: _present(layer) for layer in expected}
    # Passed = non-tests layers match expectation (tests may lack a valid helper).
    passed = all(actual[layer] == expected[layer] for layer in expected if layer != "tests")

    mc = ManipulationCheck(
        run_id=run_id, condition=condition,
        context_present=actual["context"], tests_present=actual["tests"],
        gates_present=actual["gates"], harness_present=actual["harness"],
        memory_present=actual["memory"],
        no_gold_in_visible_inputs=True if sandbox_policy is not None else None,
        network_disabled=(not sandbox_policy.allow_network) if sandbox_policy else None,
        support_manifest_hash=bundle.bundle_hash,
        passed=passed,
    )
    rd.write_model("manipulation.json", mc)


def _resolve_mode(task: TaskSpec, evaluator: str) -> str:
    if evaluator == "local":
        return "fixture"
    if evaluator == "docker":
        return "real"
    # auto
    return "fixture" if task.local_repo_path else "real"


def _template(task: TaskSpec) -> Path:
    from se_support.config import repo_root

    if not task.local_repo_path:
        raise ValueError("run_single (local mode) requires TaskSpec.local_repo_path")
    p = Path(task.local_repo_path)
    return p if p.is_absolute() else repo_root() / p
