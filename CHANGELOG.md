# Changelog

## [1.0.0-rc1] - 2026-08-30

### Fixed
- Agent lifecycle audit now surrounds actual agent execution.

### Added
- JWT authentication and role authorization boundary.
- `/ready` database readiness check.
- `/metrics` operational endpoint.
- Migration roundtrip CI check.
- Formal MVP acceptance criteria.
- RC validation script.
- ADR-008.

---
## [0.5.1-alpha] - 2026-08-30

### Added
- Containerized allowlisted scanner runner.
- Semgrep adapter.
- Gitleaks adapter.
- Trivy adapter.
- CPU, memory, PID and timeout controls.
- Network disabled and workspace read-only.
- Scanner evidence normalization.
- Bounded rework controller (`max_attempts=2`).
- External validation endpoint.
- ADR-007.

---

## [0.5.0-alpha] - 2026-08-30

### Added
- Test Agent.
- Controlled source validator.
- Python AST validation.
- Built-in secret scanning.
- Lightweight SAST scanning.
- Validation evidence and findings.
- TEST-001 and SCAN-001.
- REWORK_REQUIRED workflow state.
- ADR-006.

### Safety
Generated source remains non-executable. Validation uses parsing and static inspection only.

---

## [0.4.0-alpha] - 2026-08-30

### Added
- Implementation Agent.
- Controlled Tool Gateway.
- Capability policy.
- Task-isolated workspace.
- Path traversal protection.
- File count and size limits.
- Explicit denial of shell, subprocess, network and deletion.
- Implementation artifact persistence.
- Implementation Gate.
- ADR-005.

### Security invariant
Generated code is written only into an authorized task workspace and is not executed.

---


## [0.3.0-alpha] - 2026-08-30

### Added
- Security Agent.
- STRIDE-oriented Threat Model.
- Structured Security Findings.
- Severity and Finding Status models.
- Security Review Result.
- Persistent `security_findings`.
- `security_review` and `risk_level` on tasks.
- Security Gate.
- `HUMAN_REVIEW` workflow state.
- Endpoint `/api/v1/tasks/{task_id}/security`.
- Security unit and E2E tests.
- ADR-004.

### Security policy
- CRITICAL -> BLOCK.
- HIGH -> HUMAN_REVIEW.
- Threat Model required.
- Security Requirements required.

### Architecture
```text
Requirements -> Gate
Architecture -> Gate
Security -> Security Gate
              |
              +-- BLOCKED
              +-- HUMAN_REVIEW
              +-- COMPLETED
```

---

## [0.2.1-alpha] - 2026-08-30

### Added
- LangGraph PostgreSQL Checkpointer.
- `thread_id = task_id`.
- Policy Loader lendo `quality-gates.yaml`.
- Lifecycle audit: `AGENT_STARTED`, `AGENT_SUCCEEDED`, `AGENT_FAILED`.
- Structured JSON logging.
- Alembic migrations.
- Integration tests.
- E2E test.
- GitHub Actions CI.

### Changed
- `v0.2.1-alpha` passa a ser a baseline operacional.
- `v0.2.0-alpha` passa a ser release histórica.
- FastAPI usa lifespan para recursos de runtime.
- Policy Engine passa a ser alimentado por configuração versionada.

---

## [0.2.0-alpha] - 2026-08-30

### Added
- Architecture Agent.
- Workflow multiagente.
- Requirements Gate.
- Architecture Gate.
- Persistência de tasks, agent runs e audit events.
- Endpoint `/audit`.
- ADR-002.

### Known limitations
- Sem durable LangGraph checkpointing.
- Policy YAML ainda não conectado ao runtime.
- Sem Alembic.
- Sem integration/E2E.

### Status
Substituída operacionalmente por `v0.2.1-alpha`.

---

## [0.1.0-alpha] - 2026-08-29

### Added
- FastAPI.
- PostgreSQL.
- LangGraph inicial.
- Requirements Agent.
- Pydantic.
- Docker Compose.
- Stub/OpenAI modes.
- Testes unitários.
- ADR-001.

### Status
Release histórica incorporada às versões posteriores.
