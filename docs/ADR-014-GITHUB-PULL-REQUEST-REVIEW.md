# ADR-014 — Read-only GitHub Pull Request Review

## Status

Accepted for Patch 4F.

## Context

STEH can derive governed engineering tasks from GitHub issues, but it cannot yet inspect an
existing pull request as a review artifact. Pull-request titles, descriptions, filenames, and
patches are attacker-controlled repository data. Giving that content authority over the agent, or
giving the agent GitHub write permissions, would expose the workflow to prompt injection,
credential disclosure, unbounded input, and repository-integrity risks.

## Decision

Add a dedicated, read-only Pull Request Review Agent behind the same validated GitHub repository
boundary used by issue analysis.

The flow is deliberately separate from the implementation graph:

1. accept only a validated owner, repository, and positive pull-request number;
2. construct fixed GitHub API paths for pull-request metadata and changed files;
3. enforce the repository allowlist, HTTPS, disabled redirects, timeout, response-size limit, and
   a maximum of 100 requested files;
4. sanitize and redact title, body, author, refs, filenames, previous filenames, and patch text;
5. enforce a cumulative patch-character budget and record incomplete coverage;
6. persist a versioned snapshot and SHA-256 receipt;
7. create one `UNTRUSTED` Context Engine source for the exact bounded review input;
8. execute the Pull Request Review Agent through the audited lifecycle;
9. produce typed findings for security, testing, quality, contracts, architecture, and
   documentation;
10. persist the advisory review and finish the review task without invoking implementation.

Every result has `requires_human_review=true`. Recommendations are limited to
`READY_FOR_HUMAN_REVIEW`, `CHANGES_REQUIRED`, or `BLOCK`; none of them changes GitHub state.

## Deterministic safeguards

The agent cannot weaken the following locally enforced conclusions:

- detected credential-like content produces a critical finding and `BLOCK`;
- instruction-like untrusted content requires changes and focused human inspection;
- truncated file or patch coverage requires changes before the review can be relied upon;
- production-code changes without identifiable test changes require changes;
- authentication, security, policy, migration, container, and CI surfaces are explicitly flagged
  for focused review.

LLM output may add findings, but required deterministic findings are merged back into the final
artifact. Source identity, hashes, risk constraints, recommendation constraints, and the human
review requirement are set by application code.

## Security boundaries

- The API does not accept arbitrary upstream URLs.
- An empty repository allowlist disables the integration.
- GitHub content remains untrusted even when authenticated transport is used.
- Private-repository access uses a fine-grained token limited to `Pull requests: read`.
- The GitHub token is secret-typed and is never stored in task or audit evidence.
- Raw patches are excluded from API receipts and audit-event payloads.
- The cumulative patch and response budgets bound memory and model input.
- The agent receives only Context Engine-bounded content when using an external model.
- No API exists for comments, approvals, requested changes, branch updates, merges, or repository
  writes.

## Persistence

Migration `0010_patch_4f_pr_review` adds nullable `source_pull_request` and
`pull_request_review` JSON columns to `tasks`. Existing task rows remain compatible.

## Consequences

- Pull requests receive traceable, reproducible, evidence-backed advisory reviews.
- A completed STEH review means the analysis finished; it never means the pull request was
  approved or merged.
- Reviews with omitted patches, files, or detected secrets fail closed at the recommendation
  layer.
- Line comments, check runs, review submission, and merge automation remain explicitly out of
  scope.
