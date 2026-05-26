"""Execution lineage — tracks HOW a compliance state was produced."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class ExecutionStatus(str, Enum):
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentExecution(BaseModel):
    """Record of a single agent's execution within a pipeline run."""

    agent_name: str
    started_at: datetime
    completed_at: datetime | None = None
    status: ExecutionStatus = ExecutionStatus.RUNNING
    input_state_version: int
    output_state_version: int | None = None
    error: str | None = None
    retry_count: int = 0
    duration_ms: float | None = None
    trace_id: str | None = None
    tool_calls: list[str] = Field(default_factory=list)


class Checkpoint(BaseModel):
    """A named point in the pipeline that can be resumed from."""

    checkpoint_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    state_version: int
    node_name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, str] = Field(default_factory=dict)


class ExecutionContext(BaseModel):
    """Full execution lineage for a compliance pipeline run."""

    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    regulation_id: str
    status: ExecutionStatus = ExecutionStatus.RUNNING
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None

    # Lineage
    agent_executions: list[AgentExecution] = Field(default_factory=list)
    checkpoints: list[Checkpoint] = Field(default_factory=list)
    state_versions: list[int] = Field(default_factory=list)

    # Error handling
    errors: list[dict] = Field(default_factory=list)
    retry_budget: int = 3
    retries_used: int = 0

    # HITL
    pending_approval: str | None = None
    approval_history: list[dict] = Field(default_factory=list)
