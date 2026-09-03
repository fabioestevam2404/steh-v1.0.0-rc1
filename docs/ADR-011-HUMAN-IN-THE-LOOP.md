# ADR-011 — Durable human-in-the-loop decisions

## Status

Accepted for Patch 4C.

## Context

The security gate could return `HUMAN_REVIEW`, but the workflow terminated and
had no authenticated mechanism to approve, reject or resume the task. Review
identity, justification and expiration were not represented as domain data.

## Decision

High-risk tasks now create a persisted, expiring review request before entering
a LangGraph `interrupt`. A reviewer submits an `APPROVE` or `REJECT` decision to
the task API. The service atomically claims the pending task and resumes the same
checkpoint with a LangGraph `Command`.

Reviewers require the `steh_reviewer` role when authentication is enabled. Every
decision records the reviewer identity, justification and timestamp. Requests
submitted after their deadline resume as `EXPIRED` and are blocked. A task can
be resumed only once; concurrent or repeated decisions receive a conflict.

## Consequences

- Approved tasks continue from security review to test planning without rerunning
  the preceding agents.
- Rejected and expired tasks terminate as blocked.
- Human decisions are queryable through the task response and audit trail.
- PostgreSQL gains a nullable JSON field through migration `0007`.
- Local development receives both user and reviewer roles; production continues
  to enforce JWT roles.
