# STEH — Software Trust Engineering Harness

Repositório mestre do **Software Trust Engineering Harness (STEH)**.

O STEH é uma plataforma de engenharia de software assistida por IA orientada a segurança, auditabilidade, observabilidade, confiabilidade, governança e qualidade.

## Baseline atual

```text
v1.0.0-rc2
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
| `v1.0.0-rc2` | Baseline executável, tipada e validada com evidência reproduzível | **Baseline** |

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

Depois:

```text
http://localhost:8000/docs
http://localhost:8000/health
```

## Histórico no Git

Ao publicar no GitHub, preserve milestones por tags:

```bash
git tag -a v0.1.0-alpha -m "STEH Alpha 0.1"
git tag -a v0.2.0-alpha -m "STEH Alpha 0.2"
git tag -a v0.2.1-alpha -m "STEH Alpha 0.2.1"
```

Consulte `docs/GIT_WORKFLOW.md`, `docs/VERSIONING.md` e `CHANGELOG.md`.
