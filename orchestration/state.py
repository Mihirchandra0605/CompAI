"""Pipeline state — thin LangGraph wrapper delegating to domain objects."""

from __future__ import annotations

from typing import Any, TypedDict


class PipelineState(TypedDict):
    """LangGraph transient state — delegates to domain objects."""

    run_id: str
    regulation_id: str
    regulation_text: str
    current_state_version: int
    compliance_state: dict[str, Any]
    execution_context: dict[str, Any]
    current_node: str
    pending_approval: str | None
    retry_count: int
    should_continue: bool
    error: str | None
