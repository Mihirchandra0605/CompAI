"""Confidence propagation model across the compliance pipeline."""

from __future__ import annotations

import math

from pydantic import BaseModel, Field


class ConfidenceContribution(BaseModel):
    """A single agent's contribution to overall confidence."""

    agent_name: str
    stage: str
    raw_confidence: float
    weight: float = 1.0
    factors: list[str] = Field(default_factory=list)


class PropagatedConfidence(BaseModel):
    """
    Aggregated confidence across the entire pipeline.
    Uses weighted geometric mean — a single weak link
    pulls down overall confidence.
    """

    contributions: list[ConfidenceContribution] = Field(default_factory=list)
    overall: float | None = None
    method: str = "weighted_geometric_mean"

    def compute(self) -> float:
        """Compute propagated confidence from all contributions."""
        if not self.contributions:
            return 0.0

        weighted_log_sum = sum(
            c.weight * math.log(max(c.raw_confidence, 1e-10))
            for c in self.contributions
        )
        total_weight = sum(c.weight for c in self.contributions)

        self.overall = (
            math.exp(weighted_log_sum / total_weight) if total_weight > 0 else 0.0
        )
        return self.overall

    def add_contribution(
        self,
        agent_name: str,
        stage: str,
        confidence: float,
        weight: float = 1.0,
        factors: list[str] | None = None,
    ) -> None:
        self.contributions.append(
            ConfidenceContribution(
                agent_name=agent_name,
                stage=stage,
                raw_confidence=confidence,
                weight=weight,
                factors=factors or [],
            )
        )
