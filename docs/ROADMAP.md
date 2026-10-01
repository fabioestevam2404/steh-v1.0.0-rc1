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

## RC3 — Complete workflow and asynchronous execution

Delivered after RC2 and released in `v1.0.0-rc3`:

- Specification/SDD and Given/When/Then criteria
- Test Plan before implementation
- rework loop connected to the graph
- resumable Human-in-the-Loop decisions
- auditable Context Engine
- read-only GitHub Issue Analysis
- read-only GitHub Pull Request Review
- auxiliary, versioned and non-authoritative LLM-as-Judge evaluation
- asynchronous execution with a PostgreSQL job queue and worker (ADR-016)
- correlated structured logs across API, worker and agents
- lazily created settings and database engine, injectable readiness
- acceptance criteria RC-17 to RC-25 with executable gates

## RC4 — Trust and operational hardening

Released in `v1.0.0-rc4`:

- validation fails closed when the workspace lacks the implementation
- bounded job recovery from LangGraph checkpoints (ADR-017)
- versioned agent prompts with pinned hashes in the evidence (ADR-018)
- queue and task metrics read from PostgreSQL; HTTP request counter fixed
- tests for expired-review blocking, negative judge verdicts and task/job
  atomicity under database failure
- acceptance criterion RC-26 (26 criteria, 30 executable gates)

## v1.0.0 — MVP 1.0

Promoted from `v1.0.0-rc4` without functional changes. All 26 acceptance
criteria have release evidence; the `v1.0.0` tag produces its own evidence on
its exact commit.

## After 1.0

Planned work is tracked as new ADRs and minor releases (`1.1.0`, ...), following
`docs/VERSIONING.md`.
