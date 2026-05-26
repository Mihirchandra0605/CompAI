"""LLM provider abstraction — decouples agents from specific LLM implementations."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class LLMResponse(BaseModel):
    """Standardized LLM response."""

    content: str
    model: str
    usage: dict[str, int] = {}
    finish_reason: str | None = None


class AbstractLLMProvider(ABC):
    """Abstract LLM interface. Implementations handle provider-specific details."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        response_format: dict[str, Any] | None = None,
    ) -> LLMResponse:
        """Generate a completion from the LLM."""
        ...

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        output_schema: dict[str, Any],
        system_prompt: str | None = None,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        """Generate a structured (JSON) output from the LLM."""
        ...


class MockLLMProvider(AbstractLLMProvider):
    """Mock LLM for testing and development without API keys."""

    def __init__(self, responses: dict[str, str] | None = None):
        self._responses = responses or {}
        self._call_count = 0

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        response_format: dict[str, Any] | None = None,
    ) -> LLMResponse:
        self._call_count += 1
        # Check for configured responses
        for key, response in self._responses.items():
            if key in prompt:
                return LLMResponse(content=response, model="mock", usage={})

        return LLMResponse(
            content="Mock LLM response",
            model="mock",
            usage={"prompt_tokens": 0, "completion_tokens": 0},
        )

    async def generate_structured(
        self,
        prompt: str,
        output_schema: dict[str, Any],
        system_prompt: str | None = None,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        self._call_count += 1
        return {}
