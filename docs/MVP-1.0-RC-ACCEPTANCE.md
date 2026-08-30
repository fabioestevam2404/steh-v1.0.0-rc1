# STEH MVP 1.0 RC — Acceptance Criteria

Release candidate: `1.0.0-rc1`

## Mandatory gates

| ID | Criterion | Required |
|---|---|---|
| RC-01 | Python source compiles | PASS |
| RC-02 | Alembic upgrades clean database to head | PASS |
| RC-03 | Alembic downgrade/upgrade smoke test | PASS |
| RC-04 | Unit tests pass | PASS |
| RC-05 | Integration tests pass against PostgreSQL | PASS |
| RC-06 | E2E task workflow passes | PASS |
| RC-07 | Lifecycle events start before actual agent execution | PASS |
| RC-08 | Authentication rejects missing/invalid token when enabled | PASS |
| RC-09 | Authorization rejects principal without required role | PASS |
| RC-10 | `/health` and `/ready` operate correctly | PASS |
| RC-11 | `/metrics` exposes operational counters | PASS |
| RC-12 | Semgrep/Gitleaks/Trivy scanner image builds | PASS |
| RC-13 | External scanner isolation verified | PASS |
| RC-14 | Ruff passes | PASS |
| RC-15 | mypy passes | PASS |
| RC-16 | GitHub Actions CI is green | PASS |

## Promotion rule

`1.0.0-rc1` MUST NOT be promoted to `1.0.0` until all mandatory gates have objective evidence.

Syntax compilation alone is not release acceptance.
