"""Deterministic mock agent (T6) -- no LLM involved.

Purpose: exercise the *entire* pipeline (workspace -> patch -> eval -> quality
card -> logs) with zero model cost and perfect reproducibility, so pipeline bugs
are found before any real model is plugged in.

Modes:
* ``gold``   -- apply the task's gold patch (should resolve the task).
* ``empty``  -- change nothing (should NOT resolve; tests still fail).
* ``broken`` -- make an unrelated/no-op edit (should NOT resolve).
* ``patch``  -- apply an explicitly provided patch string.
"""

from __future__ import annotations

import time
from pathlib import Path

from se_support.config import repo_root
from se_support.runner.run_dir import (
    FILE_FINAL_MESSAGE,
    RunDirectory,
    TranscriptEvent,
)
from se_support.runner.workspace import Workspace
from se_support.schemas import AgentRunResult, RunStatus, TaskSpec


class MockAgent:
    def __init__(self, mode: str = "gold", patch_text: str | None = None) -> None:
        if mode not in {"gold", "empty", "broken", "patch"}:
            raise ValueError(f"unknown mock mode: {mode}")
        self.mode = mode
        self.patch_text = patch_text
        self.name = f"mock_agent[{mode}]"

    def run(
        self,
        task: TaskSpec,
        condition: str,
        workspace: Workspace,
        run_dir: RunDirectory,
    ) -> AgentRunResult:
        t0 = time.time()
        run_dir.append_transcript(
            TranscriptEvent(
                step=0,
                role="system",
                content=f"MockAgent mode={self.mode} condition={condition} task={task.task_id}",
            )
        )

        applied_ok = True
        note = ""
        if self.mode == "gold":
            diff = self._load_gold(task)
            applied_ok = workspace.apply_patch(diff, check=False)
            note = "applied gold patch"
        elif self.mode == "patch":
            applied_ok = workspace.apply_patch(self.patch_text or "", check=False)
            note = "applied provided patch"
        elif self.mode == "broken":
            # Touch an unrelated marker file: changes the diff but fixes nothing.
            (workspace.path / "MOCK_NOOP.txt").write_text("noop edit by mock agent\n")
            note = "made a no-op unrelated edit"
        else:  # empty
            note = "made no changes"

        run_dir.append_transcript(
            TranscriptEvent(step=1, role="assistant", content=note, meta={"applied_ok": applied_ok})
        )
        run_dir.write_text(
            FILE_FINAL_MESSAGE,
            f"# Mock agent ({self.mode})\n\n{note}. patch_applied={applied_ok}.\n",
        )

        return AgentRunResult(
            run_id=run_dir.path.name,
            status=RunStatus.completed,
            patch_path=None,  # filled by the orchestrator after computing final_diff
            transcript_path=str(run_dir.path / "transcript.jsonl"),
            commands_path=str(run_dir.path / "commands.jsonl"),
            final_message_path=str(run_dir.path / FILE_FINAL_MESSAGE),
            duration_sec=round(time.time() - t0, 4),
            error=None,
        )

    @staticmethod
    def _load_gold(task: TaskSpec) -> str:
        if not task.gold_patch_path:
            return ""
        p = Path(task.gold_patch_path)
        if not p.is_absolute():
            p = repo_root() / p
        return p.read_text(encoding="utf-8")
