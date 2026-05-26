"""Contract for the Intent Extraction Agent."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .base import AgentInput, AgentOutput


class IntentInput(AgentInput):
    """What the IntentAgent requires."""

    regulation_text: str
    regulation_source: str | None = None
    focus_clauses: list[str] | None = None


class ExtractedIntent(BaseModel):
    """A single extracted compliance intent."""

    intent_id: str
    clause_reference: str
    description: str
    severity: str  # "critical", "major", "minor"
    category: str
    measurable_criteria: list[str]
    target_systems: list[str]
    evidence_requirements: list[str]
    confidence: float


class IntentOutput(AgentOutput):
    """What the IntentAgent produces."""

    intents: list[ExtractedIntent] = Field(default_factory=list)
    regulation_summary: str | None = None
    unprocessed_clauses: list[str] = Field(default_factory=list)
