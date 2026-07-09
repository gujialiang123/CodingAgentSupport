"""AgentRunResult: pointers to the raw artifacts produced by one run.

This model deliberately stores *paths*, not inlined blobs. The heavy raw data
(transcript, per-command logs, intermediate patches, support artifacts) lives on
disk under the run directory so it can be replayed by future metric scripts.
Keeping the result record small keeps indexing/aggregation cheap.
"""

from __future__ import annotations

from enum import Enum

from pydantic import Field

from se_support.schemas.base import SEModel


class RunStatus(str, Enum):
    completed = "completed"
    failed = "failed"
    timeout = "timeout"
    error = "error"


class AgentRunResult(SEModel):
    run_id: str
    status: RunStatus = RunStatus.completed
    patch_path: str | None = Field(None, description="Final unified diff produced by the agent.")
    transcript_path: str | None = Field(None, description="JSONL of every agent step.")
    commands_path: str | None = Field(None, description="JSONL of every executed command.")
    support_artifacts_dir: str | None = Field(None, description="Injected support artifacts.")
    final_message_path: str | None = Field(None, description="Agent's final summary message.")
    duration_sec: float | None = None
    error: str | None = None
