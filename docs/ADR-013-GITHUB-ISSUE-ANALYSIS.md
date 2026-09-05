# ADR-013 — Read-only GitHub Issue Analysis

## Status

Accepted for Patch 4E.

## Context

STEH can execute a governed engineering workflow, but task intake still depends on a manually
written request. GitHub issues contain useful problem statements, labels, constraints, and
acceptance hints. Treating issue content as trusted instructions, accepting arbitrary URLs, or
granting write permissions would introduce prompt-injection, SSRF, credential, and repository
integrity risks.

## Decision

Add a read-only GitHub Issue Analysis boundary and a dedicated analysis agent.

Clients provide only a validated owner, repository, and positive issue number. STEH constructs the
GitHub API path internally and does not accept arbitrary source URLs. A fail-closed repository
allowlist determines which repositories can be read; an empty allowlist disables ingestion.

The flow is:

1. fetch one issue through the GitHub Issues API;
2. reject pull-request payloads and unexpected upstream responses;
3. normalize and redact issue title/body before persistence;
4. enforce a configured body-size limit and mark truncation;
5. mark instruction-like content without executing it;
6. persist a versioned issue snapshot and SHA-256 receipt;
7. run the Issue Analysis Agent through the standard audited lifecycle;
8. produce typed problem, requirement, acceptance, risk, dependency, ambiguity, priority, and
   recommendation fields;
9. create two untrusted Context Engine sources from the sanitized issue and analysis;
10. execute the existing SDD, security, HITL, test-planning, implementation, validation, and rework
   workflow.

The integration exposes no operation for creating comments, editing issues, assigning users,
changing labels, closing issues, or modifying repository content.

The agent recommendation is advisory input to the existing specification and policy workflow. It
does not bypass Policy Engine gates or grant the analysis agent authority to execute changes.

## Security boundaries

- The server builds the API URL from validated path segments.
- HTTPS is mandatory for the configured GitHub API base URL.
- Redirect following is disabled.
- GitHub tokens are optional, secret-typed configuration and never included in evidence. Private
  issue access should use a fine-grained token limited to `Issues: read`.
- API-fetched issue content remains `UNTRUSTED` even when GitHub transport is authenticated.
- Common secrets are redacted before database, checkpoint, prompt, or audit persistence.
- Raw title/body content is excluded from task responses and audit events.
- The agent receives an explicit untrusted-data prompt boundary and has no GitHub tools.

## Persistence

Migration `0009_patch_4e_issue_analysis` adds nullable `source_issue` and `issue_analysis`
JSON columns to tasks. Existing tasks remain compatible.

## Consequences

- Issues can become traceable STEH tasks without manual transcription.
- Analysis remains reproducible against the exact sanitized issue revision.
- Private repositories can be read when a least-privilege token is configured.
- The current patch ingests the issue body and labels only; comments, linked issues, projects, and
  write-back are explicitly out of scope.
