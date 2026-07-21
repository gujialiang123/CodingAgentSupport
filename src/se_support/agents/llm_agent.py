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
    blocking_failures,
    build_system_prompt,
    get_condition,
    run_gates,
)

_BASH_RE = re.compile(r"```bash\s*\n(.*?)```", re.DOTALL)
_MAX_OBS = 4000


class LLMAgent:
    def __init__(self, client: ChatClient, max_turns: int = 20, sandbox_policy=None) -> None:
        self.client = client
        self.max_turns = max_turns
        # When set, agent bash commands run under this sandbox policy (EP-01).
        self.sandbox_policy = sandbox_policy
        # When set, the frozen support bundle the agent's prompt is built from (EP-02).
        self.support_bundle = None
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

                bash = self._extract_bash(reply)
                if bash is not None:
                    if self.sandbox_policy is not None:
                        proc, _backend = workspace.run_sandboxed(
                            bash, self.sandbox_policy, step=step
                        )
                    else:
                        proc = workspace._run("bash", "-lc", bash, step=step, check=False)
                    obs = (proc.stdout + proc.stderr)[:_MAX_OBS]
                    obs_msg = f"[exit={proc.returncode}]\n{obs}"
                    messages.append({"role": "user", "content": obs_msg})
                    run_dir.append_transcript(
                        TranscriptEvent(step=step, role="tool", content=obs_msg)
                    )
                elif self._is_submit(reply):
                    if cond.gates:
                        results = run_gates(workspace.path)
                        run_dir.write_json(FILE_GATE_RESULTS, results)
                        failures = blocking_failures(results)
                        if failures:
                            fb = "Blocking gate(s) failed; fix before submitting:\n" + "\n".join(
                                f"- {f['gate_name']}: {f['output_preview'][:500]}" for f in failures
                            )
                            messages.append({"role": "user", "content": fb})
                            run_dir.append_transcript(
                                TranscriptEvent(step=step, role="tool", content=fb)
                            )
                            step += 1
                            continue
                    submitted = True
                    break
                else:
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
