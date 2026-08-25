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
> O índice normativo v1 (`NBR-000`) está **disponível**: catálogo de autoridade
> (seção/página/tipo/estado) sem regras executáveis nem transcrição da norma.
> O envelope comum v1 (`ARCH-001`) está **disponível**: recipiente versionado,
> JSON canônico, Decimal-string e identidade por conteúdo.
> O profiler PDF v1 (`PDF-001`) está **disponível** neste worktree candidato
> (`candidate_complete`; integração **pendente** do operador): artefato
> `page-profiles` sobre as 12 pranchas AY0410, backend Poppler (subprocessos
> com cwd temporário restritivo; rejeição de symlink na entrada; parsers
> fail-closed para SVG/`pdftotext`/`pdffonts`/`pdfimages`/`pdfinfo` truncados,
> incompletos, com múltiplas `<page>` por pedido de página única, `Pages:`
> duplicados ou linhas `pdfimages` cortadas após `bpc`; timeout SVG mata o
> filho mesmo em erro de parse) e guias em `docs/PDF_PROFILING.md`.
> Payloads de extração semântica permanecem **planejados**.
> OPR-PUBLIC-001 criou este histórico público novo, com um único commit raiz
> sanitizado. **Publicação** do histórico só foi autorizada depois de
> REPO-003B + OPR-PUBLIC-001; o repositório **não** deve ser tornado público
> sem essas tasks. O histórico privado anterior continua separado.

## O que já funciona

| Capacidade | Status | Descrição breve |
|------------|--------|-----------------|
| Scaffold Python 3.12 e gates offline | **Disponível** | Estrutura `src/`/`tests/`, scripts de bootstrap e teste sem rede |
| Registro determinístico das 14 fontes | **Disponível** | `nbr12721.sources`: IDs lógicos, mapeamento explícito para path físico, manifest canônico |
| Índice normativo v1 (autoridade) | **Disponível** | `nbr12721.normative` + `registries/normative-reference-index.json` (NBR-000) |
| Envelope comum de artefatos v1 | **Disponível** | `nbr12721.artifacts` + schema/goldens (ARCH-001); payload de domínio opaco |
| Profiler PDF page-profiles v1 | **Disponível** (candidate; integração pendente) | `nbr12721.pdf`, `profiles/page-profiles.json`, Poppler (PDF-001) |
| Inventário público de fixtures privadas | **Disponível** | `manifests/private-fixtures-v1.json` (metadata/hashes; sem bytes) |
| Helper + materializador privado | **Disponível** | `scripts/private-fixtures/` (XDG; cópias read-only em `inputs/private/`) |
| Árvore Git sanitizada (sem PDFs/XLSX reais) | **Disponível** | REPO-003B remove os 14 originais da árvore Git rastreada |
| Gate da árvore pública | **Disponível** | `scripts/ci/validate-public-tree.py` (commit ou snapshot candidato) |
| Documentação inicial para usuários | **Disponível** | README, guias em `docs/` e teste stdlib de estrutura/links |
| Workflow CI validate-and-package | **Disponível** | Gates públicos sem store; `artifact.zip` só com árvore sanitizada |
| Publicação / histórico sanitizado | **Disponível** | OPR-PUBLIC-001 concluída; histórico público independente |

Detalhes técnicos: tasks `REPO-001` … `REPO-003B`, `OPR-PUBLIC-001`, `NBR-000`
e `ARCH-001` — ver [ROADMAP.md](ROADMAP.md).

## O que ainda não funciona

| Capacidade | Status |
|------------|--------|
| Payloads semânticos por estágio (extraction/project/NBR/…) | **Planejada** |
| Extração semântica de PDF e OCR | **Planejada** |
| Motor normativo e cálculo dos Quadros I/II/IV-B | **Planejada** |
| Preenchimento e exportação do template XLSX | **Planejada** |
| Pipeline ponta a ponta até `resultado.xlsx` | **Planejada** |
| Interface gráfica ou CLI de produto | **Planejada** |
| Remoto/histórico público | **Disponível** |

Consulte o [roadmap completo](ROADMAP.md) para milestones, dependências e gates.

## Fluxo futuro (visão geral)

```text
fontes imutáveis (store privado → inputs/private/ quando required)
  → perfil e verificação das fontes (ID lógico preservado)
  → índice normativo (autoridade por seção; já disponível)
  → evidências extraídas dos PDFs
  → fatos observados e resoluções explícitas
  → modelo do empreendimento
  → motor normativo determinístico
  → validações e reconciliação
  → modelo semântico da planilha
  → cópia preenchida do template XLSX
```

Hoje estão implementados o registro de fontes, o boundary privado, a árvore
rastreada sanitizada, o catálogo normativo v1, o envelope comum v1 e o profiler
PDF `page-profiles` v1 (`nbr12721.pdf`, Poppler) — não o pipeline de domínio nem
os payloads semânticos de cada estágio.

## Pré-requisitos

Estes itens devem estar **já provisionados** no ambiente; os scripts **não**
instalam pacotes nem acessam a rede:

- Python **3.12 ou superior**
- Git
- Bash
- `sha256sum` (utilitário GNU/coreutils)
- Poppler (`pdfinfo`, `pdftotext`, `pdffonts`, `pdfimages`, `pdftocairo`) —
  **obrigatório** na descoberta pública de `unittest` (PDFs sintéticos, sem skip)
  e também para regenerar/conferir `page-profiles` sobre fixtures privadas

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
- **unittest** executa a suíte offline **sem** store privado, mas **exige
  Poppler local** para os testes sintéticos de `tests/test_pdf_profiler.py`
  (não há skip oportunista).

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
| Artifact sanitizado | **Disponível** |
| Histórico Git público sanitizado | **Disponível** (OPR-PUBLIC-001) |

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

**Histórico público sanitizado.** Este repositório nasceu de um snapshot
sanitizado e não possui os ancestrais privados. Ele **não** podia ser tornado
público até REPO-003B + OPR-PUBLIC-001; essas tasks já estão **Disponíveis**
neste histórico. O repositório histórico anterior deve permanecer separado e
privado.

## Mapa da documentação

| Documento | Para quem | Conteúdo |
|-----------|-----------|----------|
| [docs/README.md](docs/README.md) | Todos | Índice por necessidade |
| [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md) | Iniciantes | Preparação e validação passo a passo |
| [docs/CONCEPTS.md](docs/CONCEPTS.md) | Leitores curiosos | Arquitetura em linguagem acessível |
| [docs/GLOSSARY.md](docs/GLOSSARY.md) | Todos | Termos técnicos e do projeto |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Operadores | Falhas conhecidas e recuperação |
| [docs/PRIVACY.md](docs/PRIVACY.md) | Todos | Cuidados com dados sensíveis |
| [docs/NORMATIVE_INDEX.md](docs/NORMATIVE_INDEX.md) | Desenvolvedores / revisores | Uso do índice normativo v1 |
| [docs/ARTIFACT_VERSIONING.md](docs/ARTIFACT_VERSIONING.md) | Desenvolvedores / revisores | Envelope comum v1 e compatibilidade |
| [docs/PDF_PROFILING.md](docs/PDF_PROFILING.md) | Desenvolvedores / operadores | Profiler PDF v1 (PDF-001) |
| [docs/PDF_CORPUS_PROFILE.md](docs/PDF_CORPUS_PROFILE.md) | Revisores | Agregados do corpus AY0410 |
| [ROADMAP.md](ROADMAP.md) | Planejamento | Milestones, tasks e gates |
| [docs/tasks/ARCH-001.md](docs/tasks/ARCH-001.md) | Desenvolvimento | Envelopes (integrado) |
| [docs/tasks/NBR-000.md](docs/tasks/NBR-000.md) | Desenvolvimento | Catálogo normativo (integrado) |
| [docs/tasks/PDF-001.md](docs/tasks/PDF-001.md) | Desenvolvimento | Profiler PDF (`candidate_complete`; não integrado) |

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
