"""RunSpec: the parameters that define one experimental run.

A run is the atomic unit of the ablation: one (task, agent, model, condition,
seed) combination. Pinning ``model`` to an exact snapshot string and recording
``condition`` is what makes the causal comparison clean -- everything except the
support condition is held fixed and logged here.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import Field

from se_support.config import CONDITION_VERSION, PROTOCOL_VERSION, SUPPORT_CONDITIONS
from se_support.schemas.base import SEModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RunSpec(SEModel):
    run_id: str = Field(..., description="Unique run id (uuid).")
    task_id: str = Field(..., description="TaskSpec.task_id this run targets.")
    agent: str = Field(..., description="Agent scaffold name, e.g. mini_swe_agent.")
    model: str = Field(..., description="Pinned model/snapshot identifier.")
    condition: str = Field(..., description=f"One of {', '.join(SUPPORT_CONDITIONS)}.")
    seed: int = 0
    max_turns: int = 50
    max_wall_time_sec: int = 3600
    max_cost_usd: float | None = None
    # Protocol/construct versioning (EP-00). Defaults keep older records readable.
    protocol_version: str = Field(
        default=PROTOCOL_VERSION, description="Execution-protocol version this run followed."
    )
    condition_version: str = Field(
        default=CONDITION_VERSION, description="Version of the C0-C6 support definitions used."
    )
    experiment_id: str | None = Field(None, description="Owning experiment id (runs/<id>/).")
    created_at: datetime = Field(default_factory=_utcnow)
