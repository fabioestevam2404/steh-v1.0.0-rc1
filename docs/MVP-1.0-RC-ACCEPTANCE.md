# STEH MVP 1.0 RC — Acceptance Criteria

Target release candidate: `1.0.0-rc3`

Previous candidate: `1.0.0-rc2` (criteria RC-01 to RC-16). RC3 keeps every RC2
criterion and adds RC-17 to RC-25 for the capabilities merged after RC2.

## Evidence model

Every CI and release run executes `scripts/validate_rc.py` and uploads a JSON
artifact containing the commit SHA, run identity, environment, timestamps,
command, return code, duration and result for each executable gate. A criterion
is accepted only when the evidence belongs to the candidate commit.

Each criterion maps to one or more gate ids in that artifact. Gates with a
letter suffix (for example `RC-12A` to `RC-12D`) are parts of the same criterion;
the criterion passes only when all of its parts pass.

The validator performs a destructive downgrade to Alembic `base`. It requires
`--allow-database-reset` and must run only against an isolated RC database.

## Baseline criteria (since RC2)

| ID | Criterion | Executable evidence | Gates |
|---|---|---|---|
| RC-01 | Python source compiles | `compileall` | RC-01 |
| RC-02 | Alembic upgrades a clean database to head | `alembic upgrade head` | RC-02 |
| RC-03 | Complete Alembic downgrade/upgrade roundtrip | `downgrade base`, then `upgrade head` | RC-03A, RC-03B |
| RC-04 | Unit tests pass | `pytest tests/unit` | RC-04 |
| RC-05 | Integration tests pass against PostgreSQL | `pytest tests/integration` | RC-05 |
| RC-06 | E2E workflows pass | `pytest tests/e2e` | RC-06 |
| RC-07 | Agent lifecycle is auditable | lifecycle unit and E2E assertions | RC-07 |
| RC-08 | Authentication rejects missing or invalid tokens | authentication unit tests | RC-08/09 |
| RC-09 | Authorization rejects insufficient roles | authorization unit tests | RC-08/09 |
| RC-10 | Health and readiness endpoints operate | API tests | RC-10 |
| RC-11 | Metrics expose HTTP counters labeled by route template, and task and queue state read from the database; `/metrics` stays available during a database outage | metrics unit tests and queue-metrics integration test | RC-11 |
| RC-12 | Semgrep, Gitleaks and Trivy image builds and runs | Docker build and smoke commands | RC-12A–RC-12D |
| RC-13 | External scanner isolation is verified | scanner and process-runner tests | RC-13 |
| RC-14 | Ruff lint and format pass | `ruff check .` and `ruff format --check .` | RC-14, RC-14B |
| RC-15 | mypy strict passes | `mypy app` | RC-15 |
| RC-16 | CI completes for the candidate commit | GitHub Actions result plus JSON artifact | workflow run |

## Post-RC2 criteria (new in RC3)

| ID | Criterion | Executable evidence | Decision |
|---|---|---|---|
| RC-17 | Specification assigns stable `FR`/`NFR`/`AC` ids with Given/When/Then scenarios, and a test plan covering every requirement (including negative security coverage) exists before implementation; SPEC, TRACE and TESTPLAN gates block otherwise | specification, test-planning, policy-engine and policy-loader tests | ADR-009 |
| RC-18 | Failed validation triggers bounded rework and ends in `REWORK_EXHAUSTED` when attempts run out, never in an unbounded loop | rework controller and rework graph tests | ADR-010 |
| RC-19 | A human decision resumes the interrupted checkpoint exactly once; duplicate decisions receive `409`; decisions after the deadline resolve as `EXPIRED` and block the task before test planning or implementation | human-review unit and E2E tests | ADR-011 |
| RC-20 | Context sources are redacted, budgeted, hashed and labeled `UNTRUSTED`; raw content never reaches responses, audit events or job payloads | Context Engine unit and E2E tests | ADR-012, ADR-016 |
| RC-21 | GitHub issue analysis is read-only, restricted by a fail-closed repository allowlist, and does not persist raw secrets | GitHub client, issue-analysis agent and E2E tests | ADR-013 |
| RC-22 | Pull request review is read-only, allowlisted and bounded; deterministic safeguards (credentials, injection markers, truncation, missing tests) cannot be weakened by the model | pull-request client, review agent and E2E tests | ADR-014 |
| RC-23 | The LLM judge is always `authoritative=false`; its rubric coverage and weighted verdict are computed by application code, and a `FAIL` verdict (like a skipped or unavailable judge) leaves an approved task `COMPLETED`, with the result attached only as advisory evidence | judge unit tests, graph tests with a failing verdict and human-review E2E assertions | ADR-015 |
| RC-24 | Agent execution is asynchronous (`202` + polling); jobs are claimed with `SKIP LOCKED`, leases are owner-only, expired leases fail closed with `TASK_ABANDONED`, failed jobs record only the error type, and a task or review claim is never persisted without its job (verified by forcing the job insert to fail) | job-queue integration tests and task E2E test | ADR-016 |
| RC-25 | Structured logs carry `task_id`, `trace_id` and `job_id` across API, worker and agents, and log error types only | logging unit tests and worker log integration test | RC3 hardening |

Each post-RC2 criterion is a gate with the same id in the JSON artifact
(`RC-17` to `RC-25`), running exactly the test files listed in
`scripts/validate_rc.py`.

## Promotion rule

`1.0.0-rc3` must not be tagged, and no release candidate may be promoted to
`1.0.0`, unless every criterion above has objective evidence from the exact
release commit. Documentation statements or results produced by a different
commit do not constitute acceptance.

## Operational prerequisites

Since RC3 the API only accepts work; a worker (`python -m app.worker`, or the
`worker` Compose service) must run for tasks to progress. Acceptance of RC-06,
RC-19 and RC-24 relies on the in-process worker used by the test suite, which
exercises the same code path.
