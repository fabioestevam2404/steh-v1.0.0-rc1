# ADR-018 — Versioned agent prompts

## Status

Accepted after RC3.

## Context

The instructions of the nine LLM agents were string literals inside each agent module.
Changing a prompt meant changing code, and the audit trail could not show which
instructions governed a given agent run. The judge rubric was already versioned and
hashed (ADR-015), so the evidence model was inconsistent across agents.

## Decision

- Each LLM agent's instructions live in `prompts/<id>.md` with a YAML header declaring
  `id` and `version`. Data sent to the model (requests, artifacts, context, repository
  content) is still assembled in code and is never part of the prompt file, which keeps
  the instruction/data boundary of ADR-012 to ADR-014 explicit.
- The prompt hash is the SHA-256 of the canonical JSON of `id`, `version` and text.
  Line endings are normalized first, so a Windows checkout produces the same hash.
- `prompts/prompts.lock.json` pins the version and hash of every prompt.
  `python -m app.services.prompts --check` fails when a prompt's text changed while its
  version did not, or when the lock is outdated. Changing a prompt therefore requires a
  version bump and a regenerated lock (`--write-lock`) in the same pull request.
- `AgentLifecycle` appends an `agent_prompt` evidence entry (`prompt_id`,
  `prompt_version`, `prompt_sha256`, `applied`) to every agent run that has a prompt.
  `applied` is false in stub mode, where the deterministic stub runs and no prompt is
  sent to a model.

The migration moved the existing instructions verbatim: each file was verified to be
byte-identical to the previous inline literal.

## Consequences

- Every agent run in the audit trail identifies the exact instructions that governed it.
- Prompt changes are reviewable as text diffs and cannot slip in without a version bump.
- The container image must include `prompts/` (copied by the Dockerfile).
- Prompt text is part of the release: criteria RC-26 and RC-26B gate it.
