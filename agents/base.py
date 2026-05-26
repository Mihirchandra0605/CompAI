"""Abstract base agent with contract enforcement and tracing."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from contracts.base import AgentInput, AgentOutput, ContractSeverity, FailureContract, RetryPolicy
from explainability.collector import TraceCollector

logger = logging.getLogger(__name__)

TInput = TypeVar("TInput", bound=AgentInput)
TOutput = TypeVar("TOutput", bound=AgentOutput)


class BaseComplianceAgent(ABC, Generic[TInput, TOutput]):
    """
    Abstract base for all compliance agents.

    Generic[TInput, TOutput] enforces that every agent
    declares its contract at the type level.
    """

    name: str = "base_agent"
    retry_policy: RetryPolicy = RetryPolicy()

    async def run(self, input: TInput, trace: TraceCollector) -> TOutput | FailureContract:
        """
        Entry point. Validates input, executes, validates output.
        Template Method — subclasses override execute(), not run().
        """
        # 1. Validate input contract
        validation_error = await self.validate_input(input)
        if validation_error:
            return validation_error

        # 2. Execute with tracing
        async with trace.span(
            f"{self.name}.execute", agent_name=self.name
        ) as span:
            try:
                output = await self.execute(input, trace)
                span.set_output(f"success={output.success}")
            except Exception as e:
                logger.error(f"Agent {self.name} failed: {e}")
                span.set_output(f"error: {str(e)}")
                return self._build_failure(e)

        # 3. Validate output contract
        output_error = await self.validate_output(output)
        if output_error:
            return output_error

        return output

    @abstractmethod
    async def execute(self, input: TInput, trace: TraceCollector) -> TOutput:
        """Subclasses implement domain logic here."""
        ...

    async def validate_input(self, input: TInput) -> FailureContract | None:
        """Override for custom input validation beyond schema."""
        return None

    async def validate_output(self, output: TOutput) -> FailureContract | None:
        """Override for custom output validation beyond schema."""
        return None

    def _build_failure(self, error: Exception) -> FailureContract:
        """Build a standardized failure from an exception."""
        return FailureContract(
            agent_name=self.name,
            error_type=type(error).__name__,
            error_message=str(error),
            severity=ContractSeverity.ERROR,
            is_retryable="timeout" in str(error).lower(),
        )
