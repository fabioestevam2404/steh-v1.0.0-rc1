# Roadmap

## Alpha 0.1 — concluído
- FastAPI
- PostgreSQL
- LangGraph
- Requirements Agent
- contratos Pydantic
- Docker
- unit tests

## Alpha 0.2 — concluído
- Architecture Agent
- Requirements Gate
- Architecture Gate
- Agent Runs
- Audit Events

## Alpha 0.2.1 — baseline
- PostgreSQL LangGraph Checkpointer
- Policy-as-Code
- lifecycle audit
- structured logging
- Alembic
- integration/E2E
- CI

## Alpha 0.3 — concluído

```text
Requirements
    |
Architecture
    |
Security Agent
    +-- Assets
    +-- Trust Boundaries
    +-- STRIDE
    +-- Findings
    +-- Controls
    +-- Residual Risks
    |
Security Gate
    |
APPROVED / BLOCKED / HUMAN REVIEW
```

## Alpha 0.4 — concluído
Implementation Agent + capability-controlled Tool Gateway + isolated workspace.

## Alpha 0.5
Test Agent + SAST + dependency/secret scanning + rework loop.

## MVP 1.0
Trust Layer completo + evidence chain + workflow auditável.


## Alpha 0.3 — Security Layer delivered
- Security Agent
- STRIDE threat model
- Security findings
- severity and status
- deterministic security gates
- HUMAN_REVIEW state
- security persistence
- security API endpoint

## Próximo: Alpha 0.4
Implementation Agent + Tool Gateway + isolated sandbox.

## Alpha 0.5 — concluído
Test Agent + non-executing controlled validation + secret scanning + lightweight SAST + deterministic rework decision.

## Alpha 0.5.1 — concluído
Containerized Process Runner + Semgrep/Gitleaks/Trivy adapters + bounded rework controller + scanner evidence.

## Próximo: MVP 1.0 Release Candidate
Runtime validation, lifecycle audit correction, CI green verification, authentication/authorization boundary, operational observability and release acceptance criteria.


