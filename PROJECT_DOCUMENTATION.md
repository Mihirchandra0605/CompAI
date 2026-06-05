# CompliAI Project Documentation

## 1. Overview

CompliAI is an autonomous multi-agent compliance engineering digital twin that transforms telecom regulation text into executable compliance workflows. It combines LLM-powered regulation extraction with deterministic probe execution, validation, and explainable verdict generation.

The current project focuses on a TRAI QoS latency compliance scenario, ingesting regulation text and simulated VoLTE telemetry to produce a compliance verdict, evidence lineage, reasoning trace, and a markdown audit report.

## 2. Key Goals

- Extract structured compliance intents from natural language regulations.
- Generate a Compliance Cognitive Language (CCL) XML representation.
- Derive probes and validation conditions from the CCL schema.
- Execute probes on telemetry/config data.
- Run deterministic validation on collected evidence.
- Aggregate verdicts and generate explainable reasoning.
- Produce a human-readable compliance report.

## 3. Main Execution Paths

### 3.1 Demo execution

- `demo_run.py` is the primary executable for the end-to-end demo.
- It loads a regulation text file and telemetry logs, sets up infrastructure, runs the pipeline, and saves the results.
- The default scenario uses TRAI QoS regulation text and sample latency logs from `tests/fixtures`.

### 3.2 Web upload backend

- `backend_new/main.py` provides a FastAPI upload endpoint at `/upload`.
- The endpoint stores user-uploaded regulation/log files, runs `demo_run.py`, and returns pipeline results.
- It also exposes `/results` for retrieving the latest saved pipeline output.

### 3.3 Frontend dashboard

- `frontEnd-React/frontend/src/App.jsx` is the React dashboard.
- It uploads files to the backend and renders the pipeline verdict, agent outputs, validation results, report preview, and logs.
- The UI supports regulation, repository, config, log, and security artifact uploads.

## 4. Architecture

The system uses an agent-oriented workflow with a central pipeline orchestrator.

```
Regulation Text
      │
      ▼
Intent Agent → CCL Generator → Mind Mapper → Skill Generator → Probe Agent → Validation Engine → XAI Analyzer → Document Builder
      │
      ▼
Compliance Verdict + Evidence Lineage + Report
```

### Core principles

- **Agents reason**: LLMs are used for regulation understanding and CCL generation.
- **Probes execute**: Evidence collection is deterministic and data-driven.
- **Validators decide**: numeric compliance verdicts are computed by code, not by LLMs.
- **Explainability is cross-cutting**: reasoning traces and confidence metadata are captured throughout.
- **CCL is the semantic core**: CCL decouples regulation understanding from probe execution.

## 5. Component Summary

### Agents

- `agents/intent/agent.py`: extracts structured intents and regulation summary.
- `agents/ccl_generator/agent.py`: converts intents into CCL XML.
- `agents/mind_mapper/agent.py`: builds a knowledge graph from CCL.
- `agents/skill_generator/agent.py`: derives probe definitions and validation conditions.
- `agents/probe/agent.py`: executes probes and collects evidence.
- `agents/xai_analyzer/agent.py`: aggregates verdicts and produces explainable reasoning.
- `agents/document_builder/agent.py`: compiles the final markdown compliance report.

### Contracts

- `contracts/base.py`: defines generic agent input/output models.
- `contracts/intent_contract.py`: intent extraction contract and models.
- `contracts/ccl_contract.py`: CCL generation contract.
- `contracts/probe_contract.py`: probe definitions and evidence contract.

### Domain

- `domain/compliance_state.py`: immutable compliance state with `evolve()` semantics.
- `domain/execution_context.py`: execution lineage and agent run metadata.

### CCL subsystem

- `ccl/builder.py`: builds a structured CCL XML representation.
- `ccl/parser.py`: parses CCL XML into domain objects.
- `ccl/validator.py`: validates CCL schema, referential integrity, and semantic correctness.
- `ccl/schema.xsd`: formal schema for Compliance Cognitive Language.

### Probes

- `probes/base.py`: probe model and evidence record definition.
- `probes/registry.py`: probe type registry.
- `probes/dispatcher.py`: asynchronous probe execution with concurrency control.
- `probes/executors/log_scan.py`: log scanning probe for telemetry data.
- `probes/executors/config_scan.py`: config scanning probe for JSON/YAML artifacts.
- `probes/validation/engine.py`: deterministic validation logic.
- `probes/validation/semantic.py`: semantic validation helper for non-numeric evidence.

### Knowledge graph

- `graph/base.py`: abstract graph backend interface.
- `graph/networkx_backend.py`: NetworkX implementation used in the demo.
- `graph/neo4j_backend.py`: stub for future Neo4j support.

### Events and observability

- `events/bus.py`: asynchronous event bus.
- `events/domain_events.py`: domain-specific event definitions.
- `explainability/trace.py`: reasoning trace representation.
- `explainability/collector.py`: trace collector and span instrumentation.
- `explainability/confidence.py`: confidence aggregation logic.

### Orchestration

- `orchestration/pipeline.py`: central pipeline orchestration.
- `orchestration/state.py`: typed pipeline state definition.
- `orchestration/langgraph_workflow.py`: skeleton for LangGraph integration.
- `orchestration/nodes.py`: node wrapper definitions.
- `orchestration/edges.py`: conditional transition logic.
- `orchestration/checkpoints.py`: human-in-the-loop checkpoint management.

### Infrastructure

- `infrastructure/llm_provider.py`: LLM provider abstraction and structured output support.
- `infrastructure/vector_store.py`: vector store abstraction and RAG interface.
- `infrastructure/storage.py`: artifact storage utilities.

### Persistence

- `persistence/base.py`: state store abstraction.
- `persistence/sqlite_store.py`: SQLite-backed state persistence.

### Backend API

- `backend_new/main.py`: upload backend for the React frontend.
- Handles file uploads, saves session data, runs the demo pipeline, and returns results.
- Exposes CORS and health endpoints.

### Frontend

- `frontEnd-React/frontend/src/App.jsx`: dashboard entry point.
- `frontEnd-React/frontend/src/components/UploadCard.jsx`: file upload UI.
- `frontEnd-React/frontend/src/components/StatusMessage.jsx`: result/status display.

## 6. Running the Project

### Python dependencies

Install required backend dependencies (from `README.md`):

```bash
pip3 install pydantic pydantic-settings structlog numpy networkx aiosqlite fastapi eval_type_backport
```

### Generate sample data

```bash
python3 tests/fixtures/generate_latency_logs.py
```

### Run the end-to-end demo

```bash
python3 demo_run.py
```

### Run the frontend/backend web flow

1. Start backend:
   - `uvicorn backend_new.main:app --reload --port 8000`
2. Start frontend:
   - `cd frontEnd-React/frontend`
   - `npm run dev`
3. Visit the UI at `localhost:5173` and upload files.

## 7. Expected Outputs

- Console pipeline run with a compliance verdict and reasoning chain.
- `pipeline_output.json` in `backend_new/` when executing via the upload backend.
- Agent output snapshots, validation result tables, and generated markdown report in the frontend UI.

## 8. Sample Use Case

The demo is tailored for:

- TRAI QoS latency regulation analysis.
- Extracting average and percentile latency obligations.
- Simulating probe execution over VoLTE telemetry.
- Verifying `average RTT ≤ 150ms` and `95th percentile RTT ≤ 200ms`.

## 9. Design Notes

- The pipeline uses a hybrid LLM + deterministic design.
- LLMs are used for extraction and semantic understanding, not for final rule verdicts.
- The system is built for auditability: each agent stage emits trace and event metadata.
- The CCL XML layer acts as the contract between regulation understanding and execution.

## 10. Recommended Next Steps

- Add more concrete tests for the agent outputs and pipeline results.
- Expand probe coverage beyond log scanning.
- Improve vector store / RAG retrieval for regulation context.
- Add detailed API docs for backend endpoints.
- Add sample regulation and telemetry data for additional telecom scenarios.

## 11. File Locations to Know

- `demo_run.py`: top-level demo orchestrator
- `backend_new/main.py`: React upload backend
- `agents/`: LLM-driven compliance stages
- `orchestration/pipeline.py`: pipeline execution flow
- `ccl/`: compliance XML model and validation
- `probes/`: evidence collection and validation
- `frontEnd-React/frontend/src/App.jsx`: dashboard UI

## 12. Contact / Ownership

This document was generated from the existing project README and codebase to provide a consolidated reference for architecture, execution, and components.
