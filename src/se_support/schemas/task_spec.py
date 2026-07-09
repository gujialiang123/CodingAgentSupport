"""TaskSpec: one repository-level SE task (PROJECT_PROPOSAL.md section 9.1).

A TaskSpec is the *input* to every run and is dataset-agnostic: SWE-bench
Verified, SWE-Gym Lite and SWE-bench Live importers all produce TaskSpec
records. It carries everything needed to (a) reconstruct the base repository
state and (b) judge correctness (fail_to_pass / pass_to_pass tests), which is
essential for recomputing metrics later without re-running the agent.
"""

from __future__ import annotations

from pydantic import Field

from se_support.schemas.base import SEModel


class TaskMetadata(SEModel):
    language: str = "python"
    gold_files_touched: int | None = None
    gold_loc_changed: int | None = None
    repo_group: str | None = None


class TaskSpec(SEModel):
    task_id: str = Field(..., description="Unique task id, e.g. swebench__django__12345.")
    dataset: str = Field(..., description="Source dataset, e.g. swebench_verified.")
    repo: str = Field(..., description="owner/name of the GitHub repository.")
    base_commit: str = Field(..., description="Commit SHA of the pre-fix repository snapshot.")
    issue_title: str = ""
    issue_body: str = ""
    test_command: str | None = Field(None, description="Command that runs the target tests.")
    setup_command: str | None = Field(None, description="Environment setup command, if any.")
    docker_image: str | None = Field(None, description="Reproducible eval image tag, if any.")
    gold_patch_path: str | None = Field(None, description="Path to the human reference patch.")
    fail_to_pass_tests: list[str] = Field(default_factory=list)
    pass_to_pass_tests: list[str] = Field(default_factory=list)
    metadata: TaskMetadata = Field(default_factory=TaskMetadata)
