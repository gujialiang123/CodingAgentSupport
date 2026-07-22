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

You are in the repository root. The target package is already importable; you do
NOT have network access, so do not try to pip install, create virtualenvs, or
fetch anything. Fix the bug by editing the repository's source files directly.
Use only NON-INTERACTIVE commands (e.g. a `python - <<'PY' ... PY` heredoc,
`sed -i`, or redirecting into a file). Do NOT use interactive editors such as
nano, vim, or less. Inspect files, make the edit, and verify it. When the fix is
complete, reply with exactly the single word:

SUBMIT

Do not include a bash block in the same message as SUBMIT."""

_HARNESS_RULES = """

ENFORCED WORKFLOW (C4). You move through states in order:
DISCOVER → DIAGNOSE → PATCH → VALIDATE → SUBMIT.

Rules (the runner enforces these):
1. Code edits are ONLY allowed in PATCH and VALIDATE. Edits attempted in
   DISCOVER or DIAGNOSE are automatically reverted.
2. To advance one state, output a line exactly: `NEXT_STATE: <STATE>`.
3. To leave DISCOVER you must first output a line `LOCALIZATION: <where the fault is>`.
4. To leave DIAGNOSE you must first output a line `DIAGNOSIS: <root cause>`.
5. To SUBMIT you must be in the SUBMIT state; to leave VALIDATE you must first
   output a line `VALIDATION: <how you verified the fix>`.
Do not edit code before NEXT_STATE: PATCH. Do not SUBMIT before validating."""


def build_system_prompt(
    task: TaskSpec,
    condition: SupportCondition,
    workspace_path: Path,
    bundle=None,
) -> str:
    """Build the system prompt.

    If a frozen ``bundle`` (EP-02 :class:`SupportBundle`) is given, context and
    memory text come from the bundle's artifacts (single frozen source). Without
    a bundle (dev/smoke), artifacts are generated inline.
    """
    parts = [_BASE]
    parts.append(f"\n## Issue\nTitle: {task.issue_title}\n\n{task.issue_body}")

    if condition.context:
        if bundle is not None and bundle.artifact("context"):
            parts.append("\n" + bundle.artifact("context").content)
        else:
            parts.append("\n" + build_context_pack(task, workspace_path))
    if condition.memory:
        if bundle is not None and bundle.artifact("memory"):
            parts.append("\n" + bundle.artifact("memory").content)
        else:
            parts.append("\n" + build_memory(task, workspace_path))
    if condition.tests and bundle is not None:
        tests_art = bundle.artifact("tests")
        if tests_art is not None and tests_art.status == "present" and tests_art.content:
            parts.append(
                "\n## Reproduction test (helper)\n"
                "A reproduction test for this issue is available at "
                "`se_support_helper_test.py` in the repo root. Run it with "
                "`python -m pytest se_support_helper_test.py` to check your fix. "
                "It should FAIL before your fix and PASS after. It is a helper, "
                "not the grader; do not edit it.\n\n```python\n"
                + tests_art.content + "\n```"
            )
    if condition.harness:
        parts.append(_HARNESS_RULES)

    return "\n".join(parts)
