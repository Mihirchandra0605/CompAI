"""Compliance domain events — the vocabulary of system state changes."""

from .base import DomainEvent


class RegulationIngested(DomainEvent):
    event_type: str = "regulation.ingested"


class IntentsExtracted(DomainEvent):
    event_type: str = "compliance.intents.extracted"


class CCLGenerated(DomainEvent):
    event_type: str = "compliance.ccl.generated"


class ProbesCompleted(DomainEvent):
    event_type: str = "compliance.probes.completed"


class EvidenceCollected(DomainEvent):
    event_type: str = "compliance.evidence.collected"


class ValidationCompleted(DomainEvent):
    event_type: str = "compliance.validation.completed"


class VerdictDetermined(DomainEvent):
    event_type: str = "compliance.verdict.determined"


class PipelineStarted(DomainEvent):
    event_type: str = "pipeline.started"


class PipelineCompleted(DomainEvent):
    event_type: str = "pipeline.completed"


class PipelineFailed(DomainEvent):
    event_type: str = "pipeline.failed"
