# ADR-010 — Controlled validation rework

## Status

Accepted for Patch 4B.

## Context

RC2 could classify validation as `REWORK_REQUIRED`, and a bounded
`ReworkController` already existed, but `validation_gate` always terminated the
LangGraph execution. The stored `rework_decision` field was therefore not
populated by the primary workflow.

## Decision

Failed validation now creates a deterministic rework decision from the failed
quality gates. When automatic rework is enabled and attempts remain, the graph
returns to the Implementation Agent with the failure reasons. Validation then
runs again on the revised implementation.

The configured maximum of two attempts includes the initial implementation and
one automatic rework. A second failed validation terminates with
`REWORK_EXHAUSTED`; successful validation terminates with `COMPLETED`.

Every decision is added to workflow evidence and rework history. The latest
decision and attempt count are persisted on the task, while all decisions become
audit events.

## Consequences

- Validation can recover automatically without an unbounded graph cycle.
- Implementation receives explicit rework reasons.
- Exhaustion is distinguishable from a policy block or execution failure.
- Operators can reconstruct every attempted correction from audit evidence.
