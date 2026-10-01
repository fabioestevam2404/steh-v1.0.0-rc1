# STEH — Software Trust Engineering Harness

Repositório mestre do **Software Trust Engineering Harness (STEH)**.

O STEH é uma plataforma de engenharia de software assistida por IA orientada a segurança, auditabilidade, observabilidade, confiabilidade, governança e qualidade.

## Baseline atual

```text
v1.0.0-rc4
```

O código executável na raiz do repositório representa a versão operacional mais recente.

## Evolução

```text
Alpha 0.1
Single-Agent Vertical Slice
        |
        v
Alpha 0.2
Initial Multi-Agent Workflow
        |
        v
Alpha 0.2.1
Durable Multi-Agent Engineering Core
        |
        v
Alpha 0.3
Security Layer
        |
        v
Alpha 0.4
Implementation Agent + Tool Gateway + Sandbox
        |
        v
Alpha 0.5
Test Agent + Security Scanners + Rework Loop
        |
        v
v1.0.0-rc1 / rc2
Release candidates: auth, métricas e evidência reproduzível
        |
        v
v1.0.0-rc3
SDD + Test Plan, rework no grafo, HITL, Context Engine,
GitHub Issue/PR (read-only), LLM-as-Judge,
execução assíncrona (fila + worker) e logs correlacionados
        |
        v
v1.0.0-rc4
Validação falha fechada, retomada de jobs por checkpoint,
prompts versionados e métricas da fila
        |
        v
MVP 1.0
```

## Releases

| Release | Função | Situação |
|---|---|---|
| `v0.1.0-alpha` | Requirements Agent e primeiro vertical slice | Histórica |
| `v0.2.0-alpha` | Architecture Agent, workflow multiagente, gates e auditoria | Histórica |
| `v0.2.1-alpha` | Hardening, persistência durável, policy-as-code, migrations, testes e CI | Histórica |
| `v0.3.0-alpha` | Security Layer, Threat Model, Security Findings e Security Gate | Histórica |
| `v0.4.0-alpha` | Controlled Implementation Layer + Tool Gateway | Histórica |
| `v0.5.0-alpha` | Test Agent + Static Validation + Rework Decision | Histórica |
| `v0.5.1-alpha` | Containerized Scanners + Bounded Rework | Histórica |
| `v1.0.0-rc1` | MVP Release Candidate hardening and verification | Histórica |
| `v1.0.0-rc2` | Baseline executável, tipada e validada com evidência reproduzível | Histórica |
| `v1.0.0-rc3` | Workflow completo pós-RC2, execução assíncrona e 25 critérios de aceite | Histórica |
| `v1.0.0-rc4` | Validação falha fechada, retomada de jobs, prompts versionados e 26 critérios de aceite | **Baseline** |

As releases não são instaladas sequencialmente. Para executar o estado atual, use diretamente a raiz deste repositório.

## Estrutura

```text
steh/
├── app/
├── migrations/
├── policies/
├── tests/
├── docs/
│   ├── releases/
│   └── architecture/
├── releases/
├── .github/workflows/
├── Dockerfile
├── docker-compose.yml
├── alembic.ini
├── pyproject.toml
├── CHANGELOG.md
├── VERSION
└── README.md
```

## Executar

Linux/macOS:

```bash
cp .env.example .env
docker compose up --build
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

O Compose sobe `postgres`, `migrate` (aplica as migrações e encerra), `api` e `worker`.

Depois:

```text
http://localhost:8000/docs
http://localhost:8000/health
```

### Execução assíncrona

Os endpoints que executam agentes respondem `202 Accepted` com o header `Location`. O processamento acontece no `worker`, e o cliente acompanha a tarefa por `GET /api/v1/tasks/{task_id}` até um status terminal ou de espera (`COMPLETED`, `BLOCKED`, `HUMAN_REVIEW`, `REWORK_EXHAUSTED`, `FAILED`). Sem worker rodando, as tarefas ficam em `QUEUED`. Detalhes em `docs/ADR-016-ASYNC-TASK-EXECUTION.md`.

Para mais vazão, rode mais réplicas do worker: `docker compose up --scale worker=3`.

## Contribuindo

Fluxo trunk-based: branches curtos (`feature/*`, `fix/*`, `docs/*`, ...) a partir do `main`, PR com CI verde e merge. Releases são tags anotadas `vX.Y.Z-rcN` no `main`.

Consulte `docs/GIT_WORKFLOW.md`, `docs/VERSIONING.md`, `CHANGELOG.md`, `docs/ROADMAP.md` e `docs/HANDOFF.md`.
