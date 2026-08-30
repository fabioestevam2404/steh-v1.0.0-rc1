# ADR-008 — MVP 1.0 Release Candidate Hardening

Status: Accepted

## Changes

1. Agent lifecycle is now wrapped around the actual agent call. `AGENT_STARTED` is persisted immediately before execution and success/failure immediately after it.
2. Task APIs have an authentication/authorization boundary.
3. JWT auth can be disabled only for local development.
4. `/ready` verifies database connectivity.
5. `/metrics` exposes machine-readable operational counters.
6. Promotion to MVP 1.0 requires objective acceptance evidence.

## Security note

The bundled HS256 secret is a local-development default only. Production deployment must inject a strong secret or replace this mechanism with an organizational identity provider.
