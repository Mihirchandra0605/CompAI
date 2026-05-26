"""LangGraph node definitions — wraps each agent's execution as a graph node."""

from __future__ import annotations

from typing import Any

from .state import PipelineState


async def intent_extraction_node(state: PipelineState) -> PipelineState:
    """Node: Extract compliance intents from regulation text.

    Wraps IntentAgent.run() and updates pipeline state.
    """
    state["current_node"] = "intent_extraction"
    # In full LangGraph implementation:
    # result = await intent_agent.run(input, trace)
    # state["compliance_state"]["intents"] = result.state_updates["intents"]
    # state["current_state_version"] += 1
    return state


async def ccl_generation_node(state: PipelineState) -> PipelineState:
    """Node: Generate CCL XML from extracted intents."""
    state["current_node"] = "ccl_generation"
    return state


async def knowledge_graph_node(state: PipelineState) -> PipelineState:
    """Node: Build compliance knowledge graph from CCL."""
    state["current_node"] = "knowledge_graph"
    return state


async def skill_generation_node(state: PipelineState) -> PipelineState:
    """Node: Derive probe definitions from CCL ProbeStrategies."""
    state["current_node"] = "skill_generation"
    return state


async def probe_execution_node(state: PipelineState) -> PipelineState:
    """Node: Execute probes and collect evidence."""
    state["current_node"] = "probe_execution"
    return state


async def validation_node(state: PipelineState) -> PipelineState:
    """Node: Validate evidence against conditions (deterministic)."""
    state["current_node"] = "validation"
    return state


async def xai_analysis_node(state: PipelineState) -> PipelineState:
    """Node: XAI analysis — aggregate verdicts and build reasoning chains."""
    state["current_node"] = "xai_analysis"
    return state


async def report_generation_node(state: PipelineState) -> PipelineState:
    """Node: Generate compliance report."""
    state["current_node"] = "report_generation"
    return state


async def hitl_gate_node(state: PipelineState) -> PipelineState:
    """Node: Pause for human-in-the-loop approval.

    Uses LangGraph interrupt() when HITL is enabled.
    """
    if state.get("pending_approval"):
        # In full impl: interrupt(approval_request)
        pass
    return state
