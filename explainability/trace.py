"""Reasoning trace primitives — the atoms of explainability."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TraceNodeType(str, Enum):
    LLM_CALL = "llm_call"
    TOOL_USE = "tool_use"
    EVIDENCE = "evidence"
    INFERENCE = "inference"
    HUMAN_EDIT = "human_edit"
    VALIDATION = "validation"
    DECISION = "decision"


class TraceNode(BaseModel):
    """A single node in a reasoning trace tree."""

    node_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: str | None = None
    node_type: TraceNodeType
    agent_name: str | None = None

    # What happened
    description: str
    input_summary: str | None = None
    output_summary: str | None = None

    # Timing
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    duration_ms: float | None = None

    # Confidence
    confidence: float | None = None
    confidence_factors: list[str] = Field(default_factory=list)

    # Evidence linkage
    evidence_ids: list[str] = Field(default_factory=list)

    # Raw data
    raw_input: dict[str, Any] | None = None
    raw_output: dict[str, Any] | None = None


class ReasoningTrace(BaseModel):
    """A complete reasoning trace for a compliance run."""

    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    run_id: str
    regulation_id: str
    nodes: list[TraceNode] = Field(default_factory=list)

    def get_tree(self) -> list[dict]:
        """Reconstruct the tree structure from flat node list."""
        children_map: dict[str | None, list[TraceNode]] = {None: []}
        for node in self.nodes:
            children_map.setdefault(node.parent_id, []).append(node)
        return self._build_tree(None, children_map)

    def _build_tree(
        self, parent_id: str | None, children_map: dict[str | None, list[TraceNode]]
    ) -> list[dict]:
        return [
            {
                "node": n.model_dump(),
                "children": self._build_tree(n.node_id, children_map),
            }
            for n in children_map.get(parent_id, [])
        ]
