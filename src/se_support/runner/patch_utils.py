"""Unified-diff parsing and simple diff metrics.

Used for locality metrics (files_touched, loc_added/deleted) and gold-overlap.
Pure text parsing -- no git needed -- so metrics can be recomputed from a stored
``final.patch`` alone.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DiffMetrics:
    files_touched: int = 0
    loc_added: int = 0
    loc_deleted: int = 0
    files: list[str] = field(default_factory=list)


def _changed_path(line: str) -> str | None:
    # Prefer the "+++ b/path" side; fall back to "--- a/path".
    if line.startswith("+++ "):
        p = line[4:].strip()
    elif line.startswith("--- "):
        p = line[4:].strip()
    else:
        return None
    if p in ("/dev/null",):
        return None
    for prefix in ("a/", "b/"):
        if p.startswith(prefix):
            p = p[len(prefix):]
    return p or None


def diff_metrics(diff_text: str) -> DiffMetrics:
    """Compute file/line counts from a unified diff."""
    files: list[str] = []
    added = deleted = 0
    for line in diff_text.splitlines():
        if line.startswith("diff --git"):
            continue
        if line.startswith("+++ "):
            path = _changed_path(line)
            if path and path not in files:
                files.append(path)
            continue
        if line.startswith("--- "):
            continue
        if line.startswith("@@"):
            continue
        if line.startswith("+"):
            added += 1
        elif line.startswith("-"):
            deleted += 1
    return DiffMetrics(files_touched=len(files), loc_added=added, loc_deleted=deleted, files=files)


def changed_files(diff_text: str) -> list[str]:
    return diff_metrics(diff_text).files
