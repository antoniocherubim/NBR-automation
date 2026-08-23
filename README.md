# Automação determinística da ABNT NBR 12721:2006

Este repositório desenvolve um sistema para transformar fontes
arquitetônicas (PDFs de plantas, norma de referência e template de planilha)
em quadros da ABNT NBR 12721:2006, preservando evidência, proveniência e
decisões explícitas para cada valor exportado.

> **Estado inicial e experimental.** O produto ainda **não** calcula quadros
> normativos, **não** lê PDFs semanticamente e **não** preenche planilhas.
> A workflow de CI (`CI-001`) está **disponível** e sua primeira execução no
> GitHub terminou com sucesso após o merge do operador.
> O boundary de fixtures privadas (`REPO-003A` + `REPO-003B`) está **disponível**
> na árvore atual: inventário público, materialização em `inputs/private/` e
> árvore Git **sem** os 14 bytes reais rastreados.
> O histórico antigo **ainda contém** esses bytes; somente OPR-PUBLIC-001
> cria um histórico público novo. Não altere a visibilidade do remoto atual.

## O que já funciona

| Capacidade | Status | Descrição breve |
|------------|--------|-----------------|
| Scaffold Python 3.12 e gates offline | **Disponível** | Estrutura `src/`/`tests/`, scripts de bootstrap e teste sem rede |
| Registro determinístico das 14 fontes | **Disponível** | `nbr12721.sources`: IDs lógicos, mapeamento explícito para path físico, manifest canônico |
| Inventário público de fixtures privadas | **Disponível** | `manifests/private-fixtures-v1.json` (metadata/hashes; sem bytes) |
| Helper + materializador privado | **Disponível** | `scripts/private-fixtures/` (XDG; cópias read-only em `inputs/private/`) |
| Árvore Git sanitizada (sem PDFs/XLSX reais) | **Disponível** | REPO-003B remove os 14 originais da árvore Git rastreada |
| Gate da árvore pública | **Disponível** | `scripts/ci/validate-public-tree.py` (commit ou snapshot candidato) |
| Documentação inicial para usuários | **Disponível** | README, guias em `docs/` e teste stdlib de estrutura/links |
| Workflow CI validate-and-package | **Disponível** | Gates públicos sem store; `artifact.zip` só com árvore sanitizada |
| Publicação / histórico sanitizado | **Bloqueada** | OPR-PUBLIC-001 após integração desta árvore |

Detalhes técnicos: tasks `REPO-001` … `REPO-003B` — ver [ROADMAP.md](ROADMAP.md).

## O que ainda não funciona

| Capacidade | Status |
|------------|--------|
| Leitura/extração de PDF (texto, vetores, OCR) | **Planejada** |
| Motor normativo e cálculo dos Quadros I/II/IV-B | **Planejada** |
| Preenchimento e exportação do template XLSX | **Planejada** |
| Pipeline ponta a ponta até `resultado.xlsx` | **Planejada** |
| Registro de referências normativas | **Bloqueada** até integração de REPO-003B |
| Interface gráfica ou CLI de produto | **Planejada** |
| Remoto/histórico publicável | **Bloqueada** (OPR-PUBLIC-001) |

Consulte o [roadmap completo](ROADMAP.md) para milestones, dependências e gates.

## Fluxo futuro (visão geral)

```text
fontes imutáveis (store privado → inputs/private/ quando required)
  → perfil e verificação das fontes (ID lógico preservado)
  → evidências extraídas dos PDFs
  → fatos observados e resoluções explícitas
  → modelo do empreendimento
  → motor normativo determinístico
  → validações e reconciliação
  → modelo semântico da planilha
  → cópia preenchida do template XLSX
```

Hoje estão implementados o registro de fontes, o boundary privado e a árvore
rastreada sanitizada — não o pipeline de domínio.

## Pré-requisitos

Estes itens devem estar **já provisionados** no ambiente; os scripts **não**
instalam pacotes nem acessam a rede:

- Python **3.12 ou superior**
- Git
- Bash
- `sha256sum` (utilitário GNU/coreutils)

## Início rápido

Execute a partir da **raiz deste repositório**:

```bash
python3 scripts/private-fixtures/validate-gate.py
python3 scripts/ci/validate-public-tree.py --candidate
PYTHONPATH=src:scripts/private-fixtures python3 -m unittest discover -s tests -p 'test_*.py' -v
```

Interpretação:

- **validate-gate.py** confere a consistência canônica entre inventário
  privado, `SHA256SUMS` e source-manifest (somente metadata). O comando valida apenas a metadata pública e não materializa o store privado.
- **validate-public-tree.py --candidate** confirma que o snapshot de trabalho
  não contém paths/digests dos 14 originais (sem exigir `git add`).
- **unittest** executa a suíte offline; **não** depende do store privado.

Para tasks `private_fixtures: required`, materialize e verifique antes:

```bash
PYTHONPATH=src:scripts/private-fixtures python3 scripts/private-fixtures/materialize.py
```

Passo a passo: [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md).

## CI e artifact (`CI-001` + REPO-003B)

A workflow `.github/workflows/validate-and-package.yml` valida o commit com
gates que funcionam em checkout **sem** store privado e **sem**
`sha256sum -c SHA256SUMS`. Depois do gate da árvore pública, gera
`artifact.zip` via `git archive` do commit e valida o ZIP (paths históricos,
`inputs/private/`, digests privados, traversal, duplicatas, CRC).

O pacote contém **somente** a árvore sanitizada (código, inventários, testes,
docs). **Não** inclui norma, template nem plantas. Retenção: **7 dias**.

| Aspecto | Estado |
|---------|--------|
| Workflow versionada | **Disponível** |
| Artifact sanitizado | **Disponível** após integração da REPO-003B |
| Histórico Git sanitizado | **Bloqueada** (OPR-PUBLIC-001) |

**Como baixar após uma execução bem-sucedida:**

1. GitHub → **Actions** → **Validate and Package** → **Artifacts**.
2. Ou: `gh run download <run-id> -n artifact.zip`

Detalhes: [docs/PRIVACY.md](docs/PRIVACY.md).

## Pasta `inputs/` — IDs lógicos vs bytes privados

Os IDs em `SHA256SUMS` / manifests continuam apontando para paths históricos
(`inputs/normativa/...`, etc.), mas esses arquivos **não** estão mais
rastreados. Os bytes vivem no store externo do operador e, em tasks
autorizadas, em `inputs/private/` (ignorado pelo Git).

| Marcador | Comportamento |
|----------|----------------|
| `none` (ou chave ausente em tasks históricas) | Não lê config XDG, não toca no store, não cria `inputs/private/` |
| `required` | Exige config/root válidos e materializa cópias read-only verificadas |
| vazio / duplicado / desconhecido / indentado | Falha fail-closed |

```bash
NBR12721_PRIVATE_INPUTS="/caminho/absoluto/para/nbr12721-private-inputs" \
  bash scripts/private-fixtures/configure.sh
bash scripts/private-fixtures/configure.sh --check
```

O registro `nbr12721.sources` recebe do chamador um mapeamento total
ID lógico → `materialize_path`; não lê XDG nem importa o mecanismo de configuração privada.

**Árvore sanitizada ≠ histórico sanitizado.** Este repositório ainda não pode
ser tornado público. OPR-PUBLIC-001 cria o histórico novo.

## Mapa da documentação

| Documento | Para quem | Conteúdo |
|-----------|-----------|----------|
| [docs/README.md](docs/README.md) | Todos | Índice por necessidade |
| [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md) | Iniciantes | Preparação e validação passo a passo |
| [docs/CONCEPTS.md](docs/CONCEPTS.md) | Leitores curiosos | Arquitetura em linguagem acessível |
| [docs/GLOSSARY.md](docs/GLOSSARY.md) | Todos | Termos técnicos e do projeto |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Operadores | Falhas conhecidas e recuperação |
| [docs/PRIVACY.md](docs/PRIVACY.md) | Todos | Cuidados com dados sensíveis |
| [ROADMAP.md](ROADMAP.md) | Planejamento | Milestones, tasks e gates |
| [docs/tasks/REPO-003B.md](docs/tasks/REPO-003B.md) | Desenvolvimento | Evidência desta migração |

## Como relatar um problema

1. Descreva o comando e a mensagem de erro **sem** anexar originais, plantas,
   norma ou dados pessoais.
2. Inclua versão do Python e resultado resumido dos gates (inventário, árvore
   pública e testes).
3. Indique a task no [ROADMAP.md](ROADMAP.md) quando possível.

## Roadmap e licença

- **Roadmap e status das tasks:** [ROADMAP.md](ROADMAP.md)
- **Licença de distribuição:** ainda **não definida**. Não redistribua bytes
  privados listados no inventário.
