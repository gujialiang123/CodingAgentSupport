"""K-candidate blind helper-test generator (EP-03, plan §5.2, §5.3).

Generates ``K`` independent helper-test candidates using a frozen generator model
and prompt. The generator is given ONLY the problem statement and scrubbed base
repository context (imports/fixtures/API/style). It never sees the gold patch,
official test patch, F2P/P2P ids, future commits, or the network.

The generator is model-agnostic via :class:`~se_support.agents.chat_client.ChatClient`
(ScriptedChatClient for offline tests; a pinned model in real runs).
"""

from __future__ import annotations

import re

from se_support.isolation.manifest import hash_text

_SYSTEM = """You write a single pytest reproduction test for a bug described in an issue.

STRICT RULES:
- The expected behavior asserted MUST be traceable to the issue text. Do not
  invent an exact error-message string or output format the issue did not state.
- Prefer behavioral assertions (an exception is raised; the message mentions the
  affected name) over brittle exact-string equality.
- Use only public APIs/imports visible in the provided repository context.
- Output ONLY one fenced python code block containing the test. No prose."""

_CODE_RE = re.compile(r"```(?:python)?\s*\n(.*?)```", re.DOTALL)


def _prompt(problem_statement: str, repo_context: str) -> list[dict]:
    user = (
        f"## Issue\n{problem_statement}\n\n"
        f"## Repository context (imports/fixtures/style; do not copy solutions)\n"
        f"{repo_context}\n\n"
        "Write one pytest test that FAILS on the current (buggy) code and would "
        "PASS once the issue is fixed. Assert only issue-level behavior."
    )
    return [{"role": "system", "content": _SYSTEM}, {"role": "user", "content": user}]


def _extract_code(reply: str) -> str | None:
    m = _CODE_RE.search(reply)
    if m:
        return m.group(1).strip()
    # Some models emit bare code; accept if it looks like a test.
    if "def test" in reply:
        return reply.strip()
    return None


def generate_candidates(
    problem_statement: str,
    repo_context: str,
    client,
    k: int = 3,
) -> list[str]:
    """Generate up to ``k`` helper-test source candidates (deduplicated)."""
    messages = _prompt(problem_statement, repo_context)
    seen: set[str] = set()
    candidates: list[str] = []
    for _ in range(k):
        reply = client.complete(messages)
        code = _extract_code(reply)
        if not code:
            continue
        h = hash_text(code)
        if h in seen:
            continue
        seen.add(h)
        candidates.append(code)
    return candidates


def prompt_hash(problem_statement: str, repo_context: str) -> str:
    msgs = _prompt(problem_statement, repo_context)
    return hash_text("\n".join(m["content"] for m in msgs))
