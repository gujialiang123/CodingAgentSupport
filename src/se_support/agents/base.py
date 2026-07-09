"""AgentRunner interface (PROJECT_PROPOSAL.md section 7.1).

Every scaffold implements ``run``: given a task, a support condition, a prepared
workspace and a run directory, it edits the workspace to produce a fix and writes
its transcript/commands logs. It returns an :class:`AgentRunResult` pointing at
the artifacts (the final diff is read from the workspace by the orchestrator).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from se_support.runner.run_dir import RunDirectory
from se_support.runner.workspace import Workspace
from se_support.schemas import AgentRunResult, TaskSpec


@runtime_checkable
class AgentRunner(Protocol):
    name: str

    def run(
        self,
        task: TaskSpec,
        condition: str,
        workspace: Workspace,
        run_dir: RunDirectory,
    ) -> AgentRunResult:
        ...
