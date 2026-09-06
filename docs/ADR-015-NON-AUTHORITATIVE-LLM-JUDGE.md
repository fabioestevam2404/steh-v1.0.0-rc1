# ADR-015: Non-authoritative LLM-as-Judge

## Status

Accepted for Patch 4G.

## Context

STEH benefits from a consistent qualitative review across the artifacts produced by
the engineering workflow. An LLM assessment is probabilistic and cannot replace
tests, scanners, policy decisions, bounded rework or accountable human approval.

## Decision

Run an auxiliary Judge only after the validation gate reports `COMPLETED`. The
Judge evaluates a sanitized and size-bounded snapshot against a versioned rubric.
The application validates complete criterion coverage and calculates weighted
scores and verdicts. Inputs and the rubric are identified by SHA-256 digests.

The persisted artifact always declares `authoritative=false`. It never changes task
status, policy results, scanner findings, rework or human-review decisions. Disabled
or unavailable execution produces a `SKIPPED` or `UNAVAILABLE` artifact while the
deterministic workflow result remains unchanged.

Raw prompts are not persisted. Audit events contain only a receipt with versions,
hashes, status, score and verdict. Model input and output pass through the existing
redaction and suspicious-instruction detection boundary.

## Consequences

- deterministic gates remain the sole automated authority;
- model failure cannot turn a completed task into a failed task;
- evaluations are reproducible by rubric and input identity, but model output may
  still vary in `openai` mode;
- consumers must display Judge results as advisory evidence only.
