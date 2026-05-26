# CompliAI Probe System Specification

> **Version**: 1.0-draft  
> **Status**: Design specification  
> **Platform**: CompliAI — Compliance Engineering Digital Twin  

---

## Table of Contents

1. [Probe Philosophy & Runtime Goals](#1-probe-philosophy--runtime-goals)
2. [Probe Ontology](#2-probe-ontology)
3. [Probe Lifecycle](#3-probe-lifecycle)
4. [Probe Taxonomy](#4-probe-taxonomy)
5. [Probe Execution Architecture](#5-probe-execution-architecture)
6. [Evidence Model](#6-evidence-model)
7. [Validation Engine Design](#7-validation-engine-design)
8. [Deterministic vs Semantic Validation](#8-deterministic-vs-semantic-validation)
9. [Probe Registry Architecture](#9-probe-registry-architecture)
10. [Async Execution Model](#10-async-execution-model)
11. [Retry & Recovery Semantics](#11-retry--recovery-semantics)
12. [Confidence & Evidence Quality](#12-confidence--evidence-quality)
13. [Explainability Integration](#13-explainability-integration)
14. [Event Integration](#14-event-integration)
15. [Telemetry Evolution Path](#15-telemetry-evolution-path)
16. [Plugin Architecture](#16-plugin-architecture)
17. [Probe Contracts & Interfaces](#17-probe-contracts--interfaces)
18. [Execution Walkthrough](#18-execution-walkthrough)
19. [Repo Structure & Core Files](#19-repo-structure--core-files)
20. [Future Scalability Design](#20-future-scalability)

---

## 1. Probe Philosophy & Runtime Goals

### What a Probe Is
A probe is the **runtime execution primitive** of the CompliAI platform. While agents perform high-level reasoning and orchestration, probes perform deterministic mechanical tasks to interact with the target systems (reading logs, parsing configs, hitting APIs). Probes are the sensory organs of the Compliance Digital Twin.

### Why Probes Exist Separately from Agents
Agents use LLMs, operate non-deterministically, and orchestrate workflows. **Probes must be 100% deterministic, repeatable, and fast.** Isolating probes from agents ensures that:
- Code accessing sensitive infrastructure is strictly controlled and sandboxed.
- Validation logic is purely deterministic and not subject to LLM hallucinations.
- The same probe can be executed thousands of times continuously without invoking expensive AI models.

### Evidence Isolation
Evidence collection is strictly isolated from evaluation. A probe's primary job is to collect and normalize evidence. Only after evidence is collected and normalized does the validation engine evaluate it against CCL constraints. This prevents probes from "baking in" evaluation logic and preserves explainable reasoning chains.

---

## 2. Probe Ontology

| Primitive | Meaning & Purpose | Lifecycle Role |
|-----------|-------------------|----------------|
| **ProbeDefinition** | Executable instruction derived from CCL `ProbeStrategy`. Defines exactly what tool to use and how to configure it. | Created by SkillGenerator, consumed by ProbeRunner. |
| **ProbeExecution** | An instantiation of a ProbeDefinition running against a specific target at a specific time. | Tracks execution state (running, completed, failed). |
| **EvidenceArtifact** | Raw data collected by a probe (e.g., a raw CSV file, a JSON config snippet). | Ephemeral or persisted storage of system state. |
| **EvidenceBatch** | Normalized, typed records derived from EvidenceArtifacts, ready for evaluation. | Passed to the Validation Engine. |
| **ValidationResult** | The output of evaluating an EvidenceBatch against a ValidationCondition. | Yields a ComplianceDecision. |
| **ProbeCapability** | A declaration of what a probe class can do (e.g., "can parse XML", "can SSH"). | Used by the ProbeRegistry to match ProbeStrategies to implementations. |
| **ProbeTarget** | The specific endpoint, file, or system being queried. | Bound at runtime from CCL TargetSystem. |
| **ExecutionContext** | The environment, credentials, and constraints for the probe run. | Injected into the probe at execution. |
| **ProbeMetadata** | Telemetry about the probe run (duration, data volume). | Emitted for observability. |
| **ConfidenceFactor** | A dimension scoring the reliability of the evidence (e.g., freshness, sample size). | Modifies the overall confidence of the ComplianceDecision. |
| **FailureReason** | Typed error (transient vs permanent) when a probe fails. | Drives retry and recovery logic. |

---

## 3. Probe Lifecycle

The probe lifecycle defines the state machine of an execution:

```
REGISTERED (Probe class is loaded in ProbeRegistry)
       │
PLANNED (ProbeDefinition is derived from CCL)
       │
DISPATCHED (Runner picks up ProbeDefinition)
       │
EXECUTING (Probe accesses TargetSystem)
       │
COLLECTING (EvidenceArtifact is fetched)
       │
NORMALIZING (Artifact is transformed to EvidenceBatch)
       │
VALIDATING (Evidence is checked against ValidationCondition)
       │
   ┌───┴───┐
   │       │
COMPLETED FAILED ──► RETRYING (if transient)
```

**Persistence Points:**
- `ProbeDefinition` is persisted as part of the compliance run plan.
- `EvidenceArtifact` is persisted in object storage (for auditability).
- `EvidenceBatch` and `ValidationResult` are appended to the ComplianceState.

---

## 4. Probe Taxonomy

| Category | Input / Execution Semantics | Evidence Type | Confidence |
|----------|-----------------------------|---------------|------------|
| **LogScanProbe** | File paths, regex, aggregation windows | Time-series metrics | High (if enough samples) |
| **ConfigScanProbe** | Config file, JSONPath/XPath | Key-value properties | High |
| **MetricProbe** | Prometheus/Datadog API queries | Aggregated metrics | High |
| **SemanticDocumentProbe** | PDF/Word docs, semantic search queries | Text snippets | Medium (LLM interpretation) |
| **APIProbe** | REST/GraphQL endpoints, Auth contexts | JSON payloads | High |
| **TelemetryProbe** | (Future) Kafka topics, streaming endpoints | Continuous events | High (realtime) |
| **ManualReviewProbe** | HITL form, instructions | Human attestation | High (human authority) |

---

## 5. Probe Execution Architecture

For V1, the architecture is lightweight, leveraging standard Python `asyncio`. No Kafka or Kubernetes required yet.

**Components:**
1. **ProbeDispatcher**: Receives a list of `ProbeDefinition`s and schedules them.
2. **AsyncProbeRunner**: A worker that executes a specific `ProbeDefinition` within an `asyncio.Task`.
3. **ExecutionQueue**: An in-memory `asyncio.Queue` for managing concurrency limits.
4. **Tool/Adapter Layer**: Probes do not implement SSH or HTTP directly; they use shared, mockable tools.

**Execution Flow:**
- The `ProbeAgent` submits definitions to the `ProbeDispatcher`.
- The Dispatcher places them in the ExecutionQueue.
- Runner tasks pull from the queue, invoke the specific probe implementation, and return `ProbeExecutionResult`s.

---

## 6. Evidence Model

Evidence must be decoupled from the probe that collected it. 

### Artifact vs. Normalized
- **Raw EvidenceArtifact**: The raw CSV file `/var/log/volte/rtt.csv`. Kept for audit and deep debugging.
- **Normalized EvidenceBatch**: The structured representation: `[{"timestamp": "...", "value": 142.3, "metric": "avg_rtt"}]`.
- **Derived Evidence**: Statistical aggregations (e.g., `mean = 142.3ms`).

### Lineage
Every `EvidenceBatch` includes a `lineage` block containing:
- `collected_by`: ID of the ProbeExecution
- `source`: Reference to the TargetSystem
- `timestamp`: Collection time

---

## 7. Validation Engine Design

The Validation Engine sits *after* normalization. It takes an `EvidenceBatch` and a CCL `ValidationCondition`.

**Threshold Evaluation:**
- **Operators**: EQ, NEQ, GT, GTE, LT, LTE, IN_RANGE, CONTAINS.
- **Aggregations**: Mean, Median, Min, Max, P95, P99, Count.

**Aggregation Logic:**
1. Filter evidence by time window.
2. Ensure `min-samples` threshold is met.
3. Apply aggregation function to EvidenceBatch.
4. Compare aggregated value against the threshold using the operator.

**Outputs:**
Produces a `ValidationResult` (PASS, FAIL, INSUFFICIENT_EVIDENCE) and a Base Confidence score.

---

## 8. Deterministic vs Semantic Validation

**CRITICAL RULE:** LLMs must NOT directly determine compliance verdicts for deterministic constraints.

### Deterministic Path (Code-driven)
- **Input:** Metric data, config booleans.
- **Engine:** Python logical operators (e.g., `value <= 150`).
- **Confidence:** Derived purely from data quality and sample size.

### Semantic Path (LLM-assisted)
- **Input:** Text policies, unstructured documents.
- **Engine:** The `SemanticDocumentProbe` retrieves the relevant text. The Validation Engine uses an LLM to evaluate if the text satisfies the CCL semantic predicate (e.g., "Does this text mandate password rotation?").
- **Confidence:** Depends heavily on LLM certainty and context relevance.

*Hybrid approach:* Even in semantic validation, the LLM outputs structured reasoning, which is then mapped to a deterministic PASS/FAIL verdict by the engine.

---

## 9. Probe Registry Architecture

The `ProbeRegistry` decouples the CCL derivation from the concrete Python classes.

**Responsibilities:**
- Maps CCL `probe_type` (e.g., `LOG_SCAN`) to a Python class (e.g., `LogScanProbe`).
- Validates that a `ProbeDefinition` has the required configuration for the matched class.
- Will serve as the entry point for dynamically loaded plugins in future versions.

```python
class ProbeRegistry:
    def register(self, probe_type: str, probe_class: Type[BaseProbe]): ...
    def get_probe(self, definition: ProbeDefinition) -> BaseProbe: ...
```

---

## 10. Async Execution Model

Why Async? Probes are heavily I/O bound (reading files, making HTTP requests). 
- Using `asyncio` allows hundreds of probes to run concurrently in a single thread without blocking.
- `asyncio.gather` is used to execute the full batch of probes required for a regulation simultaneously.
- **Timeouts:** Every `ProbeExecution` is wrapped in `asyncio.wait_for` to prevent hanging on unresponsive TargetSystems.
- **Cancellation:** If the parent pipeline is cancelled (e.g., by HITL), pending probe tasks are cleanly cancelled.

---

## 11. Retry & Recovery Semantics

Probes classify failures to determine recovery:

| Failure | Classification | Action | Example |
|---------|----------------|--------|---------|
| Network timeout | Transient | Retry with exp. backoff | API rate limit, dropped SSH |
| File not found | Permanent | Fail immediately | Config file moved |
| Parse error | Permanent | Fail immediately | JSON config is malformed |
| Missing samples | Data Deficiency | Yield INSUFFICIENT_EVIDENCE | Log rotation cleared old data |

The `ProbeDispatcher` handles automatic retries for Transient failures up to a `max_retries` limit defined in the ExecutionContext.

---

## 12. Confidence & Evidence Quality

Validation Engine calculates confidence based on multiple factors (`ConfidenceFactor`):

1. **Freshness Score**: `1.0` if collected just now, decaying if older cached evidence is used.
2. **Sample Adequacy**: `min(1.0, current_samples / required_samples)`.
3. **Measurement Certainty**: `1.0` for deterministic data, `< 1.0` for semantic/LLM evaluations based on logprobs or reasoning strength.
4. **Probe Reliability**: Base confidence of the probe type (e.g., direct database query = 0.99, scraping HTML = 0.85).

*Final Confidence = Geometric Mean of all applied factors.*

---

## 13. Explainability Integration

Probes do not just return data; they return **Execution Traces**.

Integrating with the Explainability Subsystem (from the Hardening Doc):
- The `AsyncProbeRunner` wraps execution in a `TraceCollector.span`.
- The probe logs: "Connected to system X", "Found Y records", "Filtered Z records".
- The Validation Engine adds a span: "Aggregated Y records to mean M", "Compared M <= Threshold T".

This ensures the XAI Analyzer agent can construct the exact derivation of *how* the data was collected and validated.

---

## 14. Event Integration

The Probe System publishes events to the `AsyncEventBus`:

- `probe.execution.started`: Includes `probe_id` and `target_system`.
- `probe.evidence.collected`: Includes reference to the persisted `EvidenceArtifact`.
- `probe.execution.failed`: Includes `FailureReason`.
- `probe.validation.completed`: Includes `ValidationResult`.

These events allow observability dashboards to track progress in real-time and trigger continuous compliance drift checks in the future.

---

## 15. Telemetry Evolution Path

**V1 (Static):**
Probes are triggered by the pipeline, reach out to systems (Pull), read static files/APIs, and complete.

**Future (Realtime Digital Twin):**
Probes evolve into long-running streams (Push).
- A `KafkaTelemetryProbe` subscribes to a topic.
- It continuously produces `EvidenceBatch`es.
- The Validation Engine operates on sliding windows (e.g., `Window(24h).mean()`).
- When a threshold is breached, it emits a `compliance.drift.detected` event, triggering the digital twin to re-evaluate the specific CCL clause without a full pipeline run.

---

## 16. Plugin Architecture

To support enterprise scalability, probes must be extensible without modifying core code.
- `probes/plugins/` directory will serve as a drop-in location.
- Using Python's `entry_points` or dynamic module loading, third-party adapters (e.g., `CiscoConfigProbe`, `AWSCloudTrailProbe`) can register themselves with the `ProbeRegistry` at startup.
- Sandboxing: Plugins operate strictly against the `BaseProbe` contract and return normalized `EvidenceBatch`es, preventing custom probes from corrupting the core Validation Engine.

---

## 17. Probe Contracts & Interfaces

```python
# probes/base.py
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

class BaseProbe(ABC):
    probe_type: str
    
    @abstractmethod
    async def execute(self, definition: ProbeDefinition, context: ExecutionContext) -> EvidenceBatch:
        """Connects to TargetSystem, collects EvidenceArtifact, and normalizes to EvidenceBatch."""
        ...

# validation/engine.py
class ValidationEngine:
    async def evaluate(self, evidence: EvidenceBatch, condition: ValidationCondition) -> ValidationResult:
        """Deterministically evaluates normalized evidence against a CCL condition."""
        ...
```

---

## 18. Execution Walkthrough: TRAI QoS Latency

1. **CCL to ProbeDef:** The `SkillGenerator` agent reads the CCL `ProbeStrategy` and emits a `ProbeDefinition` (Type: `LOG_SCAN`, Target: `core_logs`, Filter: `volte`).
2. **Dispatch:** `ProbeAgent` submits this definition to `ProbeDispatcher`.
3. **Execution:** `LogScanProbe.execute()` runs asynchronously. It opens `/var/log/volte/rtt.csv`, reads 24,681 records.
4. **Normalization:** The probe creates an `EvidenceBatch` of floats representing RTTs.
5. **Validation:** The `ValidationEngine` receives the batch and the `ValidationCondition` (`mean <= 150`).
6. **Aggregation:** The engine calculates the mean of the 24,681 records (142.3).
7. **Comparison:** 142.3 <= 150 evaluates to `True`.
8. **Result:** Returns `ValidationResult(PASS, confidence=0.97)` to the `ProbeAgent`.
9. **Traceability:** The trace includes the raw CSV path, the sample count, the mean, and the exact boolean comparison logic.

---

## 19. Repo Structure & Core Files

```
probes/
├── __init__.py
├── base.py                 # BaseProbe, EvidenceBatch, interfaces
├── registry.py             # ProbeRegistry for dynamic lookup
├── dispatcher.py           # Async execution queue and runners
├── executors/              # Concrete probe implementations
│   ├── log_scan.py
│   ├── config_scan.py
│   └── semantic_doc.py
├── validation/             # Validation Engine
│   ├── engine.py           # Core validation logic
│   ├── deterministic.py    # Threshold evaluation
│   └── semantic.py         # LLM-assisted validation wrapper
├── plugins/                # Future custom probes
└── adapters/               # Reusable I/O tools (ssh, http, s3)
```

---

## 20. Future Scalability Design

To evolve into a global, distributed Digital Twin:
- **Distributed Execution:** The `ProbeDispatcher` can be replaced with a Celery or Temporal worker queue. ProbeDefinitions become serialized tasks distributed across a fleet of worker nodes located near the target systems (edge processing).
- **Streaming Telemetry:** Integrating Apache Flink or Spark Structured Streaming into the Validation Engine to evaluate continuous `EvidenceBatch` streams in real-time.
- **Continuous Compliance:** The pipeline becomes entirely event-driven. A config change in the network automatically triggers a `ConfigScanProbe`, re-validates the affected constraint, and updates the Digital Twin dashboard live.
