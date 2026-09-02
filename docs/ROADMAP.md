# STEH Roadmap

## Delivered foundation

### Alpha 0.1 — Core

- FastAPI, PostgreSQL and LangGraph
- Requirements Agent and Pydantic contracts
- Docker and unit tests

### Alpha 0.2 and 0.2.1 — Architecture and hardening

- Architecture Agent and deterministic gates
- Agent runs, audit events and structured logging
- PostgreSQL checkpointer, Policy-as-Code and Alembic
- integration, E2E and CI foundations

### Alpha 0.3 — Security

- Security Agent and STRIDE threat model
- persisted findings and deterministic security gates
- `HUMAN_REVIEW`, security API and audit trail

### Alpha 0.4 — Controlled implementation

- Implementation Agent
- capability-controlled Tool Gateway
- isolated workspace

### Alpha 0.5 and 0.5.1 — Validation

- Test Agent and non-executing validation
- Semgrep, Gitleaks and Trivy adapters
- containerized Process Runner
- bounded rework decisions and scanner evidence

## Release candidates

### RC1 — Functional baseline

- initial 16-gate release contract
- authentication, metrics and runtime validation

### RC2 — Reproducible evidence

- executable and typed baseline
- full migration roundtrip
- separated unit, integration and E2E gates
- scanner-image build and executable smoke tests
- commit-bound JSON evidence artifact
- release workflow for `rc` tags

## After RC2

- Specification/SDD and Given/When/Then criteria
- Test Plan before implementation
- rework loop connected to the graph
- resumable Human-in-the-Loop decisions
- Context Engine
- GitHub Issue Analysis and PR Review agents
- auxiliary LLM-as-Judge evaluation
