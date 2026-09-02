# STEH MVP 1.0 RC — Acceptance Criteria

Target release candidate: `1.0.0-rc2`

## Evidence model

Every CI and release run executes `scripts/validate_rc.py` and uploads a JSON
artifact containing the commit SHA, run identity, environment, timestamps,
command, return code, duration and result for each executable gate. A criterion
is accepted only when the evidence belongs to the candidate commit.

The validator performs a destructive downgrade to Alembic `base`. It requires
`--allow-database-reset` and must run only against an isolated RC database.

## Mandatory gates

| ID | Criterion | Executable evidence |
|---|---|---|
| RC-01 | Python source compiles | `compileall` |
| RC-02 | Alembic upgrades a clean database to head | `alembic upgrade head` |
| RC-03 | Complete Alembic downgrade/upgrade roundtrip | `downgrade base`, then `upgrade head` |
| RC-04 | Unit tests pass | `pytest tests/unit` |
| RC-05 | Integration tests pass against PostgreSQL | `pytest tests/integration` |
| RC-06 | E2E workflows pass | `pytest tests/e2e` |
| RC-07 | Agent lifecycle is auditable | lifecycle unit and E2E assertions |
| RC-08 | Authentication rejects missing or invalid tokens | authentication unit tests |
| RC-09 | Authorization rejects insufficient roles | authorization unit tests |
| RC-10 | Health and readiness endpoints operate | API tests |
| RC-11 | Metrics expose operational counters | metrics tests |
| RC-12 | Semgrep, Gitleaks and Trivy image builds and runs | Docker build and smoke commands |
| RC-13 | External scanner isolation is verified | scanner and process-runner tests |
| RC-14 | Ruff passes | `ruff check .` |
| RC-15 | mypy strict passes | `mypy app` |
| RC-16 | CI completes for the candidate commit | GitHub Actions result plus JSON artifact |

## Promotion rule

`1.0.0-rc2` must not be promoted to `1.0.0` unless every mandatory criterion
has objective evidence from the exact release commit. Documentation statements
or results produced by a different commit do not constitute acceptance.
