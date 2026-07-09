"""Shared base model for all se_support data contracts.

All data models inherit from :class:`SEModel`, which pins Pydantic behaviour
that matters for reproducible experiment records:

* ``extra="forbid"`` -- unknown fields raise, so a typo in a fixture or a
  drifted producer is caught immediately rather than silently dropped.
* ``validate_assignment=True`` -- mutating a field re-validates it.

Every model also exposes :meth:`json_schema` so the CLI can export a stable
``schemas/*.schema.json`` file per model (single source of truth: the model).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class SEModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        use_enum_values=True,
    )

    @classmethod
    def json_schema(cls) -> dict[str, Any]:
        """Return the JSON schema for this model."""
        return cls.model_json_schema()
