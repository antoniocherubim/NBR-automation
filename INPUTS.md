# Inputs do projeto NBR 12721

Este documento descreve o **inventário lógico** das fontes do projeto de
automação da ABNT NBR 12721:2006. Os bytes reais **não** estão mais na árvore
Git rastreada (REPO-003B).

## Organização lógica (IDs públicos)

Os IDs estáveis em `SHA256SUMS`, `manifests/source-manifest.json` e
`manifests/private-fixtures-v1.json` preservam os paths históricos:

- `inputs/normativa/` — norma de referência (PDF).
- `inputs/template/` — planilha XLSX tratada como template de saída.
- `inputs/projetos_modelo/AY0410/` — corpus inicial/golden fixture:
  - `01_implantacao/`
  - `02_estacionamento/`
  - `03_memoriais_areas/`
  - `04_torre_01/`
  - `05_torre_02/`
  - `06_cortes_fachadas/`

Esses paths são **identidades lógicas públicas**, não uma promessa de que os
bytes continuam rastreados nesses locais.

## Onde os bytes vivem agora

| Camada | Local | Git |
|--------|-------|-----|
| Store autoritativo | diretório privado externo do operador | fora do Git |
| Cópia de trabalho | `inputs/private/` (materialização verificada) | ignorado (`/inputs/private/`) |
| Inventário público | `SHA256SUMS` + manifests | rastreado (somente metadata/hashes) |

Tasks com `private_fixtures: required` materializam cópias read-only sob
`inputs/private/`, verificadas por tipo, tamanho e SHA-256. Tasks públicas
(`none`) não consultam o store nem criam essa pasta.

## Imutabilidade

Os arquivos de entrada continuam imutáveis: o projeto **nunca** escreve no
store externo e as cópias materializadas são read-only. Alterar bytes para
“passar” em hash, teste ou ZIP é proibido.

## Privacidade e histórico

Remover os originais do `HEAD` **não** sanitiza o histórico Git antigo. O
remoto atual permanece privado até a cerimônia manual **OPR-PUBLIC-001**.
Detalhes: [docs/PRIVACY.md](docs/PRIVACY.md).
