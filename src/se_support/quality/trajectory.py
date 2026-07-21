"""Trajectory/process-metric extraction from run logs (EP-08).

Pure, offline parsing of a run directory's ``transcript.jsonl``,
``commands.jsonl`` and ``state_transitions.json`` into
:class:`~se_support.schemas.patch_quality_card.ProcessMetrics`. Because it only
reads saved artifacts, new process metrics can be back-filled without re-running.
"""

from __future__ import annotations

import json
from pathlib import Path

from se_support.runner.run_dir import FILE_COMMANDS, FILE_TRANSCRIPT
from se_support.schemas.patch_quality_card import ProcessMetrics


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def extract_process_metrics(run_dir: Path) -> ProcessMetrics:
    run_dir = Path(run_dir)
    transcript = _read_jsonl(run_dir / FILE_TRANSCRIPT)
    commands = _read_jsonl(run_dir / FILE_COMMANDS)

    # Agent bash commands are the ones tagged with a sandbox backend in meta, or
    # (unsandboxed) every non-git command. Count all recorded commands as a proxy
    # but separate git orchestration ops.
    agent_cmds = [c for c in commands if not c.get("command", "").startswith("git ")]
    failed = sum(1 for c in agent_cmds if (c.get("exit_code") or 0) != 0)
    sandbox_backends = {c.get("meta", {}).get("sandbox") for c in commands
                        if c.get("meta", {}).get("sandbox")}

    assistant_turns = [e for e in transcript if e.get("role") == "assistant"]

    # Gate + harness signals from tool messages / state_transitions.
    gate_failures = sum(
        1 for e in transcript
        if e.get("role") == "tool" and "gate(s) failed" in e.get("content", "")
    )
    gate_revisions = sum(
        1 for e in transcript
        if e.get("role") == "tool" and "gate revision" in e.get("content", "")
    )
    st_path = run_dir / "state_transitions.json"
    st = json.loads(st_path.read_text()) if st_path.exists() else []
    harness_rejections = sum(
        1 for r in st if isinstance(r, dict) and r.get("type") == "rejection"
    )

    stop_reason = None
    final_msg = run_dir / "final_message.md"
    if final_msg.exists():
        text = final_msg.read_text()
        if "submitted=True" in text:
            stop_reason = "submitted"
        elif "timeout" in text.lower():
            stop_reason = "timeout"
        elif "error" in text.lower():
            stop_reason = "error"

    return ProcessMetrics(
        turns=len(assistant_turns),
        commands_run=len(agent_cmds),
        failed_commands=failed,
        gate_failures=gate_failures,
        gate_revisions=gate_revisions,
        harness_rejections=harness_rejections,
        sandbox_backend=next(iter(sandbox_backends)) if sandbox_backends else None,
        stop_reason=stop_reason,
    )
