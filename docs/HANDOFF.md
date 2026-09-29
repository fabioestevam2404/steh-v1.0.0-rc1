# STEH — Handoff

_Estado em 2026-09-29, commit `6f3fdf8` (`main`, merge do PR #11)._

## 1. Onde está o projeto

- **Repositório canônico:** https://github.com/fabioestevam2404/steh-v1.0.0-rc1 (público).
- **Baseline tagueada:** `v1.0.0-rc2` (`VERSION`, `app/version.py` e `pyproject.toml`).
- **Desde o RC2, entraram no `main` (PRs #4 a #11), ainda sem tag:**
  - Specification/SDD com critérios Given/When/Then e Test Plan antes da implementação (ADR-009)
  - Rework loop ligado ao grafo (ADR-010)
  - Human-in-the-Loop com retomada durável (ADR-011)
  - Context Engine auditável (ADR-012)
  - Análise read-only de GitHub Issues (ADR-013)
  - Revisão read-only de Pull Requests (ADR-014)
  - LLM-as-Judge auxiliar e não autoritativo (ADR-015)

A pasta local `C:\Projetos\Pipelines\steh\` é um **snapshot antigo da Alpha 0.1**, sem histórico em comum com este repositório. Serve só como arquivo e não deve receber desenvolvimento.

## 2. Estado verificado

**CI no GitHub:** as 5 últimas execuções do workflow `STEH RC Validation` no `main` terminaram com sucesso. A mais recente é do commit `6f3fdf8`, em 2026-09-06.

**Validação local (Windows, Python 3.12.14, 2026-09-29):** rodei `scripts/validate_rc.py --allow-database-reset` contra um Postgres 17 isolado. Resultado: **PASS nos 18 gates**, em 309 s.

| Gate | Resultado |
|---|---|
| RC-01 compileall | PASS |
| RC-02 / 03A / 03B Alembic: upgrade → downgrade base → upgrade (11 migrações) | PASS |
| RC-04 unit / RC-05 integration / RC-06 e2e | PASS |
| RC-07 lifecycle, RC-08/09 auth, RC-10 health, RC-11 metrics, RC-13 scanner isolation | PASS |
| RC-14 ruff check / RC-15 mypy strict | PASS |
| RC-12A–D build da imagem de scanners e smoke tests de Gitleaks, Trivy e Semgrep | PASS (o build leva ~3,5 min) |

## 3. Como rodar localmente

```bash
uv venv --python 3.12 .venv && uv pip install -e ".[dev]"
cp .env.example .env
docker compose up --build        # API em :8000, Postgres publicado em :5433
```

Validação completa, **só contra um banco descartável**, porque o script faz `downgrade base`:

```bash
docker run -d --rm --name steh-rc-validate -e POSTGRES_DB=steh -e POSTGRES_USER=steh \
  -e POSTGRES_PASSWORD=steh -p 127.0.0.1:5435:5432 postgres:17-alpine
export DATABASE_URL=postgresql+psycopg://steh:steh@127.0.0.1:5435/steh
export LANGGRAPH_DATABASE_URL="postgresql://steh:steh@127.0.0.1:5435/steh?sslmode=disable"
export LLM_MODE=stub AUTH_ENABLED=false POLICY_FILE=policies/quality-gates.yaml
python scripts/validate_rc.py --allow-database-reset --output artifacts/rc-evidence.json
```

**Armadilha no Windows:** se o Postgres for publicado só em `127.0.0.1`, **use `127.0.0.1` nas URLs, não `localhost`**. `localhost` resolve primeiro para `::1`, e o `psycopg` fica pendurado sem timeout. Os testes de integração travam sem nenhuma mensagem de erro.

## 4. Pendências encontradas

1. **Versão e CHANGELOG defasados.** O `CHANGELOG.md` termina no RC2, e as 7 entregas da seção 1 não aparecem em lugar nenhum. Sugestão: criar uma seção `[Unreleased]` agora e, no próximo RC, subir `VERSION`, `app/version.py`, `pyproject.toml` e o teste `test_health_reports_application_version` juntos.
2. **Formatação sem gate.** `ruff format --check .` aponta **55 arquivos** fora do padrão. O RC-14 só roda `ruff check`. Sugestão: um PR que só formata, sem mudança de lógica, e depois um gate `ruff format --check`.
3. **Branches já mergeados:** `feature/github-issue-analysis`, `feature/hitl-resume` e `feature/pr-review-agent` estão 0 commits à frente do `main` e podem ser apagados.
4. **`docs/GIT_WORKFLOW.md` desatualizado.** Cita um branch `develop`, que não existe, e exemplos de branches da Alpha 0.3. O CI também dispara em `develop`. Sugestão: alinhar o documento ao fluxo real (`main` + `feature/*` / `fix/*` + PR).
5. **README desatualizado.** O diagrama de evolução para em "MVP 1.0" e não cita as entregas pós-RC2.
6. **Critério RC-16** (CI verde no commit candidato, com o artefato JSON) precisa ser cumprido de novo no commit que virar o próximo RC.

## 5. Próximo marco

Pelo `docs/ROADMAP.md`: o **próximo release candidate** traz hardening de segurança e operação pós-integração, mais **evidência de aceite atualizada para o workflow completo pós-RC2**.

Ordem sugerida:

1. Resolver as pendências 1 a 5 em PRs pequenos.
2. Revisar `docs/MVP-1.0-RC-ACCEPTANCE.md` para cobrir SDD, rework, HITL, Context Engine, GitHub Issue/PR e Judge.
3. Fazer o hardening de segurança e operação.
4. Tag `v1.0.0-rc3`, com CI verde e o artefato de evidência do commit exato.
5. Promover a `v1.0.0` só se todos os critérios tiverem evidência daquele commit, conforme a regra de promoção do documento de aceite.

## 6. Regras do projeto que não podem ser quebradas

- A LLM fornece evidências; os **gates determinísticos decidem**. O Judge é auxiliar e nunca sobrepõe um gate nem a revisão humana (ADR-015).
- Os agentes não têm acesso direto ao host. A execução passa pelo Tool Gateway e pelos scanners em container, com rede desligada e workspace read-only (ADR-005 e ADR-007).
- As integrações com o GitHub são **read-only** e restritas a `GITHUB_ALLOWED_REPOSITORIES`.
