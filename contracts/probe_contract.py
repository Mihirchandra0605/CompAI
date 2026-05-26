"""Contract for the Probe Agent."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .base import AgentInput, AgentOutput


class ProbeDefinition(BaseModel):
    """A single probe definition derived from CCL."""

    probe_id: str
    derived_from: str  # CCL probe-strategy ID
    probe_type: str  # LOG_SCAN, CONFIG_SCAN, etc.
    config: dict[str, Any]
    expected_output_schema: dict[str, Any] | None = None


class ProbeResult(BaseModel):
    """Result of a single probe execution."""

    probe_id: str
    evidence_id: str
    status: str  # success, failed, timeout
    data: dict[str, Any] = Field(default_factory=dict)
    sample_count: int = 0
    collection_window: dict[str, str] | None = None
    error: str | None = None
    duration_ms: float | None = None


class ProbeInput(AgentInput):
    """What the ProbeAgent requires."""

    probe_definitions: list[ProbeDefinition]
    ccl_document: str | None = None


class ProbeOutput(AgentOutput):
    """What the ProbeAgent produces."""

    probe_results: list[ProbeResult] = Field(default_factory=list)
    total_evidence_items: int = 0
    failed_probes: list[str] = Field(default_factory=list)
