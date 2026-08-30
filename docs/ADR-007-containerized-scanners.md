# ADR-007 — Containerized External Security Scanners

Status: Accepted  
Release: v0.5.1-alpha

## Decision

External scanners execute only through an allowlisted Docker runner.

Allowed:
- Semgrep
- Gitleaks
- Trivy

Controls:
- `shell=False`
- fixed command templates
- no network
- read-only root filesystem
- read-only workspace mount
- timeout
- memory limit
- CPU limit
- PID limit

The LLM cannot provide arbitrary process arguments.

## Fail-closed behavior

Malformed scanner output or execution failure is preserved as failed evidence and may require rework.

## Rework

`max_attempts = 2`.

Alpha 0.5.1 does not automatically regenerate code. The controller bounds and records rework decisions; remediation remains a separate authorized action.
