"""Compliance Pipeline — end-to-end orchestration without LangGraph dependency.

This module implements the core compliance pipeline as a linear async workflow.
It follows the same architectural pattern as a LangGraph StateGraph but uses
plain async Python for V1 simplicity. Migration to LangGraph is straightforward
since all node functions are independent async callables.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from agents.ccl_generator.agent import CCLGeneratorAgent
from agents.document_builder.agent import DocumentBuilderAgent, DocumentInput
from agents.intent.agent import IntentAgent
from agents.mind_mapper.agent import MindMapperAgent, MindMapperInput
from agents.probe.agent import ProbeAgent
from agents.skill_generator.agent import SkillGeneratorAgent, SkillGeneratorInput
from agents.xai_analyzer.agent import XAIAnalyzerAgent, XAIInput
from contracts.base import AgentMetadata, FailureContract
from contracts.ccl_contract import CCLInput
from contracts.intent_contract import ExtractedIntent, IntentInput
from contracts.probe_contract import ProbeDefinition, ProbeInput
from domain.compliance_state import ComplianceState, ComplianceVerdict
from domain.execution_context import AgentExecution, ExecutionContext, ExecutionStatus
from events.bus import AsyncEventBus
from events.domain_events import (
    CCLGenerated,
    IntentsExtracted,
    PipelineCompleted,
    PipelineFailed,
    PipelineStarted,
    ProbesCompleted,
    ValidationCompleted,
    VerdictDetermined,
)
from explainability.collector import TraceCollector
from probes.dispatcher import ProbeDispatcher
from probes.validation.engine import ValidationCondition, ValidationEngine

logger = logging.getLogger(__name__)


class PipelineResult:
    """Result of a compliance pipeline run."""

    def __init__(
        self,
        state: ComplianceState,
        execution_context: ExecutionContext,
        trace: TraceCollector,
        success: bool = True,
        error: str | None = None,
    ):
        self.state = state
        self.execution_context = execution_context
        self.trace = trace
        self.success = success
        self.error = error


class CompliancePipeline:
    """
    End-to-end compliance validation pipeline.

    Orchestrates: Intent → CCL → Probe → Validate → XAI → Report
    """

    def __init__(
        self,
        intent_agent: IntentAgent,
        ccl_agent: CCLGeneratorAgent,
        mind_mapper_agent: MindMapperAgent,
        skill_generator_agent: SkillGeneratorAgent,
        probe_agent: ProbeAgent,
        xai_agent: XAIAnalyzerAgent,
        doc_agent: DocumentBuilderAgent,
        validation_engine: ValidationEngine,
        event_bus: AsyncEventBus | None = None,
    ):
        self._intent_agent = intent_agent
        self._ccl_agent = ccl_agent
        self._mind_mapper_agent = mind_mapper_agent
        self._skill_generator_agent = skill_generator_agent
        self._probe_agent = probe_agent
        self._xai_agent = xai_agent
        self._doc_agent = doc_agent
        self._validation_engine = validation_engine
        self._event_bus = event_bus

    async def run(
        self,
        regulation_id: str,
        regulation_text: str,
        probe_definitions: list[dict[str, Any]] | None = None,
        validation_conditions: list[dict[str, Any]] | None = None,
    ) -> PipelineResult:
        """Execute the full compliance pipeline."""
        run_id = str(uuid.uuid4())
        trace = TraceCollector(run_id=run_id, regulation_id=regulation_id)

        # Initialize state
        state = ComplianceState(
            regulation_id=regulation_id,
            run_id=run_id,
            regulation_text=regulation_text,
        )
        exec_ctx = ExecutionContext(
            run_id=run_id,
            regulation_id=regulation_id,
        )

        await self._emit_event(PipelineStarted(
            source="pipeline",
            run_id=run_id,
            payload={"regulation_id": regulation_id},
        ))

        try:
            # Stage 1: Intent Extraction
            state, exec_ctx = await self._run_intent_stage(
                state, exec_ctx, trace, regulation_text
            )

            # Stage 2: CCL Generation
            state, exec_ctx = await self._run_ccl_stage(
                state, exec_ctx, trace, regulation_text
            )

            # Stage 3: Build Knowledge Graph
            state, exec_ctx = await self._run_mind_mapper_stage(
                state, exec_ctx, trace
            )

            # Stage 4: Generate Probe Skills
            state, exec_ctx = await self._run_skill_generation_stage(
                state, exec_ctx, trace
            )

            # Stage 5: Probe Execution
            state, exec_ctx = await self._run_probe_stage(
                state, exec_ctx, trace, probe_definitions
            )

            # Stage 6: Validation
            state, exec_ctx = await self._run_validation_stage(
                state, exec_ctx, trace, validation_conditions
            )

            # Stage 7: XAI Analysis
            state, exec_ctx = await self._run_xai_stage(
                state, exec_ctx, trace, regulation_text
            )

            # Stage 8: Report Generation
            state, exec_ctx = await self._run_report_stage(
                state, exec_ctx, trace, regulation_text
            )

            # Mark completed
            exec_ctx.status = ExecutionStatus.COMPLETED
            exec_ctx.completed_at = datetime.now(timezone.utc)

            await self._emit_event(PipelineCompleted(
                source="pipeline",
                run_id=run_id,
                payload={"verdict": state.verdict.value},
            ))

            return PipelineResult(state=state, execution_context=exec_ctx, trace=trace)

        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            exec_ctx.status = ExecutionStatus.FAILED
            exec_ctx.errors.append({"error": str(e), "stage": "pipeline"})

            await self._emit_event(PipelineFailed(
                source="pipeline",
                run_id=run_id,
                payload={"error": str(e)},
            ))

            return PipelineResult(
                state=state,
                execution_context=exec_ctx,
                trace=trace,
                success=False,
                error=str(e),
            )

    async def _run_intent_stage(
        self,
        state: ComplianceState,
        exec_ctx: ExecutionContext,
        trace: TraceCollector,
        regulation_text: str,
    ) -> tuple[ComplianceState, ExecutionContext]:
        """Stage 1: Extract intents from regulation text."""
        logger.info("Stage 1: Intent Extraction")
        start = datetime.now(timezone.utc)

        metadata = AgentMetadata(
            run_id=state.run_id,
            agent_name="intent_agent",
            state_version=state.version.version,
        )

        intent_input = IntentInput(
            metadata=metadata,
            compliance_state_version=state.version.version,
            regulation_text=regulation_text,
        )

        result = await self._intent_agent.run(intent_input, trace)

        if isinstance(result, FailureContract):
            raise RuntimeError(f"Intent extraction failed: {result.error_message}")

        state = state.evolve(
            "intent_agent",
            intents=[i.model_dump() for i in result.intents],
        )

        exec_ctx.agent_executions.append(AgentExecution(
            agent_name="intent_agent",
            started_at=start,
            completed_at=datetime.now(timezone.utc),
            status=ExecutionStatus.COMPLETED,
            input_state_version=state.version.parent_version or 1,
            output_state_version=state.version.version,
        ))

        await self._emit_event(IntentsExtracted(
            source="intent_agent",
            run_id=state.run_id,
            payload={"intent_count": len(result.intents)},
        ))

        return state, exec_ctx

    async def _run_ccl_stage(
        self,
        state: ComplianceState,
        exec_ctx: ExecutionContext,
        trace: TraceCollector,
        regulation_text: str,
    ) -> tuple[ComplianceState, ExecutionContext]:
        """Stage 2: Generate CCL from intents."""
        logger.info("Stage 2: CCL Generation")
        start = datetime.now(timezone.utc)

        metadata = AgentMetadata(
            run_id=state.run_id,
            agent_name="ccl_generator",
            state_version=state.version.version,
        )

        intents = [ExtractedIntent(**i) for i in (state.intents or [])]
        ccl_input = CCLInput(
            metadata=metadata,
            compliance_state_version=state.version.version,
            regulation_text=regulation_text,
            intents=intents,
            regulation_id=state.regulation_id,
        )

        result = await self._ccl_agent.run(ccl_input, trace)

        if isinstance(result, FailureContract):
            raise RuntimeError(f"CCL generation failed: {result.error_message}")

        state = state.evolve("ccl_generator", ccl_document=result.ccl_xml)

        exec_ctx.agent_executions.append(AgentExecution(
            agent_name="ccl_generator",
            started_at=start,
            completed_at=datetime.now(timezone.utc),
            status=ExecutionStatus.COMPLETED,
            input_state_version=state.version.parent_version or 1,
            output_state_version=state.version.version,
        ))

        await self._emit_event(CCLGenerated(
            source="ccl_generator",
            run_id=state.run_id,
            payload={"clauses": result.clause_count, "constraints": result.constraint_count},
        ))

        return state, exec_ctx

    async def _run_mind_mapper_stage(
        self,
        state: ComplianceState,
        exec_ctx: ExecutionContext,
        trace: TraceCollector,
    ) -> tuple[ComplianceState, ExecutionContext]:
        """Stage 3: Build compliance knowledge graph from CCL."""
        logger.info("Stage 3: Mind Mapping")
        start = datetime.now(timezone.utc)

        metadata = AgentMetadata(
            run_id=state.run_id,
            agent_name="mind_mapper",
            state_version=state.version.version,
        )

        mapper_input = MindMapperInput(
            metadata=metadata,
            compliance_state_version=state.version.version,
            ccl_document=state.ccl_document or "",
            regulation_id=state.regulation_id,
        )

        result = await self._mind_mapper_agent.run(mapper_input, trace)

        if isinstance(result, FailureContract):
            raise RuntimeError(f"Mind mapping failed: {result.error_message}")

        state = state.evolve("mind_mapper", compliance_graph=result.graph_summary)

        exec_ctx.agent_executions.append(AgentExecution(
            agent_name="mind_mapper",
            started_at=start,
            completed_at=datetime.now(timezone.utc),
            status=ExecutionStatus.COMPLETED,
            input_state_version=state.version.parent_version or 1,
            output_state_version=state.version.version,
        ))

        return state, exec_ctx

    async def _run_skill_generation_stage(
        self,
        state: ComplianceState,
        exec_ctx: ExecutionContext,
        trace: TraceCollector,
    ) -> tuple[ComplianceState, ExecutionContext]:
        """Stage 4: Derive probes and validation conditions from CCL."""
        logger.info("Stage 4: Skill Generation")
        start = datetime.now(timezone.utc)

        metadata = AgentMetadata(
            run_id=state.run_id,
            agent_name="skill_generator",
            state_version=state.version.version,
        )

        skill_input = SkillGeneratorInput(
            metadata=metadata,
            compliance_state_version=state.version.version,
            ccl_document=state.ccl_document or "",
            regulation_id=state.regulation_id,
        )

        result = await self._skill_generator_agent.run(skill_input, trace)

        if isinstance(result, FailureContract):
            raise RuntimeError(f"Skill generation failed: {result.error_message}")

        state = state.evolve(
            "skill_generator",
            probe_definitions=[pd.model_dump() for pd in result.probe_definitions],
            validation_conditions=result.validation_conditions,
        )

        exec_ctx.agent_executions.append(AgentExecution(
            agent_name="skill_generator",
            started_at=start,
            completed_at=datetime.now(timezone.utc),
            status=ExecutionStatus.COMPLETED,
            input_state_version=state.version.parent_version or 1,
            output_state_version=state.version.version,
        ))

        return state, exec_ctx

    async def _run_probe_stage(
        self,
        state: ComplianceState,
        exec_ctx: ExecutionContext,
        trace: TraceCollector,
        probe_definitions: list[dict[str, Any]] | None,
    ) -> tuple[ComplianceState, ExecutionContext]:
        """Stage 3: Execute probes and collect evidence."""
        logger.info("Stage 3: Probe Execution")
        start = datetime.now(timezone.utc)

        metadata = AgentMetadata(
            run_id=state.run_id,
            agent_name="probe_agent",
            state_version=state.version.version,
        )

        # Use provided probe definitions or derive from CCL
        if probe_definitions:
            definitions = [ProbeDefinition(**pd) for pd in probe_definitions]
        else:
            definitions = self._derive_default_probes(state)

        probe_input = ProbeInput(
            metadata=metadata,
            compliance_state_version=state.version.version,
            probe_definitions=definitions,
            ccl_document=state.ccl_document,
        )

        result = await self._probe_agent.run(probe_input, trace)

        if isinstance(result, FailureContract):
            raise RuntimeError(f"Probe execution failed: {result.error_message}")

        state = state.evolve(
            "probe_agent",
            evidence_collection=[r.model_dump() for r in result.probe_results],
            probe_definitions=[d.model_dump() for d in definitions],
        )

        exec_ctx.agent_executions.append(AgentExecution(
            agent_name="probe_agent",
            started_at=start,
            completed_at=datetime.now(timezone.utc),
            status=ExecutionStatus.COMPLETED,
            input_state_version=state.version.parent_version or 1,
            output_state_version=state.version.version,
        ))

        await self._emit_event(ProbesCompleted(
            source="probe_agent",
            run_id=state.run_id,
            payload={"total_evidence": result.total_evidence_items},
        ))

        return state, exec_ctx

    async def _run_validation_stage(
        self,
        state: ComplianceState,
        exec_ctx: ExecutionContext,
        trace: TraceCollector,
        validation_conditions: list[dict[str, Any]] | None,
    ) -> tuple[ComplianceState, ExecutionContext]:
        """Stage 4: Validate evidence against conditions."""
        logger.info("Stage 4: Validation")
        start = datetime.now(timezone.utc)

        # Use provided conditions or derive defaults
        if validation_conditions:
            conditions = [ValidationCondition(**vc) for vc in validation_conditions]
        else:
            conditions = self._derive_default_conditions(state)

        # For V1, build synthetic evidence batches from probe results
        from probes.base import EvidenceBatch, EvidenceRecord

        validation_results = []
        evidence_collection = state.evidence_collection or []

        for condition in conditions:
            # Find matching evidence
            matching_evidence = self._find_matching_evidence(
                condition, evidence_collection
            )
            if matching_evidence:
                result = await self._validation_engine.evaluate(
                    matching_evidence, condition
                )
                validation_results.append(result.model_dump())
            else:
                # No matching evidence
                validation_results.append({
                    "condition_id": condition.condition_id,
                    "constraint_id": condition.constraint_id,
                    "verdict": "insufficient_evidence",
                    "measured_value": None,
                    "threshold_value": condition.threshold_value,
                    "operator": condition.operator,
                    "sample_count": 0,
                    "confidence": 0.0,
                    "reasoning": "No matching evidence found",
                })

        state = state.evolve("validation_engine", validation_results=validation_results)

        exec_ctx.agent_executions.append(AgentExecution(
            agent_name="validation_engine",
            started_at=start,
            completed_at=datetime.now(timezone.utc),
            status=ExecutionStatus.COMPLETED,
            input_state_version=state.version.parent_version or 1,
            output_state_version=state.version.version,
        ))

        await self._emit_event(ValidationCompleted(
            source="validation_engine",
            run_id=state.run_id,
            payload={"results_count": len(validation_results)},
        ))

        return state, exec_ctx

    async def _run_xai_stage(
        self,
        state: ComplianceState,
        exec_ctx: ExecutionContext,
        trace: TraceCollector,
        regulation_text: str,
    ) -> tuple[ComplianceState, ExecutionContext]:
        """Stage 5: XAI Analysis."""
        logger.info("Stage 5: XAI Analysis")
        start = datetime.now(timezone.utc)

        metadata = AgentMetadata(
            run_id=state.run_id,
            agent_name="xai_analyzer",
            state_version=state.version.version,
        )

        xai_input = XAIInput(
            metadata=metadata,
            compliance_state_version=state.version.version,
            validation_results=state.validation_results or [],
            intents=state.intents or [],
            evidence_collection=state.evidence_collection or [],
            regulation_text=regulation_text,
        )

        result = await self._xai_agent.run(xai_input, trace)

        if isinstance(result, FailureContract):
            raise RuntimeError(f"XAI analysis failed: {result.error_message}")

        # Map verdict string to enum
        verdict_map = {
            "compliant": ComplianceVerdict.COMPLIANT,
            "non_compliant": ComplianceVerdict.NON_COMPLIANT,
            "partially_compliant": ComplianceVerdict.PARTIALLY_COMPLIANT,
            "insufficient_evidence": ComplianceVerdict.INSUFFICIENT_EVIDENCE,
        }
        verdict = verdict_map.get(
            result.regulation_verdict.lower(), ComplianceVerdict.PENDING
        )

        state = state.evolve(
            "xai_analyzer",
            xai_analysis={
                "regulation_verdict": result.regulation_verdict,
                "confidence": result.confidence,
                "partial_compliance_score": result.partial_compliance_score,
                "clause_verdicts": result.clause_verdicts,
                "reasoning_chain": result.reasoning_chain,
                "recommendations": result.recommendations,
                "confidence_breakdown": result.confidence_breakdown,
            },
            verdict=verdict,
            confidence=result.confidence,
        )

        exec_ctx.agent_executions.append(AgentExecution(
            agent_name="xai_analyzer",
            started_at=start,
            completed_at=datetime.now(timezone.utc),
            status=ExecutionStatus.COMPLETED,
            input_state_version=state.version.parent_version or 1,
            output_state_version=state.version.version,
        ))

        await self._emit_event(VerdictDetermined(
            source="xai_analyzer",
            run_id=state.run_id,
            payload={"verdict": result.regulation_verdict, "confidence": result.confidence},
        ))

        return state, exec_ctx

    async def _run_report_stage(
        self,
        state: ComplianceState,
        exec_ctx: ExecutionContext,
        trace: TraceCollector,
        regulation_text: str,
    ) -> tuple[ComplianceState, ExecutionContext]:
        """Stage 6: Report Generation."""
        logger.info("Stage 6: Report Generation")
        start = datetime.now(timezone.utc)

        metadata = AgentMetadata(
            run_id=state.run_id,
            agent_name="document_builder",
            state_version=state.version.version,
        )

        doc_input = DocumentInput(
            metadata=metadata,
            compliance_state_version=state.version.version,
            regulation_id=state.regulation_id,
            regulation_text=regulation_text,
            xai_analysis=state.xai_analysis or {},
            validation_results=state.validation_results or [],
            intents=state.intents or [],
            evidence_collection=state.evidence_collection or [],
        )

        result = await self._doc_agent.run(doc_input, trace)

        if isinstance(result, FailureContract):
            raise RuntimeError(f"Report generation failed: {result.error_message}")

        state = state.evolve("document_builder", report=result.report_markdown)

        exec_ctx.agent_executions.append(AgentExecution(
            agent_name="document_builder",
            started_at=start,
            completed_at=datetime.now(timezone.utc),
            status=ExecutionStatus.COMPLETED,
            input_state_version=state.version.parent_version or 1,
            output_state_version=state.version.version,
        ))

        return state, exec_ctx

    def _derive_default_probes(self, state: ComplianceState) -> list[ProbeDefinition]:
        """Derive probe definitions from state when none provided."""
        return [ProbeDefinition(**pd) for pd in (state.probe_definitions or [])]

    def _derive_default_conditions(
        self, state: ComplianceState
    ) -> list[ValidationCondition]:
        """Derive validation conditions from state."""
        return [ValidationCondition(**vc) for vc in (state.validation_conditions or [])]

    def _find_matching_evidence(
        self, condition: ValidationCondition, evidence_collection: list[dict]
    ) -> "EvidenceBatch | None":
        """Find evidence that matches a validation condition."""
        from probes.base import EvidenceBatch, EvidenceRecord

        # For V1, aggregate all evidence into a single batch
        all_records = []
        total_sample_count = 0
        for ev in evidence_collection:
            if ev.get("status") == "success":
                total_sample_count += ev.get("sample_count", 0)
                data = ev.get("data", {})
                records = data.get("records", [])
                for r in records:
                    if isinstance(r, dict) and "value" in r:
                        all_records.append(EvidenceRecord(**r))

        if all_records:
            return EvidenceBatch(
                probe_id="aggregated",
                records=all_records,
                sample_count=len(all_records),
            )
        return None

    async def _emit_event(self, event: Any) -> None:
        """Emit a domain event if event bus is available."""
        if self._event_bus:
            await self._event_bus.publish(event)
