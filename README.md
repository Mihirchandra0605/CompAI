# CompliAI — Autonomous Compliance Engineering Digital Twin

An autonomous multi-agent AI system that converts telecom regulations into executable compliance validation workflows, producing explainable verdicts with full evidence traceability.

---

## Quick Start

```bash
# Navigate to the project
cd compliai

# Install dependencies
pip3 install pydantic pydantic-settings structlog numpy networkx aiosqlite fastapi eval_type_backport

# Generate simulated telecom data
python3 tests/fixtures/generate_latency_logs.py

# Run the end-to-end demo
python3 demo_run.py
```

Or simply:
```bash
make demo
```

---

## Final Executable & Expected Output

The main executable is **`demo_run.py`** — a complete end-to-end compliance pipeline run against the TRAI QoS latency regulation using simulated VoLTE data.

### What It Does

1. Loads TRAI QoS Regulation 2024, §4.2.1 (VoLTE latency requirements)
2. Extracts compliance intents (via Intent Agent)
3. Generates CCL XML (via CCL Generator Agent)
4. Executes probes against 21,248 simulated VoLTE call records
5. Performs deterministic validation (code-driven, NOT LLM-driven)
6. Produces XAI analysis with reasoning chain and confidence scores
7. Generates a full compliance report in markdown

### Expected Result

```
======================================================================
  CompliAI — TRAI QoS Latency Compliance Demo
======================================================================

[1/6] Loaded regulation: TRAI Quality of Service Regulations, 2024...

[2/6] Starting compliance pipeline...

----------------------------------------------------------------------
  PIPELINE RESULTS
----------------------------------------------------------------------

  Run ID:     <uuid>
  Verdict:    non_compliant
  Confidence: 1.00
  Success:    True

  Execution Stages:
    ✓ intent_agent: completed
    ✓ ccl_generator: completed
    ✓ probe_agent: completed (~260ms)
    ✓ validation_engine: completed (~240ms)
    ✓ xai_analyzer: completed
    ✓ document_builder: completed

  Reasoning Trace: 13 nodes

  XAI Analysis:
    Regulation Verdict: NON_COMPLIANT
    Partial Score:      50%

  Reasoning Chain:
    → Regulation requires: Ensure VoLTE call quality by maintaining RTT latency
      within acceptable bounds
    →   Criterion: Average RTT latency ≤ 150ms over 24h window
    →   Criterion: 95th percentile RTT latency ≤ 200ms over 24h window
    → MEAN(rtt_latency_avg) = 145.6 LTE 150.0ms → PASS (margin: +4.4ms)
    → P95(rtt_latency_p95) = 223.6 LTE 200.0ms → FAIL (margin: -23.6ms)
    → Summary: 1 constraints PASS, 1 constraints FAIL

  Recommendations:
    • Constraint con:4.2.1:002: measured value (223.6) exceeds threshold (200.0)
      by 23.6. Investigate root cause.
```

### Generated Compliance Report (Markdown)

The pipeline also produces a full compliance report:

```markdown
# CompliAI Compliance Report

**Regulation**: trai-qos-2024-4.2.1
**Overall Verdict**: ❌ NON_COMPLIANT
**Confidence**: 100%
**Partial Compliance Score**: 50%

## Constraint Results

| # | Constraint    | Threshold | Measured | Result  | Margin |
|---|---------------|-----------|----------|---------|--------|
| 1 | con:4.2.1:001 | LTE 150.0 | 145.6    | ✅ PASS | +4.4   |
| 2 | con:4.2.1:002 | LTE 200.0 | 223.6    | ❌ FAIL | -23.6  |

## Evidence Summary
- probe:run:001: success (21,248 samples)
- probe:run:002: success (21,248 samples)

## Recommendations
- Investigate VoLTE call routing for tail-latency spikes
- Review core network congestion patterns during peak hours
```

---

## V1 Target Scenario

**TRAI Quality of Service Regulations 2024, Chapter IV, §4.2.1**

> "The service provider shall ensure that the average round-trip latency for voice over LTE calls does not exceed 150 milliseconds as measured at the core network boundary, with 95th percentile latency not exceeding 200 milliseconds, measured over any rolling 24-hour window."

### Validation Results

| Constraint | Threshold | Measured | Verdict |
|---|---|---|---|
| Average RTT Latency | ≤ 150ms | 145.6ms | ✅ PASS |
| P95 RTT Latency | ≤ 200ms | 223.6ms | ❌ FAIL |

**Final Verdict: NON_COMPLIANT** — Both constraints must pass (AND logic). P95 latency exceeds threshold by 23.6ms.

---

## Architecture

```
Regulation Text (TRAI QoS 2024, §4.2.1)
  │
  ▼
┌─────────────────────────────────────────────────────────┐
│ 1. Intent Agent       │ Extracts structured intents     │
├───────────────────────┼─────────────────────────────────┤
│ 2. CCL Generator      │ Produces CCL XML                │
├───────────────────────┼─────────────────────────────────┤
│ 3. Mind Mapper        │ Builds NetworkX knowledge graph │
├───────────────────────┼─────────────────────────────────┤
│ 4. Skill Generator    │ Derives probe definitions       │
├───────────────────────┼─────────────────────────────────┤
│ 5. Probe Agent        │ Executes probes, collects data  │
├───────────────────────┼─────────────────────────────────┤
│ 6. XAI Analyzer       │ Aggregates verdicts, explains   │
├───────────────────────┼─────────────────────────────────┤
│ 7. Document Builder   │ Generates compliance report     │
└─────────────────────────────────────────────────────────┘
  │
  ▼
Compliance Verdict + Evidence Lineage + Reasoning Trace + Report
```

### Key Architectural Principles

1. **Agents Reason** — Agents orchestrate workflows and interpret regulations using LLMs
2. **Probes Execute** — Probes are deterministic runtime primitives that collect evidence
3. **Validators Decide** — Compliance verdicts are computed by code (numpy), not LLMs
4. **XAI is Cross-Cutting** — Every agent emits traceability metadata via `TraceCollector`
5. **CCL is the Semantic Core** — XML intermediate representation between regulation and execution

---

## Project Structure (106 files)

```
compliai/
├── demo_run.py                    ← MAIN EXECUTABLE (run this)
├── pyproject.toml                 ← Project definition & dependencies
├── Makefile                       ← Build commands
├── README.md
│
├── agents/                        # The 7 compliance agents
│   ├── base.py                    # BaseComplianceAgent (Generic + Template Method)
│   ├── intent/                    # 1. Intent extraction (LLM-powered)
│   │   ├── agent.py
│   │   └── prompts.py
│   ├── ccl_generator/             # 2. CCL XML generation (LLM-powered)
│   │   ├── agent.py
│   │   └── prompts.py
│   ├── mind_mapper/               # 3. Knowledge graph construction
│   │   └── agent.py
│   ├── skill_generator/           # 4. Probe derivation from CCL
│   │   └── agent.py
│   ├── probe/                     # 5. Probe orchestration
│   │   └── agent.py
│   ├── xai_analyzer/              # 6. Explainability & verdict aggregation
│   │   └── agent.py
│   └── document_builder/          # 7. Report generation
│       └── agent.py
│
├── contracts/                     # Typed I/O boundaries between agents
│   ├── base.py                    # AgentInput, AgentOutput, FailureContract
│   ├── intent_contract.py
│   ├── ccl_contract.py
│   └── probe_contract.py
│
├── domain/                        # Canonical domain model
│   ├── compliance_state.py        # Immutable state with evolve() pattern
│   └── execution_context.py       # Execution lineage tracking
│
├── ccl/                           # Compliance Cognitive Language subsystem
│   ├── schema.xsd                 # Formal XML Schema Definition
│   ├── parser.py                  # XML → Python objects
│   ├── validator.py               # 4-level validation (schema/referential/semantic/execution)
│   ├── builder.py                 # Python objects → XML
│   └── samples/
│       └── trai_qos_latency.xml   # Reference CCL for TRAI QoS
│
├── probes/                        # Probe execution engine
│   ├── base.py                    # BaseProbe, EvidenceBatch, EvidenceRecord
│   ├── registry.py                # ProbeRegistry (type → class mapping)
│   ├── dispatcher.py              # Async dispatcher with semaphore concurrency
│   ├── executors/
│   │   ├── log_scan.py            # LogScanProbe (CSV parsing + filtering)
│   │   └── config_scan.py         # ConfigScanProbe (JSON extraction)
│   └── validation/
│       ├── engine.py              # Deterministic ValidationEngine (numpy)
│       └── semantic.py            # LLM-assisted SemanticValidator
│
├── graph/                         # Knowledge graph layer
│   ├── base.py                    # AbstractGraphBackend interface
│   ├── networkx_backend.py        # NetworkX implementation (V1)
│   └── neo4j_backend.py           # Neo4j stub (future)
│
├── events/                        # Domain event system
│   ├── base.py                    # DomainEvent (immutable, serializable)
│   ├── bus.py                     # AsyncEventBus (in-process, Kafka-ready)
│   └── domain_events.py           # 10 compliance event types
│
├── explainability/                # Cross-cutting XAI architecture
│   ├── trace.py                   # ReasoningTrace, TraceNode (tree structure)
│   ├── collector.py               # TraceCollector (context-manager spans)
│   └── confidence.py              # PropagatedConfidence (weighted geometric mean)
│
├── orchestration/                 # Pipeline workflow engine
│   ├── pipeline.py                # CompliancePipeline (async orchestration)
│   ├── state.py                   # PipelineState TypedDict
│   ├── langgraph_workflow.py      # LangGraph StateGraph skeleton
│   ├── nodes.py                   # Node function definitions
│   ├── edges.py                   # Conditional edge logic
│   └── checkpoints.py             # HITL checkpoint management
│
├── hitl/                          # Human-in-the-loop subsystem
│   └── approval.py               # ApprovalGate, ApprovalRequest, OverridePropagator
│
├── persistence/                   # Pipeline state persistence
│   ├── base.py                    # AbstractStateStore interface
│   └── sqlite_store.py            # SQLite implementation (V1)
│
├── infrastructure/                # Shared infrastructure abstractions
│   ├── llm_provider.py            # AbstractLLMProvider + MockLLMProvider
│   ├── vector_store.py            # AbstractVectorStore (Qdrant-ready)
│   └── storage.py                 # ArtifactStorage
│
├── observability/                 # Logging & tracing
│   ├── logger.py                  # Structured logging (structlog)
│   └── langsmith.py               # LangSmith tracing hooks
│
├── backend/                       # FastAPI application
│   └── app/
│       ├── main.py                # App factory + lifespan
│       ├── config.py              # Pydantic Settings
│       └── api/v1/
│           ├── pipelines.py       # POST /api/v1/pipelines/run
│           └── health.py          # GET /api/v1/health
│
├── frontend/                      # Next.js 14 dashboard
│   ├── package.json
│   └── src/app/
│       ├── page.js                # Dashboard (verdict summary)
│       ├── pipeline/page.js       # Pipeline visualization
│       ├── reports/page.js        # Compliance report viewer
│       └── graph/page.js          # Knowledge graph display
│
├── docker/                        # Docker deployment
│   ├── Dockerfile.backend
│   └── docker-compose.yml
│
├── configs/
│   └── default.yaml               # Application configuration
│
└── tests/
    └── fixtures/
        ├── sample_regulation.txt       # TRAI QoS regulation text
        ├── sample_latency_logs.csv     # 25,000 simulated VoLTE records
        ├── sample_config.json          # Simulated telecom config
        └── generate_latency_logs.py    # Data generation script
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI, Pydantic v2 |
| Orchestration | LangGraph-ready (async pipeline V1) |
| Graph | NetworkX (Neo4j-ready abstraction) |
| Vector | Qdrant abstraction (in-memory V1) |
| Persistence | SQLite via aiosqlite (PostgreSQL-ready) |
| Observability | structlog, LangSmith hooks |
| Frontend | Next.js 14, Tailwind CSS, dark theme |
| Deployment | Docker, docker-compose |

---

## API Usage

```bash
# Start the API server
make serve
# or: python3 -m uvicorn backend.app.main:app --reload --port 8000

# Run a compliance pipeline via API
curl -X POST http://localhost:8000/api/v1/pipelines/run \
  -H "Content-Type: application/json" \
  -d '{
    "regulation_id": "trai-qos-2024-4.2.1",
    "regulation_text": "The service provider shall ensure that the average round-trip latency for voice over LTE calls does not exceed 150 milliseconds..."
  }'
```

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| Immutable state (`evolve()` pattern) | Full audit trail, recomputation from any checkpoint, diff-based changes |
| Typed contracts at agent boundaries | Fail-fast on schema violations, no silent breakage between agents |
| Deterministic validation engine | Compliance verdicts MUST be reproducible — LLMs cannot determine pass/fail for numeric thresholds |
| Cross-cutting explainability | TraceCollector is injected into every agent, not bolted on as a final stage |
| Event-driven architecture | Enables future migration to continuous compliance (realtime digital twin) |
| CCL as intermediate representation | Decouples regulation understanding from probe execution — allows regeneration without code changes |

---

## How the Validation Works (No LLM)

The `ValidationEngine` in `probes/validation/engine.py` performs pure code-based evaluation:

```python
# Simplified flow:
values = extract_numeric_values(evidence_records)    # [138.2, 145.7, 151.3, ...]
aggregated = numpy.mean(values)                       # 145.6
passes = aggregated <= threshold                      # 145.6 <= 150.0 → True
verdict = "PASS" if passes else "FAIL"
```

LLMs are used for:
- Intent extraction (understanding regulation text)
- CCL generation (structuring requirements as XML)
- Semantic validation (non-numeric constraints like "adequate documentation")

LLMs are **never** used for deterministic verdicts.

---

## Future Roadmap

| Version | Capability |
|---|---|
| V1 (current) | Batch pipeline, static probes, single regulation |
| V2 | Webhook-triggered re-evaluation, HITL approval workflow, PostgreSQL persistence |
| V3 | Continuous telemetry streams, real-time drift detection, full digital twin dashboard |
