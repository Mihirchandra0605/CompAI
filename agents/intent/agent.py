"""Intent Extraction Agent — extracts compliance intents from regulation text."""

from __future__ import annotations

import json
import logging
import uuid

from agents.base import BaseComplianceAgent
from contracts.intent_contract import ExtractedIntent, IntentInput, IntentOutput
from explainability.collector import TraceCollector
from explainability.trace import TraceNodeType
from infrastructure.llm_provider import AbstractLLMProvider

from .prompts import INTENT_SYSTEM_PROMPT, INTENT_USER_PROMPT

logger = logging.getLogger(__name__)


class IntentAgent(BaseComplianceAgent[IntentInput, IntentOutput]):
    """Extracts structured compliance intents from regulation text."""

    name = "intent_agent"

    def __init__(self, llm: AbstractLLMProvider):
        self._llm = llm

    async def execute(self, input: IntentInput, trace: TraceCollector) -> IntentOutput:
        """Extract intents from regulation text using LLM."""
        focus_instruction = ""
        if input.focus_clauses:
            focus_instruction = (
                f"Focus specifically on these clauses: {', '.join(input.focus_clauses)}"
            )

        prompt = INTENT_USER_PROMPT.format(
            regulation_text=input.regulation_text,
            focus_clause_instruction=focus_instruction,
        )

        async with trace.span(
            "llm_intent_extraction", TraceNodeType.LLM_CALL, agent_name=self.name
        ) as span:
            span.set_input(f"Regulation text ({len(input.regulation_text)} chars)")

            response = await self._llm.generate(
                prompt=prompt,
                system_prompt=INTENT_SYSTEM_PROMPT,
                temperature=0.0,
            )

            span.set_output(response.content[:200])

        # Parse the LLM response
        async with trace.span(
            "parse_intent_response", TraceNodeType.INFERENCE, agent_name=self.name
        ) as span:
            try:
                parsed = json.loads(response.content)
                intents_raw = parsed.get("intents", [])
                regulation_summary = parsed.get("regulation_summary")
            except json.JSONDecodeError:
                # Attempt to extract JSON from the response
                intents_raw = self._extract_intents_fallback(input.regulation_text)
                regulation_summary = None

            intents = []
            for raw in intents_raw:
                intent = ExtractedIntent(
                    intent_id=raw.get("intent_id", f"int:{uuid.uuid4().hex[:8]}"),
                    clause_reference=raw.get("clause_reference", "unknown"),
                    description=raw.get("description", ""),
                    severity=raw.get("severity", "major"),
                    category=raw.get("category", "quality_of_service"),
                    measurable_criteria=raw.get("measurable_criteria", []),
                    target_systems=raw.get("target_systems", []),
                    evidence_requirements=raw.get("evidence_requirements", []),
                    confidence=raw.get("confidence", 0.7),
                )
                intents.append(intent)

            span.set_confidence(
                sum(i.confidence for i in intents) / max(len(intents), 1),
                ["llm_extraction_quality"],
            )
            span.set_output(f"Extracted {len(intents)} intents")

        return IntentOutput(
            metadata=input.metadata,
            success=True,
            intents=intents,
            regulation_summary=regulation_summary,
            state_updates={
                "intents": [i.model_dump() for i in intents],
            },
        )

    def _extract_intents_fallback(self, regulation_text: str) -> list[dict]:
        """Fallback intent extraction when LLM response is not valid JSON."""
        # Simple heuristic fallback for V1
        return [
            {
                "intent_id": f"int:fallback:{uuid.uuid4().hex[:8]}",
                "clause_reference": "unknown",
                "description": "Extracted from regulation text (fallback mode)",
                "severity": "major",
                "category": "quality_of_service",
                "measurable_criteria": [],
                "target_systems": [],
                "evidence_requirements": [],
                "confidence": 0.3,
            }
        ]
