"""Base probe interface and evidence models."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ProbeStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class FailureType(str, Enum):
    TRANSIENT = "transient"
    PERMANENT = "permanent"
    DATA_DEFICIENCY = "data_deficiency"


class EvidenceArtifact(BaseModel):
    """Raw evidence collected by a probe."""

    artifact_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_type: str
    source_reference: str
    raw_data: Any = None
    collected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    size_bytes: int = 0


class EvidenceRecord(BaseModel):
    """A single normalized evidence record."""

    timestamp: datetime | None = None
    value: float | str | bool
    metric: str
    unit: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceBatch(BaseModel):
    """Normalized evidence ready for validation."""

    batch_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    probe_id: str
    records: list[EvidenceRecord] = Field(default_factory=list)
    sample_count: int = 0
    collection_window_start: datetime | None = None
    collection_window_end: datetime | None = None
    collected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    lineage: dict[str, Any] = Field(default_factory=dict)


class ProbeDefinitionModel(BaseModel):
    """Executable probe definition derived from CCL ProbeStrategy."""

    probe_id: str
    derived_from: str
    probe_type: str
    config: dict[str, Any]
    target: str | None = None
    expected_output_schema: dict[str, Any] | None = None
    timeout_seconds: float = 30.0


class ExecutionContext(BaseModel):
    """Runtime context for probe execution."""

    run_id: str
    timeout_seconds: float = 30.0
    max_retries: int = 3
    metadata: dict[str, str] = Field(default_factory=dict)


class BaseProbe(ABC):
    """Abstract base for all probes. Probes are deterministic execution primitives."""

    probe_type: str = "base"

    @abstractmethod
    async def execute(
        self, definition: ProbeDefinitionModel, context: ExecutionContext
    ) -> EvidenceBatch:
        """Execute the probe, collect evidence, and normalize to EvidenceBatch."""
        ...
