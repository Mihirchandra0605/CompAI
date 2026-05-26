"""Contract for the CCL Generator Agent."""

from __future__ import annotations

from pydantic import Field

from .base import AgentInput, AgentOutput
from .intent_contract import ExtractedIntent


class CCLInput(AgentInput):
    """What the CCLGenerator requires."""

    regulation_text: str
    intents: list[ExtractedIntent]
    regulation_id: str
    regulation_title: str | None = None


class CCLOutput(AgentOutput):
    """What the CCLGenerator produces."""

    ccl_xml: str  # The full CCL XML document
    clause_count: int = 0
    constraint_count: int = 0
    probe_strategy_count: int = 0
    validation_errors: list[str] = Field(default_factory=list)
