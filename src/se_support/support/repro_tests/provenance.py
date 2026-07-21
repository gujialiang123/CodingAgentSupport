"""Assertion-provenance + suspicious-literal audit (EP-03, plan §5.2, §5.4).

Enforces the rule: *the expected behavior of every assertion must be traceable to
the issue*. We extract string/number literals used in the test's ``assert``
statements and flag any that do not appear in the problem statement, since those
are candidates for an invented (non-issue) oracle or leaked official string.
"""

from __future__ import annotations

import ast
import re


def _literals_in_asserts(test_source: str) -> list[str]:
    """Return string/number literals that appear inside assert statements."""
    literals: list[str] = []
    try:
        tree = ast.parse(test_source)
    except SyntaxError:
        return literals
    for node in ast.walk(tree):
        if isinstance(node, ast.Assert):
            for sub in ast.walk(node):
                if isinstance(sub, ast.Constant) and isinstance(sub.value, (str, int, float)):
                    literals.append(str(sub.value))
    return literals


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower())


def suspicious_literals(test_source: str, issue_text: str, min_len: int = 4) -> list[str]:
    """String literals in assertions that are not traceable to the issue text.

    Short literals (< ``min_len``) and pure identifiers are ignored; the concern is
    long exact-message strings that the issue never specified (e.g. a leaked
    maintainer message format).
    """
    issue = _normalize(issue_text)
    flagged: list[str] = []
    for lit in _literals_in_asserts(test_source):
        if not isinstance(lit, str):
            continue
        if len(lit) < min_len:
            continue
        # A single word/identifier (e.g. a column name) is fine if in the issue.
        if _normalize(lit) in issue:
            continue
        # Multi-word exact strings not present in the issue are suspicious.
        if len(lit.split()) >= 3 or len(lit) >= 25:
            flagged.append(lit)
    return flagged


def has_issue_provenance(test_source: str, issue_text: str) -> bool:
    """True if no assertion relies on a literal untraceable to the issue."""
    return not suspicious_literals(test_source, issue_text)


def contains_forbidden_literal(test_source: str, forbidden: list[str]) -> list[str]:
    """Return any forbidden (e.g. official-test) substrings present verbatim."""
    return [f for f in forbidden if f and f in test_source]
