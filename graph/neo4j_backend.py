"""Neo4j graph backend stub — for future migration from NetworkX.

This is a placeholder that implements the AbstractGraphBackend interface
with NotImplementedError. When Neo4j is needed, replace the internals
with neo4j driver calls while keeping the interface identical.
"""

from __future__ import annotations

from typing import Any

from .base import AbstractGraphBackend, GraphEdge, GraphEdgeType, GraphNode, GraphNodeType


class Neo4jGraphBackend(AbstractGraphBackend):
    """
    Neo4j implementation stub.

    Migration path:
    1. Install neo4j driver: pip install neo4j
    2. Implement each method using Cypher queries
    3. Swap in config: graph_backend = Neo4jGraphBackend(uri, user, password)
    """

    def __init__(self, uri: str = "", user: str = "", password: str = "") -> None:
        self._uri = uri
        self._user = user
        self._password = password
        # TODO: self._driver = neo4j.GraphDatabase.driver(uri, auth=(user, password))

    def add_node(self, node: GraphNode) -> None:
        raise NotImplementedError("Neo4j backend not implemented. Use NetworkXGraphBackend for V1.")

    def add_edge(self, edge: GraphEdge) -> None:
        raise NotImplementedError("Neo4j backend not implemented. Use NetworkXGraphBackend for V1.")

    def get_node(self, node_id: str) -> GraphNode | None:
        raise NotImplementedError("Neo4j backend not implemented. Use NetworkXGraphBackend for V1.")

    def get_neighbors(self, node_id: str, edge_type: GraphEdgeType | None = None) -> list[GraphNode]:
        raise NotImplementedError("Neo4j backend not implemented. Use NetworkXGraphBackend for V1.")

    def query_by_type(self, node_type: GraphNodeType) -> list[GraphNode]:
        raise NotImplementedError("Neo4j backend not implemented. Use NetworkXGraphBackend for V1.")

    def get_subgraph(self, root_id: str, depth: int = 3) -> dict[str, Any]:
        raise NotImplementedError("Neo4j backend not implemented. Use NetworkXGraphBackend for V1.")

    def clear(self) -> None:
        raise NotImplementedError("Neo4j backend not implemented. Use NetworkXGraphBackend for V1.")

    def to_dict(self) -> dict[str, Any]:
        raise NotImplementedError("Neo4j backend not implemented. Use NetworkXGraphBackend for V1.")
