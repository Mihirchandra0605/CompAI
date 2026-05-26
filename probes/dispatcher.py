"""Probe Dispatcher — schedules and runs probes asynchronously."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from .base import BaseProbe, EvidenceBatch, ExecutionContext, ProbeDefinitionModel
from .registry import ProbeRegistry

logger = logging.getLogger(__name__)


class ProbeExecutionResult:
    """Result of a single probe execution."""

    def __init__(
        self,
        probe_id: str,
        evidence_batch: EvidenceBatch | None = None,
        error: str | None = None,
        duration_ms: float = 0.0,
    ):
        self.probe_id = probe_id
        self.evidence_batch = evidence_batch
        self.error = error
        self.duration_ms = duration_ms
        self.success = evidence_batch is not None and error is None


class ProbeDispatcher:
    """
    Dispatches probe definitions to registered probe implementations.
    Handles concurrency, timeouts, and retries.
    """

    def __init__(
        self,
        registry: ProbeRegistry,
        max_concurrent: int = 10,
        default_timeout: float = 30.0,
    ):
        self._registry = registry
        self._max_concurrent = max_concurrent
        self._default_timeout = default_timeout
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def dispatch_all(
        self,
        definitions: list[ProbeDefinitionModel],
        context: ExecutionContext,
    ) -> list[ProbeExecutionResult]:
        """Dispatch all probe definitions concurrently."""
        tasks = [
            self._execute_with_semaphore(definition, context)
            for definition in definitions
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        execution_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                execution_results.append(
                    ProbeExecutionResult(
                        probe_id=definitions[i].probe_id,
                        error=str(result),
                    )
                )
            else:
                execution_results.append(result)

        return execution_results

    async def _execute_with_semaphore(
        self,
        definition: ProbeDefinitionModel,
        context: ExecutionContext,
    ) -> ProbeExecutionResult:
        """Execute a single probe with concurrency limiting."""
        async with self._semaphore:
            return await self._execute_probe(definition, context)

    async def _execute_probe(
        self,
        definition: ProbeDefinitionModel,
        context: ExecutionContext,
    ) -> ProbeExecutionResult:
        """Execute a single probe with timeout handling."""
        start_time = datetime.now(timezone.utc)
        timeout = definition.timeout_seconds or self._default_timeout

        try:
            probe = self._registry.get_probe(definition)
            evidence_batch = await asyncio.wait_for(
                probe.execute(definition, context),
                timeout=timeout,
            )
            duration = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            logger.info(
                f"Probe {definition.probe_id} completed: "
                f"{evidence_batch.sample_count} samples in {duration:.0f}ms"
            )

            return ProbeExecutionResult(
                probe_id=definition.probe_id,
                evidence_batch=evidence_batch,
                duration_ms=duration,
            )

        except asyncio.TimeoutError:
            duration = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            error = f"Probe timed out after {timeout}s"
            logger.error(f"Probe {definition.probe_id}: {error}")
            return ProbeExecutionResult(
                probe_id=definition.probe_id,
                error=error,
                duration_ms=duration,
            )

        except KeyError as e:
            return ProbeExecutionResult(
                probe_id=definition.probe_id,
                error=f"Probe type not found: {e}",
            )

        except Exception as e:
            duration = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            logger.error(f"Probe {definition.probe_id} failed: {e}")
            return ProbeExecutionResult(
                probe_id=definition.probe_id,
                error=str(e),
                duration_ms=duration,
            )
