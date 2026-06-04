"""
CompliAI End-to-End Demo — TRAI QoS Latency Compliance

This script demonstrates the complete compliance pipeline:
1. Regulation ingestion
2. Intent extraction
3. CCL generation
4. Probe execution
5. Deterministic validation
6. XAI analysis
7. Report generation

Uses simulated VoLTE latency data against TRAI QoS regulations.
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Load .env file
from dotenv import load_dotenv
load_dotenv()

from agents.ccl_generator.agent import CCLGeneratorAgent
from agents.document_builder.agent import DocumentBuilderAgent
from agents.intent.agent import IntentAgent
from agents.mind_mapper.agent import MindMapperAgent
from agents.probe.agent import ProbeAgent
from agents.skill_generator.agent import SkillGeneratorAgent
from agents.xai_analyzer.agent import XAIAnalyzerAgent
from infrastructure.llm_provider import AbstractLLMProvider, LLMResponse, MockLLMProvider
from orchestration.pipeline import CompliancePipeline
from probes.dispatcher import ProbeDispatcher
from probes.executors.log_scan import LogScanProbe
from probes.registry import ProbeRegistry
from probes.validation.engine import ValidationEngine
from infrastructure.vector_store import ChromaVectorStore
from events.bus import AsyncEventBus


# Paths
FIXTURES_DIR = Path(__file__).parent / "tests" / "fixtures"
REGULATION_FILE = FIXTURES_DIR / "trai_qos_2024_full.txt"
LATENCY_LOGS_FILE = FIXTURES_DIR / "sample_latency_logs.csv"



async def main():
    """Run the end-to-end compliance demo."""
    print("=" * 70)
    print("  CompliAI — TRAI QoS Latency Compliance Demo")
    print("=" * 70)
    print()

    # Load regulation
    regulation_text = REGULATION_FILE.read_text()
    print(f"[1/6] Loaded regulation: {regulation_text.strip()[:80]}...")
    print()

    # Setup infrastructure
    from infrastructure.llm_provider import get_llm_provider
    from infrastructure.slm_service import SLMService

    llm = get_llm_provider()
    vector_store = ChromaVectorStore()
    
    # Initialize the Centralized SLM Service
    slm_service = SLMService(llm_provider=llm, vector_store=vector_store)

    probe_registry = ProbeRegistry()
    probe_registry.register("LOG_SCAN", LogScanProbe)
    dispatcher = ProbeDispatcher(probe_registry)
    validation_engine = ValidationEngine()

    # Setup event bus to capture pipeline execution logs
    event_bus = AsyncEventBus()
    pipeline_logs = []

    async def _capture_event(event):
        label_map = {
            "pipeline.started":                    "Pipeline initialised — starting compliance validation.",
            "compliance.intents.extracted":        f"Intent Extraction complete — {event.payload.get('intent_count', '?')} obligations identified.",
            "compliance.ccl.generated":            f"CCL Generator complete — {event.payload.get('clauses', '?')} clauses, {event.payload.get('constraints', '?')} constraints.",
            "compliance.probes.completed":         f"Probe Agent complete — {event.payload.get('total_evidence', '?')} evidence records collected.",
            "compliance.validation.completed":     f"Validation Engine complete — {event.payload.get('results_count', '?')} rules evaluated.",
            "compliance.verdict.determined":       f"XAI Analyzer complete — Verdict: {str(event.payload.get('verdict', '?')).upper()} ({event.payload.get('confidence', 0)*100:.0f}% confidence).",
            "pipeline.completed":                  "Pipeline completed successfully.",
            "pipeline.failed":                     f"Pipeline FAILED — {event.payload.get('error', 'Unknown error')}.",
        }
        pipeline_logs.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event.event_type,
            "message": label_map.get(event.event_type, f"[{event.event_type}] {event.payload}"),
        })

    event_bus.subscribe("pipeline.*", _capture_event)
    event_bus.subscribe("compliance.*", _capture_event)
    await event_bus.start()

    # Build pipeline
    pipeline = CompliancePipeline(
        intent_agent=IntentAgent(slm_service=slm_service),
        ccl_agent=CCLGeneratorAgent(slm_service=slm_service),
        mind_mapper_agent=MindMapperAgent(slm_service=slm_service),
        skill_generator_agent=SkillGeneratorAgent(slm_service=slm_service),
        probe_agent=ProbeAgent(dispatcher),
        xai_agent=XAIAnalyzerAgent(slm_service=slm_service),
        doc_agent=DocumentBuilderAgent(slm_service=slm_service),
        validation_engine=validation_engine,
        event_bus=event_bus,
    )

    # Define probes (normally derived from CCL by SkillGenerator)
    probe_definitions = [
        {
            "probe_id": "probe:run:001",
            "derived_from": "ps:4.2.1:001",
            "probe_type": "LOG_SCAN",
            "config": {
                "file_path": str(LATENCY_LOGS_FILE),
                "columns": ["timestamp", "call_id", "call_type", "rtt_ms"],
                "filter": {"call_type": "volte"},
                "aggregation": {"method": "mean", "column": "rtt_ms"},
                "window": "24h",
            },
        },
        {
            "probe_id": "probe:run:002",
            "derived_from": "ps:4.2.1:002",
            "probe_type": "LOG_SCAN",
            "config": {
                "file_path": str(LATENCY_LOGS_FILE),
                "columns": ["timestamp", "call_id", "call_type", "rtt_ms"],
                "filter": {"call_type": "volte"},
                "aggregation": {"method": "p95", "column": "rtt_ms"},
                "window": "24h",
            },
        },
    ]

    # Define validation conditions (normally derived from CCL)
    validation_conditions = [
        {
            "condition_id": "vc:4.2.1:001",
            "constraint_id": "con:4.2.1:001",
            "condition_type": "DETERMINISTIC",
            "measure_name": "rtt_latency_avg",
            "operator": "LTE",
            "threshold_value": 150.0,
            "threshold_unit": "ms",
            "aggregation": "MEAN",
            "window": "PT24H",
            "min_samples": 100,
        },
        {
            "condition_id": "vc:4.2.1:002",
            "constraint_id": "con:4.2.1:002",
            "condition_type": "DETERMINISTIC",
            "measure_name": "rtt_latency_p95",
            "operator": "LTE",
            "threshold_value": 200.0,
            "threshold_unit": "ms",
            "aggregation": "P95",
            "window": "PT24H",
            "min_samples": 100,
        },
    ]

    # Execute pipeline
    print("[2/6] Starting compliance pipeline...")
    print()

    result = await pipeline.run(
        regulation_id="trai-qos-2024-4.2.1",
        regulation_text=regulation_text,
        probe_definitions=probe_definitions,
        validation_conditions=validation_conditions,
    )

    # Print results
    print("-" * 70)
    print("  PIPELINE RESULTS")
    print("-" * 70)
    print()
    print(f"  Run ID:     {result.state.run_id}")
    print(f"  Verdict:    {result.state.verdict.value}")
    print(f"  Confidence: {result.state.confidence:.2f}" if result.state.confidence else "  Confidence: N/A")
    print(f"  Success:    {result.success}")
    print()

    # Execution stages
    print("  Execution Stages:")
    for ae in result.execution_context.agent_executions:
        duration = ""
        if ae.completed_at and ae.started_at:
            ms = (ae.completed_at - ae.started_at).total_seconds() * 1000
            duration = f" ({ms:.0f}ms)"
        print(f"    * {ae.agent_name}: {ae.status.value}{duration}")
    print()

    # Trace summary
    trace = result.trace.get_trace()
    print(f"  Reasoning Trace: {len(trace.nodes)} nodes")
    print()

    # XAI Analysis
    xai = result.state.xai_analysis
    if xai:
        print("  XAI Analysis:")
        print(f"    Regulation Verdict: {xai.get('regulation_verdict')}")
        print(f"    Partial Score:      {xai.get('partial_compliance_score', 0)*100:.0f}%")
        print()
        print("  Reasoning Chain:")
        for step in xai.get("reasoning_chain", [])[:8]:
            print(f"    → {step}")
        print()
        recs = xai.get("recommendations", [])
        if recs:
            print("  Recommendations:")
            for rec in recs:
                print(f"    • {rec}")
            print()

    # Report
    if result.state.report:
        print("=" * 70)
        print("  GENERATED COMPLIANCE REPORT")
        print("=" * 70)
        print()
        print(result.state.report)

    # Stop event bus
    await event_bus.stop()

    # ── Save all results to backend_new/pipeline_output.json ──────────────
    xai = result.state.xai_analysis or {}
    stages_info = []
    for ae in result.execution_context.agent_executions:
        duration_ms = 0
        if ae.completed_at and ae.started_at:
            duration_ms = int((ae.completed_at - ae.started_at).total_seconds() * 1000)
        desc_map = {
            "intent_agent":      "Extracted regulatory clauses and compliance obligations.",
            "ccl_generator":     "Generated Compliance Cognitive Language (CCL) XML schema.",
            "mind_mapper":       "Constructed semantic knowledge graph from CCL.",
            "skill_generator":   "Derived executable probe definitions from CCL.",
            "probe_agent":       "Executed data scanners and collected telemetry evidence.",
            "validation_engine": "Performed deterministic NumPy validation on evidence.",
            "xai_analyzer":      "Aggregated verdicts and generated explainable reasoning.",
            "document_builder":  "Compiled final markdown compliance audit report.",
        }
        stages_info.append({
            "name": ae.agent_name,
            "status": ae.status.value,
            "duration_ms": duration_ms,
            "description": desc_map.get(ae.agent_name, ae.agent_name),
        })

    validation_results = []
    for vr in (result.state.validation_results or []):
        validation_results.append({
            "constraint_id":  vr.get("constraint_id", ""),
            "condition_id":   vr.get("condition_id", ""),
            "operator":       vr.get("operator", ""),
            "threshold":      vr.get("threshold_value"),
            "measured":       vr.get("measured_value"),
            "verdict":        vr.get("verdict", ""),
            "sample_count":   vr.get("sample_count", 0),
            "confidence":     vr.get("confidence", 0),
            "reasoning":      vr.get("reasoning", ""),
        })

    output = {
        "run_id":                   result.state.run_id,
        "regulation_id":            result.state.regulation_id,
        "verdict":                  result.state.verdict.value,
        "confidence":               result.state.confidence,
        "partial_compliance_score": xai.get("partial_compliance_score"),
        "reasoning_chain":          xai.get("reasoning_chain", []),
        "recommendations":          xai.get("recommendations", []),
        "report":                   result.state.report,
        "ccl_xml":                  result.state.ccl_document or "",
        "stages":                   stages_info,
        "validation_results":       validation_results,
        "logs":                     pipeline_logs,
        "generated_at":             datetime.now(timezone.utc).isoformat(),
    }

    output_path = Path(__file__).parent / "backend_new" / "pipeline_output.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2, default=str))
    print()
    print(f"[✓] Pipeline output saved → {output_path}")

    return result


if __name__ == "__main__":
    asyncio.run(main())
