"""Probe Agent — orchestrates probe execution, evidence collection, and validation."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from agents.base import BaseComplianceAgent
from contracts.probe_contract import ProbeDefinition, ProbeInput, ProbeOutput, ProbeResult
from explainability.collector import TraceCollector
from explainability.trace import TraceNodeType
from probes.base import ExecutionContext, ProbeDefinitionModel
from probes.dispatcher import ProbeDispatcher

logger = logging.getLogger(__name__)


class ProbeAgent(BaseComplianceAgent[ProbeInput, ProbeOutput]):
    """Orchestrates probe execution and evidence collection."""

    name = "probe_agent"

    def __init__(self, dispatcher: ProbeDispatcher, slm_service=None):
        super().__init__(slm_service=slm_service)
        self._dispatcher = dispatcher

    async def execute(self, input: ProbeInput, trace: TraceCollector) -> ProbeOutput:
        """Execute all probe definitions and collect evidence."""
        context = ExecutionContext(
            run_id=input.metadata.run_id,
            timeout_seconds=30.0,
            max_retries=3,
        )

        # Convert contract definitions to internal models
        definitions = [
            ProbeDefinitionModel(
                probe_id=pd.probe_id,
                derived_from=pd.derived_from,
                probe_type=pd.probe_type,
                config=pd.config,
            )
            for pd in input.probe_definitions
        ]

        async with trace.span(
            f"executing_{len(definitions)}_probes",
            TraceNodeType.TOOL_USE,
            agent_name=self.name,
        ) as span:
            span.set_input(f"{len(definitions)} probes to execute")

            # Dispatch all probes
            execution_results = await self._dispatcher.dispatch_all(definitions, context)

            # Collect results
            probe_results: list[ProbeResult] = []
            failed_probes: list[str] = []
            total_evidence = 0

            for result in execution_results:
                if result.success and result.evidence_batch:
                    probe_results.append(
                        ProbeResult(
                            probe_id=result.probe_id,
                            evidence_id=result.evidence_batch.batch_id,
                            status="success",
                            data={
                                "records": [
                                    r.model_dump() for r in result.evidence_batch.records
                                ],
                                "sample_count": result.evidence_batch.sample_count,
                            },
                            sample_count=result.evidence_batch.sample_count,
                            collection_window={
                                "start": str(result.evidence_batch.collection_window_start),
                                "end": str(result.evidence_batch.collection_window_end),
                            }
                            if result.evidence_batch.collection_window_start
                            else None,
                            duration_ms=result.duration_ms,
                        )
                    )
                    total_evidence += result.evidence_batch.sample_count
                else:
                    probe_results.append(
                        ProbeResult(
                            probe_id=result.probe_id,
                            evidence_id=f"ev:failed:{uuid.uuid4().hex[:8]}",
                            status="failed",
                            error=result.error,
                            duration_ms=result.duration_ms,
                        )
                    )
                    failed_probes.append(result.probe_id)

            span.set_output(
                f"{len(probe_results)} results, {total_evidence} evidence items, "
                f"{len(failed_probes)} failures"
            )
            span.set_confidence(
                1.0 - (len(failed_probes) / max(len(definitions), 1)),
                ["probe_success_rate"],
            )

        return ProbeOutput(
            metadata=input.metadata,
            success=len(failed_probes) == 0,
            probe_results=probe_results,
            total_evidence_items=total_evidence,
            failed_probes=failed_probes,
            state_updates={
                "evidence_collection": [r.model_dump() for r in probe_results],
            },
        )
