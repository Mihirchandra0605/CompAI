"""Context-manager based trace collection — agents emit traces naturally."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncGenerator

from .trace import ReasoningTrace, TraceNode, TraceNodeType


class _SpanHandle:
    """Mutable handle for setting span data within a context manager."""

    def __init__(self, node: TraceNode):
        self._node = node

    def set_output(self, output: str) -> None:
        self._node.output_summary = output[:500]

    def set_input(self, input_summary: str) -> None:
        self._node.input_summary = input_summary[:500]

    def set_confidence(self, score: float, factors: list[str] | None = None) -> None:
        self._node.confidence = score
        self._node.confidence_factors = factors or []

    def link_evidence(self, evidence_id: str) -> None:
        self._node.evidence_ids.append(evidence_id)


class TraceCollector:
    """
    Injected into every agent. Agents emit trace nodes as they reason.

    Usage:
        async with trace.span("extracting_intents", TraceNodeType.LLM_CALL) as span:
            result = await llm.ainvoke(prompt)
            span.set_output(str(result))
            span.set_confidence(0.85, ["high_quality_regulation"])
    """

    def __init__(self, run_id: str, regulation_id: str):
        self._trace = ReasoningTrace(run_id=run_id, regulation_id=regulation_id)
        self._stack: list[str] = []

    @asynccontextmanager
    async def span(
        self,
        description: str,
        node_type: TraceNodeType = TraceNodeType.INFERENCE,
        agent_name: str | None = None,
    ) -> AsyncGenerator[_SpanHandle, None]:
        """Create a traced span. Supports nesting."""
        node = TraceNode(
            parent_id=self._stack[-1] if self._stack else None,
            node_type=node_type,
            agent_name=agent_name,
            description=description,
        )
        self._stack.append(node.node_id)
        self._trace.nodes.append(node)

        handle = _SpanHandle(node)
        try:
            yield handle
        finally:
            node.completed_at = datetime.now(timezone.utc)
            node.duration_ms = (
                node.completed_at - node.started_at
            ).total_seconds() * 1000
            self._stack.pop()

    def get_trace(self) -> ReasoningTrace:
        return self._trace
