# ADR-004 — Security Layer as a First-Class Domain

Status: Accepted  
Release: v0.3.0-alpha

## Context

Security cannot be represented only as an LLM prompt or a checklist.

STEH needs structured security artifacts that can be persisted, evaluated by deterministic policies and audited.

## Decision

Introduce:

- `SecurityAgent`
- `ThreatModel`
- `SecurityFinding`
- `Severity`
- `FindingStatus`
- `SecurityReviewResult`
- persistent `security_findings`
- deterministic Security Gates

STRIDE is used as a threat-modeling lens, not as proof of security.

## Security Gate semantics

```text
CRITICAL finding
      |
      v
    BLOCK

HIGH finding
      |
      v
HUMAN_REVIEW

MEDIUM / LOW
      |
      v
ALLOW WITH EVIDENCE
```

Threat Model and Security Requirements are mandatory artifacts.

## Consequence

The system now distinguishes:

```text
AI-generated security analysis
            |
            v
Structured Security Evidence
            |
            v
Deterministic Policy Evaluation
            |
            v
BLOCK / HUMAN REVIEW / ALLOW
```
