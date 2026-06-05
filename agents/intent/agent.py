"""Intent Extraction Agent — extracts compliance intents from regulation text."""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from agents.base import BaseComplianceAgent
from contracts.intent_contract import ExtractedIntent, IntentInput, IntentOutput
from explainability.collector import TraceCollector
from explainability.trace import TraceNodeType
from infrastructure.llm_provider import AbstractLLMProvider
from infrastructure.vector_store import ChromaVectorStore

from .prompts import INTENT_SYSTEM_PROMPT, INTENT_USER_PROMPT

logger = logging.getLogger(__name__)


class IntentAgent(BaseComplianceAgent[IntentInput, IntentOutput]):
    """Extracts structured compliance intents from regulation text with RAG support."""

    name = "intent_agent"

    def __init__(self, slm_service):
        super().__init__(slm_service=slm_service)

    async def execute(self, input: IntentInput, trace: TraceCollector) -> IntentOutput:
        """Extract intents from regulation text using SLM Service with RAG."""
        
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

            # We use structured output format matching ExtractedIntent structure, though here we expect raw JSON matching the contract
            schema = {
                "intents": [
                    {
                        "intent_id": "string",
                        "clause_reference": "string",
                        "description": "string",
                        "severity": "string",
                        "category": "string",
                        "measurable_criteria": ["string"],
                        "target_systems": ["string"],
                        "evidence_requirements": ["string"],
                        "confidence": "number"
                    }
                ],
                "regulation_summary": "string"
            }
            
            try:
                parsed = await self._slm_service.query_structured(
                    prompt=prompt,
                    system_prompt=INTENT_SYSTEM_PROMPT,
                    output_schema=schema,
                    temperature=0.0,
                    use_rag=True,
                    rag_query=" ".join(input.focus_clauses) if input.focus_clauses else input.regulation_text[:200]
                )
                span.set_output(str(parsed)[:200])
            except Exception as e:
                logger.error(f"Failed to generate structured intent: {e}")
                parsed = {}

        # Parse the LLM response
        async with trace.span(
            "parse_intent_response", TraceNodeType.INFERENCE, agent_name=self.name
        ) as span:
            intents_raw = parsed.get("intents", [])
            if isinstance(intents_raw, str):
                try:
                    intents_raw = json.loads(intents_raw)
                except json.JSONDecodeError:
                    intents_raw = []

            if isinstance(intents_raw, dict):
                intents_raw = [intents_raw]

            if not isinstance(intents_raw, list):
                intents_raw = []

            if not intents_raw:
                logger.warning("Intent extraction returned no structured intents; using fallback extraction.")
                intents_raw = self._extract_intents_fallback(input.regulation_text)

            regulation_summary = parsed.get("regulation_summary")

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

            if intents:
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
