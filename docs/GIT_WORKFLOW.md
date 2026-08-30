# Git Workflow

## Branches

```text
main
develop
feature/*
fix/*
release/*
```

Próximo desenvolvimento:

```text
main
 |
 +-- develop
      |
      +-- feature/alpha-0.3-security-agent
      +-- feature/alpha-0.3-threat-model
      +-- feature/alpha-0.3-security-gates
```

## Tags

```bash
git tag -a v0.1.0-alpha -m "STEH Alpha 0.1"
git tag -a v0.2.0-alpha -m "STEH Alpha 0.2"
git tag -a v0.2.1-alpha -m "STEH Alpha 0.2.1"
```

## Regra de repositório

Não manter três cópias ativas do projeto. O histórico deve ser preservado por:

```text
Commits
+
Tags
+
GitHub Releases
+
CHANGELOG
+
ADRs
```
