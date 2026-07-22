"""Container-based C2 helper generation + validation (P2).

Validates helper candidates **inside the SWE-bench instance container** where the
repo's dependencies exist, so fail-before/pass-after actually execute (a bare
clone cannot import the package). Generation, provenance/leakage audit and
freezing are unchanged; only the base/gold *execution* moves into containers.

Flow (plan Priority 2):
1. start a base container (instance image at /testbed, HEAD = base commit);
2. generate K blind candidates (issue + scrubbed repo context only);
3. gold-blind select: candidate that collects and FAILS on base for an
   issue-relevant reason, with issue provenance and no forbidden official literal;
4. freeze BEFORE consulting gold;
5. apply the gold patch in a second container and run the frozen candidate to
   classify pass-after (offline diagnostic only);
6. classify T0-T4; T0-T2 are reported, never silently dropped.
"""

from __future__ import annotations

from pathlib import Path

from se_support.runner.container_workspace import ContainerWorkspace
from se_support.schemas import TaskSpec
from se_support.support.context_pack import build_context_pack
from se_support.support.repro_tests.generator import generate_candidates, prompt_hash
from se_support.support.repro_tests.injector import freeze
from se_support.support.repro_tests.pregen import forbidden_literals_from_test_patch
from se_support.support.repro_tests.provenance import (
    contains_forbidden_literal,
    has_issue_provenance,
    suspicious_literals,
)
from se_support.support.repro_tests.schema import (
    CONFIRMATORY_CLASSES,
    HelperTestArtifact,
    ReproTestClass,
)

_HELPER_PATH = "/testbed/_c2_candidate_test.py"


def _run_candidate_in_container(cw: ContainerWorkspace, source: str) -> tuple[bool, bool]:
    """Return (collected, passed) for running ``source`` at /testbed."""
    cw.inject_file(_HELPER_PATH, source)
    proc, _ = cw.run_sandboxed(
        "python -m pytest -q --no-header -p no:cacheprovider _c2_candidate_test.py"
    )
    cw._exec(f"rm -f {_HELPER_PATH}")
    collected = proc.returncode in (0, 1)
    passed = proc.returncode == 0
    return collected, passed


def _load_gold_diff(task: TaskSpec) -> str | None:
    from se_support.config import repo_root

    if not task.gold_patch_path:
        return None
    p = Path(task.gold_patch_path)
    if not p.is_absolute():
        p = repo_root() / p
    return p.read_text(encoding="utf-8") if p.exists() else None


def generate_helper_in_container(
    task: TaskSpec,
    client,
    *,
    namespace: str = "swebench",
    env: dict | None = None,
    k: int = 3,
    generator_model: str | None = None,
) -> HelperTestArtifact:
    """Generate + validate a C2 helper using instance containers (P2)."""
    instance_id = task.task_id.split("__", 1)[1] if "__" in task.task_id else task.task_id
    problem = task.issue_body or task.issue_title
    forbidden = forbidden_literals_from_test_patch(task.test_patch_path)

    base_cw = ContainerWorkspace.start(instance_id, None, namespace=namespace, env=env)
    try:
        repo_context = build_context_pack(task, base_cw.path, reader=base_cw)
        candidates = generate_candidates(problem, repo_context, client, k=k)

        # Gold-blind selection: first candidate that collects + fails on base +
        # has issue provenance + no forbidden official literal.
        selected = None
        fallback = None
        for cand in candidates:
            collected, passed = _run_candidate_in_container(base_cw, cand)
            if not collected:
                continue
            if fallback is None:
                fallback = cand
            if (not passed) and has_issue_provenance(cand, problem) \
                    and not contains_forbidden_literal(cand, forbidden):
                selected = cand
                break
        chosen = selected or fallback
        if chosen is None:
            return HelperTestArtifact(
                task_id=task.task_id, test_source="", generator_model=generator_model,
                prompt_hash=prompt_hash(problem, repo_context),
                classification=ReproTestClass.T0_invalid, notes="no runnable candidate",
            )

        artifact = HelperTestArtifact(
            task_id=task.task_id, test_source=chosen, generator_model=generator_model,
            prompt_hash=prompt_hash(problem, repo_context),
        )
        artifact = freeze(artifact)  # freeze BEFORE consulting gold

        collected, passed = _run_candidate_in_container(base_cw, chosen)
        artifact.collected = collected
        artifact.fail_before = collected and not passed
    finally:
        base_cw.close()

    # Offline gold diagnostic in a fresh container (classification only).
    pass_after = None
    gold_diff = _load_gold_diff(task)
    if gold_diff:
        gold_cw = ContainerWorkspace.start(instance_id, None, namespace=namespace, env=env)
        try:
            gold_cw.inject_file("/testbed/_c2_gold.patch", gold_diff)
            ap, _ = gold_cw.run_sandboxed("git apply _c2_gold.patch && echo APPLIED")
            if "APPLIED" in ap.stdout:
                g_collected, g_passed = _run_candidate_in_container(gold_cw, chosen)
                pass_after = g_collected and g_passed
        finally:
            gold_cw.close()
    artifact.pass_after_gold = pass_after

    # Classify.
    if not artifact.collected:
        cls = ReproTestClass.T0_invalid
    elif not artifact.fail_before:
        cls = ReproTestClass.T1_non_reproducing
    elif pass_after is None:
        cls = ReproTestClass.T3_valid_reproduction
    elif pass_after:
        cls = ReproTestClass.T3_valid_reproduction
    else:
        cls = ReproTestClass.T2_incompatible_oracle

    # Provenance/leakage audit -> T4.
    flagged = suspicious_literals(chosen, problem)
    forbidden_hit = contains_forbidden_literal(chosen, forbidden)
    artifact.suspicious_literals = flagged
    artifact.issue_provenance_ok = not flagged and not forbidden_hit
    if cls in CONFIRMATORY_CLASSES and artifact.issue_provenance_ok:
        cls = ReproTestClass.T4_decoupled_valid
    artifact.classification = cls
    return artifact
