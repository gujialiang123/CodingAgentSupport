"""Tests for the run-directory + JSONL logging contract (T3 groundwork).

These guard the "record raw data richly so metrics can be recomputed later"
requirement: whatever we append must read back losslessly.
"""

from __future__ import annotations

from se_support.runner.run_dir import (
    FILE_RUN_SPEC,
    CommandRecord,
    RunDirectory,
    TranscriptEvent,
)
from se_support.schemas import RunSpec


def test_create_layout(tmp_path):
    rd = RunDirectory.create(tmp_path, "exp1", "run1")
    assert rd.path.is_dir()
    for sub in ("support", "intermediate_patches", "logs"):
        assert (rd.path / sub).is_dir()


def test_transcript_and_commands_roundtrip(tmp_path):
    rd = RunDirectory.create(tmp_path, "exp1", "run1")
    rd.append_transcript(TranscriptEvent(step=0, role="system", content="you are an agent"))
    rd.append_transcript(TranscriptEvent(step=1, role="assistant", content="ls", tokens_out=2))
    rd.append_command(CommandRecord(step=1, command="ls", exit_code=0, duration_sec=0.1))

    events = rd.read_transcript()
    assert [e.step for e in events] == [0, 1]
    assert events[1].tokens_out == 2

    cmds = rd.read_commands()
    assert len(cmds) == 1
    assert cmds[0].command == "ls"
    assert cmds[0].exit_code == 0


def test_write_model(tmp_path):
    rd = RunDirectory.create(tmp_path, "exp1", "run1")
    spec = RunSpec(run_id="run1", task_id="t", agent="mini_swe_agent",
                   model="m", condition="C0_minimal")
    path = rd.write_model(FILE_RUN_SPEC, spec)
    assert path.exists()
    assert '"condition": "C0_minimal"' in path.read_text()
