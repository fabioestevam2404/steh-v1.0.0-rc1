# Git Workflow

## Modelo

Trunk-based com Pull Requests. `main` é o único branch de longa duração e sempre representa a versão operacional mais recente.

```text
main
 |
 +-- feature/<nome>   nova capacidade        ex.: feature/llm-as-judge
 +-- fix/<nome>       correção               ex.: fix/rc2-baseline-recovery
 +-- release/<versão> preparação de RC       ex.: release/v1.0.0-rc2
 +-- docs/<nome>      só documentação        ex.: docs/handoff
 +-- chore/<nome>     manutenção sem efeito funcional
 +-- style/<nome>     formatação sem mudança de lógica
```

Não existe branch `develop`.

## Ciclo de uma mudança

1. Criar o branch a partir do `main` atualizado.
2. Fazer commits no padrão Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`, `test:`, `ci:`, `release:`, `style:`).
3. Abrir o PR para o `main`.
4. O workflow **STEH RC Validation** (`.github/workflows/ci.yml`) roda os gates de `scripts/validate_rc.py` e publica a evidência em JSON. O merge só acontece com o CI verde.
5. Fazer o merge com merge commit e apagar o branch.
6. Registrar a mudança na seção `[Unreleased]` do `CHANGELOG.md`. Se houver decisão arquitetural, criar um ADR em `docs/ADR-###-*.md`.

Mantenha os PRs pequenos e com um único propósito. Mudanças mecânicas, como formatação em massa, vão em PR separado de mudanças de lógica.

## Releases e tags

Um release candidate é cortado a partir do `main`:

1. Branch `release/vX.Y.Z-rcN`: atualizar `VERSION`, `app/version.py`, `pyproject.toml` (formato PEP 440, ex.: `1.0.0rc3`) e o teste de versão; transformar `[Unreleased]` em `[X.Y.Z-rcN] - AAAA-MM-DD`; criar `docs/releases/vX.Y.Z-rcN.md`.
2. Fazer o merge do PR com o CI verde.
3. Criar e enviar uma tag anotada no commit de merge:

   ```bash
   git switch main && git pull --ff-only
   git tag -a v1.0.0-rc4 -m "STEH v1.0.0-rc4"
   git push origin v1.0.0-rc4
   ```

4. O workflow **STEH Release Validation** (`.github/workflows/release.yml`) roda em tags `v*-alpha*` e `v*-rc*` e guarda a evidência por 90 dias.

A promoção para uma versão estável segue a regra de `docs/MVP-1.0-RC-ACCEPTANCE.md`: todo critério precisa de evidência do commit exato da tag. Veja também `docs/VERSIONING.md`.

## Regra de repositório

Não manter cópias paralelas do projeto. O histórico é preservado por:

```text
Commits + Tags + GitHub Releases + CHANGELOG + ADRs
```
