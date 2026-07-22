"""Controllable LLM agent (mini bash-loop) implementing AgentRunner.

A compact, fully-controllable ReAct-style loop -- the kind of scaffold the study
needs so support conditions can be injected/removed cleanly. It is model-agnostic
via :class:`~se_support.agents.chat_client.ChatClient` (vLLM locally now, pinned
API later).

Loop per turn:
1. ask the model,
2. if the reply contains a ```bash``` block, run it in the workspace and feed
   back the (truncated) output,
3. if the reply is ``SUBMIT``, optionally run gates (condition C3); if a blocking
   gate fails, feed the failure back and keep going; otherwise finish.

Every model message and command is logged to the RunDirectory, so the full
interaction is replayable for post-hoc metrics.
"""

from __future__ import annotations

import re
import time

from se_support.agents.chat_client import ChatClient
from se_support.runner.run_dir import (
    FILE_FINAL_MESSAGE,
    FILE_GATE_RESULTS,
    RunDirectory,
    TranscriptEvent,
)
from se_support.runner.workspace import Workspace
from se_support.schemas import AgentRunResult, RunStatus, TaskSpec
from se_support.support import (
    build_system_prompt,
    get_condition,
)
from se_support.support.gate_policy import (
    GatePolicy,
    blocking_failures,
    format_feedback,
    run_policy,
)
from se_support.support.harness import HarnessStateMachine

_BASH_RE = re.compile(r"```bash\s*\n(.*?)```", re.DOTALL)
_MAX_OBS = 4000

# Harness (C4) directives parsed from the agent's message.
_NEXT_STATE_RE = re.compile(r"^NEXT_STATE:\s*([A-Z]+)\s*$", re.MULTILINE)
_RECORD_RES = {
    "localization": re.compile(r"^LOCALIZATION:\s*(.+)$", re.MULTILINE),
    "diagnosis": re.compile(r"^DIAGNOSIS:\s*(.+)$", re.MULTILINE),
    "validation": re.compile(r"^VALIDATION:\s*(.+)$", re.MULTILINE),
}


class LLMAgent:
    def __init__(self, client: ChatClient, max_turns: int = 20, sandbox_policy=None) -> None:
        self.client = client
        self.max_turns = max_turns
        # When set, agent bash commands run under this sandbox policy (EP-01).
        self.sandbox_policy = sandbox_policy
        # When set, the frozen support bundle the agent's prompt is built from (EP-02).
        self.support_bundle = None
        # C3 gate policy + base-tree advisory baseline (EP-07).
        self.gate_policy = GatePolicy()
        self.gate_baseline: dict = {}
        self.name = f"llm_agent[{getattr(client, 'model', 'unknown')}]"

    def run(
        self,
        task: TaskSpec,
        condition: str,
        workspace: Workspace,
        run_dir: RunDirectory,
    ) -> AgentRunResult:
        t0 = time.time()
        cond = get_condition(condition)
        system = build_system_prompt(task, cond, workspace.path, bundle=self.support_bundle)
        messages: list[dict[str, str]] = [{"role": "system", "content": system}]
        run_dir.append_transcript(TranscriptEvent(step=0, role="system", content=system))

        # EP-04: enforced workflow state machine when C4 (harness) is active.
        harness = HarnessStateMachine() if cond.harness else None
        gate_revisions = 0  # EP-07 revision budget counter

        status = RunStatus.completed
        error = None
        step = 1
        submitted = False
        try:
            while step <= self.max_turns:
                reply = self.client.complete(messages)
                messages.append({"role": "assistant", "content": reply})
                run_dir.append_transcript(
                    TranscriptEvent(step=step, role="assistant", content=reply)
                )

                # Parse + apply harness records/transitions from this message.
                if harness is not None:
                    fb = self._apply_harness_directives(reply, harness, run_dir, step)
                    if fb:
                        messages.append({"role": "user", "content": fb})
                        run_dir.append_transcript(
                            TranscriptEvent(step=step, role="tool", content=fb)
                        )

                bash = self._extract_bash(reply)
                if bash is not None:
                    if self.sandbox_policy is not None:
                        proc, _backend = workspace.run_sandboxed(
                            bash, self.sandbox_policy, step=step
                        )
                    elif not hasattr(workspace, "_run"):
                        # Container workspace: always exec inside the container.
                        proc, _backend = workspace.run_sandboxed(bash, None, step=step)
                    else:
                        proc = workspace._run("bash", "-lc", bash, step=step, check=False)
                    obs = (proc.stdout + proc.stderr)[:_MAX_OBS]
                    obs_msg = f"[exit={proc.returncode}]\n{obs}"

                    # EP-04: reject edits made outside PATCH/VALIDATE by reverting.
                    if harness is not None and not harness.can_edit() and workspace.is_dirty():
                        workspace.revert_all()
                        harness.reject("edit", f"edits not allowed in {harness.state.value}")
                        obs_msg += (
                            f"\n[HARNESS] Edits are not allowed in {harness.state.value}; "
                            "your changes were reverted. Localize/diagnose first, then "
                            "NEXT_STATE: PATCH."
                        )
                    messages.append({"role": "user", "content": obs_msg})
                    run_dir.append_transcript(
                        TranscriptEvent(step=step, role="tool", content=obs_msg)
                    )
                elif self._is_submit(reply):
                    # EP-04: block SUBMIT unless the workflow reached SUBMIT.
                    if harness is not None and not harness.can_submit():
                        harness.reject("submit", f"cannot submit from {harness.state.value}")
                        fb = (
                            f"[HARNESS] Cannot SUBMIT from {harness.state.value}. Complete "
                            "DISCOVER→DIAGNOSE→PATCH→VALIDATE with the required records "
                            "(LOCALIZATION/DIAGNOSIS/VALIDATION) and NEXT_STATE directives first."
                        )
                        messages.append({"role": "user", "content": fb})
                        run_dir.append_transcript(
                            TranscriptEvent(step=step, role="tool", content=fb)
                        )
                        step += 1
                        continue
                    if cond.gates:
                        gate_exec = (workspace.gate_exec_fn()
                                     if hasattr(workspace, "gate_exec_fn") else None)
                        results = run_policy(
                            workspace.path, self.gate_baseline, self.gate_policy,
                            exec_fn=gate_exec,
                        )
                        run_dir.write_json(
                            FILE_GATE_RESULTS, [r.to_dict() for r in results]
                        )
                        failures = blocking_failures(results)
                        if failures and gate_revisions < self.gate_policy.revision_budget:
                            gate_revisions += 1
                            fb = format_feedback(failures) + (
                                f"\n[gate revision {gate_revisions}/"
                                f"{self.gate_policy.revision_budget}]"
                            )
                            messages.append({"role": "user", "content": fb})
                            run_dir.append_transcript(
                                TranscriptEvent(step=step, role="tool", content=fb)
                            )
                            step += 1
                            continue
                        # Budget exhausted or gates pass: proceed to submit.
                    submitted = True
                    break
                else:
                    if harness is None:
                        nudge = (
                            "Reply with exactly one ```bash``` block to run a command, "
                            "or the single word SUBMIT when done."
                        )
                        messages.append({"role": "user", "content": nudge})
                        run_dir.append_transcript(
                            TranscriptEvent(step=step, role="tool", content=nudge)
                        )
                step += 1
            if not submitted and step > self.max_turns:
                status = RunStatus.timeout
        except Exception as exc:  # noqa: BLE001 - record and continue pipeline
            status = RunStatus.error
            error = repr(exc)

        if harness is not None:
            self._write_state_transitions(harness, run_dir)

        run_dir.write_text(
            FILE_FINAL_MESSAGE,
            f"# LLM agent ({self.name})\ncondition={condition} status={status} "
            f"turns={step} submitted={submitted}\n",
        )
        return AgentRunResult(
            run_id=run_dir.path.name,
            status=status,
            transcript_path=str(run_dir.path / "transcript.jsonl"),
            commands_path=str(run_dir.path / "commands.jsonl"),
            final_message_path=str(run_dir.path / FILE_FINAL_MESSAGE),
            duration_sec=round(time.time() - t0, 4),
            error=error,
        )

    @staticmethod
    def _extract_bash(reply: str) -> str | None:
        m = _BASH_RE.search(reply)
        return m.group(1).strip() if m else None

    @staticmethod
    def _is_submit(reply: str) -> bool:
        return reply.strip().upper() == "SUBMIT" or reply.strip().upper().endswith("\nSUBMIT")

    @staticmethod
    def _apply_harness_directives(reply, harness, run_dir, step) -> str | None:
        """Parse LOCALIZATION/DIAGNOSIS/VALIDATION records + NEXT_STATE directive.

        Returns feedback text to send the agent (e.g. a rejected transition), or
        None. Records are captured before transitions so prerequisites can be met
        in the same message.
        """
        for kind, rx in _RECORD_RES.items():
            m = rx.search(reply)
            if m:
                harness.record(kind, m.group(1))

        m = _NEXT_STATE_RE.search(reply)
        if not m:
            return None
        t = harness.request_transition(m.group(1))
        if not t.ok:
            missing = t.reason
            hint = ""
            if "missing required" in missing:
                need = missing.split("missing required ")[1].split(" record")[0]
                hint = (f" Output a line `{need.upper()}: <...>` and then "
                        f"NEXT_STATE: {t.to}.")
            return f"[HARNESS] Transition {t.frm}->{t.to} rejected: {t.reason}.{hint}"
        return f"[HARNESS] Now in {harness.state.value}."

    @staticmethod
    def _write_state_transitions(harness, run_dir) -> None:
        rows = []
        for t in harness.transitions:
            rows.append({"type": "transition", "from": t.frm, "to": t.to,
                         "ok": t.ok, "reason": t.reason})
        for r in harness.rejections:
            rows.append({"type": "rejection", "state": r.state,
                         "action": r.action, "reason": r.reason})
        run_dir.write_json("state_transitions.json", rows)
