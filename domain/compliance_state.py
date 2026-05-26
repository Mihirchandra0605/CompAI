"""Canonical compliance state — the single source of truth for a compliance run."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class StateVersion(BaseModel):
    """Immutable version marker for compliance state snapshots."""

    version: int = 1
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by_agent: str | None = None
    parent_version: int | None = None
    checksum: str | None = None


class ComplianceVerdict(str, Enum):
    PENDING = "pending"
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class ComplianceState(BaseModel):
    """
    The canonical domain object. Every agent reads from and writes to this.

    Design invariants:
    - This object is NEVER mutated in place during a pipeline run.
    - Each agent produces a NEW ComplianceState with an incremented version.
    - The previous state is retained as a checkpoint.
    - All fields are Optional because state is progressively enriched.
    """

    # Identity
    state_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    regulation_id: str
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # Versioning
    version: StateVersion = Field(default_factory=StateVersion)

    # Progressive enrichment — each agent populates its section
    regulation_text: str | None = None
    intents: list[dict[str, Any]] | None = None
    ccl_document: str | None = None
    compliance_graph: dict[str, Any] | None = None
    probe_definitions: list[dict[str, Any]] | None = None
    evidence_collection: list[dict[str, Any]] | None = None
    validation_results: list[dict[str, Any]] | None = None
    xai_analysis: dict[str, Any] | None = None
    report: str | None = None

    # Verdict
    verdict: ComplianceVerdict = ComplianceVerdict.PENDING
    confidence: float | None = None

    # Metadata
    tags: dict[str, str] = Field(default_factory=dict)

    def evolve(self, agent_name: str, **updates) -> ComplianceState:
        """Create a new state version with the given updates.

        This is the ONLY way to modify compliance state.
        Returns a new immutable snapshot.
        """
        new_version = StateVersion(
            version=self.version.version + 1,
            created_by_agent=agent_name,
            parent_version=self.version.version,
        )
        data = self.model_dump()
        data.update(updates)
        data["version"] = new_version
        return ComplianceState(**data)
