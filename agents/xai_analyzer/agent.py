"""XAI Analyzer Agent — produces explainable compliance analysis from validation results."""

from __future__ import annotations

import logging
from typing import Any

from agents.base import BaseComplianceAgent
from contracts.base import AgentInput, AgentOutput
from explainability.collector import TraceCollector
from explainability.confidence import PropagatedConfidence
from explainability.trace import TraceNodeType
from pydantic import Field
from probes.validation.engine import ValidationResult, ValidationVerdict

logger = logging.getLogger(__name__)


class XAIInput(AgentInput):
    """Input for the XAI Analyzer."""

    validation_results: list[dict[str, Any]]
    intents: list[dict[str, Any]]
    evidence_collection: list[dict[str, Any]]
    regulation_text: str | None = None


class XAIOutput(AgentOutput):
    """Output from the XAI Analyzer."""

    regulation_verdict: str
    confidence: float
    partial_compliance_score: float
    clause_verdicts: list[dict[str, Any]] = Field(default_factory=list)
    reasoning_chain: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    confidence_breakdown: dict[str, float] = Field(default_factory=dict)


class XAIAnalyzerAgent(BaseComplianceAgent[XAIInput, XAIOutput]):
    """Aggregates validation results into explainable compliance analysis."""

    name = "xai_analyzer"

    async def execute(self, input: XAIInput, trace: TraceCollector) -> XAIOutput:
        """Analyze validation results and produce explainable verdicts."""
        async with trace.span(
            "aggregate_verdicts", TraceNodeType.INFERENCE, agent_name=self.name
        ) as span:
            # Aggregate constraint-level results
            results = [ValidationResult(**r) for r in input.validation_results]

            passing = [r for r in results if r.verdict == ValidationVerdict.PASS]
            failing = [r for r in results if r.verdict == ValidationVerdict.FAIL]
            insufficient = [
                r for r in results if r.verdict == ValidationVerdict.INSUFFICIENT_EVIDENCE
            ]

            total_evaluated = len(passing) + len(failing)
            partial_score = len(passing) / max(total_evaluated, 1)

            # Determine regulation-level verdict
            if failing:
                reg_verdict = "NON_COMPLIANT"
            elif insufficient and not failing:
                reg_verdict = "INSUFFICIENT_EVIDENCE"
            elif passing and not failing:
                reg_verdict = "COMPLIANT"
            else:
                reg_verdict = "PENDING"

            # Propagate confidence
            confidence_model = PropagatedConfidence()
            for r in results:
                confidence_model.add_contribution(
                    agent_name="validation_engine",
                    stage="validation",
                    confidence=r.confidence,
                    weight=1.0,
                )
            overall_confidence = confidence_model.compute()

            span.set_output(f"Verdict: {reg_verdict}, confidence: {overall_confidence:.2f}")
            span.set_confidence(overall_confidence, ["aggregated_validation_confidence"])

        # Build reasoning chain
        async with trace.span(
            "build_reasoning_chain", TraceNodeType.INFERENCE, agent_name=self.name
        ) as span:
            reasoning_chain = self._build_reasoning_chain(results, input.intents)
            recommendations = self._generate_recommendations(failing, insufficient)
            span.set_output(f"{len(reasoning_chain)} reasoning steps")

        # Build clause verdicts
        clause_verdicts = self._build_clause_verdicts(results, input.intents)

        return XAIOutput(
            metadata=input.metadata,
            success=True,
            regulation_verdict=reg_verdict,
            confidence=overall_confidence,
            partial_compliance_score=partial_score,
            clause_verdicts=clause_verdicts,
            reasoning_chain=reasoning_chain,
            recommendations=recommendations,
            confidence_breakdown={
                "evidence_freshness": sum(r.freshness_score for r in results) / max(len(results), 1),
                "sample_adequacy": sum(r.sample_adequacy for r in results) / max(len(results), 1),
                "measurement_certainty": sum(r.measurement_certainty for r in results)
                / max(len(results), 1),
            },
            state_updates={
                "xai_analysis": {
                    "regulation_verdict": reg_verdict,
                    "confidence": overall_confidence,
                    "partial_compliance_score": partial_score,
                },
                "verdict": reg_verdict.lower(),
                "confidence": overall_confidence,
            },
        )

    def _build_reasoning_chain(
        self, results: list[ValidationResult], intents: list[dict]
    ) -> list[str]:
        """Build human-readable reasoning chain."""
        chain = []
        for intent in intents:
            chain.append(
                f"Regulation requires: {intent.get('description', 'Unknown requirement')}"
            )
            for criterion in intent.get("measurable_criteria", []):
                chain.append(f"  Criterion: {criterion}")

        for r in results:
            chain.append(r.reasoning)

        # Summary
        passing = sum(1 for r in results if r.verdict == ValidationVerdict.PASS)
        failing = sum(1 for r in results if r.verdict == ValidationVerdict.FAIL)
        chain.append(f"Summary: {passing} constraints PASS, {failing} constraints FAIL")

        return chain

    def _generate_recommendations(
        self,
        failing: list[ValidationResult],
        insufficient: list[ValidationResult],
    ) -> list[str]:
        """Generate actionable recommendations from failures."""
        recommendations = []
        for r in failing:
            if r.measured_value and r.threshold_value:
                excess = r.measured_value - r.threshold_value
                recommendations.append(
                    f"Constraint {r.constraint_id}: measured value "
                    f"({r.measured_value:.1f}) exceeds threshold ({r.threshold_value}) "
                    f"by {excess:.1f}. Investigate root cause."
                )
        for r in insufficient:
            recommendations.append(
                f"Constraint {r.constraint_id}: insufficient evidence. "
                f"Collect more samples (have {r.sample_count})."
            )
        return recommendations

    def _build_clause_verdicts(
        self, results: list[ValidationResult], intents: list[dict]
    ) -> list[dict]:
        """Build per-clause verdict summaries."""
        # Group results by constraint prefix
        passing_ids = [r.constraint_id for r in results if r.verdict == ValidationVerdict.PASS]
        failing_ids = [r.constraint_id for r in results if r.verdict == ValidationVerdict.FAIL]

        verdicts = []
        for intent in intents:
            clause_ref = intent.get("clause_reference", "unknown")
            verdict = "COMPLIANT" if not failing_ids else "NON_COMPLIANT"
            verdicts.append(
                {
                    "clause_reference": clause_ref,
                    "verdict": verdict,
                    "passing_constraints": passing_ids,
                    "failing_constraints": failing_ids,
                    "description": intent.get("description", ""),
                }
            )
        return verdicts
