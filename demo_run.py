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
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from agents.ccl_generator.agent import CCLGeneratorAgent
from agents.document_builder.agent import DocumentBuilderAgent
from agents.intent.agent import IntentAgent
from agents.probe.agent import ProbeAgent
from agents.xai_analyzer.agent import XAIAnalyzerAgent
from infrastructure.llm_provider import AbstractLLMProvider, LLMResponse, MockLLMProvider
from orchestration.pipeline import CompliancePipeline
from probes.dispatcher import ProbeDispatcher
from probes.executors.log_scan import LogScanProbe
from probes.registry import ProbeRegistry
from probes.validation.engine import ValidationEngine

# Paths
FIXTURES_DIR = Path(__file__).parent / "tests" / "fixtures"
REGULATION_FILE = FIXTURES_DIR / "sample_regulation.txt"
LATENCY_LOGS_FILE = FIXTURES_DIR / "sample_latency_logs.csv"


class DemoLLMProvider(AbstractLLMProvider):
    """LLM provider that returns pre-defined responses for the demo scenario."""

    async def generate(
        self,
        prompt: str,
        system_prompt=None,
        temperature=0.0,
        max_tokens=4096,
        response_format=None,
    ) -> LLMResponse:
        """Return appropriate demo responses based on prompt content."""
        if "compliance intent" in (system_prompt or "").lower() or "extract" in prompt.lower():
            return LLMResponse(
                content=json.dumps(self._intent_response()),
                model="demo-gpt4",
                usage={"prompt_tokens": 500, "completion_tokens": 300},
            )
        elif "ccl" in (system_prompt or "").lower() or "ccl" in prompt.lower():
            return LLMResponse(
                content=self._ccl_response(),
                model="demo-gpt4",
                usage={"prompt_tokens": 800, "completion_tokens": 1200},
            )
        else:
            return LLMResponse(content="{}", model="demo-gpt4", usage={})

    async def generate_structured(self, prompt, output_schema, system_prompt=None, temperature=0.0):
        return self._intent_response()

    def _intent_response(self) -> dict:
        return {
            "intents": [
                {
                    "intent_id": "int:4.2.1:001",
                    "clause_reference": "Chapter IV, §4.2.1",
                    "description": "Ensure VoLTE call quality by maintaining RTT latency within acceptable bounds",
                    "severity": "critical",
                    "category": "quality_of_service",
                    "measurable_criteria": [
                        "Average RTT latency ≤ 150ms over 24h window",
                        "95th percentile RTT latency ≤ 200ms over 24h window",
                    ],
                    "target_systems": ["core_network_boundary"],
                    "evidence_requirements": [
                        "VoLTE RTT latency metrics from core network logs"
                    ],
                    "confidence": 0.91,
                }
            ],
            "regulation_summary": "TRAI QoS 2024 §4.2.1 mandates VoLTE RTT latency thresholds at core network boundary",
        }

    def _ccl_response(self) -> str:
        return """<?xml version="1.0" encoding="UTF-8"?>
<ccl:document xmlns:ccl="urn:compliai:ccl:v1" xmlns:qos="urn:compliai:ccl:ext:qos:v1">
  <ccl:metadata>
    <ccl:version>1.0</ccl:version>
    <ccl:generated-by agent="ccl_generator" model="gpt-4" />
    <ccl:schema-version>urn:compliai:ccl:v1</ccl:schema-version>
  </ccl:metadata>
  <ccl:target-systems>
    <ccl:target-system id="ts:core-network-logs">
      <ccl:type>LOG_SYSTEM</ccl:type>
      <ccl:access-method>FILE_SYSTEM</ccl:access-method>
      <ccl:location>/var/log/volte/rtt_metrics.csv</ccl:location>
    </ccl:target-system>
  </ccl:target-systems>
  <ccl:regulation id="reg:trai-qos-2024">
    <ccl:title>TRAI Quality of Service Regulations, 2024</ccl:title>
    <ccl:authority>TRAI</ccl:authority>
    <ccl:jurisdiction>India</ccl:jurisdiction>
    <ccl:clause id="cl:4.2.1" section-ref="Chapter IV, §4.2.1">
      <ccl:text>The service provider shall ensure that the average RTT latency for VoLTE calls does not exceed 150ms with p95 not exceeding 200ms over 24h.</ccl:text>
      <ccl:obligation>MANDATORY</ccl:obligation>
      <ccl:risk>
        <ccl:risk-type>OPERATIONAL</ccl:risk-type>
        <ccl:severity>HIGH</ccl:severity>
      </ccl:risk>
      <ccl:intent id="int:4.2.1:001">
        <ccl:description>Ensure VoLTE latency quality</ccl:description>
        <ccl:objective id="obj:4.2.1:001" logic="AND">
          <ccl:constraint id="con:4.2.1:001" type="METRIC">
            <ccl:measure name="rtt_latency_avg">
              <ccl:unit>ms</ccl:unit>
              <ccl:aggregation>MEAN</ccl:aggregation>
            </ccl:measure>
            <ccl:threshold>
              <ccl:operator>LTE</ccl:operator>
              <ccl:value>150</ccl:value>
              <ccl:unit>ms</ccl:unit>
              <ccl:window>PT24H</ccl:window>
              <ccl:min-samples>100</ccl:min-samples>
            </ccl:threshold>
            <ccl:validation-condition type="DETERMINISTIC">
              <ccl:predicate>measure(rtt_latency_avg) &lt;= threshold(150, ms)</ccl:predicate>
            </ccl:validation-condition>
          </ccl:constraint>
          <ccl:constraint id="con:4.2.1:002" type="METRIC">
            <ccl:measure name="rtt_latency_p95">
              <ccl:unit>ms</ccl:unit>
              <ccl:aggregation>P95</ccl:aggregation>
            </ccl:measure>
            <ccl:threshold>
              <ccl:operator>LTE</ccl:operator>
              <ccl:value>200</ccl:value>
              <ccl:unit>ms</ccl:unit>
              <ccl:window>PT24H</ccl:window>
              <ccl:min-samples>100</ccl:min-samples>
            </ccl:threshold>
            <ccl:validation-condition type="DETERMINISTIC">
              <ccl:predicate>measure(rtt_latency_p95) &lt;= threshold(200, ms)</ccl:predicate>
            </ccl:validation-condition>
          </ccl:constraint>
        </ccl:objective>
      </ccl:intent>
    </ccl:clause>
  </ccl:regulation>
</ccl:document>"""


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
    llm = DemoLLMProvider()
    probe_registry = ProbeRegistry()
    probe_registry.register("LOG_SCAN", LogScanProbe)
    dispatcher = ProbeDispatcher(probe_registry)
    validation_engine = ValidationEngine()

    # Build pipeline
    pipeline = CompliancePipeline(
        intent_agent=IntentAgent(llm),
        ccl_agent=CCLGeneratorAgent(llm),
        probe_agent=ProbeAgent(dispatcher),
        xai_agent=XAIAnalyzerAgent(),
        doc_agent=DocumentBuilderAgent(),
        validation_engine=validation_engine,
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
        print(f"    ✓ {ae.agent_name}: {ae.status.value}{duration}")
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

    return result


if __name__ == "__main__":
    asyncio.run(main())
