# Versionamento

STEH usa Semantic Versioning para versões públicas e PEP 440 para o pacote Python.

```text
vMAJOR.MINOR.PATCH-PRERELEASE
```

Exemplos:

```text
v0.1.0-alpha
v0.2.0-alpha
v0.2.1-alpha
v0.3.0-alpha
v1.0.0-rc1
v1.0.0-rc2
v1.0.0-rc3
v1.0.0-rc4
```

## MINOR
Nova capacidade funcional ou arquitetural significativa.

## PATCH
Hardening, correção, observabilidade, CI, migrations ou refactor sem novo domínio funcional.

## Release candidate

Uma tag `vX.Y.Z-rcN` identifica uma candidata à versão estável. A promoção exige
CI verde e evidência de validação vinculada ao commit exato da tag.

No `pyproject.toml`, o equivalente PEP 440 omite o hífen:

```text
Tag/versão pública: v1.0.0-rc4
Pacote Python:      1.0.0rc4
```

## Baseline
Somente a versão mais recente é operacional. As anteriores permanecem acessíveis por tags/releases.
