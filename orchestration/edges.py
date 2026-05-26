"""Conditional edge logic for the LangGraph workflow."""

from __future__ import annotations

from .state import PipelineState


def should_continue(state: PipelineState) -> str:
    """Determine if the pipeline should continue to the next node."""
    if state.get("error"):
        return "error_handler"
    if not state.get("should_continue", True):
        return "end"
    return "continue"


def needs_hitl_approval(state: PipelineState) -> str:
    """Determine if HITL approval is needed before continuing."""
    if state.get("pending_approval"):
        return "hitl_gate"
    return "continue"


def should_retry(state: PipelineState) -> str:
    """Determine if the current node should be retried."""
    retry_count = state.get("retry_count", 0)
    if retry_count >= 3:
        return "fail"
    if state.get("error"):
        return "retry"
    return "continue"


def select_validation_path(state: PipelineState) -> str:
    """Route to deterministic or semantic validation based on constraint type."""
    # In full impl: inspect the constraint types in state
    # For V1: always deterministic
    return "deterministic"
