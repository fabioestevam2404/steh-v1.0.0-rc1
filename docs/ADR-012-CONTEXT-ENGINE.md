# ADR-012 — Context Engine

## Status

Accepted for Patch 4D.

## Context

The workflow previously derived requirements only from the task request. Agents had no
versioned way to consume project documentation, repository notes, policies, or supplementary
requirements. Passing arbitrary text directly to an LLM would weaken reproducibility,
auditability, privacy, and the prompt-instruction boundary.

## Decision

STEH creates one immutable context snapshot before the Requirements Agent runs. The snapshot is
stored in the LangGraph state and in the task record, so checkpoint resume and bounded rework use
the same material.

The Context Engine:

- validates source identifiers, versions, kinds, priorities, sizes, and metadata;
- rejects duplicate source/version identities;
- orders sources deterministically by priority, identifier, and version;
- enforces per-source, total-token, and source-count budgets;
- normalizes control characters and redacts common secret formats before persistence;
- labels all API-supplied material as `UNTRUSTED`;
- detects common instruction-injection markers and records the signal;
- hashes each stored source, the request, and the complete bundle with SHA-256;
- gives the Requirements Agent an explicit data-only prompt envelope;
- exposes and audits receipts containing provenance and hashes, never raw source content.

`TRUSTED` is reserved for future authenticated connectors that can establish source provenance.
Clients cannot promote API-supplied text to trusted context.

## Consequences

- Agent executions are reproducible against a stable context bundle.
- Human-review resume never refetches or silently changes source material.
- API responses and audit events can prove which snapshot was used without returning raw text.
- Secret redaction and injection detection reduce risk but do not prove input safety.
- The initial implementation uses a deterministic character-to-token estimate. Provider-native
  tokenizers may replace this estimate behind the same contract later.

## Migration

Migration `0008_patch_4d_context_engine` adds the nullable JSON context bundle to existing tasks.
New tasks always receive a bundle, including an empty bundle when no sources are supplied.
