"""Pipeline execution endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()


class PipelineRunRequest(BaseModel):
    """Request to start a compliance pipeline run."""

    regulation_id: str
    regulation_text: str
    probe_definitions: list[dict[str, Any]] | None = None
    validation_conditions: list[dict[str, Any]] | None = None


class PipelineRunResponse(BaseModel):
    """Response from a pipeline run."""

    run_id: str
    regulation_id: str
    verdict: str
    confidence: float | None = None
    partial_compliance_score: float | None = None
    report: str | None = None
    execution_stages: list[dict[str, Any]] = Field(default_factory=list)
    trace_summary: dict[str, Any] = Field(default_factory=dict)


@router.post("/run", response_model=PipelineRunResponse)
async def run_pipeline(request: PipelineRunRequest):
    """Execute a compliance validation pipeline."""
    from orchestration.pipeline import CompliancePipeline
    from agents.intent.agent import IntentAgent
    from agents.ccl_generator.agent import CCLGeneratorAgent
    from agents.mind_mapper.agent import MindMapperAgent
    from agents.skill_generator.agent import SkillGeneratorAgent
    from agents.probe.agent import ProbeAgent
    from agents.xai_analyzer.agent import XAIAnalyzerAgent
    from agents.document_builder.agent import DocumentBuilderAgent
    from infrastructure.llm_provider import MockLLMProvider
    from infrastructure.slm_service import SLMService
    from infrastructure.vector_store import ChromaVectorStore
    from probes.dispatcher import ProbeDispatcher
    from probes.registry import ProbeRegistry
    from probes.executors.log_scan import LogScanProbe
    from probes.executors.config_scan import ConfigScanProbe
    from probes.validation.engine import ValidationEngine
    from events.bus import AsyncEventBus

    # Setup infrastructure
    llm = MockLLMProvider()
    vector_store = ChromaVectorStore()
    slm_service = SLMService(llm_provider=llm, vector_store=vector_store)
    probe_registry = ProbeRegistry()
    probe_registry.register("LOG_SCAN", LogScanProbe)
    probe_registry.register("CONFIG_SCAN", ConfigScanProbe)
    dispatcher = ProbeDispatcher(probe_registry)
    event_bus = AsyncEventBus()

    # Build pipeline
    pipeline = CompliancePipeline(
        intent_agent=IntentAgent(slm_service=slm_service),
        ccl_agent=CCLGeneratorAgent(slm_service=slm_service),
        mind_mapper_agent=MindMapperAgent(slm_service=slm_service),
        skill_generator_agent=SkillGeneratorAgent(slm_service=slm_service),
        probe_agent=ProbeAgent(dispatcher),
        xai_agent=XAIAnalyzerAgent(slm_service=slm_service),
        doc_agent=DocumentBuilderAgent(slm_service=slm_service),
        validation_engine=ValidationEngine(),
        event_bus=event_bus,
    )

    try:
        result = await pipeline.run(
            regulation_id=request.regulation_id,
            regulation_text=request.regulation_text,
            probe_definitions=request.probe_definitions,
            validation_conditions=request.validation_conditions,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Build response
    xai = result.state.xai_analysis or {}
    return PipelineRunResponse(
        run_id=result.state.run_id,
        regulation_id=result.state.regulation_id,
        verdict=result.state.verdict.value,
        confidence=result.state.confidence,
        partial_compliance_score=xai.get("partial_compliance_score"),
        report=result.state.report,
        execution_stages=[
            ae.model_dump() for ae in result.execution_context.agent_executions
        ],
        trace_summary={
            "trace_id": result.trace.get_trace().trace_id,
            "node_count": len(result.trace.get_trace().nodes),
        },
    )
