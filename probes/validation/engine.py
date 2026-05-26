"""Validation Engine — evaluates evidence against CCL constraints deterministically."""

from __future__ import annotations

import logging
import math
from enum import Enum
from typing import Any

import numpy as np
from pydantic import BaseModel, Field

from probes.base import EvidenceBatch, EvidenceRecord

logger = logging.getLogger(__name__)


class ValidationVerdict(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    PARTIAL = "partial"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class ValidationCondition(BaseModel):
    """A fully executable condition derived from a CCL constraint."""

    condition_id: str
    constraint_id: str
    condition_type: str = "DETERMINISTIC"  # DETERMINISTIC or SEMANTIC
    measure_name: str
    operator: str  # LTE, GTE, EQ, NEQ, IN_RANGE
    threshold_value: float
    threshold_unit: str
    aggregation: str = "MEAN"  # MEAN, MEDIAN, P95, P99, MAX, MIN
    window: str | None = None  # ISO 8601 duration
    min_samples: int = 100
    tolerance: float = 0.0


class ValidationResult(BaseModel):
    """Result of evaluating a single validation condition."""

    condition_id: str
    constraint_id: str
    verdict: ValidationVerdict
    measured_value: float | None = None
    threshold_value: float
    operator: str
    sample_count: int = 0
    confidence: float = 0.0
    reasoning: str = ""
    evidence_batch_id: str | None = None

    # Confidence factors
    freshness_score: float = 1.0
    sample_adequacy: float = 1.0
    measurement_certainty: float = 1.0


class ValidationEngine:
    """
    Deterministic validation engine.

    CRITICAL: This engine does NOT use LLMs for deterministic constraints.
    Compliance verdicts are computed by code, not by AI.
    """

    async def evaluate(
        self,
        evidence: EvidenceBatch,
        condition: ValidationCondition,
    ) -> ValidationResult:
        """Evaluate evidence against a validation condition."""
        # Check minimum samples
        if evidence.sample_count < condition.min_samples:
            return ValidationResult(
                condition_id=condition.condition_id,
                constraint_id=condition.constraint_id,
                verdict=ValidationVerdict.INSUFFICIENT_EVIDENCE,
                threshold_value=condition.threshold_value,
                operator=condition.operator,
                sample_count=evidence.sample_count,
                confidence=0.0,
                reasoning=(
                    f"Insufficient evidence: {evidence.sample_count} samples "
                    f"< {condition.min_samples} required"
                ),
                evidence_batch_id=evidence.batch_id,
                sample_adequacy=evidence.sample_count / condition.min_samples,
            )

        # Extract numeric values from evidence
        values = self._extract_numeric_values(evidence.records)
        if not values:
            return ValidationResult(
                condition_id=condition.condition_id,
                constraint_id=condition.constraint_id,
                verdict=ValidationVerdict.INSUFFICIENT_EVIDENCE,
                threshold_value=condition.threshold_value,
                operator=condition.operator,
                sample_count=0,
                confidence=0.0,
                reasoning="No numeric values found in evidence",
                evidence_batch_id=evidence.batch_id,
            )

        # Apply aggregation
        aggregated = self._aggregate(values, condition.aggregation)

        # Apply comparison operator
        passes = self._compare(
            aggregated, condition.operator, condition.threshold_value, condition.tolerance
        )

        # Calculate confidence
        sample_adequacy = min(1.0, len(values) / condition.min_samples)
        confidence = self._calculate_confidence(
            sample_adequacy=sample_adequacy,
            measurement_certainty=0.99,  # Deterministic = high certainty
            freshness_score=1.0,
        )

        verdict = ValidationVerdict.PASS if passes else ValidationVerdict.FAIL

        margin = condition.threshold_value - aggregated
        reasoning = (
            f"{condition.aggregation}({condition.measure_name}) = {aggregated:.1f} "
            f"{condition.operator} {condition.threshold_value}{condition.threshold_unit} "
            f"→ {'PASS' if passes else 'FAIL'} "
            f"(margin: {margin:+.1f}{condition.threshold_unit})"
        )

        return ValidationResult(
            condition_id=condition.condition_id,
            constraint_id=condition.constraint_id,
            verdict=verdict,
            measured_value=aggregated,
            threshold_value=condition.threshold_value,
            operator=condition.operator,
            sample_count=len(values),
            confidence=confidence,
            reasoning=reasoning,
            evidence_batch_id=evidence.batch_id,
            freshness_score=1.0,
            sample_adequacy=sample_adequacy,
            measurement_certainty=0.99,
        )

    def _extract_numeric_values(self, records: list[EvidenceRecord]) -> list[float]:
        """Extract numeric values from evidence records."""
        values = []
        for record in records:
            if isinstance(record.value, (int, float)):
                values.append(float(record.value))
        return values

    def _aggregate(self, values: list[float], method: str) -> float:
        """Apply aggregation function to values."""
        arr = np.array(values)
        m = method.upper()
        if m == "MEAN":
            return float(np.mean(arr))
        elif m == "MEDIAN":
            return float(np.median(arr))
        elif m == "P95":
            return float(np.percentile(arr, 95))
        elif m == "P99":
            return float(np.percentile(arr, 99))
        elif m == "MAX":
            return float(np.max(arr))
        elif m == "MIN":
            return float(np.min(arr))
        elif m == "SUM":
            return float(np.sum(arr))
        elif m == "COUNT":
            return float(len(arr))
        else:
            return float(np.mean(arr))

    def _compare(
        self,
        value: float,
        operator: str,
        threshold: float,
        tolerance: float = 0.0,
    ) -> bool:
        """Apply comparison operator."""
        op = operator.upper()
        if op == "LTE":
            return value <= (threshold + tolerance)
        elif op == "GTE":
            return value >= (threshold - tolerance)
        elif op == "EQ":
            return abs(value - threshold) <= tolerance
        elif op == "NEQ":
            return abs(value - threshold) > tolerance
        elif op == "LT":
            return value < threshold
        elif op == "GT":
            return value > threshold
        else:
            logger.warning(f"Unknown operator: {operator}, defaulting to LTE")
            return value <= threshold

    def _calculate_confidence(
        self,
        sample_adequacy: float,
        measurement_certainty: float,
        freshness_score: float,
    ) -> float:
        """Calculate confidence as geometric mean of factors."""
        factors = [sample_adequacy, measurement_certainty, freshness_score]
        # Filter out zeros to prevent log(0)
        factors = [max(f, 1e-10) for f in factors]
        log_sum = sum(math.log(f) for f in factors)
        return math.exp(log_sum / len(factors))
