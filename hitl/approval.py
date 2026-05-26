"""Human-in-the-loop approval workflow primitives."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class ApprovalGate(str, Enum):
    """Named gates where the pipeline can pause for human review."""

    POST_INTENT = "post_intent"
    POST_CCL = "post_ccl"
    POST_GRAPH = "post_graph"
    POST_PROBES = "post_probes"
    PRE_VERDICT = "pre_verdict"
    PRE_REPORT = "pre_report"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EDIT_REQUESTED = "edit_requested"


class ApprovalRequest(BaseModel):
    """A request for human approval at a pipeline gate."""

    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    run_id: str
    gate: ApprovalGate
    state_version: int
    artifact_type: str
    artifact_snapshot: dict
    requested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    requested_by: str
    context: str | None = None


class ApprovalDecision(BaseModel):
    """A human's decision on an approval request."""

    request_id: str
    status: ApprovalStatus
    decided_by: str
    decided_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reason: str | None = None
    edits: dict | None = None

    @property
    def requires_recomputation(self) -> bool:
        return self.status == ApprovalStatus.EDIT_REQUESTED and self.edits is not None


class OverridePropagator:
    """
    Determines which downstream pipeline stages must be re-executed
    when a human edits an artifact.
    """

    STAGE_ORDER = ["intent", "ccl", "graph", "probes", "evidence", "xai", "report"]

    @classmethod
    def invalidated_stages(cls, edited_stage: str) -> list[str]:
        """Return all stages that must be recomputed after an edit."""
        if edited_stage not in cls.STAGE_ORDER:
            return []
        idx = cls.STAGE_ORDER.index(edited_stage)
        return cls.STAGE_ORDER[idx + 1:]

    @classmethod
    def create_resume_point(cls, edited_stage: str, new_state: dict) -> dict:
        """Create new pipeline state clearing invalidated fields."""
        invalidated = cls.invalidated_stages(edited_stage)
        for stage in invalidated:
            new_state.pop(stage, None)
        return new_state
