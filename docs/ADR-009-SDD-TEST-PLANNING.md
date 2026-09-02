# ADR-009 — Specification-driven development and test planning

## Status

Accepted for Patch 4A.

## Context

The RC2 workflow moved directly from requirements to architecture and created a
test artifact only after implementation. Natural-language requirements therefore
lacked stable identifiers, executable acceptance structure and traceability to a
test plan.

## Decision

The workflow now creates two governed artifacts before implementation:

1. A software specification assigns `FR-###` and `NFR-###` identifiers and maps
   them to `AC-###` Given/When/Then scenarios.
2. A test plan maps `TC-###` cases to every specified requirement and includes a
   negative security case.

Deterministic policy gates block progression when an artifact is missing,
malformed or incomplete. Both artifacts are persisted on the task and exposed by
the task API. Implementation receives the approved test plan as an input.

## Consequences

- Architecture and implementation operate on versionable, typed contracts.
- Missing requirement and security-test coverage is detected before code changes.
- PostgreSQL schema gains nullable JSON columns for backward compatibility.
- Human-review behavior remains unchanged; test planning starts only after the
  security gate allows progression.
