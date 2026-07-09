"""Tests for se_support data contracts (T1).

Covers, for every model:
* valid fixture round-trips (load -> dump -> reload equals).
* an invalid example raises ValidationError.
* JSON-schema export produces valid, self-consistent JSON.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from se_support.schemas import (
    EXPORTED_MODELS,
    AgentRunResult,
    EvalResult,
    PatchQualityCard,
    RunSpec,
    TaskSpec,
    export_schemas,
)

FIXTURES = Path(__file__).parent / "fixtures"

MODEL_BY_FIXTURE = {
    "task_spec": TaskSpec,
    "run_spec": RunSpec,
    "agent_run_result": AgentRunResult,
    "eval_result": EvalResult,
    "patch_quality_card": PatchQualityCard,
}


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.valid.json").read_text())


@pytest.mark.parametrize("name,model", list(MODEL_BY_FIXTURE.items()))
def test_valid_fixture_roundtrips(name, model):
    data = _load_fixture(name)
    obj = model.model_validate(data)
    # dump -> reload must be stable.
    reloaded = model.model_validate(json.loads(obj.model_dump_json()))
    assert reloaded == obj


def test_taskspec_defaults_and_nested():
    obj = TaskSpec(task_id="t", dataset="d", repo="a/b", base_commit="c")
    assert obj.metadata.language == "python"
    assert obj.fail_to_pass_tests == []


def test_unknown_field_forbidden():
    with pytest.raises(ValidationError):
        TaskSpec(task_id="t", dataset="d", repo="a/b", base_commit="c", bogus=1)


def test_missing_required_field_raises():
    with pytest.raises(ValidationError):
        RunSpec(task_id="t", agent="a", model="m", condition="C0_minimal")  # no run_id


def test_wrong_type_raises():
    with pytest.raises(ValidationError):
        EvalResult(run_id="r", fail_to_pass_passed="not-an-int")


def test_enum_values_serialised():
    card = PatchQualityCard(run_id="r", task_id="t")
    dumped = json.loads(card.model_dump_json())
    assert dumped["quality_level"] == "Q0_invalid"


def test_export_schemas(tmp_path):
    written = export_schemas(tmp_path)
    assert len(written) == len(EXPORTED_MODELS)
    for path in written:
        schema = json.loads(path.read_text())
        assert schema["type"] == "object"
        assert "properties" in schema
