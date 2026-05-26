"""Domain event primitives. Lightweight, serializable, future-proof."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EventPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class DomainEvent(BaseModel):
    """
    Base class for all domain events.

    Design invariants:
    - Events are IMMUTABLE after creation
    - Events are SERIALIZABLE (for future Kafka/Redis migration)
    - Events carry their own ROUTING metadata
    - Events include CAUSATION chain for traceability
    """

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    priority: EventPriority = EventPriority.NORMAL

    # Causation chain
    source: str
    run_id: str | None = None
    correlation_id: str | None = None
    causation_id: str | None = None

    # Payload
    payload: dict[str, Any] = Field(default_factory=dict)

    # Routing hints
    partition_key: str | None = None

    model_config = {"frozen": True}
