"""Probe Registry — maps probe types to implementations."""

from __future__ import annotations

import logging
from typing import Type

from .base import BaseProbe, ProbeDefinitionModel

logger = logging.getLogger(__name__)


class ProbeRegistry:
    """Registry of available probe implementations."""

    def __init__(self) -> None:
        self._probes: dict[str, Type[BaseProbe]] = {}

    def register(self, probe_type: str, probe_class: Type[BaseProbe]) -> None:
        """Register a probe implementation for a given type."""
        self._probes[probe_type] = probe_class
        logger.info(f"Registered probe: {probe_type} -> {probe_class.__name__}")

    def get_probe(self, definition: ProbeDefinitionModel) -> BaseProbe:
        """Get a probe instance for the given definition."""
        probe_class = self._probes.get(definition.probe_type.upper())
        if not probe_class:
            raise KeyError(
                f"No probe registered for type '{definition.probe_type}'. "
                f"Available: {list(self._probes.keys())}"
            )
        return probe_class()

    def list_types(self) -> list[str]:
        """List all registered probe types."""
        return list(self._probes.keys())
