"""Abstract graph interface — backend-agnostic compliance knowledge graph."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class GraphNodeType(str, Enum):
    REGULATION = "regulation"
    CLAUSE = "clause"
    INTENT = "intent"
    OBJECTIVE = "objective"
    CONSTRAINT = "constraint"
    MEASURE = "measure"
    THRESHOLD = "threshold"
    EVIDENCE = "evidence"
    PROBE = "probe"
    TARGET_SYSTEM = "target_system"
    VERDICT = "verdict"


class GraphEdgeType(str, Enum):
    CONTAINS = "contains"
    REQUIRES = "requires"
    MEASURES = "measures"
    SATISFIES = "satisfies"
    PRODUCES = "produces"
    EVALUATES = "evaluates"
    DERIVES_FROM = "derives_from"
    REFERENCES = "references"


class GraphNode(BaseModel):
    """A node in the compliance knowledge graph."""

    node_id: str
    node_type: GraphNodeType
    label: str
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    """An edge in the compliance knowledge graph."""

    source_id: str
    target_id: str
    edge_type: GraphEdgeType
    properties: dict[str, Any] = Field(default_factory=dict)


class AbstractGraphBackend(ABC):
    """Abstract graph backend interface."""

    @abstractmethod
    def add_node(self, node: GraphNode) -> None:
        ...

    @abstractmethod
    def add_edge(self, edge: GraphEdge) -> None:
        ...

    @abstractmethod
    def get_node(self, node_id: str) -> GraphNode | None:
        ...

    @abstractmethod
    def get_neighbors(self, node_id: str, edge_type: GraphEdgeType | None = None) -> list[GraphNode]:
        ...

    @abstractmethod
    def query_by_type(self, node_type: GraphNodeType) -> list[GraphNode]:
        ...

    @abstractmethod
    def get_subgraph(self, root_id: str, depth: int = 3) -> dict[str, Any]:
        """Get a subgraph rooted at a node."""
        ...

    @abstractmethod
    def clear(self) -> None:
        ...

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        """Serialize the graph to a dictionary."""
        ...
