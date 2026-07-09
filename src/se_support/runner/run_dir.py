"""Run-directory layout and structured (JSONL) experiment logging.

Motivation (user requirement): capture raw data richly enough that **new
metrics can be recomputed from logs without re-running experiments**. This
module fixes the on-disk contract so every run is replayable.

Directory layout (PROJECT_PROPOSAL.md section 16)::

    runs/{experiment_id}/{run_id}/
        task.json                 # TaskSpec (the run input)
        run_spec.json             # RunSpec (pinned model/condition/seed)
        condition.yaml            # resolved support-condition config (later)
        support/                  # injected support artifacts (context, memory, ...)
        intermediate_patches/     # diff after each edit attempt
        transcript.jsonl          # one TranscriptEvent per line
        commands.jsonl            # one CommandRecord per line
        final.patch               # final unified diff
        final_message.md          # agent's final summary
        eval_result.json          # EvalResult (correctness)
        gate_results.json         # raw gate outputs
        quality_card.json         # PatchQualityCard (non-functional quality)
        logs/                     # free-form stdout/stderr dumps referenced by path

The two JSONL streams have fixed schemas (:class:`TranscriptEvent`,
:class:`CommandRecord`) so producers and future metric consumers agree.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import Field

from se_support.schemas.base import SEModel


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class TranscriptEvent(SEModel):
    """One step of the agent loop (append-only to ``transcript.jsonl``)."""

    ts: str = Field(default_factory=_utcnow_iso)
    step: int = Field(..., description="0-based step index within the run.")
    role: str = Field(..., description="'system' | 'user' | 'assistant' | 'tool'.")
    content: str = Field("", description="Raw text for this step.")
    tokens_in: int | None = None
    tokens_out: int | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class CommandRecord(SEModel):
    """One executed shell command (append-only to ``commands.jsonl``)."""

    ts: str = Field(default_factory=_utcnow_iso)
    step: int | None = None
    command: str = ""
    exit_code: int | None = None
    duration_sec: float | None = None
    stdout_path: str | None = Field(None, description="Path under logs/ for large stdout.")
    stderr_path: str | None = Field(None, description="Path under logs/ for large stderr.")
    stdout_preview: str = Field("", description="Truncated inline stdout for quick reads.")
    meta: dict[str, Any] = Field(default_factory=dict)


# Canonical filenames within a run directory.
FILE_TASK = "task.json"
FILE_RUN_SPEC = "run_spec.json"
FILE_TRANSCRIPT = "transcript.jsonl"
FILE_COMMANDS = "commands.jsonl"
FILE_FINAL_PATCH = "final.patch"
FILE_FINAL_MESSAGE = "final_message.md"
FILE_EVAL = "eval_result.json"
FILE_GATE_RESULTS = "gate_results.json"
FILE_QUALITY = "quality_card.json"

DIR_SUPPORT = "support"
DIR_INTERMEDIATE = "intermediate_patches"
DIR_LOGS = "logs"


class RunDirectory:
    """Create and write the standard artifacts for a single run.

    Example::

        rd = RunDirectory.create(runs_root, "pilot_C0", run_id)
        rd.write_model(FILE_RUN_SPEC, run_spec)
        rd.append_transcript(TranscriptEvent(step=0, role="system", content="..."))
    """

    def __init__(self, path: Path) -> None:
        self.path = path

    @classmethod
    def create(cls, runs_root: Path, experiment_id: str, run_id: str) -> RunDirectory:
        path = Path(runs_root) / experiment_id / run_id
        path.mkdir(parents=True, exist_ok=True)
        for sub in (DIR_SUPPORT, DIR_INTERMEDIATE, DIR_LOGS):
            (path / sub).mkdir(exist_ok=True)
        return cls(path)

    # -- structured JSONL streams --------------------------------------------
    def append_transcript(self, event: TranscriptEvent) -> None:
        self._append_jsonl(FILE_TRANSCRIPT, event)

    def append_command(self, record: CommandRecord) -> None:
        self._append_jsonl(FILE_COMMANDS, record)

    def _append_jsonl(self, filename: str, model: SEModel) -> None:
        with (self.path / filename).open("a", encoding="utf-8") as fh:
            fh.write(model.model_dump_json() + "\n")

    # -- whole-object writers ------------------------------------------------
    def write_model(self, filename: str, model: SEModel) -> Path:
        target = self.path / filename
        target.write_text(model.model_dump_json(indent=2) + "\n", encoding="utf-8")
        return target

    def write_text(self, filename: str, text: str) -> Path:
        target = self.path / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        return target

    def write_json(self, filename: str, obj: Any) -> Path:
        target = self.path / filename
        target.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
        return target

    # -- readers (used by offline metric scripts) ----------------------------
    def read_transcript(self) -> list[TranscriptEvent]:
        return [TranscriptEvent(**o) for o in self._read_jsonl(FILE_TRANSCRIPT)]

    def read_commands(self) -> list[CommandRecord]:
        return [CommandRecord(**o) for o in self._read_jsonl(FILE_COMMANDS)]

    def _read_jsonl(self, filename: str) -> list[dict[str, Any]]:
        path = self.path / filename
        if not path.exists():
            return []
        out: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                out.append(json.loads(line))
        return out
