"""LangSmith tracing integration hooks."""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Any, Generator

logger = logging.getLogger(__name__)


class LangSmithTracer:
    """
    LangSmith integration for observability.

    When LANGSMITH_API_KEY is set, traces agent and tool executions
    to the LangSmith dashboard for debugging and monitoring.
    """

    def __init__(self) -> None:
        self._enabled = bool(os.environ.get("LANGSMITH_API_KEY"))
        self._project = os.environ.get("LANGSMITH_PROJECT", "compliai-v1")

        if self._enabled:
            try:
                from langsmith import Client
                self._client = Client()
                logger.info(f"LangSmith tracing enabled (project: {self._project})")
            except ImportError:
                logger.warning("langsmith package not installed, tracing disabled")
                self._enabled = False
        else:
            logger.info("LangSmith tracing disabled (no API key)")

    @property
    def enabled(self) -> bool:
        return self._enabled

    @contextmanager
    def trace_agent(self, agent_name: str, run_id: str) -> Generator[dict[str, Any], None, None]:
        """Context manager for tracing agent execution."""
        metadata: dict[str, Any] = {
            "agent_name": agent_name,
            "run_id": run_id,
        }

        if self._enabled:
            try:
                os.environ.setdefault("LANGCHAIN_PROJECT", self._project)
                os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
            except Exception as e:
                logger.warning(f"LangSmith trace setup failed: {e}")

        try:
            yield metadata
        finally:
            pass

    @contextmanager
    def trace_tool(self, tool_name: str, agent_name: str) -> Generator[dict[str, Any], None, None]:
        """Context manager for tracing tool execution."""
        metadata: dict[str, Any] = {
            "tool_name": tool_name,
            "agent_name": agent_name,
        }
        try:
            yield metadata
        finally:
            pass


# Global singleton
langsmith_tracer = LangSmithTracer()
