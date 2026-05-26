"""Abstract persistence for compliance state and execution context."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from domain.compliance_state import ComplianceState
from domain.execution_context import ExecutionContext


class AbstractStateStore(ABC):
    """Abstract persistence interface."""

    @abstractmethod
    async def save_state(self, state: ComplianceState) -> None:
        ...

    @abstractmethod
    async def load_state(self, state_id: str, version: int | None = None) -> ComplianceState | None:
        """Load state. If version is None, load latest."""
        ...

    @abstractmethod
    async def list_versions(self, state_id: str) -> list[int]:
        ...

    @abstractmethod
    async def save_checkpoint(self, run_id: str, node_name: str, state: ComplianceState) -> str:
        """Save a checkpoint. Returns checkpoint_id."""
        ...

    @abstractmethod
    async def load_checkpoint(self, checkpoint_id: str) -> tuple[str, ComplianceState] | None:
        """Load checkpoint. Returns (node_name, state)."""
        ...

    @abstractmethod
    async def save_execution_context(self, ctx: ExecutionContext) -> None:
        ...

    @abstractmethod
    async def load_execution_context(self, run_id: str) -> ExecutionContext | None:
        ...
