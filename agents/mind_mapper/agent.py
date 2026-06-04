"""Mind Mapper Agent — builds compliance knowledge graph from parsed CCL."""

from __future__ import annotations

import logging
from typing import Any

from agents.base import BaseComplianceAgent
from contracts.base import AgentInput, AgentMetadata, AgentOutput
from explainability.collector import TraceCollector
from explainability.trace import TraceNodeType
from graph.base import GraphEdge, GraphEdgeType, GraphNode, GraphNodeType
from graph.networkx_backend import NetworkXGraphBackend
from pydantic import Field

logger = logging.getLogger(__name__)


class MindMapperInput(AgentInput):
    """Input for the Mind Mapper agent."""

    ccl_document: str
    regulation_id: str


class MindMapperOutput(AgentOutput):
    """Output from the Mind Mapper agent."""

    graph_summary: dict[str, Any] = Field(default_factory=dict)
    node_count: int = 0
    edge_count: int = 0


class MindMapperAgent(BaseComplianceAgent[MindMapperInput, MindMapperOutput]):
    """Builds a compliance knowledge graph from CCL documents."""

    name = "mind_mapper"

    def __init__(
        self,
        graph_backend: NetworkXGraphBackend | None = None,
        slm_service=None,
    ):
        super().__init__(slm_service=slm_service)
        self._graph = graph_backend or NetworkXGraphBackend()

    async def execute(
        self, input: MindMapperInput, trace: TraceCollector
    ) -> MindMapperOutput:
        """Build knowledge graph from CCL."""
        from ccl.parser import CCLParser

        async with trace.span(
            "parse_ccl_for_graph", TraceNodeType.TOOL_USE, agent_name=self.name
        ) as span:
            parser = CCLParser()
            try:
                doc = parser.parse(input.ccl_document)
            except ValueError as e:
                span.set_output(f"Parse error: {e}")
                return MindMapperOutput(
                    metadata=input.metadata,
                    success=False,
                    state_updates={},
                )
            span.set_output(f"Parsed CCL: {doc.regulation.regulation_id if doc.regulation else 'none'}")

        async with trace.span(
            "build_compliance_graph", TraceNodeType.INFERENCE, agent_name=self.name
        ) as span:
            self._graph.clear()

            if doc.regulation:
                self._build_graph_from_regulation(doc)

            graph_dict = self._graph.to_dict()
            span.set_output(
                f"Graph: {self._graph.node_count} nodes, {self._graph.edge_count} edges"
            )
            span.set_confidence(0.95, ["deterministic_graph_construction"])

        return MindMapperOutput(
            metadata=input.metadata,
            success=True,
            graph_summary=graph_dict,
            node_count=self._graph.node_count,
            edge_count=self._graph.edge_count,
            state_updates={"compliance_graph": graph_dict},
        )

    def _build_graph_from_regulation(self, doc) -> None:
        """Build graph nodes and edges from parsed CCL."""
        reg = doc.regulation

        # Regulation node
        self._graph.add_node(GraphNode(
            node_id=reg.regulation_id,
            node_type=GraphNodeType.REGULATION,
            label=reg.title,
            properties={"authority": reg.authority, "jurisdiction": reg.jurisdiction},
        ))

        # Target systems
        for ts in doc.target_systems:
            self._graph.add_node(GraphNode(
                node_id=ts.system_id,
                node_type=GraphNodeType.TARGET_SYSTEM,
                label=ts.location or ts.system_id,
                properties={"type": ts.system_type, "access": ts.access_method},
            ))

        # Clauses
        for clause in reg.clauses:
            self._graph.add_node(GraphNode(
                node_id=clause.clause_id,
                node_type=GraphNodeType.CLAUSE,
                label=clause.section_ref,
                properties={"obligation": clause.obligation},
            ))
            self._graph.add_edge(GraphEdge(
                source_id=reg.regulation_id,
                target_id=clause.clause_id,
                edge_type=GraphEdgeType.CONTAINS,
            ))

            # Intents
            for intent in clause.intents:
                self._graph.add_node(GraphNode(
                    node_id=intent.intent_id,
                    node_type=GraphNodeType.INTENT,
                    label=intent.description[:50],
                    properties={"category": intent.category},
                ))
                self._graph.add_edge(GraphEdge(
                    source_id=clause.clause_id,
                    target_id=intent.intent_id,
                    edge_type=GraphEdgeType.CONTAINS,
                ))

                # Objectives and Constraints
                for obj in intent.objectives:
                    self._graph.add_node(GraphNode(
                        node_id=obj.objective_id,
                        node_type=GraphNodeType.OBJECTIVE,
                        label=obj.description[:50],
                        properties={"logic": obj.logic},
                    ))
                    self._graph.add_edge(GraphEdge(
                        source_id=intent.intent_id,
                        target_id=obj.objective_id,
                        edge_type=GraphEdgeType.CONTAINS,
                    ))

                    for con in obj.constraints:
                        self._graph.add_node(GraphNode(
                            node_id=con.constraint_id,
                            node_type=GraphNodeType.CONSTRAINT,
                            label=con.description[:50],
                            properties={"type": con.constraint_type},
                        ))
                        self._graph.add_edge(GraphEdge(
                            source_id=obj.objective_id,
                            target_id=con.constraint_id,
                            edge_type=GraphEdgeType.REQUIRES,
                        ))

                        # Link constraint to target systems via probe strategies
                        if con.evidence_requirement:
                            for ps in con.evidence_requirement.probe_strategies:
                                if ps.target_system_ref:
                                    self._graph.add_edge(GraphEdge(
                                        source_id=con.constraint_id,
                                        target_id=ps.target_system_ref,
                                        edge_type=GraphEdgeType.MEASURES,
                                        properties={"probe_type": ps.probe_type},
                                    ))
