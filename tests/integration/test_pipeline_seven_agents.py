from __future__ import annotations

from pathlib import Path

from agents.ccl_generator.agent import CCLGeneratorAgent
from agents.document_builder.agent import DocumentBuilderAgent
from agents.intent.agent import IntentAgent
from agents.mind_mapper.agent import MindMapperAgent
from agents.probe.agent import ProbeAgent
from agents.skill_generator.agent import SkillGeneratorAgent
from agents.xai_analyzer.agent import XAIAnalyzerAgent
from orchestration.pipeline import CompliancePipeline
from probes.dispatcher import ProbeDispatcher
from probes.executors.log_scan import LogScanProbe
from probes.registry import ProbeRegistry
from probes.validation.engine import ValidationEngine


class FakeSLMService:
    def __init__(self, ccl_xml: str) -> None:
        self.ccl_xml = ccl_xml

    async def query(
        self,
        prompt: str,
        system_prompt: str | None = None,
        use_rag: bool = False,
        rag_query: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> str:
        if "compliance report" in prompt.lower():
            return "# Test Compliance Report\n\nGenerated from fake SLM."
        return self.ccl_xml

    async def query_structured(
        self,
        prompt: str,
        output_schema: dict,
        system_prompt: str | None = None,
        use_rag: bool = False,
        rag_query: str | None = None,
        temperature: float = 0.0,
    ) -> dict:
        if "reasoning_chain" in output_schema:
            return {
                "reasoning_chain": ["Validated generated probes against latency evidence."],
                "recommendations": ["Investigate tail latency above the configured threshold."],
            }
        return {
            "intents": [
                {
                    "intent_id": "int:test:001",
                    "clause_reference": "4.2.1",
                    "description": "Ensure VoLTE latency stays within QoS thresholds.",
                    "severity": "major",
                    "category": "quality_of_service",
                    "measurable_criteria": ["Average RTT <= 150 ms", "P95 RTT <= 200 ms"],
                    "target_systems": ["core-network-logs"],
                    "evidence_requirements": ["VoLTE RTT CSV logs"],
                    "confidence": 0.9,
                }
            ],
            "regulation_summary": "VoLTE latency QoS test regulation.",
        }


def _write_latency_csv(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "timestamp,call_id,call_type,rtt_ms",
                "2026-01-01T00:00:00Z,c1,volte,100",
                "2026-01-01T00:01:00Z,c2,volte,120",
                "2026-01-01T00:02:00Z,c3,volte,140",
                "2026-01-01T00:03:00Z,c4,volte,180",
                "2026-01-01T00:04:00Z,c5,volte,240",
            ]
        ),
        encoding="utf-8",
    )


def _ccl_xml(log_path: Path) -> str:
    source = str(log_path).replace("\\", "/")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<ccl:document xmlns:ccl="urn:compliai:ccl:v1">
  <ccl:metadata>
    <ccl:version>1.0</ccl:version>
    <ccl:generated-by agent="test" />
  </ccl:metadata>
  <ccl:target-systems>
    <ccl:target-system id="ts:core-network-logs">
      <ccl:type>LOG_SYSTEM</ccl:type>
      <ccl:access-method>FILE_SYSTEM</ccl:access-method>
      <ccl:location>{source}</ccl:location>
    </ccl:target-system>
  </ccl:target-systems>
  <ccl:regulation id="reg:test">
    <ccl:title>Test QoS Regulation</ccl:title>
    <ccl:authority>Test Authority</ccl:authority>
    <ccl:jurisdiction>Test</ccl:jurisdiction>
    <ccl:clause id="cl:4.2.1" section-ref="4.2.1">
      <ccl:text>VoLTE latency thresholds.</ccl:text>
      <ccl:obligation>MANDATORY</ccl:obligation>
      <ccl:intent id="int:test:001">
        <ccl:description>Ensure VoLTE latency quality.</ccl:description>
        <ccl:category>quality_of_service</ccl:category>
        <ccl:objective id="obj:test:001" logic="AND">
          <ccl:constraint id="con:test:avg" type="METRIC">
            <ccl:description>Average RTT must be within threshold.</ccl:description>
            <ccl:measure name="rtt_latency_avg">
              <ccl:unit>ms</ccl:unit>
              <ccl:aggregation>MEAN</ccl:aggregation>
            </ccl:measure>
            <ccl:threshold>
              <ccl:operator>LTE</ccl:operator>
              <ccl:value>150</ccl:value>
              <ccl:unit>ms</ccl:unit>
              <ccl:min-samples>1</ccl:min-samples>
            </ccl:threshold>
            <ccl:evidence-requirement id="evr:test:avg" evidence-type="METRIC">
              <ccl:probe-strategy id="ps:test:avg" probe-type="LOG_SCAN">
                <ccl:method>Parse CSV RTT logs, filter VoLTE calls, compute mean.</ccl:method>
                <ccl:target-system-ref ref="ts:core-network-logs" />
              </ccl:probe-strategy>
            </ccl:evidence-requirement>
            <ccl:validation-condition type="DETERMINISTIC" />
          </ccl:constraint>
          <ccl:constraint id="con:test:p95" type="METRIC">
            <ccl:description>P95 RTT must be within threshold.</ccl:description>
            <ccl:measure name="rtt_latency_p95">
              <ccl:unit>ms</ccl:unit>
              <ccl:aggregation>P95</ccl:aggregation>
            </ccl:measure>
            <ccl:threshold>
              <ccl:operator>LTE</ccl:operator>
              <ccl:value>200</ccl:value>
              <ccl:unit>ms</ccl:unit>
              <ccl:min-samples>1</ccl:min-samples>
            </ccl:threshold>
            <ccl:evidence-requirement id="evr:test:p95" evidence-type="METRIC">
              <ccl:probe-strategy id="ps:test:p95" probe-type="LOG_SCAN">
                <ccl:method>Parse CSV RTT logs, filter VoLTE calls, compute p95.</ccl:method>
                <ccl:target-system-ref ref="ts:core-network-logs" />
              </ccl:probe-strategy>
            </ccl:evidence-requirement>
            <ccl:validation-condition type="DETERMINISTIC" />
          </ccl:constraint>
        </ccl:objective>
      </ccl:intent>
    </ccl:clause>
  </ccl:regulation>
</ccl:document>"""


async def test_pipeline_runs_full_seven_agent_flow_from_generated_skills(tmp_path):
    log_path = tmp_path / "latency.csv"
    _write_latency_csv(log_path)

    slm_service = FakeSLMService(_ccl_xml(log_path))
    registry = ProbeRegistry()
    registry.register("LOG_SCAN", LogScanProbe)

    pipeline = CompliancePipeline(
        intent_agent=IntentAgent(slm_service=slm_service),
        ccl_agent=CCLGeneratorAgent(slm_service=slm_service),
        mind_mapper_agent=MindMapperAgent(slm_service=slm_service),
        skill_generator_agent=SkillGeneratorAgent(slm_service=slm_service),
        probe_agent=ProbeAgent(ProbeDispatcher(registry), slm_service=slm_service),
        xai_agent=XAIAnalyzerAgent(slm_service=slm_service),
        doc_agent=DocumentBuilderAgent(slm_service=slm_service),
        validation_engine=ValidationEngine(),
    )

    result = await pipeline.run(
        regulation_id="reg:test",
        regulation_text="VoLTE latency thresholds.",
    )

    stages = [stage.agent_name for stage in result.execution_context.agent_executions]
    assert stages == [
        "intent_agent",
        "ccl_generator",
        "mind_mapper",
        "skill_generator",
        "probe_agent",
        "validation_engine",
        "xai_analyzer",
        "document_builder",
    ]
    assert result.state.compliance_graph
    assert len(result.state.probe_definitions or []) == 2
    assert len(result.state.validation_conditions or []) == 2
    assert len(result.state.evidence_collection or []) == 2
    assert len(result.state.validation_results or []) == 2
    assert result.state.report.startswith("# Test Compliance Report")
