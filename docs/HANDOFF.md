# STEH — Handoff

_Estado em 2026-10-01, preparado no PR de promoção a `v1.0.0` (MVP 1.0)._

## 1. Onde está o projeto

- **Repositório canônico:** https://github.com/fabioestevam2404/steh-v1.0.0-rc1 (público). Só existe o branch `main`; o trabalho segue `docs/GIT_WORKFLOW.md` (branch curto → PR com CI verde → merge commit → apagar branch).
- **Versão:** `1.0.0`, a primeira estável (`VERSION`, `app/version.py`, `pyproject.toml`), promovida a partir do `v1.0.0-rc4` sem mudança funcional. A tag `v1.0.0` deve ser criada no commit de merge do PR de promoção (ver seção 5).
- **Releases anteriores:** `v1.0.0-rc4` (2026-10-01, evidência 30/30 no run 36855509999, commit `20ba8fc`), `v1.0.0-rc3` e `v1.0.0-rc2`. Notas em `docs/releases/`.
- **O que o RC4 entregou (base da 1.0):** validação que falha fechada com workspace vazio, retomada de jobs por checkpoint (ADR-017), prompts versionados com hash na evidência (ADR-018), métricas da fila e os testes que faltavam nos critérios RC-19, RC-23 e RC-24. Detalhes em `docs/releases/v1.0.0-rc4.md`.
- **Contrato da API:** os endpoints que executam agentes respondem `202` e o cliente acompanha por `GET /api/v1/tasks/{task_id}` (desde o RC3). Sem worker rodando, as tarefas ficam em `QUEUED`.

A pasta local `C:\Projetos\Pipelines\steh\` é um **snapshot antigo da Alpha 0.1**, sem histórico em comum com este repositório. Serve só como arquivo e não deve receber desenvolvimento.

## 2. Estado verificado

- **Validação local** (`scripts/validate_rc.py`, Postgres 17 isolado, Windows, Python 3.12): **30/30 gates PASS** para os 26 critérios de `docs/MVP-1.0-RC-ACCEPTANCE.md`.
- **Docker Compose** (`postgres` → `migrate` → `api` + `worker`, volume `steh_workspaces`): fluxo `202 QUEUED → HUMAN_REVIEW → 202 RESUMING → COMPLETED`, decisão duplicada `409`, `/ready` `503` com o Postgres parado, worker encerra com código 0 no SIGTERM, recibos de prompt no `/audit`, `/metrics` com dados de fila e de requisições.
- **CI:** o workflow `STEH RC Validation` roda os 30 gates em cada PR e em cada push no `main`; o `STEH Release Validation` roda em tags `v*-rc*` e guarda a evidência por 90 dias.

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

**Mudar um prompt de agente:** editar `prompts/<id>.md`, subir a `version` e rodar `python -m app.services.prompts --write-lock` no mesmo PR (o gate RC-26B falha caso contrário).

**Armadilhas no Windows:**

- Com o Postgres publicado só em `127.0.0.1`, **use `127.0.0.1` nas URLs, não `localhost`**: `localhost` resolve primeiro para `::1` e o `psycopg` fica pendurado sem timeout.
- O `.gitattributes` força LF em `*.sh`. Se o container falhar com `exec /app/docker-entrypoint.sh: no such file or directory`, o arquivo está com CRLF: apague a cópia local e restaure-a do índice: `rm docker-entrypoint.sh && git checkout -- docker-entrypoint.sh`.
- O terminal padrão é Windows PowerShell 5.1: um comando por linha (sem `&&`) e sempre a partir de `C:\Projetos\Pipelines\steh-v1.0.0-rc1`.
- Enviar JSON com acentos pelo `curl` do Git Bash pode gerar `400`; use um cliente Python (httpx) para testes manuais.

## 4. Limitações conhecidas

Nenhuma dívida técnica levantada até aqui está em aberto. Limitações aceitas e documentadas:

1. Se o worker morrer enquanto grava os eventos de auditoria do fim do workflow, a retomada pode registrar alguns `POLICY_DECISION`/`REWORK_DECISION` em dobro; status e artefatos não são afetados (ADR-017).
2. Entre hosts diferentes o volume de workspace não é compartilhado; um job retomado em outro host falha a `workspace_integrity` e o rework regenera os arquivos (não há aprovação falsa).
3. As métricas da fila são calculadas por consulta ao Postgres a cada coleta do `/metrics`; com volumes muito grandes de jobs, pode ser preciso limitar a janela.

## 5. Próximo marco

1. **Tag `v1.0.0`:** depois do merge do PR de promoção com CI verde, no commit de merge (confirmar o merge pela API antes de apagar o branch):

   ```bash
   git switch main
   git pull --ff-only
   git tag -a v1.0.0 -m "STEH v1.0.0"
   git push origin v1.0.0
   ```

   O `STEH Release Validation` passa a rodar também em tags estáveis. Conferir que terminou verde e que o artefato `release-validation-evidence` registra `release_version: 1.0.0` e 30/30 gates (regra de promoção). Depois, publicar o GitHub Release como **latest** (não pre-release) com o texto de `docs/releases/v1.0.0.md`.
2. **Depois da 1.0:** novas capacidades entram como ADRs e versões minor (`1.1.0`, ...), seguindo `docs/VERSIONING.md`.

## 6. Regras do projeto que não podem ser quebradas

- A LLM fornece evidências; os **gates determinísticos decidem**. O Judge é auxiliar e nunca sobrepõe um gate nem a revisão humana (ADR-015).
- A validação **falha fechada**: sem os arquivos declarados pela implementação no workspace, não há aprovação.
- Os agentes não têm acesso direto ao host. A execução passa pelo Tool Gateway e pelos scanners em container, com rede desligada e workspace read-only (ADR-005 e ADR-007).
- As integrações com o GitHub são **read-only** e restritas a `GITHUB_ALLOWED_REPOSITORIES`.
- Payloads de job nunca carregam conteúdo bruto do cliente ou do GitHub; o worker lê os snapshots já redigidos (ADR-016). A retomada de jobs é limitada por `WORKER_MAX_ATTEMPTS` e continua do checkpoint (ADR-017).
- Instruções de agente só mudam com nova versão do prompt e lock atualizado (ADR-018).
