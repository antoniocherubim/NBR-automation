# Primeiros passos

Este guia ajuda a **validar o ambiente local** sem instalar dependências pela
rede e sem modificar o store privado. Execute os comandos a partir da **raiz
do repositório** (onde estão `README.md` e `SHA256SUMS`).

## 1. Confirmar ferramentas

```bash
python3 --version
git --version
bash --version
command -v sha256sum
```

| Ferramenta | Versão mínima | Observação |
|------------|---------------|------------|
| Python | 3.12 | Obrigatório para compilar e testar |
| Git | qualquer recente | Controle de versão e snapshot candidato |
| Bash | qualquer recente | Scripts de configuração das fixtures privadas |
| sha256sum | GNU/coreutils | Usado pelo materializador/adapter, não pela CI pública |

Os scripts **não instalam** pacotes nem acessam a internet.

## 2. Gates públicos (sem store)

Após REPO-003B, a verificação pública **não** executa `sha256sum -c SHA256SUMS`
(os bytes não estão mais rastreados). Use:

```bash
python3 scripts/private-fixtures/validate-gate.py
python3 scripts/ci/validate-public-tree.py --candidate
```

- **validate-gate.py** — reconcilia inventário privado, `SHA256SUMS` e
  source-manifest (metadata). Opera no modo público e não materializa fixtures privadas.
- **validate-public-tree.py --candidate** — examina o snapshot de trabalho
  (HEAD menos deleções no disco, mais arquivos novos não ignorados), sem
  exigir `git add`. Falha se houver path histórico, `inputs/private/`
  rastreado ou digest de fixture privada.

## 3. Preparar fixtures privadas (somente quando necessário)

Configure e materialize o store conforme a seção 5. Os gates públicos não executam essa etapa.

## 4. Executar testes

```bash
PYTHONPATH=src:scripts/private-fixtures python3 -m unittest discover -s tests -p 'test_*.py' -v
```

A suíte pública usa fixtures sintéticas/temporárias e **não** depende do
store real.

## 5. Tasks privadas (`private_fixtures: required`)

Configure o store (fora do Git, fora do run):

```bash
NBR12721_PRIVATE_INPUTS="/caminho/absoluto/para/nbr12721-private-inputs" \
  bash scripts/private-fixtures/configure.sh
bash scripts/private-fixtures/configure.sh --check
```

Materialize e verifique:

```bash
PYTHONPATH=src:scripts/private-fixtures python3 scripts/private-fixtures/materialize.py
```

O registro de fontes verifica os bytes em `materialize_path` preservando o ID
lógico. O módulo `nbr12721.sources` recebe o mapeamento do chamador; não lê
XDG.

## 6. Regras importantes

### Não edite o store nem force hashes

Originais no store externo e cópias em `inputs/private/` são imutáveis.
Não altere bytes para “passar” em teste, ZIP ou policy.

### Árvore sanitizada ≠ histórico sanitizado

Este repositório público nasceu sem os commits antigos que continham os 14 PDFs/XLSX. O repositório histórico anterior deve permanecer privado e separado.

### Commit e integração são do operador

`APPROVED` técnico **não** integra automaticamente.

### CI — gates sem store

A workflow **Validate and Package** está **Disponível**. Sua primeira execução
no GitHub terminou com sucesso após o merge do operador (baseline CI-001).
A workflow opera sobre a árvore pública sanitizada:

1. corre `validate-gate`, `compileall`, `unittest`, `git diff --check` e
   `validate-public-tree.py --commit "$GITHUB_SHA"`;
2. **não** executa `sha256sum -c SHA256SUMS`;
3. gera `artifact.zip` do commit e valida ausência de path/digest privado;
4. publica artifact privado com retenção de **7 dias**, contendo somente a
   árvore sanitizada.

**Baixar:** Actions → artifact, ou `gh run download <run-id> -n artifact.zip`.

Ensaio local do ZIP a partir do snapshot candidato (sem staging):

```bash
python3 - <<'PY'
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path[:0] = ["src", "scripts/ci"]
from candidate_snapshot import candidate_file_map, write_candidate_zip

files = candidate_file_map(Path("."), base="HEAD")
with tempfile.TemporaryDirectory() as tmp:
    zip_path = Path(tmp) / "artifact-candidate.zip"
    write_candidate_zip(Path("."), zip_path, files)
    result = subprocess.run(
        [
            "python3",
            "scripts/ci/validate-artifact-zip.py",
            str(zip_path),
            "CANDIDATE",
        ],
        check=False,
    )
    print("entradas", len(files), "exit", result.returncode)
    raise SystemExit(result.returncode)
PY
```

## 7. Próximos passos

- Arquitetura: [CONCEPTS.md](CONCEPTS.md)
- Termos: [GLOSSARY.md](GLOSSARY.md)
- Roadmap: [ROADMAP.md](../ROADMAP.md)
- Privacidade: [PRIVACY.md](PRIVACY.md)
