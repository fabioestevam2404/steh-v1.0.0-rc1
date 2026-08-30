# ADR-003 — Alpha 0.2.1 Hardening

Status: Accepted

## Decision

Before adding the Security Agent, STEH must support:

- durable LangGraph checkpoints in PostgreSQL
- policy-as-code loaded from YAML
- explicit agent lifecycle events
- structured JSON logs
- controlled schema migration
- integration and E2E tests
- CI quality gates

## Consequence

Alpha 0.2.1 becomes the durable multi-agent engineering core upon which the Security Layer can safely be added.
