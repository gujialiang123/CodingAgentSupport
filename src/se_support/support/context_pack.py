"""Context pack generator (C1).

Two versions are provided:

* **v1** (``build_context_pack``) — a lexical/structural file map + test-command
  hint. Cheap, leak-free, kept as a fallback when no reader can read file bodies.
* **v2** (``build_context_pack_v2``) — *issue-based retrieval*: score repo files by
  lexical/symbol overlap with the issue text, return the top-k files with the most
  relevant snippets (with ``path:line`` provenance), plus related existing test
  files, all trimmed to a fixed token budget. A **random-context control**
  (``build_random_context_pack``) fills the same budget with randomly chosen
  snippets, so an experiment can separate *more tokens* from *more relevant
  context* (plan P5, C1 v2).

All variants are gold-free: they read only the issue text and the base tree.
"""

from __future__ import annotations

import random
import re
from pathlib import Path

from se_support.schemas import TaskSpec

_SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".ruff_cache", "node_modules"}
_MAX_FILES = 60

# ~4 chars/token heuristic; keep C1's injected context bounded and comparable.
_DEFAULT_TOKEN_BUDGET = 1500
_CHARS_PER_TOKEN = 4

_STOPWORDS = {
    "the", "and", "for", "that", "this", "with", "from", "have", "not", "but",
    "you", "are", "was", "were", "when", "then", "would", "should", "could",
    "which", "into", "your", "will", "there", "their", "what", "about", "here",
    "code", "issue", "bug", "error", "test", "tests", "python", "def", "class",
    "self", "return", "true", "false", "none", "value", "values", "using", "use",
}
_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")
_SYMBOL = re.compile(r"`([^`]+)`|\b([A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_.]*)\b")


def _issue_text(task: TaskSpec) -> str:
    return " ".join(filter(None, [task.issue_title, task.issue_body]))


def issue_query_terms(task: TaskSpec, limit: int = 12) -> list[str]:
    """Salient identifiers/symbols from the issue, ranked by frequency.

    Backtick-quoted spans and dotted symbols (``mod.func``) are boosted because
    they are the strongest signal of which code the issue is about.
    """
    text = _issue_text(task)
    boosted: list[str] = []
    for m in _SYMBOL.finditer(text):
        span = (m.group(1) or m.group(2) or "").strip()
        for tok in _IDENT.findall(span):
            boosted.append(tok)
    counts: dict[str, int] = {}
    for tok in _IDENT.findall(text):
        low = tok.lower()
        if low in _STOPWORDS:
            continue
        counts[tok] = counts.get(tok, 0) + 1
    for tok in boosted:
        counts[tok] = counts.get(tok, 0) + 5  # provenance boost
    ranked = sorted(counts, key=lambda t: (-counts[t], t.lower()))
    return ranked[:limit]


def build_context_pack(task: TaskSpec, workspace_path: Path, reader=None) -> str:
    files: list[str] = []
    if reader is not None and hasattr(reader, "list_repo_files"):
        files = reader.list_repo_files(_MAX_FILES)
    else:
        for p in sorted(workspace_path.rglob("*")):
            if any(part in _SKIP_DIRS for part in p.parts):
                continue
            if p.is_file():
                files.append(str(p.relative_to(workspace_path)))
            if len(files) >= _MAX_FILES:
                break

    lines = ["## Repository context (auto-generated)", ""]
    lines.append(f"Repository: {task.repo}")
    if task.test_command:
        lines.append(f"Test command hint: `{task.test_command}`")
    lines.append("")
    lines.append("Files:")
    lines += [f"- {f}" for f in files]
    if len(files) >= _MAX_FILES:
        lines.append(f"- ... (truncated at {_MAX_FILES} files)")
    return "\n".join(lines) + "\n"


def _read(reader, workspace_path: Path, relpath: str, max_bytes: int = 20000) -> str:
    if reader is not None and hasattr(reader, "read_file"):
        return reader.read_file(relpath, max_bytes)
    p = workspace_path / relpath
    try:
        return p.read_text(encoding="utf-8", errors="replace")[:max_bytes]
    except OSError:
        return ""


def _candidate_files(reader, workspace_path: Path, terms: list[str]) -> list[str]:
    if reader is not None and hasattr(reader, "grep_files"):
        hits = reader.grep_files(terms)
        if hits:
            return hits
    # Disk fallback: scan file bodies for any term.
    lowered = [t.lower() for t in terms]
    out: list[str] = []
    for p in sorted(workspace_path.rglob("*.py")):
        if any(part in _SKIP_DIRS for part in p.parts):
            continue
        try:
            body = p.read_text(encoding="utf-8", errors="replace").lower()
        except OSError:
            continue
        if any(t in body for t in lowered):
            out.append(str(p.relative_to(workspace_path)))
        if len(out) >= 40:
            break
    return out


def _score_file(path: str, body: str, terms: list[str]) -> int:
    low = body.lower()
    score = sum(low.count(t.lower()) for t in terms)
    # Prefer source over tests for the primary hit list; tests handled separately.
    if "/test" in path or path.startswith("test"):
        score = score // 2
    return score


def _best_snippet(
    body: str, terms: list[str], span: int = 6, max_lines: int = 14
) -> list[tuple[int, str]]:
    """Return ``(lineno, text)`` for the window around the densest term match."""
    lines = body.splitlines()
    if not lines:
        return []
    low_terms = [t.lower() for t in terms]
    best_i, best_hits = 0, -1
    for i, ln in enumerate(lines):
        low = ln.lower()
        hits = sum(low.count(t) for t in low_terms)
        if hits > best_hits:
            best_hits, best_i = hits, i
    start = max(0, best_i - span // 2)
    end = min(len(lines), start + max_lines)
    return [(start + 1 + k, lines[start + k]) for k in range(end - start)]


def build_context_pack_v2(
    task: TaskSpec,
    workspace_path: Path,
    reader=None,
    *,
    token_budget: int = _DEFAULT_TOKEN_BUDGET,
    top_k: int = 5,
) -> str:
    """Issue-based retrieval context with provenance and a fixed token budget."""
    terms = issue_query_terms(task)
    if not terms:
        return build_context_pack(task, workspace_path, reader=reader)

    candidates = _candidate_files(reader, workspace_path, terms)
    scored: list[tuple[int, str, str]] = []
    for rel in candidates:
        body = _read(reader, workspace_path, rel)
        if not body:
            continue
        scored.append((_score_file(rel, body, terms), rel, body))
    scored.sort(key=lambda x: (-x[0], x[1]))

    src = [s for s in scored if not ("/test" in s[1] or s[1].startswith("test"))]
    tests = [s for s in scored if ("/test" in s[1] or s[1].startswith("test"))]

    budget_chars = token_budget * _CHARS_PER_TOKEN
    lines = ["## Issue-relevant repository context (retrieved, C1 v2)", ""]
    lines.append(f"Repository: {task.repo}")
    if task.test_command:
        lines.append(f"Test command hint: `{task.test_command}`")
    lines.append(f"Query terms: {', '.join(terms)}")
    lines.append("")
    used = len("\n".join(lines))

    def _emit_block(rel: str, body: str) -> bool:
        nonlocal used
        snippet = _best_snippet(body, terms)
        if not snippet:
            return True
        header = f"### {rel} (lines {snippet[0][0]}-{snippet[-1][0]})"
        block = [header, "```python"]
        block += [f"{n:>5}  {txt}" for n, txt in snippet]
        block.append("```")
        text = "\n".join(block)
        if used + len(text) > budget_chars:
            return False
        lines.append(text)
        lines.append("")
        used += len(text) + 1
        return True

    lines.append("## Top relevant source")
    for _score, rel, body in src[:top_k]:
        if not _emit_block(rel, body):
            break
    if tests:
        lines.append("## Related existing tests")
        for _score, rel, body in tests[:2]:
            if not _emit_block(rel, body):
                break
    return "\n".join(lines) + "\n"


def build_random_context_pack(
    task: TaskSpec,
    workspace_path: Path,
    reader=None,
    *,
    token_budget: int = _DEFAULT_TOKEN_BUDGET,
    seed: int = 0,
) -> str:
    """Control for C1 v2: same token budget, randomly chosen snippets.

    Separates the effect of *more tokens* from *more relevant context*. Uses only
    the base tree (gold-free) and the same rendering as v2 so the only difference
    is relevance.
    """
    rng = random.Random(seed)
    files: list[str] = []
    if reader is not None and hasattr(reader, "list_repo_files"):
        files = [f for f in reader.list_repo_files(200) if f.endswith(".py")]
    else:
        files = [str(p.relative_to(workspace_path))
                 for p in workspace_path.rglob("*.py")
                 if not any(part in _SKIP_DIRS for part in p.parts)]
    rng.shuffle(files)

    budget_chars = token_budget * _CHARS_PER_TOKEN
    lines = ["## Repository context (random control, C1 v2-random)", ""]
    lines.append(f"Repository: {task.repo}")
    if task.test_command:
        lines.append(f"Test command hint: `{task.test_command}`")
    lines.append("")
    used = len("\n".join(lines))
    for rel in files:
        body = _read(reader, workspace_path, rel)
        b_lines = body.splitlines()
        if len(b_lines) < 4:
            continue
        start = rng.randint(0, max(0, len(b_lines) - 14))
        chunk = b_lines[start:start + 14]
        block = [f"### {rel} (lines {start + 1}-{start + len(chunk)})", "```python"]
        block += [f"{start + 1 + k:>5}  {txt}" for k, txt in enumerate(chunk)]
        block.append("```")
        text = "\n".join(block)
        if used + len(text) > budget_chars:
            break
        lines.append(text)
        lines.append("")
        used += len(text) + 1
    return "\n".join(lines) + "\n"
