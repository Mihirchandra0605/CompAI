"""Semantic Validator — LLM-assisted validation for non-deterministic constraints."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel

from infrastructure.llm_provider import AbstractLLMProvider
from probes.base import EvidenceBatch
from probes.validation.engine import ValidationCondition, ValidationResult, ValidationVerdict

logger = logging.getLogger(__name__)


class SemanticValidationRequest(BaseModel):
    """Request for semantic (LLM-assisted) validation."""

    constraint_id: str
    predicate: str  # e.g., "Does this text mandate password rotation?"
    evidence_text: str
    context: str = ""


class SemanticValidator:
    """
    LLM-assisted validator for non-deterministic (semantic) constraints.

    IMPORTANT: Even in semantic validation, the LLM outputs structured reasoning
    which is then mapped to a deterministic PASS/FAIL by the engine.
    The LLM assists reasoning, it does NOT directly determine the verdict.
    """

    SYSTEM_PROMPT = """You are a compliance analysis expert.
You will be given a compliance predicate and evidence text.
Evaluate whether the evidence satisfies the predicate.

Respond with a JSON object:
{
  "satisfies": true/false,
  "confidence": 0.0-1.0,
  "reasoning": "step-by-step explanation",
  "key_phrases": ["relevant phrases from evidence"]
}
"""

    def __init__(self, llm: AbstractLLMProvider):
        self._llm = llm

    async def evaluate(
        self,
        request: SemanticValidationRequest,
    ) -> ValidationResult:
        """Evaluate evidence against a semantic predicate using LLM."""
        prompt = (
            f"PREDICATE: {request.predicate}\n\n"
            f"EVIDENCE TEXT:\n{request.evidence_text[:2000]}\n\n"
            f"CONTEXT: {request.context}\n\n"
            "Does the evidence satisfy the predicate? Respond with JSON."
        )

        try:
            response = await self._llm.generate(
                prompt=prompt,
                system_prompt=self.SYSTEM_PROMPT,
                temperature=0.0,
            )

            import json
            parsed = json.loads(response.content)
            satisfies = parsed.get("satisfies", False)
            confidence = parsed.get("confidence", 0.5)
            reasoning = parsed.get("reasoning", "LLM evaluation")

        except Exception as e:
            logger.error(f"Semantic validation failed: {e}")
            return ValidationResult(
                condition_id=f"sem:{request.constraint_id}",
                constraint_id=request.constraint_id,
                verdict=ValidationVerdict.INSUFFICIENT_EVIDENCE,
                measured_value=None,
                threshold_value=0.0,
                operator="SEMANTIC",
                confidence=0.0,
                reasoning=f"Semantic evaluation failed: {e}",
            )

        # Map LLM output to deterministic verdict
        verdict = ValidationVerdict.PASS if satisfies else ValidationVerdict.FAIL

        # Apply confidence penalty for semantic evaluation
        adjusted_confidence = confidence * 0.85  # Semantic always lower than deterministic

        return ValidationResult(
            condition_id=f"sem:{request.constraint_id}",
            constraint_id=request.constraint_id,
            verdict=verdict,
            measured_value=None,
            threshold_value=0.0,
            operator="SEMANTIC",
            confidence=adjusted_confidence,
            reasoning=reasoning,
            measurement_certainty=confidence,
        )
