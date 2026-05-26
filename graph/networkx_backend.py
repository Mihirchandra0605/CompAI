"""NetworkX implementation of the compliance knowledge graph."""

from __future__ import annotations

from typing import Any

import networkx as nx

from .base import (
    AbstractGraphBackend,
    GraphEdge,
    GraphEdgeType,
    GraphNode,
    GraphNodeType,
)


class NetworkXGraphBackend(AbstractGraphBackend):
    """NetworkX-based compliance knowledge graph."""

    def __init__(self) -> None:
        self._graph = nx.DiGraph()

    def add_node(self, node: GraphNode) -> None:
        self._graph.add_node(
            node.node_id,
            node_type=node.node_type.value,
            label=node.label,
            **node.properties,
        )

    def add_edge(self, edge: GraphEdge) -> None:
        self._graph.add_edge(
            edge.source_id,
            edge.target_id,
            edge_type=edge.edge_type.value,
            **edge.properties,
        )

    def get_node(self, node_id: str) -> GraphNode | None:
        if node_id not in self._graph.nodes:
            return None
        data = self._graph.nodes[node_id]
        return GraphNode(
            node_id=node_id,
            node_type=GraphNodeType(data.get("node_type", "regulation")),
            label=data.get("label", ""),
            properties={k: v for k, v in data.items() if k not in ("node_type", "label")},
        )

    def get_neighbors(
        self, node_id: str, edge_type: GraphEdgeType | None = None
    ) -> list[GraphNode]:
        if node_id not in self._graph.nodes:
            return []

        neighbors = []
        for _, target, data in self._graph.edges(node_id, data=True):
            if edge_type and data.get("edge_type") != edge_type.value:
                continue
            node = self.get_node(target)
            if node:
                neighbors.append(node)
        return neighbors

    def query_by_type(self, node_type: GraphNodeType) -> list[GraphNode]:
        nodes = []
        for node_id, data in self._graph.nodes(data=True):
            if data.get("node_type") == node_type.value:
                nodes.append(GraphNode(
                    node_id=node_id,
                    node_type=node_type,
                    label=data.get("label", ""),
                    properties={k: v for k, v in data.items() if k not in ("node_type", "label")},
                ))
        return nodes

    def get_subgraph(self, root_id: str, depth: int = 3) -> dict[str, Any]:
        """Get a subgraph using BFS from root."""
        if root_id not in self._graph.nodes:
            return {"nodes": [], "edges": []}

        visited = set()
        queue = [(root_id, 0)]
        nodes = []
        edges = []

        while queue:
            current, current_depth = queue.pop(0)
            if current in visited or current_depth > depth:
                continue
            visited.add(current)

            node = self.get_node(current)
            if node:
                nodes.append(node.model_dump())

            if current_depth < depth:
                for _, target, data in self._graph.edges(current, data=True):
                    edges.append({
                        "source": current,
                        "target": target,
                        "type": data.get("edge_type", ""),
                    })
                    queue.append((target, current_depth + 1))

        return {"nodes": nodes, "edges": edges}

    def clear(self) -> None:
        self._graph.clear()

    def to_dict(self) -> dict[str, Any]:
        """Serialize the graph."""
        return {
            "nodes": [
                {"id": n, **d} for n, d in self._graph.nodes(data=True)
            ],
            "edges": [
                {"source": u, "target": v, **d}
                for u, v, d in self._graph.edges(data=True)
            ],
            "node_count": self._graph.number_of_nodes(),
            "edge_count": self._graph.number_of_edges(),
        }

    @property
    def node_count(self) -> int:
        return self._graph.number_of_nodes()

    @property
    def edge_count(self) -> int:
        return self._graph.number_of_edges()
