# STEH — Handoff

_Estado em 2026-09-30, preparado no PR de release `v1.0.0-rc3`._

## 1. Onde está o projeto

- **Repositório canônico:** https://github.com/fabioestevam2404/steh-v1.0.0-rc1 (público). Só existe o branch `main`; o trabalho segue `docs/GIT_WORKFLOW.md` (branch curto → PR com CI verde → merge commit → apagar branch).
- **Versão:** `1.0.0-rc3` (`VERSION`, `app/version.py`, `pyproject.toml`). A tag `v1.0.0-rc3` deve ser criada no commit de merge do PR de release (ver seção 5).
- **O que o RC3 entrega:** o workflow completo pós-RC2 (ADR-009 a ADR-015) e o hardening operacional: execução assíncrona com fila no Postgres e worker (ADR-016), logs correlacionados e configuração/banco criados sob demanda. Detalhes em `docs/releases/v1.0.0-rc3.md` e no `CHANGELOG.md`.
- **Mudança de contrato:** os endpoints que executam agentes respondem `202` e o cliente acompanha por `GET /api/v1/tasks/{task_id}`. Sem worker rodando, as tarefas ficam em `QUEUED`.

A pasta local `C:\Projetos\Pipelines\steh\` é um **snapshot antigo da Alpha 0.1**, sem histórico em comum com este repositório. Serve só como arquivo e não deve receber desenvolvimento.

## 2. Estado verificado

- **Validação local em 2026-09-29/30** (`scripts/validate_rc.py`, Postgres 17 isolado, Windows, Python 3.12): **28/28 gates PASS**, incluindo a ida e volta das migrações até a `0012`.
- **Docker Compose** (`postgres` → `migrate` → `api` + `worker`): fluxo `202 QUEUED → HUMAN_REVIEW`, decisão `202 RESUMING → COMPLETED`, decisão duplicada `409`, `/ready` `503` com o Postgres parado, worker encerra com código 0 no SIGTERM.
- **CI:** o workflow `STEH RC Validation` roda os 28 gates em cada PR e em cada push no `main`; o `STEH Release Validation` roda em tags `v*-rc*`.

## 3. Como rodar localmente

```bash
uv venv --python 3.12 .venv && uv pip install -e ".[dev]"
cp .env.example .env
docker compose up --build        # postgres, migrate, api (:8000) e worker
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

**Armadilhas no Windows:**

- Com o Postgres publicado só em `127.0.0.1`, **use `127.0.0.1` nas URLs, não `localhost`**: `localhost` resolve primeiro para `::1` e o `psycopg` fica pendurado sem timeout.
- O `.gitattributes` força LF em `*.sh`. Se o container falhar com `exec /app/docker-entrypoint.sh: no such file or directory`, o arquivo está com CRLF: apague a cópia local e restaure-a do índice: `rm docker-entrypoint.sh && git checkout -- docker-entrypoint.sh`.
- Enviar JSON com acentos pelo `curl` do Git Bash pode gerar `400`; use um cliente Python (httpx) para testes manuais.

## 4. Pendências e dívidas em aberto

Todas as dívidas levantadas na conferência de 2026-09-29 foram resolvidas (PRs #13 a #20), exceto:

1. **Prompts só no código.** Cada agente tem o prompt inline, sem versão nem hash na evidência (ao contrário da rubrica do Judge). Mudar um prompt exige mudar código.
2. ~~**Lacunas de teste nos critérios de aceite.**~~ Cobertas depois do RC3: revisão expirada bloqueia antes da implementação (RC-19), veredito `FAIL` do Judge mantém a tarefa `COMPLETED` (RC-23) e tarefa/reivindicação nunca ficam gravadas sem o job quando a gravação do job falha (RC-24; o teste falha se a atomicidade for removida).
3. **Operação da fila:** sem métricas de profundidade e latência; um worker que morre deixa a tarefa `FAILED` (`TASK_ABANDONED`), sem retomada a partir do checkpoint.

## 5. Próximo marco

1. **Tag do RC3:** depois do merge do PR de release com CI verde, no commit de merge:

   ```bash
   git switch main && git pull --ff-only
   git tag -a v1.0.0-rc3 -m "STEH v1.0.0-rc3"
   git push origin v1.0.0-rc3
   ```

   Conferir que o `STEH Release Validation` terminou verde e guardou o artefato `release-validation-evidence` (critério RC-16).
2. **Depois do RC3:** escolher entre fechar as pendências da seção 4 ou decidir a promoção a `v1.0.0`, que exige evidência do commit exato para os 25 critérios (`docs/MVP-1.0-RC-ACCEPTANCE.md`).

## 6. Regras do projeto que não podem ser quebradas

- A LLM fornece evidências; os **gates determinísticos decidem**. O Judge é auxiliar e nunca sobrepõe um gate nem a revisão humana (ADR-015).
- Os agentes não têm acesso direto ao host. A execução passa pelo Tool Gateway e pelos scanners em container, com rede desligada e workspace read-only (ADR-005 e ADR-007).
- As integrações com o GitHub são **read-only** e restritas a `GITHUB_ALLOWED_REPOSITORIES`.
- Payloads de job nunca carregam conteúdo bruto do cliente ou do GitHub; o worker lê os snapshots já redigidos (ADR-016). Jobs não são reexecutados automaticamente.
