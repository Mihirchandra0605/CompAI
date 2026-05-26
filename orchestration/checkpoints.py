"""HITL checkpoint hooks for the orchestration pipeline."""

from __future__ import annotations

import logging
from typing import Any

from hitl.approval import ApprovalGate, ApprovalRequest, ApprovalStatus, OverridePropagator
from .state import PipelineState

logger = logging.getLogger(__name__)


class CheckpointManager:
    """Manages HITL checkpoints in the pipeline."""

    def __init__(self, hitl_enabled: bool = False) -> None:
        self._enabled = hitl_enabled
        self._pending_requests: dict[str, ApprovalRequest] = {}

    def is_gate_active(self, gate: ApprovalGate) -> bool:
        """Check if a specific approval gate is active."""
        return self._enabled

    async def request_approval(
        self,
        state: PipelineState,
        gate: ApprovalGate,
        artifact_snapshot: dict[str, Any],
    ) -> ApprovalRequest:
        """Create and persist an approval request."""
        request = ApprovalRequest(
            run_id=state["run_id"],
            gate=gate,
            state_version=state["current_state_version"],
            artifact_type=gate.value.replace("post_", "").replace("pre_", ""),
            artifact_snapshot=artifact_snapshot,
            requested_by=state["current_node"],
        )
        self._pending_requests[request.request_id] = request
        logger.info(f"HITL approval requested: {gate.value} (request={request.request_id})")
        return request

    async def process_decision(
        self,
        request_id: str,
        status: ApprovalStatus,
        decided_by: str,
        edits: dict[str, Any] | None = None,
    ) -> PipelineState | None:
        """Process a human decision on a pending request.

        Returns updated pipeline state if edits require recomputation.
        """
        request = self._pending_requests.get(request_id)
        if not request:
            raise ValueError(f"No pending request: {request_id}")

        if status == ApprovalStatus.REJECTED:
            logger.info(f"HITL request {request_id} rejected by {decided_by}")
            return None

        if status == ApprovalStatus.EDIT_REQUESTED and edits:
            # Propagate override — invalidate downstream stages
            edited_stage = request.artifact_type
            invalidated = OverridePropagator.invalidated_stages(edited_stage)
            logger.info(
                f"HITL edit on {edited_stage} invalidates: {invalidated}"
            )

        del self._pending_requests[request_id]
        return None

    def get_pending_requests(self, run_id: str | None = None) -> list[ApprovalRequest]:
        """Get all pending approval requests, optionally filtered by run."""
        requests = list(self._pending_requests.values())
        if run_id:
            requests = [r for r in requests if r.run_id == run_id]
        return requests
