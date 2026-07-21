"""Information-isolation architecture (EP-01).

Implements the provenance firewall and sandbox contract from
EXPERIMENT_PLAN_2026-07-21.md §6: agent shell commands run network-disabled and
filesystem-confined; agent-visible task data is scrubbed of gold/official-test
fields; the workspace git history is flattened so future commits are
unrecoverable; and every run records a hashed manifest of visible inputs.
"""

from se_support.isolation.manifest import (
    ArtifactHash,
    VisibleInputManifest,
    hash_bytes,
    hash_file,
    hash_text,
)
from se_support.isolation.policy import SandboxPolicy
from se_support.isolation.sandbox import build_sandbox_argv, sandbox_available
from se_support.isolation.scrub import (
    AGENT_VISIBLE_FIELDS,
    FORBIDDEN_FIELDS,
    assert_no_forbidden_fields,
    scrub_git_history,
    scrubbed_task_dict,
)

__all__ = [
    "SandboxPolicy",
    "build_sandbox_argv",
    "sandbox_available",
    "scrub_git_history",
    "scrubbed_task_dict",
    "assert_no_forbidden_fields",
    "AGENT_VISIBLE_FIELDS",
    "FORBIDDEN_FIELDS",
    "VisibleInputManifest",
    "ArtifactHash",
    "hash_bytes",
    "hash_file",
    "hash_text",
]
