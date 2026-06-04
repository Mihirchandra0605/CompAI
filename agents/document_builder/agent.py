"""Document Builder Agent — generates compliance reports from XAI analysis."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from agents.base import BaseComplianceAgent
from contracts.base import AgentInput, AgentOutput
from explainability.collector import TraceCollector
from explainability.trace import TraceNodeType
from pydantic import Field

logger = logging.getLogger(__name__)


class DocumentInput(AgentInput):
    """Input for the Document Builder."""

    regulation_id: str
    regulation_text: str
    xai_analysis: dict[str, Any]
    validation_results: list[dict[str, Any]]
    intents: list[dict[str, Any]]
    evidence_collection: list[dict[str, Any]]


class DocumentOutput(AgentOutput):
    """Output from the Document Builder."""

    report_markdown: str = ""
    report_format: str = "markdown"


class DocumentBuilderAgent(BaseComplianceAgent[DocumentInput, DocumentOutput]):
    """Generates structured compliance reports."""

    name = "document_builder"

    async def execute(self, input: DocumentInput, trace: TraceCollector) -> DocumentOutput:
        """Generate a compliance report."""
        async with trace.span(
            "generate_report", TraceNodeType.TOOL_USE, agent_name=self.name
        ) as span:
            if self._slm_service:
                prompt = (
                    f"Generate a professional, markdown-formatted compliance report for regulation {input.regulation_id}.\n\n"
                    f"Regulation Text:\n{input.regulation_text[:2000]}\n\n"
                    f"XAI Analysis:\n{input.xai_analysis}\n\n"
                    f"Validation Results:\n{input.validation_results}\n\n"
                    "Please structure it beautifully with clear sections: Overview, Constraint Results, Evidence Summary, Reasoning, and Recommendations. Use tables where appropriate."
                )
                try:
                    report = await self._slm_service.query(
                        prompt=prompt,
                        system_prompt="You are an expert compliance report generator.",
                        use_rag=True,
                        rag_query=f"Compliance report template and standards for {input.regulation_id}"
                    )
                except Exception as e:
                    logger.error(f"Document Builder SLM call failed: {e}")
                    report = self._build_report(input)
            else:
                report = self._build_report(input)
                
            span.set_output(f"Generated report ({len(report)} chars)")
            span.set_confidence(0.95, ["deterministic_formatting"])

        return DocumentOutput(
            metadata=input.metadata,
            success=True,
            report_markdown=report,
            state_updates={"report": report},
        )

    def _build_report(self, input: DocumentInput) -> str:
        """Build the compliance report markdown."""
        xai = input.xai_analysis
        verdict = xai.get("regulation_verdict", "PENDING")
        confidence = xai.get("confidence", 0.0)
        partial_score = xai.get("partial_compliance_score", 0.0)

        verdict_icon = "✅" if verdict == "COMPLIANT" else "❌"
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        lines = [
            "# CompliAI Compliance Report",
            "",
            f"**Regulation**: {input.regulation_id}",
            f"**Run ID**: {input.metadata.run_id}",
            f"**Date**: {now}",
            f"**Overall Verdict**: {verdict_icon} {verdict}",
            f"**Confidence**: {confidence*100:.0f}%",
            f"**Partial Compliance Score**: {partial_score*100:.0f}%",
            "",
            "---",
            "",
            "## Regulation Text",
            "",
            f"> {input.regulation_text[:500]}",
            "",
            "---",
            "",
            "## Constraint Results",
            "",
            "| # | Constraint | Threshold | Measured | Result | Margin |",
            "|---|-----------|-----------|----------|--------|--------|",
        ]

        for i, result in enumerate(input.validation_results, 1):
            measured = result.get("measured_value")
            threshold = result.get("threshold_value")
            v = result.get("verdict", "unknown")
            icon = "✅" if v == "pass" else "❌" if v == "fail" else "⚠️"
            margin = f"{threshold - measured:+.1f}" if measured is not None and threshold is not None else "N/A"
            constraint_id = result.get("constraint_id", f"constraint-{i}")
            operator = result.get("operator", "<=")
            measured_str = f"{measured:.1f}" if measured is not None else "N/A"

            lines.append(
                f"| {i} | {constraint_id} | {operator} {threshold} | "
                f"{measured_str} | {icon} {v.upper()} | {margin} |"
            )

        lines.extend([
            "",
            "---",
            "",
            "## Evidence Summary",
            "",
        ])

        for ev in input.evidence_collection:
            status = ev.get("status", "unknown")
            samples = ev.get("sample_count", 0)
            probe_id = ev.get("probe_id", "unknown")
            lines.append(f"- **{probe_id}**: {status} ({samples} samples)")

        lines.extend([
            "",
            "---",
            "",
            "## Reasoning Chain",
            "",
        ])

        reasoning = xai.get("reasoning_chain", [])
        for i, step in enumerate(reasoning, 1):
            lines.append(f"{i}. {step}")

        recommendations = xai.get("recommendations", [])
        if recommendations:
            lines.extend([
                "",
                "---",
                "",
                "## Recommendations",
                "",
            ])
            for rec in recommendations:
                lines.append(f"- {rec}")

        lines.extend([
            "",
            "---",
            "",
            f"*Report generated by CompliAI v0.1.0 at {now}*",
            f"*Traceability: Run {input.metadata.run_id}, Regulation {input.regulation_id}*",
        ])

        return "\n".join(lines)
