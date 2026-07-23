"""Tests for C1 v2 issue-based retrieval context (plan P5)."""

from __future__ import annotations

import json
from pathlib import Path

from se_support.schemas import TaskSpec
from se_support.support.context_pack import (
    build_context_pack_v2,
    build_random_context_pack,
    issue_query_terms,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _task() -> TaskSpec:
    return TaskSpec.model_validate(
        json.loads((FIXTURES / "task_mini_repo.json").read_text())
    )


def test_query_terms_boost_dotted_symbol():
    terms = issue_query_terms(_task())
    # `calc.subtract` is a dotted symbol -> both parts should rank highly.
    assert "subtract" in terms
    assert "calc" in terms
    # stopwords excluded
    assert "the" not in [t.lower() for t in terms]


def test_v2_retrieves_relevant_file_with_provenance():
    out = build_context_pack_v2(_task(), FIXTURES / "mini_repo")
    assert "calc.py" in out
    assert "(lines " in out            # provenance present
    assert "Query terms:" in out
    # the buggy line should be surfaced in the snippet
    assert "subtract" in out


def test_v2_respects_token_budget():
    small = build_context_pack_v2(_task(), FIXTURES / "mini_repo", token_budget=80)
    big = build_context_pack_v2(_task(), FIXTURES / "mini_repo", token_budget=4000)
    assert len(small) <= len(big)
    assert len(small) <= 80 * 4 + 400  # budget (chars) + header slack


def test_random_context_is_deterministic_by_seed():
    a = build_random_context_pack(_task(), FIXTURES / "mini_repo", seed=1)
    b = build_random_context_pack(_task(), FIXTURES / "mini_repo", seed=1)
    c = build_random_context_pack(_task(), FIXTURES / "mini_repo", seed=2)
    assert a == b
    assert "random control" in a
    # different seed may reorder/shift; content still bounded
    assert isinstance(c, str)
