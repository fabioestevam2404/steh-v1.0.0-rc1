# ADR-006 — Controlled Validation and Bounded Rework

Status: Accepted  
Release: v0.5.0-alpha

## Decision

Generated artifacts are validated without granting the agent shell or host execution.

Alpha 0.5 introduces:
- Python AST syntax validation
- built-in secret scanning
- built-in lightweight SAST
- Test Agent
- deterministic validation gates
- `REWORK_REQUIRED`

## Important boundary

The validator parses and scans generated source. It does **not** execute arbitrary generated code.

External Semgrep, Gitleaks, Trivy and dependency scanners remain integration targets for the next hardening step because invoking them requires a controlled process runner/container sandbox.

## Rework

Alpha 0.5 produces a deterministic `REWORK_REQUIRED` decision. Automatic regeneration is intentionally not unbounded. A future bounded rework controller will enforce maximum attempts and preserve evidence for each attempt.
