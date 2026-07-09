"""System-prompt assembly conditioned on the SupportCondition.

The base instructions are identical across conditions; support flags *add*
material (context, memory, harness rules). This keeps the causal comparison
clean: differences in agent behaviour trace to the added support, not to a
rewritten prompt.
"""

from __future__ import annotations

from pathlib import Path

from se_support.schemas import TaskSpec
from se_support.support.condition import SupportCondition
from se_support.support.context_pack import build_context_pack
from se_support.support.memory import build_memory

_BASE = """You are a software engineering agent fixing a bug in a repository.

You interact by emitting shell commands. To run a command, reply with EXACTLY one
fenced bash block:

```bash
<your command>
```

You are in the repository root. Inspect files, edit them (e.g. with `python -`,
`sed`, or writing files), and verify your fix. When the fix is complete, reply
with exactly the single word:

SUBMIT

Do not include a bash block in the same message as SUBMIT."""

_HARNESS_RULES = """

WORKFLOW RULES (must follow in order):
1. First localize: inspect the repository and identify the faulty file/function
   BEFORE editing anything.
2. State a short diagnosis of the root cause.
3. Make the minimal edit that fixes the root cause.
4. Verify by running the relevant tests/commands.
5. If a check fails, classify why before making another edit.
Do not edit code before completing step 1. Do not SUBMIT before verifying."""


def build_system_prompt(
    task: TaskSpec,
    condition: SupportCondition,
    workspace_path: Path,
) -> str:
    parts = [_BASE]
    parts.append(f"\n## Issue\nTitle: {task.issue_title}\n\n{task.issue_body}")

    if condition.context:
        parts.append("\n" + build_context_pack(task, workspace_path))
    if condition.memory:
        parts.append("\n" + build_memory(task, workspace_path))
    if condition.harness:
        parts.append(_HARNESS_RULES)

    return "\n".join(parts)
