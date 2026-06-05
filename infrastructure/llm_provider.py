"""LLM provider abstraction — decouples agents from specific LLM implementations."""

from __future__ import annotations

import json
import logging
import os
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)


def _extract_json_payload(content: str) -> str | None:
    """Extract the first JSON object or array from model output."""
    content = content.strip()

    if content.startswith("```"):
        # Remove markdown fences if present
        lines = content.splitlines()
        if len(lines) >= 3 and lines[-1].strip().startswith("```"):
            content = "\n".join(lines[1:-1]).strip()

    # Remove any leading text before actual JSON
    first_json_start = min(
        [idx for idx in (content.find('{'), content.find('[')) if idx != -1] or [len(content)]
    )
    content = content[first_json_start:]

    if not content or content[0] not in '{[':
        return None

    opening = content[0]
    closing = '}' if opening == '{' else ']'
    depth = 0
    in_string = False
    escaped = False

    for idx, ch in enumerate(content):
        if in_string:
            if escaped:
                escaped = False
            elif ch == '\\':
                escaped = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
        elif ch == opening:
            depth += 1
        elif ch == closing:
            depth -= 1
            if depth == 0:
                return content[: idx + 1].strip()

    return None


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


class OpenAILLMProvider(AbstractLLMProvider):
    """OpenAI compatible LLM provider (works with OpenAI, Groq, Together AI, Ollama, etc.)."""

    def __init__(self, model_name: str = "llama3-8b-8192", base_url: str | None = None, api_key: str | None = None):
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError("Please install openai: pip install openai")

        self.model_name = model_name
        
        # Default to Groq if not specified and key exists
        if base_url is None:
            if "GROQ_API_KEY" in os.environ or api_key:
                base_url = "https://api.groq.com/openai/v1"
                api_key = api_key or os.environ.get("GROQ_API_KEY")
            elif "OPENAI_API_KEY" in os.environ:
                base_url = "https://api.openai.com/v1"
                api_key = os.environ.get("OPENAI_API_KEY")
            else:
                # Default to local Ollama if no keys
                base_url = "http://localhost:11434/v1"
                api_key = "ollama"

        self.client = AsyncOpenAI(api_key=api_key or "dummy", base_url=base_url)

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        response_format: dict[str, Any] | None = None,
    ) -> LLMResponse:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        kwargs = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format

        try:
            response = await self.client.chat.completions.create(**kwargs)
            choice = response.choices[0]
            
            usage_dict = {}
            if response.usage:
                usage_dict = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                }

            return LLMResponse(
                content=choice.message.content or "",
                model=response.model,
                usage=usage_dict,
                finish_reason=choice.finish_reason,
            )
        except Exception as e:
            logger.error(f"LLM API Error: {e}")
            raise

    async def generate_structured(
        self,
        prompt: str,
        output_schema: dict[str, Any],
        system_prompt: str | None = None,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        
        # We simulate structured JSON output by appending instructions
        sys_p = system_prompt or "You are a helpful AI."
        sys_p += f"\n\nYou MUST return ONLY valid JSON matching this schema:\n{json.dumps(output_schema, indent=2)}"
        
        resp = await self.generate(
            prompt=prompt,
            system_prompt=sys_p,
            temperature=temperature,
        )
        
        try:
            return json.loads(resp.content)
        except json.JSONDecodeError:
            content = resp.content.strip()
            payload = _extract_json_payload(content)
            if payload:
                try:
                    return json.loads(payload)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse extracted JSON payload: {e}\nPayload: {payload}")

            logger.error(f"Failed to parse structured output; raw content:\n{resp.content}")
            return {}


def get_llm_provider() -> AbstractLLMProvider:
    """Factory to get the configured LLM provider."""
    provider_type = os.environ.get("LLM_PROVIDER", "openai").lower()
    
    if provider_type == "mock":
        return MockLLMProvider()
        
    # Default to OpenAI compatible provider (handles Groq/Ollama/OpenAI via env vars inside)
    model = os.environ.get("LLM_MODEL", "llama3-8b-8192")
    return OpenAILLMProvider(model_name=model)
