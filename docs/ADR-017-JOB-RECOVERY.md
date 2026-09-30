# ADR-017 — Bounded job recovery from LangGraph checkpoints

## Status

Accepted after RC3. Amends ADR-016 ("abandoned jobs fail closed, no automatic retries").

## Context

ADR-016 marks a job `FAILED` and its task `TASK_ABANDONED` as soon as the worker stops
renewing the lease. A single worker restart (deploy, OOM, host loss) therefore discards
every in-flight task, even though LangGraph already persisted the workflow state after
each completed node.

ADR-016 rejected retries because a naive retry repeats every LLM call and agent run and
can apply implementation changes twice. Two further risks were found while designing
recovery:

- LangGraph's default `durability="async"` writes a step's checkpoint while the next
  step runs, so a crash can lose the latest checkpoint.
- Implementation files live in the worker's local workspace. A recovered job on another
  worker would validate an empty directory, and an empty workspace used to validate as
  PASS. That gap was closed separately: validation now fails unless every declared file
  is present (`workspace_integrity`).

## Decision

### Requeue expired jobs a bounded number of times

When a lease expires, the reaper checks `attempts` against `WORKER_MAX_ATTEMPTS`
(default `2`: the original run plus one recovery).

- Below the limit the job returns to `QUEUED`, keeping its attempt count, and the task
  receives `TASK_RECOVERY_SCHEDULED`.
- At the limit the ADR-016 behavior applies unchanged: job `FAILED`, task `FAILED`,
  `TASK_ABANDONED`.

In both cases agent runs left in `STARTED` by the dead worker are marked `ABANDONED`, so
the audit trail never shows an agent as still running.

### Resume from the last checkpoint instead of restarting

A job whose `attempts` is greater than one runs in recovery mode:

| Job kind | Recovery behavior |
|---|---|
| `EXECUTE_TASK` | Read the thread checkpoint. No checkpoint: start normally. Pending nodes: continue with `invoke(None)`, so only the interrupted node runs again. Finished or waiting for a human: reuse the stored state without invoking the graph. |
| `RESUME_HUMAN_REVIEW` | If the review interrupt is still pending, the decision was never applied: resume with the same `Command`. Otherwise continue or reuse the state as above. The claim and its audit event were already committed by the API and are not repeated. |
| `ANALYZE_GITHUB_ISSUE` | If the analysis and context bundle are already persisted, skip the analysis agent and recover the workflow; otherwise run the job again from the start. |
| `REVIEW_PULL_REQUEST` | Run again from the start (a single agent with no graph). |

The task receives `TASK_RECOVERED` (with the attempt number) instead of a second
`TASK_STARTED`.

### Synchronous checkpoint durability

Workflow invocations use `durability="sync"`: a step starts only after the previous
checkpoint is stored, so recovery resumes exactly after the last completed node.

### Shared workspace in Docker Compose

`api` and `worker` mount the named volume `steh_workspaces` at `/tmp/steh-workspaces`,
so a recovered job on another worker replica on the same host finds the implementation
files. Across hosts the volume is not shared; `workspace_integrity` then fails
validation, and bounded rework regenerates the files instead of approving empty output.

## Consequences

- A worker restart no longer discards in-flight tasks; at most the interrupted node
  runs again (one extra LLM call in the common case).
- A job that repeatedly kills its worker is attempted at most `WORKER_MAX_ATTEMPTS`
  times and then fails closed.
- `WORKER_MAX_ATTEMPTS=1` restores the exact ADR-016 behavior.
- If a worker dies after the graph finished but while the service was recording
  post-workflow audit events, recovery records those events again. Duplicated
  `POLICY_DECISION` or `REWORK_DECISION` events are possible in that narrow window;
  task artifacts and status are not affected.
- `durability="sync"` adds one checkpoint write latency per node.
