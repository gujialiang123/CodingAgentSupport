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
    status: str = "ok"  # "ok" | "infrastructure_failure"


def _infrastructure_failure(rd, run_id, stage, state, task) -> RunOutcome:
    """Record an invalid run (unclean base tree) that must NOT count as an agent
    failure, and return a sentinel outcome (integrity fix, Phase 3)."""
    rd.write_json("integrity/status.json", {
        "status": "infrastructure_failure", "stage": stage,
        "unexplained_changes": state.get("unexplained_changes", []),
    })
    empty_eval = EvalResult(run_id=run_id, resolved=False, patch_applies=False)
    empty_eval.run_id = run_id
    rd.write_text(FILE_FINAL_PATCH, "")
    card = build_card(task, empty_eval, "", _load_gold_diff(task), run_dir=rd.path)
    rd.write_model(FILE_EVAL, empty_eval)
    rd.write_model(FILE_QUALITY, card)
    return RunOutcome(run_id=run_id, run_dir=rd.path, eval_result=empty_eval,
                      quality_card=card, status="infrastructure_failure")


def _load_gold_diff(task: TaskSpec) -> str | None:
    from se_support.config import repo_root

    if not task.gold_patch_path:
        return None
    p = Path(task.gold_patch_path)
    if not p.is_absolute():
        p = repo_root() / p
    return p.read_text(encoding="utf-8") if p.exists() else None


class InfrastructureFailure(RuntimeError):
    """Raised when the base tree is not clean before the agent runs.

    The run is invalid infrastructure, NOT an agent failure, and must be excluded
    from agent-outcome statistics (integrity fix, Phase 3).
    """

    def __init__(self, stage: str, state: dict) -> None:
        super().__init__(f"unclean tree at {stage}: {state.get('unexplained_changes')}")
        self.stage = stage
        self.state = state


def _resolve_helper_artifact(
    task, cond, use_container, helper_cache_dir, generator_client, model,
    docker_env, rd,
):
    """Resolve the frozen/generated C2 helper BEFORE the agent container starts.

    Prefers a pre-frozen, container-validated helper (deterministic). Otherwise
    generates one in a SEPARATE generator/validator container (or a host gen zone
    for fixture mode) that is fully closed before the agent container starts, so
    the helper is never produced inside the agent's own container.
    """
    helper_artifact = None
    try:
        cached = _load_frozen_helper(task, helper_cache_dir)
        if cached is not None:
            helper_artifact = cached
        elif use_container:
            from se_support.support.repro_tests.pregen_container import (
                generate_helper_in_container,
            )

            helper_artifact = generate_helper_in_container(
                task, generator_client, env=docker_env, generator_model=model
            )
        else:
            from se_support.support.repro_tests.pregen import generate_helper_for_task

            helper_artifact = generate_helper_for_task(
                task, generator_client, rd.path / "gen_zone", generator_model=model
            )
        rd.write_json("support/helper_artifact.json", helper_artifact.model_dump())
    except Exception as exc:  # noqa: BLE001 - record, do not crash the run
        rd.write_json("support/helper_artifact_error.json", {"error": repr(exc)})
    return helper_artifact


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
    in_container: bool = False,
    namespace: str = "swebench",
    helper_cache_dir: Path | None = None,
    memory_cache_dir: Path | None = None,
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

    When ``in_container=True`` (P1) the agent runs **inside** the task's SWE-bench
    instance image at ``/testbed`` (deps installed, network off), so it can run the
    repo's real tests, C3 gates, and the C2 helper. Official Docker eval unchanged.
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
    use_container = in_container and mode == "real"

    from se_support.support.condition import get_condition as _get_cond

    cond = _get_cond(condition)

    # Integrity fix: resolve the C2 helper BEFORE the agent container starts, so
    # it can be delivered as a read-only mount (experiment input) rather than
    # written into the repo git tree (which would contaminate the final patch).
    helper_artifact = None
    helper_host_sha = None
    support_mount = None
    if cond.tests and generator_client is not None:
        helper_artifact = _resolve_helper_artifact(
            task, cond, use_container, helper_cache_dir, generator_client,
            model, docker_env, rd,
        )
        if use_container and helper_artifact is not None and helper_artifact.test_source:
            import hashlib

            support_mount = rd.path / "support_mount"
            support_mount.mkdir(parents=True, exist_ok=True)
            (support_mount / "helper_test.py").write_text(
                helper_artifact.test_source, encoding="utf-8"
            )
            helper_host_sha = hashlib.sha256(
                helper_artifact.test_source.encode()
            ).hexdigest()

    # Build the agent workspace from the base state.
    container = None
    if use_container:
        from se_support.runner.container_workspace import ContainerWorkspace

        instance_id = task.task_id.split("__", 1)[1] if "__" in task.task_id else task.task_id
        container = ContainerWorkspace.start(
            instance_id, rd, namespace=namespace, env=docker_env,
            support_mount=support_mount,
        )
        agent_ws = container
        reader = container
    elif mode == "fixture":
        agent_ws = Workspace.from_template(_template(task), rd.path / "agent_workspace", rd)
        reader = None
    else:
        agent_ws = Workspace.from_git(
            task.repo, task.base_commit, rd.path / "agent_workspace", rd
        )
        reader = None

    try:
        return _run_body(
            task, agent, condition, cond, run_id, rd, mode, use_container,
            agent_ws, container, reader, generator_client, model,
            sandbox_policy, dataset_name, docker_python_exe, docker_env,
            helper_cache_dir, memory_cache_dir,
            helper_artifact=helper_artifact, helper_host_sha=helper_host_sha,
        )
    finally:
        if container is not None:
            container.close()


def _run_body(
    task, agent, condition, cond, run_id, rd, mode, use_container,
    agent_ws, container, reader, generator_client, model,
    sandbox_policy, dataset_name, docker_python_exe, docker_env,
    helper_cache_dir=None,
    memory_cache_dir=None,
    helper_artifact=None,
    helper_host_sha=None,
) -> RunOutcome:
    # Integrity: S0 snapshot immediately after the container starts (before any
    # support setup). Modified TRACKED files here mean a tampered image (abort);
    # pre-existing UNTRACKED files (e.g. a shipped build/lib tree) are benign
    # base-image state -- recorded as a baseline and excluded from the agent patch.
    base_untracked = []
    if use_container:
        s0 = container.git_state(strict_untracked=False)
        rd.write_json("integrity/git_state_s0.json", s0)
        if not s0["clean"]:
            return _infrastructure_failure(rd, run_id, "S0_CONTAINER_START", s0, task)
        base_untracked = s0["untracked_files"]

    # EP-02: generate the frozen support bundle before the agent starts. The C2
    # helper (if any) was resolved BEFORE container start and is mounted read-only
    # at /testbed/.se_support/helper_test.py -- it is NOT written into the git tree.
    from se_support.support import build_bundle

    bundle = build_bundle(
        task, condition, agent_ws.path, helper_artifact=helper_artifact,
        reader=reader, memory_cache_dir=memory_cache_dir,
    )
    bundle.write(rd.path / "support")
    if hasattr(agent, "support_bundle"):
        agent.support_bundle = bundle

    # Integrity: record the mounted helper hash (as seen in-container) and verify
    # it matches the host artifact we wrote before start.
    helper_sha_before = None
    if use_container and helper_host_sha is not None:
        helper_sha_before = container.helper_sha256()

    # EP-07: advisory-gate baseline on the BASE tree (before edits). C3 v2 policy.
    if cond.gates and hasattr(agent, "gate_baseline"):
        from se_support.support.gate_policy import compute_baseline_v2

        gate_exec = container.gate_exec_fn() if use_container else None
        agent.gate_baseline = compute_baseline_v2(
            agent_ws.path, getattr(agent, "gate_policy", None), exec_fn=gate_exec
        )

    # EP-01 provenance firewall (host sandbox OR container isolation).
    if sandbox_policy is not None or use_container:
        _apply_isolation(task, condition, run_id, agent, agent_ws, rd, sandbox_policy,
                         use_container=use_container)

    # A4/E0: manipulation check.
    _write_manipulation_check(run_id, condition, cond, bundle, sandbox_policy, rd,
                              use_container=use_container)

    # Integrity: S1 snapshot after ALL support setup, immediately before the
    # agent runs. The tree must still be clean -- otherwise support setup (or a
    # dirty image) mutated the repo and the run is infrastructure, not agent.
    if use_container:
        s1 = container.git_state(baseline_untracked=base_untracked, strict_untracked=True)
        rd.write_json("integrity/git_state_s1.json", s1)
        if not s1["clean"]:
            return _infrastructure_failure(rd, run_id, "S1_PRE_AGENT", s1, task)

    _write_provenance(rd, run_id, task, condition, model, use_container, bundle,
                      helper_host_sha, agent, container if use_container else None)

    agent.run(task, condition, agent_ws, rd)

    if use_container:
        final_diff, patch_manifest = agent_ws.final_diff_with_manifest(
            extra_excludes=base_untracked
        )
        s2 = container.git_state(baseline_untracked=base_untracked, strict_untracked=True)
        rd.write_json("integrity/git_state_s2.json", s2)
        rd.write_json("integrity/patch_manifest.json", patch_manifest)
        if helper_host_sha is not None:
            after = container.helper_sha256()
            rd.write_json("integrity/helper_hash.json", {
                "host_sha256": helper_host_sha,
                "container_sha256_before": helper_sha_before,
                "container_sha256_after": after,
                "helper_unchanged": (helper_sha_before == after and after is not None),
            })
        # Hard invariant: the helper must never be in the agent's final patch.
        if patch_manifest.get("helper_leak"):
            raise RuntimeError(
                "integrity violation: helper artifact leaked into final patch "
                f"({patch_manifest.get('included_paths')})"
            )
    else:
        final_diff = agent_ws.final_diff()
    rd.write_text(FILE_FINAL_PATCH, final_diff)

    # Evaluate (always the official Docker harness for real tasks).
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

    return RunOutcome(run_id=run_id, run_dir=rd.path, eval_result=eval_result,
                      quality_card=card)


def _write_provenance(rd, run_id, task, condition, model, use_container, bundle,
                      helper_host_sha, agent, container) -> None:
    """Record full run provenance for reproducibility (integrity fix, Phase 5)."""
    import hashlib

    from se_support.config import CONDITION_VERSION, PROTOCOL_VERSION
    from se_support.runner.container_workspace import (
        PATCH_EXTRACTOR_VERSION,
        instance_image_name,
    )

    bundle_sha = None
    try:
        bundle_sha = hashlib.sha256(
            "".join(sorted(a.hash or "" for a in bundle.artifacts)).encode()
        ).hexdigest()
    except Exception:  # noqa: BLE001
        pass
    gate_pol = getattr(agent, "gate_policy", None)
    prov = {
        "run_id": run_id,
        "task_id": task.task_id,
        "condition": condition,
        "model": model,
        "protocol_version": PROTOCOL_VERSION,
        "condition_version": CONDITION_VERSION,
        "patch_extractor_version": PATCH_EXTRACTOR_VERSION,
        "gate_policy_version": getattr(gate_pol, "version", None),
        "helper_sha256": helper_host_sha,
        "support_bundle_sha256": bundle_sha,
        "repo": task.repo,
        "base_commit": task.base_commit,
        "container_image": (
            instance_image_name(task.task_id.split("__", 1)[-1]) if use_container else None
        ),
        "in_container": bool(use_container),
    }
    if container is not None:
        head = container.git_state().get("head")
        prov["container_head"] = head
    rd.write_json("integrity/provenance.json", prov)


def _apply_isolation(task, condition, run_id, agent, agent_ws, rd, sandbox_policy,
                     use_container: bool = False) -> None:
    import json

    from se_support.isolation import (
        VisibleInputManifest,
        assert_no_forbidden_fields,
        hash_text,
        sandbox_available,
        scrubbed_task_dict,
    )

    if use_container or (sandbox_policy is not None and sandbox_policy.enable_sandbox):
        agent_ws.scrub()

    scrubbed = scrubbed_task_dict(task)
    assert_no_forbidden_fields(scrubbed)
    scrubbed_blob = json.dumps(scrubbed, sort_keys=True)
    rd.write_json("scrubbed_task.json", scrubbed)

    if use_container:
        # Network isolation is provided by the container (--network none); the
        # agent execs inside /testbed and cannot reach the host run dir.
        backend = "container"
        network_allowed = False
    else:
        backend = sandbox_available() if sandbox_policy.enable_sandbox else "none"
        network_allowed = sandbox_policy.allow_network
    manifest = VisibleInputManifest(
        run_id=run_id, condition=condition, base_commit=task.base_commit,
        scrubbed_task_hash=hash_text(scrubbed_blob),
        sandbox_backend=backend or "none",
        network_allowed=network_allowed,
    )
    rd.write_model("visible_input_manifest.json", manifest)

    # Ensure the agent uses the sandbox policy (host workspaces only; the
    # container workspace ignores the policy and isolates via --network none).
    if hasattr(agent, "sandbox_policy") and not use_container:
        agent.sandbox_policy = sandbox_policy


def _write_manipulation_check(run_id, condition, cond, bundle, sandbox_policy, rd,
                              use_container: bool = False) -> None:
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

    net_disabled = None
    if use_container:
        net_disabled = True
    elif sandbox_policy is not None:
        net_disabled = not sandbox_policy.allow_network

    mc = ManipulationCheck(
        run_id=run_id, condition=condition,
        context_present=actual["context"], tests_present=actual["tests"],
        gates_present=actual["gates"], harness_present=actual["harness"],
        memory_present=actual["memory"],
        no_gold_in_visible_inputs=True if (sandbox_policy is not None or use_container) else None,
        network_disabled=net_disabled,
        support_manifest_hash=bundle.bundle_hash,
        passed=passed,
    )
    rd.write_model("manipulation.json", mc)


def _load_frozen_helper(task: TaskSpec, cache_dir: Path | None):
    """Load a pre-frozen, container-validated C2 helper for ``task`` if present.

    P4: helpers are frozen once (scripts/freeze_helpers.py) and reused read-only,
    so C2/C2+C3 runs are deterministic and don't burn generator API budget. Only
    confirmatory (T3/T4) helpers are loaded; anything else falls back to
    per-run generation. Returns ``None`` when no usable cached helper exists.
    """
    if cache_dir is None:
        return None
    path = Path(cache_dir) / f"{task.task_id}.json"
    if not path.exists():
        return None
    from se_support.support.repro_tests.schema import (
        CONFIRMATORY_CLASSES,
        HelperTestArtifact,
        ReproTestClass,
    )

    artifact = HelperTestArtifact.model_validate_json(path.read_text(encoding="utf-8"))
    if ReproTestClass(artifact.classification) not in CONFIRMATORY_CLASSES:
        return None
    if not artifact.test_source:
        return None
    return artifact


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
