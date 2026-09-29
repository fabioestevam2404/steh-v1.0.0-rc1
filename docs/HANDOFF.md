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

1. ~~**CHANGELOG defasado.**~~ Seção `[Unreleased]` criada no PR #13. Falta, no próximo RC, subir `VERSION`, `app/version.py`, `pyproject.toml` e o teste `test_health_reports_application_version` juntos.
2. ~~**Formatação sem gate.**~~ 55 arquivos formatados (AST idêntica) e novo gate RC-14B `ruff format --check .`. O ruff foi fixado em `>=0.16,<0.17`, para que uma versão nova não mude o estilo e quebre o gate; subir de versão é um PR próprio (atualizar o pin e reformatar). O commit de formatação está em `.git-blame-ignore-revs`.
3. **Branches já mergeados:** `feature/github-issue-analysis`, `feature/hitl-resume` e `feature/pr-review-agent` estão 0 commits à frente do `main` e podem ser apagados.
4. ~~**`docs/GIT_WORKFLOW.md` desatualizado.**~~ Reescrito com o fluxo real (trunk-based + PR + tags de RC), e `develop` removido do gatilho do CI.
5. ~~**README desatualizado.**~~ Diagrama de evolução e tabela de releases passam a citar as entregas pós-RC2; `docs/architecture/README.md` deixa de apontar a `v0.2.1-alpha` como baseline.
6. **Critério RC-16** (CI verde no commit candidato, com o artefato JSON) precisa ser cumprido de novo no commit que virar o próximo RC.

### Dívidas técnicas para o hardening do RC3

Levantadas em 2026-09-29, ao conferir o código contra a lista de problemas da Alpha 0.1.

7. ~~**`POST /api/v1/tasks` é síncrono.**~~ Resolvido pelo ADR-016 (fila no Postgres + worker, os 4 endpoints respondem `202`). Texto original: `create_task` chama `execute_task` dentro da requisição e só responde quando o workflow inteiro termina (até 9 agentes, com rework). Com `LLM_MODE=openai`, isso arrisca timeout de cliente e de proxy, e segura um worker por tarefa. Sugestão: responder `202 Accepted` com status `CREATED` e executar em background (`BackgroundTasks` agora, fila ou worker depois); o cliente acompanha por `GET /tasks/{id}`. **Muda o contrato da API e os E2E**, então precisa de ADR próprio.
8. ~~**Logs com pouca cobertura.**~~ Resolvido: `log_context()` com `contextvars` + `ContextFilter`, logs por agente no `AgentLifecycle` e logs de job no worker. Texto original: O `JsonFormatter` já existe, mas o app só emite 3 logs (`workflow_started`, `workflow_completed`, `workflow_failed`), e o `trace_id` é passado à mão em cada `extra=`. Sugestão: guardar `task_id` e `trace_id` em `contextvars`, injetá-los com um `logging.Filter` e registrar `agent_started` / `agent_completed` (com `duration_ms`) no `lifecycle`, em paralelo aos audit events.
9. **Objetos globais criados na importação.** `settings = get_settings()` (importado direto por 10 módulos) e o `engine` / `SessionLocal` em `app/db/session.py` nascem no import; o `/ready` usa o `SessionLocal` sem `Depends`. Hoje não quebra nada (o `conftest.py` define as URLs), mas dificulta testar com outra configuração ou com um banco falso. Sugestão: `get_settings()` e `get_session()` via `Depends`, trocáveis por `app.dependency_overrides`. Fazer depois do PR de formatação, para o diff ficar legível.
10. ~~**`app/db/init_db.py` morto**~~ (`create_all` fora do Alembic, sem nenhum chamador). Removido no mesmo PR que adicionou esta seção.
11. **Prompts só no código.** A pasta `prompts/` foi removida e cada agente tem o prompt inline. Não há duplicação, mas mudar um prompt exige mudar código e não há versão nem hash do prompt na evidência (ao contrário da rubrica do Judge). Baixa prioridade; avaliar junto com a evidência de aceite do RC3.

## 5. Próximo marco

Pelo `docs/ROADMAP.md`: o **próximo release candidate** traz hardening de segurança e operação pós-integração, mais **evidência de aceite atualizada para o workflow completo pós-RC2**.

Ordem sugerida:

1. Resolver as pendências 2 e 3 (formatação e branches mergeados).
2. Revisar `docs/MVP-1.0-RC-ACCEPTANCE.md` para cobrir SDD, rework, HITL, Context Engine, GitHub Issue/PR e Judge.
3. Fazer o hardening de segurança e operação, incluindo as dívidas 7 a 9 (e a 11, se couber).
4. Tag `v1.0.0-rc3`, com CI verde e o artefato de evidência do commit exato.
5. Promover a `v1.0.0` só se todos os critérios tiverem evidência daquele commit, conforme a regra de promoção do documento de aceite.

## 6. Regras do projeto que não podem ser quebradas

- A LLM fornece evidências; os **gates determinísticos decidem**. O Judge é auxiliar e nunca sobrepõe um gate nem a revisão humana (ADR-015).
- Os agentes não têm acesso direto ao host. A execução passa pelo Tool Gateway e pelos scanners em container, com rede desligada e workspace read-only (ADR-005 e ADR-007).
- As integrações com o GitHub são **read-only** e restritas a `GITHUB_ALLOWED_REPOSITORIES`.
