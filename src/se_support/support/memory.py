"""Repository memory generator (C5).

**v2 (plan P5).** C5 models *durable, repository-scoped* knowledge an experienced
maintainer would carry between tasks: build/test recipes, conventions, module
boundaries, fixture patterns, compatibility constraints and common failure
recovery. It is:

* **repository-scoped, not task-scoped** — derived only from repo-wide files
  (README/CONTRIBUTING/pyproject/tox/setup.cfg/conftest, top-level layout). The
  *current* task's issue text, changed files and diagnostics never enter C5.
* **generated once and frozen** before any evaluation task is seen
  (``scripts/freeze_repo_memory.py`` writes ``data/repo_memory/<repo>.md``);
  ``build_memory`` prefers the frozen artifact so C5 cannot smuggle in
  task-specific hints.

Basic *operational access* ("how to install / run the tests") is deliberately
**not** unique to C5 — it belongs to the shared baseline available to every
condition — so C5 measures *memory*, not *operational access* (plan P5).
"""

from __future__ import annotations

import re
from pathlib import Path

from se_support.schemas import TaskSpec

_CONVENTION_FILES = ("pyproject.toml", "setup.cfg", "tox.ini", "ruff.toml", ".ruff.toml")
_DOC_FILES = ("README.md", "README.rst", "CONTRIBUTING.md", "CONTRIBUTING.rst")


def repo_slug(repo: str) -> str:
    """Filesystem-safe key for a repo (``psf/requests`` -> ``psf__requests``)."""
    return repo.replace("/", "__")


def _read(reader, workspace_path: Path, relpath: str, max_bytes: int = 8000) -> str:
    if reader is not None and hasattr(reader, "read_file"):
        return reader.read_file(relpath, max_bytes)
    p = workspace_path / relpath
    try:
        return p.read_text(encoding="utf-8", errors="replace")[:max_bytes]
    except OSError:
        return ""


def _has(reader, workspace_path: Path, relpath: str) -> bool:
    if reader is not None and hasattr(reader, "has_file"):
        return reader.has_file(relpath)
    return (workspace_path / relpath).exists()


def _top_level_packages(reader, workspace_path: Path) -> list[str]:
    files: list[str] = []
    if reader is not None and hasattr(reader, "list_repo_files"):
        files = reader.list_repo_files(200)
    else:
        files = [str(p.relative_to(workspace_path))
                 for p in workspace_path.rglob("*")
                 if p.is_file()]
    pkgs: set[str] = set()
    for f in files:
        parts = f.split("/")
        if len(parts) >= 2 and parts[1] == "__init__.py":
            pkgs.add(parts[0])
        elif len(parts) == 1 and f.endswith(".py") and f != "setup.py":
            pkgs.add(f)
    return sorted(pkgs)[:12]


def _compat_constraints(text: str) -> list[str]:
    out: list[str] = []
    m = re.search(r"python_requires\s*=\s*['\"]([^'\"]+)['\"]", text)
    if m:
        out.append(f"Supported Python: {m.group(1)}")
    vers = sorted(set(re.findall(r"Programming Language :: Python :: (\d+\.\d+)", text)))
    if vers:
        out.append(f"Declared Python versions: {', '.join(vers)}")
    return out


def build_repo_memory(repo: str, workspace_path: Path, reader=None) -> str:
    """Derive repository-scoped memory (no task-specific inputs)."""
    lines = [f"## Repository memory: {repo} (AGENTS.md, frozen, repo-scoped)", ""]

    pkgs = _top_level_packages(reader, workspace_path)
    if pkgs:
        lines.append("### Module boundaries")
        lines.append(f"- Top-level packages/modules: {', '.join(pkgs)}")
        lines.append("- Keep edits within the module that owns the behavior.")
        lines.append("")

    conv = [f for f in _CONVENTION_FILES if _has(reader, workspace_path, f)]
    if conv:
        lines.append("### Conventions & tooling")
        lines.append(f"- Config/convention files: {', '.join(conv)}")
        joined = " ".join(_read(reader, workspace_path, f) for f in conv)
        for tool in ("ruff", "flake8", "black", "isort", "mypy", "pytest"):
            if tool in joined.lower():
                lines.append(f"- Repo configures `{tool}`; match its settings.")
        compat = _compat_constraints(joined)
        for c in compat:
            lines.append(f"- {c}")
        lines.append("")

    if _has(reader, workspace_path, "conftest.py") or _has(
        reader, workspace_path, "tests/conftest.py"
    ):
        lines.append("### Fixture patterns")
        lines.append("- Repo uses pytest `conftest.py` fixtures; reuse existing "
                     "fixtures rather than constructing state inline.")
        lines.append("")

    for doc in _DOC_FILES:
        if _has(reader, workspace_path, doc):
            body = _read(reader, workspace_path, doc, 4000)
            hints = []
            for ln in body.splitlines():
                s = ln.strip("-*# ").strip()
                if not s or s.startswith("..") or "img.shields" in s \
                        or "image::" in s or "://" in s:
                    continue  # skip RST directives / badges / bare URLs
                if re.search(r"\b(convention|style|guideline|must|please|do not|"
                             r"backward|compat|deprecat)\b", s, re.I):
                    hints.append(s)
            if hints:
                lines.append(f"### Notes distilled from {doc}")
                for h in hints[:5]:
                    lines.append(f"- {h[:160]}")
                lines.append("")
            break

    lines.append("### Common failure recovery")
    lines.append("- If imports fail, check you are in the repo's env and the "
                 "package is importable from the top-level package.")
    lines.append("- If a test errors on collection, fix the import/signature "
                 "before assuming the logic is wrong.")
    lines.append("- Prefer minimal diffs; do not touch unrelated files or tests.")
    return "\n".join(lines) + "\n"


def _frozen_path(repo: str, cache_dir: Path | None) -> Path | None:
    if cache_dir is None:
        return None
    p = Path(cache_dir) / f"{repo_slug(repo)}.md"
    return p if p.exists() else None


def build_memory(
    task: TaskSpec, workspace_path: Path, reader=None, cache_dir: Path | None = None
) -> str:
    """C5 artifact for a task's repo: frozen repo memory if present, else derived.

    Task fields are intentionally not consulted beyond ``task.repo`` — C5 is
    repo-scoped and must not leak task-specific setup/test/issue information.
    """
    frozen = _frozen_path(task.repo, cache_dir)
    if frozen is not None:
        return frozen.read_text(encoding="utf-8")
    return build_repo_memory(task.repo, workspace_path, reader=reader)
