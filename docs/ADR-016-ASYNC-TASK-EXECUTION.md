# ADR-016 — Asynchronous task execution with a PostgreSQL job queue

## Status

Accepted for RC3 hardening.

## Context

Four endpoints executed LLM agents inside the HTTP request:

| Endpoint | Work performed in the request |
|---|---|
| `POST /api/v1/tasks` | context, requirements, specification, architecture, security |
| `POST /api/v1/tasks/from-github-issue` | GitHub fetch, issue analysis and the workflow above |
| `POST /api/v1/tasks/{task_id}/human-review` | test planning, implementation, validation, bounded rework and judge |
| `POST /api/v1/tasks/from-github-pull-request` | GitHub fetch and pull-request review over up to 100k patch characters |

In `stub` mode this completes in milliseconds. With `LLM_MODE=openai`, a single request can
take minutes, exceeding client and proxy timeouts while holding an API worker thread. A process
restart during a request left the task in a non-terminal state with no audit trail explaining why.

ADR-001 rejected additional infrastructure (Kafka, Kubernetes) for the MVP, so the solution must
reuse the existing PostgreSQL database.

## Decision

### Accept synchronously, execute asynchronously

Each endpoint performs only fast, deterministic and client-attributable work in the request:

- payload validation and Context Engine construction (`ValueError` becomes `422`);
- GitHub fetch, sanitization and snapshot persistence (existing `403`/`404`/`422`/`502` mapping);
- the atomic human-review claim (existing `409` on duplicate or concurrent decisions).

It then enqueues a job and responds **`202 Accepted`** with the current `TaskResponse`, a
`Location` header pointing to `GET /api/v1/tasks/{task_id}` and `Retry-After: 2`. New tasks are
returned as `QUEUED`; human-review decisions are returned as `RESUMING`.

### Durable queue in PostgreSQL

A new `task_jobs` table (migration `0012`) stores `job_id`, `task_id`, `kind`, `payload`,
`status` (`QUEUED`, `RUNNING`, `SUCCEEDED`, `FAILED`), `attempts`, `locked_by`,
`lease_expires_at`, `last_error` and timestamps.

Job kinds: `EXECUTE_TASK`, `ANALYZE_GITHUB_ISSUE`, `REVIEW_PULL_REQUEST` and
`RESUME_HUMAN_REVIEW`.

**Job payloads never contain raw client or GitHub content.** Context bundles and GitHub
snapshots are sanitized and redacted before persistence (ADR-012 to ADR-014), and the worker reads
them from the task record. Only the human-review resume payload (reviewer, outcome, justification
and decision time) is stored, and it is identical to the already-audited `HUMAN_REVIEW_DECIDED`
event.

### Worker process

`python -m app.worker` runs from the same image as the API. Each iteration:

1. reaps expired leases;
2. claims the oldest queued job with `SELECT ... FOR UPDATE SKIP LOCKED`, so several workers never
   claim the same job;
3. renews the lease from a heartbeat thread while the job runs;
4. marks the job `SUCCEEDED` or `FAILED`. A failed job leaves the task `FAILED` with a
   `TASK_FAILED` event that records only the error type.

Workers scale horizontally by running more replicas. `SIGTERM` stops the loop after the current
job finishes.

### Abandoned jobs fail closed

When a worker stops renewing its lease (crash, OOM or host loss), the next worker marks the job
`FAILED` with `last_error=LeaseExpired` and the task `FAILED` with a `TASK_ABANDONED` event.

Jobs are **not retried automatically**. A retry would repeat LLM calls, agent runs and audit
events, and could apply implementation changes twice. Recovery is an explicit, auditable decision
(re-submit the task). Resuming from the last LangGraph checkpoint is a possible future extension.

### Migrations run once

The container entrypoint runs `alembic upgrade head` only when `RUN_MIGRATIONS` is `true` (the
default, preserving single-container behavior). Docker Compose runs a one-shot `migrate` service
and starts `api` and `worker` with `RUN_MIGRATIONS=false` after it succeeds, so replicas never run
migrations concurrently.

## Consequences

- **Breaking API change:** the four endpoints return `202` instead of `201`/`200`, and the response
  no longer contains workflow artifacts. Clients poll `GET /api/v1/tasks/{task_id}` until a
  terminal or waiting status (`COMPLETED`, `BLOCKED`, `HUMAN_REVIEW`, `REWORK_EXHAUSTED`,
  `FAILED`). No synchronous compatibility mode is provided while the project is a release
  candidate.
- Request latency no longer depends on LLM latency, and API threads are no longer held by agents.
- Every accepted task either reaches a recorded outcome or is explicitly abandoned. Silent stuck
  tasks are no longer possible.
- A worker must run for tasks to progress. `docker compose up` starts one.
- E2E tests drain the queue in-process with `app.worker.run_once`, which keeps them deterministic
  and independent of timing.
- Queue depth, oldest queued age, expired leases and job durations are exported by
  `/metrics`, computed from PostgreSQL at scrape time so they stay correct across API
  and worker replicas (added after RC3).
