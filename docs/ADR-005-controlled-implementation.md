# ADR-005 — Controlled Implementation Layer

Status: Accepted  
Release: v0.4.0-alpha

## Decision

STEH may generate implementation artifacts only through a capability-controlled Tool Gateway.

The Implementation Agent receives approved requirements, architecture and security review.

## Prohibited in Alpha 0.4

- host filesystem access
- shell execution
- subprocess execution
- arbitrary network access
- file deletion
- path traversal
- environment secret access

## Allowed

- create/modify files inside a task-specific workspace
- return artifact evidence

## Safety invariant

```text
Implementation Agent
        |
        v
   Tool Gateway
        |
 Capability Policy
        |
        v
Task Workspace Only
```

No direct agent-to-host execution path is permitted.
