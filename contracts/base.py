"""Base contracts for agent communication."""

from __future__ import annotations

from abc import ABC
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ContractSeverity(str, Enum):
    """How critical a contract violation is."""

    WARNING = "warning"
    ERROR = "error"
    FATAL = "fatal"


class AgentMetadata(BaseModel):
    """Metadata propagated across agent boundaries."""

    run_id: str
    agent_name: str
    state_version: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    trace_id: str | None = None
    parent_trace_id: str | None = None
    tags: dict[str, str] = Field(default_factory=dict)


class AgentInput(BaseModel, ABC):
    """Base class for all agent inputs."""

    metadata: AgentMetadata
    compliance_state_version: int


class AgentOutput(BaseModel, ABC):
    """Base class for all agent outputs."""

    metadata: AgentMetadata
    success: bool
    state_updates: dict[str, Any] = Field(default_factory=dict)
    reasoning_trace_id: str | None = None


class FailureContract(BaseModel):
    """Standardized failure reporting across all agents."""

    agent_name: str
    error_type: str
    error_message: str
    severity: ContractSeverity
    is_retryable: bool = False
    retry_after_seconds: int | None = None
    partial_output: dict[str, Any] | None = None
    suggestions: list[str] = Field(default_factory=list)


class RetryPolicy(BaseModel):
    """Per-agent retry configuration."""

    max_retries: int = 3
    base_delay_seconds: float = 1.0
    exponential_backoff: bool = True
    retryable_error_types: list[str] = Field(
        default_factory=lambda: ["llm_timeout", "rate_limit", "transient_error"]
    )
