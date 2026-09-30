# Changelog

## [Unreleased]

---

## [1.0.0-rc3] - 2026-09-30

Everything merged after `v1.0.0-rc2` (PRs #4 to #20). See
`docs/releases/v1.0.0-rc3.md`.

### Changed (BREAKING)
- Task execution is asynchronous (ADR-016). `POST /api/v1/tasks`,
  `/from-github-issue`, `/from-github-pull-request` and
  `/{task_id}/human-review` now return `202 Accepted` with a `Location` header
  and `Retry-After: 2`. New tasks start as `QUEUED`; review decisions return
  `RESUMING`. Clients poll `GET /api/v1/tasks/{task_id}` for artifacts.
  Validation, context, GitHub ingestion and review-claim errors are still
  returned synchronously (`409`, `422`, `403`, `404`, `502`).
- Invalid context sources now return `422` instead of `500`.
- `GET /ready` returns `503` when the database is unavailable (previously an
  unhandled `500`) and receives its session through dependency injection.
- Settings and the database engine are created on first use instead of at
  import: `get_settings()`, `get_engine()`, `get_session_factory()` and
  `new_session()` replace the module-level `settings`, `engine` and
  `SessionLocal` objects.
- Docker Compose runs migrations once in a `migrate` service; the entrypoint
  skips them when `RUN_MIGRATIONS=false`.

### Added
- PostgreSQL job queue (`task_jobs`, migration `0012`) and worker process
  (`python -m app.worker`, `worker` service in Compose): `SKIP LOCKED` claims,
  renewable lease, `TASK_ABANDONED` on lease expiry and no automatic retries.
  Job payloads never contain raw client or GitHub content (ADR-016).
- `QUEUED` task status, `JOB_QUEUED` and `TASK_ABANDONED` audit events,
  `WORKER_POLL_INTERVAL_SECONDS` and `WORKER_LEASE_SECONDS` settings.
- Contextual structured logging: `log_context()` binds `task_id`, `trace_id`
  and `job_id` through `contextvars`, and a logging filter adds them to every
  record in the API and the worker. New log events: `agent_started`,
  `agent_completed` and `agent_failed` (with `duration_ms` and `error_type`),
  `job_queued`, `job_succeeded`, `job_failed` and `task_abandoned`. Error
  messages are never logged, only error types.
- Specification-driven workflow: `FR-###`/`NFR-###` requirements mapped to
  `AC-###` Given/When/Then scenarios, and a `TC-###` test plan created before
  implementation, with gates SPEC-001..003, TRACE-001 and TESTPLAN-001..003
  (ADR-009, PR #4).
- Bounded rework connected to the graph: failed validation returns to the
  Implementation Agent with the failure reasons, up to the configured maximum,
  ending in `REWORK_EXHAUSTED` (ADR-010, PR #6).
- Durable Human-in-the-Loop: expiring review requests, LangGraph `interrupt`
  and checkpoint resume via `POST /api/v1/tasks/{task_id}/human-review`,
  `steh_reviewer` role and single-use decisions (ADR-011, PR #7).
- Auditable Context Engine: immutable, budgeted, hashed and redacted context
  snapshot per task; API-supplied sources are always `UNTRUSTED` (ADR-012, PR #8).
- Read-only GitHub Issue Analysis via `POST /api/v1/tasks/from-github-issue`,
  behind a fail-closed repository allowlist (ADR-013, PR #9).
- Read-only GitHub Pull Request Review via
  `POST /api/v1/tasks/from-github-pull-request`, with deterministic safeguards
  that the agent cannot weaken (ADR-014, PR #10).
- Auxiliary LLM-as-Judge with a versioned rubric (`policies/judge-rubric.yaml`);
  always `authoritative=false` and never changes task status or gates
  (ADR-015, PR #11).
- Migrations `0006` to `0011` (nullable JSON columns on `tasks`).
- Configuration: `AUTH_REVIEWER_ROLE`, `HUMAN_REVIEW_TTL_MINUTES`, `CONTEXT_*`,
  `GITHUB_*` and `JUDGE_*` (see `.env.example`).

### Fixed
- Security E2E workflow aligned with the Specification Agent (PR #5).
- Shortened the Patch 4E Alembic revision identifier (PR #9).
- Removed the unused `init_db` helper that created tables outside Alembic
  (PR #14).
- Shell scripts keep LF line endings on Windows checkouts (`.gitattributes`);
  containers built from a Windows working copy no longer fail to start
  (PR #18).

### Tooling
- Repository formatted with `ruff format`; new gate RC-14B and ruff pinned to
  `>=0.16,<0.17` (PR #16).
- CI no longer triggers on the nonexistent `develop` branch (PR #15).
- Validation evidence and scanner image are named after `VERSION` instead of a
  hard-coded release candidate.

### Documentation
- `docs/HANDOFF.md` with the verified post-RC2 state (PR #12).
- `[Unreleased]` changelog for post-RC2 work (PR #13).
- Git workflow and README aligned with the trunk-based flow (PR #15).
- Acceptance criteria RC-17 to RC-25 with one executable gate each (PR #19).

### Validation
- `scripts/validate_rc.py`: 28 gates, including migration roundtrip to `0012`,
  unit, integration and E2E suites, scanner image and ruff/mypy.
- Evidence for the release commit is produced by the CI and release workflows.

---

## [1.0.0-rc2] - 2026-09-02

### Fixed
- Recovered FastAPI startup and pytest collection.
- Aligned database, API, Pydantic and LangGraph contracts.
- Eliminated all strict mypy and Ruff violations.
- Decoupled unit tests from the PostgreSQL checkpointer.
- Replaced fragile scanner installers with checksummed release artifacts.
- Restored Semgrep compatibility with an explicit setuptools constraint.

### Added
- Full Alembic `head -> base -> head` validation.
- Separated unit, integration and E2E release gates.
- Executable smoke tests for Semgrep, Gitleaks and Trivy.
- Commit-bound JSON validation evidence.
- Health, readiness and operational metrics coverage.
- RC tag validation workflow and Node.js 24-compatible Actions.

### Validation
- Ruff: PASS.
- mypy strict: PASS.
- Unit, integration and E2E tests: PASS.
- PostgreSQL migration roundtrip: PASS.
- Scanner image build and smoke tests: PASS.
- GitHub Actions and RC evidence: PASS.

---

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
