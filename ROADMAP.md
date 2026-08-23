# ROADMAP — automação determinística da ABNT NBR 12721

Status do documento: **baseline de planejamento**

Data da inspeção: **2026-08-19**
Escopo desta versão: arquitetura, pesquisa inicial, milestones, tasks e gates. O primeiro módulo funcional de infraestrutura (`nbr12721.sources`, REPO-002 integrado) registra fontes imutáveis; nenhum runtime de domínio, extração ou pipeline foi implementado.

## 1. Objetivo e critério de sucesso

O produto transforma fontes arquitetônicas heterogêneas em quadros da ABNT NBR 12721:2006 sem ocultar ausência, conflito, incerteza de extração ou decisão de engenharia:

```text
fontes imutáveis
  -> perfil/preflight das fontes
  -> evidências observadas
  -> fatos e resoluções explícitas
  -> modelo semântico do empreendimento
  -> motor normativo determinístico
  -> validações e reconciliação
  -> modelo semântico do workbook
  -> cópia preenchida do template XLSX
```

O sistema estará correto somente quando conseguir explicar, para cada valor primitivo exportado, a evidência, regra e/ou decisão que o sustenta. Produzir um XLSX sem essa explicação não é sucesso.

## 2. Gates não negociáveis

Todos os milestones e reviews devem preservar estes gates:

1. Originais privados nunca são modificados. Vivem fora do Git no store do operador e são materializados somente para tasks autorizadas em `inputs/private/`, com verificação SHA-256 permanente. A árvore rastreada após REPO-003B não contém os 14 bytes reais.
2. Valor ausente nunca vira zero, string vazia ou coeficiente default silenciosamente.
3. Decisão de engenharia nunca é inferida para permitir que o pipeline prossiga.
4. Confiança de extração não concede autoridade normativa.
5. Conflitos preservam todas as evidências relevantes e não são resolvidos por precedência implícita.
6. Todo primitivo escrito no workbook possui proveniência observada, derivada ou decidida explicitamente.
7. O motor NBR calcula independentemente das fórmulas do Excel; fórmulas e caches do template são objetos de comparação.
8. OCR é backend regional de fallback, não a arquitetura do pipeline.
9. AY0410 é fixture e corpus de desenvolvimento, não ontologia nem regra de negócio.
10. Valores de engenharia usam `Decimal`; conversão por `float` é proibida nos contratos normativos.
11. Artefatos intermediários são versionados, validáveis e serializados canonicamente.
12. Nenhuma task autoriza commit, push, deploy, integração ou execução automática da próxima task; essas ações permanecem sob controle do operador.

## 3. Achados da inspeção inicial

### 3.1 Repositório e inputs

- No início da inspeção, o diretório ainda não era um repositório Git e continha apenas `INPUTS.md`, `SHA256SUMS` e os originais; esta execução acrescentou somente este roadmap.
- Os 14 hashes conferem: norma, workbook e 12 PDFs do AY0410.
- **Boundary público:** os 14 bytes reais são privados/licenciados e não existem na árvore Git rastreada após REPO-003B. O repositório mantém inventário, hashes, contratos, código e fixtures sintéticas. O histórico antigo ainda os contém até OPR-PUBLIC-001.
- O `.gitignore` sozinho não remove objetos do histórico atual. O remoto atual deve permanecer privado; depois da migração será criado um histórico público novo a partir da árvore sanitizada, sem ancestrais contendo os originais.
- As 12 pranchas são PDFs de uma página, em formatos grandes e dimensões heterogêneas.
- Dez pranchas declaram produtor AutoCAD `pdfplot11.hdi`; duas declaram `PDFium`.
### 3.2 Norma fornecida

O PDF é a **ABNT NBR 12721:2006, segunda edição, versão corrigida 3**, que incorpora as erratas de 2007 e a Errata 3 de 19/01/2021. O título de metadados do PDF menciona 2021, mas o corpo normativo continua identificado como 2006.

Pontos que afetam diretamente o modelo:

- 3.7 classifica áreas por quatro dimensões diferentes: área real, uso, padrão de custo e forma de divisão;
- 3.7.2.1 separa área privativa principal e acessória;
- 3.7.2.2 atribui três papéis possíveis às vagas: vinculada como acessória, unidade autônoma ou área comum indeterminada;
- 3.7.3 distingue coberta-padrão, coberta de padrão diferente, descoberta e equivalente;
- 3.7.4 distingue divisão proporcional e não proporcional;
- 5.2 a 5.6 usam faces e eixos de paredes distintos conforme a categoria da área;
- 5.7.3 fornece intervalos de coeficientes médios em vários casos; o intervalo não escolhe um valor;
- 5.8.1 define as colunas 1–18 do Quadro I;
- 5.8.2 define as colunas 19–38 do Quadro II e a distribuição proporcional pela área equivalente de divisão não proporcional;
- 5.8.3 define IV-B e exige IV-B-1 em situações com áreas de terreno de uso exclusivo;
- 3.14 e 5.8.2 definem o coeficiente de proporcionalidade como a razão da coluna 30 da unidade pelo total da coluna 30.

### 3.3 Corpus AY0410

- Implantação, estacionamentos e memoriais apresentam somente cerca de 98–101 palavras nativas por prancha, quase todas ligadas às assinaturas/aprovação.
- As quatro pranchas das torres e os dois cortes têm entre 726 e 1.248 palavras nativas; há rótulos como `SACADA 7,74 M2`, áreas de apartamentos, barriletes e vazios.
- Pouco texto não significa scan: estacionamentos são fortemente vetoriais e não contêm imagens raster; no memorial coberto, uma conversão experimental para SVG revelou mais de 100 mil paths.
- Os memoriais têm tabelas, legendas, totais e contornos visualmente legíveis, mas grande parte do texto CAD foi convertida em geometria/contornos e não aparece em `pdftotext`.
- O corpus é híbrido: a implantação contém imagens; cada memorial contém uma imagem grande; um corte contém 164 objetos de imagem; várias outras pranchas não contêm imagens.
- Os memoriais municipais de áreas e as anotações de cômodos são evidência/cross-check, não resultados NBR prontos.

### 3.4 Template XLSX

- Checksum atual: `6ad3eb9b849e34cc7a419e0954d7ed817a9659d56fb213b36d83b4e78c38d19b`.
- O workbook tem 13 sheets visíveis: capa, instruções, informações preliminares e Quadros I a VIII, incluindo IV-B e IV-B.1.
- Há 1.300 células de fórmula, `calcChain.xml`, caches de cálculo e ligações entre sheets; o arquivo vazio contém 563 caches `#DIV/0!` esperados pela ausência de dados.
- Não há macros, conexões externas, proteção de sheet ou validação de dados.
- O Quadro I oferece 26 linhas de tipos de pavimento; o Quadro II e os Quadros IV-B/B.1 oferecem 23 linhas de tipos de unidade. A coluna quantidade multiplica tipos idênticos.
- As fórmulas do Quadro II arredondam coeficientes para cinco casas e rateios para duas casas.
- A própria sheet de instruções avisa que o arredondamento pode gerar diferenças entre os totais dos Quadros I e II e entre a soma dos coeficientes e `1,00000`.
- O Quadro IV-B calcula área principal como área privativa total menos uma área acessória informada separadamente; o modelo de workbook não pode perder essa distinção.
- IV-B e IV-B.1 estão simultaneamente visíveis no original, embora a norma determine seleção/substituição conforme o caso.
- O arquivo foi modificado pela Tangram em 2012 e a capa contém dados dessa empresa e de uma responsável técnica. Portanto, ele não é um template neutro ou comprovadamente oficial da ABNT.

## 4. Arquitetura proposta

### 4.1 Boundaries

```text
source registry / immutable bytes
        |
        v
PDF/XLSX adapters -----------------------------+
        |                                      |
        v                                      |
Evidence + extraction metadata                 |
        |                                      |
        v                                      |
ObservedFact -> Resolution/Decision boundary   |
        |                                      |
        v                                      |
Project/Building/Floor/Unit/AreaRecord          |
        |                                      |
        v                                      |
NBR rules + Decimal calculations               |
        |                                      |
        v                                      |
Quadro I/II/IV-B(/IV-B-1) semantic models      |
        |                                      |
        +-> validators/provenance graph <-------+
        |
        v
WorkbookModel -> versioned template adapter -> output copy
```

O domínio e o motor NBR não importam bibliotecas de PDF, OCR, planilha ou UI. Adapters produzem evidências; nunca produzem decisões normativas.

#### Boundary de fixtures privadas

Após REPO-003A/REPO-003B, os bytes reais não pertencem ao repositório da aplicação:

```text
diretório privado estável fora do Git (read-only)
        |
        | configuração local XDG, criada a partir de
        | NBR12721_PRIVATE_INPUTS pelo operador
        v
preparação local do ambiente de trabalho
        |
        | somente se a task declarar private_fixtures: required
        | valida path/tipo/tamanho/SHA-256; sem rede
        v
inputs/private/ no checkout temporário (ignorado, cópia read-only)

task pública sem marcador ----------> não consulta nem copia fixtures
fixtures sintéticas públicas -------> podem permanecer rastreadas
```

A configuração fica sob `${XDG_CONFIG_HOME:-$HOME/.config}`. Um helper explícito
recebe `NBR12721_PRIVATE_INPUTS` do operador e grava somente o path nessa
configuração. Tasks públicas não consultam esse arquivo nem copiam fixtures;
tasks privadas falham fechado quando a raiz configurada está ausente ou é
inválida.

### 4.2 Estado, autoridade e proveniência

`Evidence` registra bytes/fonte, página, região/coordenadas, backend/versão/configuração, conteúdo observado e confiança de extração quando aplicável.

`ObservedFact` interpreta evidências sem apagar as origens. Sua confiança semântica continua distinta de autoridade normativa.

`Resolution` é uma união explícita. A task `CORE-001` deve fechar a representação, preservando no mínimo:

- `OBSERVED`: há observação direta e proveniência;
- `DERIVED`: regra determinística e dependências identificadas;
- `REQUIRES_DECISION`: questão, alternativas/restrições e evidências, sem valor adotado;
- `MISSING`: obrigação conhecida e ausência demonstrada, sem valor sentinela;
- `CONFLICT`: valores incompatíveis e conjunto completo de evidências.

Uma decisão externa resolvida deve ter identidade, autor/autoridade, justificativa, escopo, instante e hash dos inputs aos quais se aplica. Ela não reescreve a observação original.

### 4.3 Taxonomia de área

`AreaRecord` deve compor dimensões ortogonais, não uma enumeração combinatória:

- vínculo espacial/entidade: empreendimento, edifício, pavimento, unidade e dependência;
- uso: privativo ou comum;
- função privativa: principal ou acessória;
- divisão: proporcional ou não proporcional;
- classe de custo: coberta-padrão, coberta de padrão diferente ou descoberta;
- área real;
- coeficiente e área equivalente, cada qual com resolução própria;
- proveniência e referência normativa.

Vagas usam um contrato próprio para o papel jurídico/normativo e projetam para `AreaRecord`; não devem ser inferidas apenas da geometria ou do rótulo `VAGA`.

### 4.4 Artefatos intermediários

Cada artefato usa envelope comum com `schema_version`, identidade do projeto, hashes das fontes, versão/configuração dos produtores e referências aos artefatos de entrada. Campos temporais/operacionais que impedem reprodução ficam fora do payload canônico.

```text
source-manifest.json
page-profiles.json
extraction.json
project.json
decisions.json            # externo e separado
nbr.json
validation-report.json
workbook-model.json
resultado.xlsx
provenance-index.json
```

Decimais são serializados como strings em forma canônica. IDs de evidência/derivação são content-addressed ou derivados deterministicamente de conteúdo estável. Schemas rejeitam campos desconhecidos na fronteira de persistência.

### 4.5 Cálculo e apresentação

O motor mantém precisão interna definida e só quantiza em boundaries explicitamente documentados. Devem existir resultados distintos para:

- cálculo normativo exato;
- valor apresentado/quantizado;
- valor encontrado no cache/fórmula do workbook.

Não se adota neste roadmap uma política de distribuição de resíduos. Primeiro, `ROUND-001` deve reproduzir e caracterizar o comportamento do template e pesquisar a base normativa; somente então uma decisão versionada autoriza `ROUND-002`.

### 4.6 Estratégia PDF

O profiler não usa uma classificação binária `texto`/`scan`. Cada página registra separadamente texto/glyphs, vetores, imagens e sinais de origem CAD. A cascata planejada é:

1. texto nativo com coordenadas;
2. tabelas e memoriais explícitos;
3. vetores, contornos e geometria;
4. OCR somente em regiões justificadas;
5. requisito de revisão/decisão quando a evidência não basta.

O sistema de coordenadas registra origem, unidade, rotação, crop/media boxes e transformação usada por cada backend.

## 5. Política das tasks

### 5.1 Escopo, revisão e documentação contínua

- Uma task só começa depois que suas dependências estiverem integradas e seus
  inputs obrigatórios tiverem sido verificados.
- Cada task tem escopo e critérios de aceitação explícitos; findings recorrentes
  exigem reavaliação do escopo ou divisão da task.
- Toda task atualiza `README.md`, `ROADMAP.md`, seu registro em `docs/tasks/` e a documentação de usuário afetada. Alteração vazia, timestamp isolado ou alegação sem evidência não satisfaz o gate.
- A documentação é escrita prioritariamente para pessoas sem conhecimento de programação, com comandos copiáveis, glossário e distinção clara entre funcionalidade disponível, planejada e bloqueada.
- Commit, push, deploy, integração, mudança de visibilidade e início da próxima
  task dependem de decisão explícita do operador.

### 5.2 Migração para publicação — OPR-PUBLIC-001

O baseline histórico versionou os originais enquanto o repositório era
privado. Portanto, remover os paths no `HEAD` não torna esse histórico
publicável.

Depois de REPO-003A e REPO-003B serem revisadas e integradas no remoto ainda privado, o operador
deve:

1. verificar que o diretório privado externo contém os 14 originais com os
   hashes esperados;
2. confirmar que a árvore integrada não rastreia PDF/XLSX real nem qualquer
   cópia sob `inputs/private/`;
3. confirmar que testes e artifact público usam somente a árvore Git
   sanitizada;
4. criar um repositório/histórico novo a partir dessa árvore, sem importar
   commits, branches, tags, PR refs ou artifacts do remoto privado;
5. inspecionar o novo histórico por extensão, path e objetos antes de alterar
   sua visibilidade;
6. manter o remoto histórico original privado ou removê-lo segundo uma decisão
   operacional separada.

OPR-PUBLIC-001 é uma cerimônia manual. REPO-003A/REPO-003B não autorizam criar remoto,
force-push, mudar visibilidade, apagar artifacts ou publicar automaticamente.

## 6. Status e dependências

- `READY_AFTER_OPR-000`: especificação pronta; falta apenas o baseline Git inicial.
- `READY`: especificação pronta e dependências satisfeitas.
- `PLANNED`: escopo definido, mas depende de artefatos anteriores.
- `WAITING_DECISION`: implementação proibida antes de uma decisão/evidência registrada.
- `BLOCKED_EXTERNAL`: requer corpus ou input ainda não fornecido.

As fases indicam capacidade, não uma fila estritamente serial. Tasks independentes podem ser executadas separadamente quando suas dependências estiverem integradas.

## 7. Milestones e tasks

### Phase 0 — Repository, contracts and research

#### REPO-001 — Bootstrap do projeto

- **Status:** `COMPLETE` (review aprovado e snapshot integrado pelo operador em 2026-08-20, commit `68e02f3`).
- **Objective:** criar o scaffold mínimo Python 3.12 e os gates locais do projeto.
- **Why it exists:** sem configuração, gates e layout de testes, mudanças posteriores não são reproduzíveis.
- **Scope:** `pyproject.toml`, layout `src/`/`tests/`, `.gitignore` e gates offline de inventário, teste e diff.
- **Out of scope:** modelos de domínio, parsers, OCR, PDF, XLSX e fórmulas NBR.
- **Dependencies:** baseline inicial e ferramentas já provisionadas; nenhuma instalação de rede durante a execução.
- **Implementation boundary:** infraestrutura local do repositório; nenhum comportamento de domínio.
- **Acceptance criteria:** bootstrap não altera rastreados; `inputs/` permanece idêntico; documentação da task/roadmap é exigida.
- **Tests/gates (evidência):** 14 hashes OK; bootstrap offline OK; 2 testes aprovados; diff sem erros de whitespace.
- **Expected artifacts:** scaffold, scripts mínimos e `docs/tasks/REPO-001.md` atualizado com evidência real — **integrados na branch canônica**.
- **Relevant source/reference:** `INPUTS.md`; este §5.

#### REPO-002 — Registro de fontes e guarda de imutabilidade

- **Status:** `COMPLETE` (review técnico aprovado na rodada 8; snapshot integrado pelo operador em 2026-08-20 no commit `06487e1`).
- **Objective:** representar cada fonte por caminho seguro, tamanho, mídia e SHA-256 e impedir output dentro de `inputs/`.
- **Why it exists:** todo ID de evidência e template deve estar vinculado aos bytes originais corretos.
- **Scope:** leitor de `SHA256SUMS`, `SourceArtifact`, validação fail-closed, allowlist de raízes de output e manifest canônico.
- **Out of scope:** conteúdo PDF/XLSX, extração, cópia ou reparo de fontes.
- **Dependencies:** REPO-001 (integrado).
- **Implementation boundary:** módulo `nbr12721.sources` sem dependência de PDF/XLSX; acesso somente leitura.
- **Acceptance criteria:** hash ausente/divergente, path traversal, symlink inesperado e tentativa de output sob `inputs/` falham; manifest é estável entre runs; contratos rejeitam paths absolutos/traversal, extensão/media_type divergentes e inteiros booleanos/Decimal; JSON Schema Draft 2020-12 descreve restrições fail-closed com `pattern`s ECMA-262 (`(?:^|/)[^/]+\\.[Pp][Dd][Ff]$` / `(?:^|/)[^/]+\\.[Xx][Ll][Ss][Xx]$`, sem flags Python `(?i)`), `artifacts.uniqueItems: true` (objetos idênticos rejeitados pelo schema e pelo contrato), filenames sem stem (`.pdf`/`.xlsx`) rejeitados pelo contrato e pelo schema, componente exatamente `.`/`..` rejeitado (paths como `.well-known/source.pdf` aceitos), extensão vinculada a `media_type`; suíte usa somente stdlib (sem Node); `.gitignore` ignora somente `/outputs/` na raiz.
- **Tests/gates (evidência do snapshot aprovado):** 14 hashes OK (0 falhas, antes e depois); bootstrap offline OK; suíte focada com 40 testes aprovados; reconstrução independente do manifest → 3254 bytes idênticos; diff sem erros de whitespace. Regressão: dois artifacts JSON idênticos rejeitados por `uniqueItems` no schema e por `validate_manifest_document`; manifest canônico aceito. `.pdf` e `.xlsx` rejeitados por `SourceArtifact`/`validate_manifest_document` e pelo JSON Schema; `.well-known/source.pdf` aceito pelos três; `.`, `./a.pdf` e `inputs/./a.pdf` rejeitados. `(?i)\\.pdf$` / `(?i)\\.xlsx$` rejeitados pelo checker stdlib de grupos ECMA-262.
- **Riscos residuais:** validação JSON Schema em produção permanece em `validate_manifest_document` (stdlib); helper de teste valida um subconjunto do schema (incluindo `uniqueItems` e rejeição sintática de grupos Python-only, sem motor JavaScript) e não substitui validador Draft 2020-12 completo até `ARCH-001`; policy de output valida destinos lógicos sob `outputs/` sem criar diretórios e verifica symlink escape apenas em componentes existentes; media types limitados a `.pdf` e `.xlsx` por mapping explícito (filenames sem stem rejeitados); superfície pública raiz expõe somente `sources` (submódulo).
- **Expected artifacts:** `schemas/source-manifest-v1.schema.json`, `manifests/source-manifest.json`, módulo `src/nbr12721/sources/` e testes dedicados — **integrados na branch canônica**.
- **Relevant source/reference:** `SHA256SUMS`, `INPUTS.md`, gate 1.

#### DOCS-001 — Documentação inicial e policy de atualização contínua

- **Status:** `COMPLETE` (retry aprovado e integrado pelo operador em 2026-08-20 no commit `03098d5`).
- **Objective:** tornar o projeto compreensível e operável por pessoas sem conhecimento de programação e tornar a atualização documental bloqueante em todas as tasks futuras.
- **Why it exists:** código correto sem orientação acessível não pode ser entregue, validado ou usado com segurança pelo público-alvo.
- **Scope:** `README.md`, índice e guias essenciais em `docs/`, glossário, privacidade, troubleshooting e testes de links/estrutura/whitespace.
- **Out of scope:** CI, release, runtime de domínio, PDF/OCR/XLSX e publicação dos inputs.
- **Dependencies:** REPO-001 e REPO-002 integradas.
- **Implementation boundary:** documentação e seus gates locais; nenhum comportamento de produto.
- **Acceptance criteria:** fluxo inicial copiável; estado real distinguido do planejado; linguagem acessível; links locais válidos; privacidade dos inputs explícita.
- **Tests/gates (evidência do snapshot aprovado):** 14 hashes OK, 0 falhas, antes/depois; bootstrap offline OK; 51 testes aprovados; 39 arquivos textuais sem trailing whitespace; diff limpo.
- **Expected artifacts:** `README.md`, guias versionados, `tests/test_documentation.py` e registro de execução — **integrados na branch canônica**.
- **Riscos residuais:** link checker limitado ao subset de docs de usuário; `pyproject.toml` readme metadata ainda aponta para `ROADMAP.md`; ambiguidade operacional exige review humano.
- **Relevant source/reference:** pedido do operador de documentação contínua; §5.1; correção de whitespace da primeira revisão.

#### CI-001 — Validação privada e artifact do repositório

- **Status:** `COMPLETE` — snapshot integrado pelo operador no merge `179a644` em 2026-08-20; primeira execução remota concluída com sucesso para esse commit.
- **Objective:** validar o commit no GitHub Actions e disponibilizar `artifact.zip` privado somente após sucesso dos gates.
- **Scope:** workflow `push` em `main` + `workflow_dispatch`; permissões mínimas (`contents: read`); actions pinadas; gates congelados; `git archive` + validação ZIP; upload direto com retenção de 7 dias; testes stdlib offline; documentação de download.
- **Out of scope:** release pública, deploy, publicação de plantas ou push automático.
- **Dependencies:** DOCS-001 (integrada).
- **Acceptance criteria:** artifact não existe quando gate falha; ZIP confronta tree Git (CRC e path-safety em **toda** entrada, inclusive diretórios; rejeita `..`/absolutos, duplicatas e diretórios inesperados); inclui snapshot rastreado exato; acesso e retenção documentados.
- **Tests/gates (evidência da implementação pós-correção reviewer, run offline):**
  - `sha256sum -c SHA256SUMS` → 14 `: SUCESSO`/`: OK`; 0 falhas (antes e depois);
  - bootstrap offline → OK (Python 3.12.3);
  - suíte do projeto → **66 passed** / 0 failed / 0 skipped (incl. 3 negativos de entradas de diretório no ZIP);
  - `git diff --check` → OK;
  - whitespace filesystem → 42 arquivos do gate documental + workflow `.yml` (43 no total amplo), 0 trailing;
  - ensaio local temporário (`git archive` HEAD + `validate-artifact-zip.py`) → 55 entradas de arquivo, 21 790 588 bytes, SHA-256 `8fd54f9229b0dc0a38ced7b75455d13ed08d655f9f4e175565347889f0ab6960` (commit-base `de577743`, árvore **sem** arquivos untracked deste candidate);
  - nenhuma rede nem execução remota durante a implementação; após merge do operador, GitHub Actions run `32382824927` para `179a644` terminou `success` em 2026-08-20.
- **Expected artifacts:** `.github/workflows/validate-and-package.yml`, `scripts/ci/validate-artifact-zip.py`, `tests/test_ci_workflow.py`, README/guias/ROADMAP/task atualizados — **integrados na branch canônica**.
- **Riscos residuais:** artifact acessível a leitores do repositório privado durante a retenção; paths Unicode exigem `core.quotePath=false` na confrontação Git/ZIP; cada commit futuro ainda depende dos gates e da disponibilidade do GitHub Actions.

#### REPO-003A — Preparação segura de fixtures privadas

- **Status:** `COMPLETE` — snapshot aprovado na rodada 6 e integrado manualmente
  pelo operador por fast-forward local no commit `eff97c1`; push de `main`
  permanece ação separada do operador.
- **Objective:** instalar, sem remover ainda os originais rastreados, o mecanismo
  seletivo que futuras tasks usarão para materializar fixtures privadas
  verificadas em checkouts temporários.
- **Why it exists:** a preparação segura precisa estar integrada antes da
  remoção dos binários, para que a migração preserve os gates de integridade.
- **Scope:** inventário público de hashes, marcador `private_fixtures`, helper
  XDG alimentado por `NBR12721_PRIVATE_INPUTS`, materializador stdlib,
  preparação/validação seletiva, testes sintéticos e documentação.
- **Out of scope:** remover ou mover os 14 originais rastreados, mudar
  CI/artifact, reescrever histórico, criar remoto público, acessar rede, alterar
  ferramentas externas ou implementar NBR/PDF/OCR/XLSX.
- **Dependencies:** REPO-001, REPO-002, DOCS-001 e CI-001 integradas.
- **Implementation boundary:** scripts locais de configuração, validação e
  materialização; nenhuma mudança no runtime público de domínio.
- **Acceptance criteria:** tasks públicas passam sem configuração; tasks
  privadas sintéticas falham sem config/root e materializam cópias
  ignoradas/read-only com config válida; path traversal, symlink, FIFO,
  diretório, tipo/tamanho/hash divergente falham; marcador vazio/duplicado/
  indentado falha (não vira `none` silencioso); staging é verificado antes da
  promoção; falha parcial restaura destino pré-existente e, na primeira
  materialização, remove destino incompleto pós-promoção; helper rejeita
  `/`/`//`, symlink com barra final, CR/newline, multiline, NUL embutido e
  qualquer checkout Git; logs de falha não revelam o root privado absoluto;
  superfície pública de `nbr12721` permanece somente `sources`; testes do
  materializador passam com `PYTHONPATH=src`; os 14
  originais rastreados permanecem byte a byte intactos nesta task.
- **Tests/gates (evidência da implementação):** `sha256sum -c` 14/14
  antes e depois; bootstrap/`validate-gate` com `private_fixtures=none`
  (bootstrap = existência do inventário; validate-gate = consistência
  canônica); `PYTHONPATH=src python3 -m unittest discover …`
  → **104 passed** / 0 failed / 0 skipped;
  `git diff --check` OK; 57 arquivos textuais sem trailing whitespace; 37
  links locais válidos; documentação e CI usam somente comandos próprios do projeto. Detalhes em `docs/tasks/REPO-003A.md`.
- **Expected artifacts:** mecanismo sob `scripts/private-fixtures/`
  (incluindo `adapter/`), inventário público e docs; runtime `src/nbr12721`
  sem pacote `private_fixtures`; nenhum binário removido — **integrados
  localmente na branch canônica**.
- **Riscos residuais:** checkouts/histórico privados ainda contêm os originais;
  CI/artifact ainda empacota `inputs/` rastreados até REPO-003B (workflow
  CI-001 inalterado, com `sha256sum` preservado no YAML); OPR-PUBLIC-001 permanece
  obrigatório antes de publicação; leftovers `.private-*` só
  apareceriam em crash extremo a meio de rename (não cobertos por
  `/inputs/private/` no `.gitignore`).
- **Relevant source/reference:** §§4.1 e 5.2;
  `SHA256SUMS`; `manifests/source-manifest.json`.

#### REPO-003B — Remoção dos originais e árvore publicável

- **Status:** `IMPLEMENTED_PENDING_COMMIT` — implementação validada localmente; commit, push e publicação permanecem com o operador.
- **Objective:** remover os 14 binários privados do tree rastreado e adaptar
  aplicação, gates e CI ao boundary já integrado.
- **Why it exists:** a árvore publicável não pode conter bytes reais; o
  histórico privado antigo será substituído por um histórico público novo em
  OPR-PUBLIC-001.
- **Scope:** remoções na árvore de trabalho (sem staging obrigatório para o gate),
  mapeamento lógico→físico em `nbr12721.sources`, gate da árvore pública,
  CI/artifact sanitizados e documentação.
- **Out of scope:** apagar o store externo, reescrever/forçar histórico, criar
  remoto, mudar visibilidade, rede, domínio NBR/PDF/XLSX.
- **Dependencies:** REPO-003A integrada; store privado configurado; 14/14
  materializados antes da remoção.
- **Implementation boundary:** `SHA256SUMS`, source-manifest e inventário
  privado permanecem byte a byte imutáveis; IDs lógicos estáveis;
  `materialize_path` é o path físico autorizado.
- **Acceptance criteria (evidência do candidate):** ver
  `docs/tasks/REPO-003B.md` — 14 deleções no snapshot candidato; zero
  `inputs/private/` rastreado; zero digest privado no snapshot; registry com
  mapping 14/14; suíte pública sem store; CI sem `sha256sum -c`; artifact
  candidato sem path/digest privado.
- **Tests/gates (evidência):**
  - materialize antes/depois → 14/14 verificados;
  - `validate-gate.py` (marker required no run) → OK;
  - `validate-public-tree.py --candidate` → files sanitizados, hits=0;
  - unittest discover → ver contagem no relatório da task;
  - `git diff --check` → OK;
  - ensaio ZIP `CANDIDATE` → entradas = snapshot, zero privados.
- **Expected artifacts:** árvore de trabalho sanitizada; checklist OPR-PUBLIC-001
  ainda pendente (histórico/remoto).
- **Riscos residuais:** histórico e remoto atuais ainda privados/contêm
  objetos antigos; integração ainda não ocorreu; OPR-PUBLIC-001 bloqueante.
- **Relevant source/reference:** REPO-003A; §§4.1 e 5.2; inventário público.

#### ARCH-001 — Envelopes e versionamento dos artefatos

- **Status:** `PLANNED`.
- **Objective:** definir envelopes, compatibilidade e serialização canônica dos estágios.
- **Why it exists:** contratos persistidos desacoplam extração, resolução, cálculo, validação e exportação.
- **Scope:** schemas v1, `schema_version`, lineage, política de campos desconhecidos, Decimal-string, IDs estáveis e separação entre payload e metadata operacional.
- **Out of scope:** implementar fatos, regras NBR ou orquestrador.
- **Dependencies:** REPO-001, REPO-002.
- **Implementation boundary:** contratos de I/O; nenhum adapter ou regra de negócio.
- **Acceptance criteria:** round-trip sem perda; serialização byte-estável; versões incompatíveis falham com diagnóstico; nenhum timestamp volátil entra no hash de conteúdo.
- **Tests/gates:** golden JSON mínimo por estágio, property tests de ordem de chaves/Decimal e testes de schema inválido.
- **Expected artifacts:** schemas/envelopes v1 e nota curta de compatibilidade.
- **Relevant source/reference:** este §4.4 e conceito `extract -> project -> nbr -> validate -> export`.

#### NBR-000 — Registro de fonte e referências normativas

- **Status:** `PLANNED` — bloqueada até integração de REPO-003B e configuração privada do operador.
- **Objective:** criar índice de regras com identidade normativa rastreável.
- **Why it exists:** toda fórmula/taxonomia deve citar a versão e seção que lhe dá autoridade.
- **Scope:** hash da norma, edição/versão corrigida, seção, página física/impressa, tipo da regra, status de formalização e notas de errata.
- **Out of scope:** transcrever a norma inteira ou implementar os Quadros.
- **Dependencies:** REPO-001, REPO-002, REPO-003B.
- **Implementation boundary:** catálogo de referências; trechos extensos/licenciados não são redistribuídos nos artefatos.
- **Acceptance criteria:** distingue 2006 de Errata 3/2021; uma regra sem referência não pode ser marcada implementada; páginas físicas e impressas não se confundem.
- **Tests/gates:** schema, IDs duplicados, referência inexistente e digest da fonte.
- **Expected artifacts:** índice normativo v1 e testes.
- **Relevant source/reference:** prefácio da NBR, seções 3.7, 3.14, 5.2–5.8 e Anexo A.

### Phase 1 — Core evidence and resolution model

#### CORE-001 — Evidence, ObservedFact, Resolution e DecisionRequirement

- **Status:** `PLANNED`.
- **Objective:** formalizar os contratos que separam observação, interpretação, derivação e decisão.
- **Why it exists:** é a barreira principal contra palpites e perda de proveniência.
- **Scope:** tagged unions, estados mínimos, confiança de extração/semântica, obrigações, conflitos e questões decidíveis.
- **Out of scope:** entidades do empreendimento, regras NBR e UI de revisão.
- **Dependencies:** ARCH-001, NBR-000.
- **Implementation boundary:** núcleo puro; sem imports de PDF/OCR/XLSX.
- **Acceptance criteria:** `MISSING` não carrega zero; `CONFLICT` preserva múltiplas evidências; `REQUIRES_DECISION` não carrega valor adotado; toda observação aponta para `SourceArtifact`.
- **Tests/gates:** construção válida/inválida de cada variante, round-trip e imutabilidade dos registros.
- **Expected artifacts:** contratos, schemas e testes unitários.
- **Relevant source/reference:** gates 2–6; este §4.2.

#### CORE-003 — Grafo de derivação e índice de proveniência

- **Status:** `PLANNED`.
- **Objective:** modelar derivação determinística como DAG consultável.
- **Why it exists:** responder “por que esta célula vale X?” exige mais que um campo `source`.
- **Scope:** nós de evidência/fato/decisão/regra/cálculo/exportação, arestas tipadas, IDs content-addressed e detecção de ciclos.
- **Out of scope:** visualizador e armazenamento em banco.
- **Dependencies:** CORE-001, ARCH-001.
- **Implementation boundary:** grafo puro e serializável; adapters apenas adicionam nós permitidos.
- **Acceptance criteria:** derivações listam regra e operands; ciclos/refs ausentes falham; traversal reproduz a árvore até fontes/decisões.
- **Tests/gates:** DAG pequeno, diamond dependency, ciclo, missing node e estabilidade de ID.
- **Expected artifacts:** `provenance-index` v1, API de traversal e testes.
- **Relevant source/reference:** regra de proveniência do projeto; NBR-000.

#### CORE-004 — Política Decimal, quantização e comparação

- **Status:** `PLANNED`.
- **Objective:** definir operações decimais comuns sem escolher política de resíduos.
- **Why it exists:** `float`, context global e arredondamento implícito rompem reprodutibilidade.
- **Scope:** parsing pt-BR/canônico em boundaries, context local, escala/unidade, quantização nomeada e comparação exata/apresentada.
- **Out of scope:** distribuição de resíduos e regras específicas dos quadros.
- **Dependencies:** ARCH-001.
- **Implementation boundary:** módulo numérico puro.
- **Acceptance criteria:** nenhum caminho normativo aceita `float`; JSON preserva Decimal; modo de rounding sempre explícito; locale não afeta cálculo.
- **Tests/gates:** casos de fronteira positivos/negativos, trailing zeros, locale e serialização.
- **Expected artifacts:** tipos/utilitários Decimal e política documentada.
- **Relevant source/reference:** gate 10; template, instruções C12 e fórmulas `ROUND` do Quadro II.

### Phase 2 — NBR domain model and taxonomies

#### CORE-002 — Project, Building, Floor, Unit, AreaRecord e ParkingSpace

- **Status:** `PLANNED`.
- **Objective:** implementar o modelo semântico mínimo do empreendimento.
- **Why it exists:** regras NBR não devem operar diretamente sobre células ou rótulos de PDF.
- **Scope:** hierarquia, IDs, pertencimento, multiplicidade de tipos, áreas e vagas com proveniência/resolução.
- **Out of scope:** taxonomia normativa final, cálculos dos Quadros e heurísticas AY0410.
- **Dependencies:** CORE-001, CORE-003, CORE-004.
- **Implementation boundary:** domínio puro e independente de adapters.
- **Acceptance criteria:** IDs únicos; relações não órfãs; quantidades positivas; área negativa proibida; nenhum campo obrigatório indefinido é convertido em default.
- **Tests/gates:** builders válidos/inválidos, duplicidade, orphan, multiplicidade e round-trip.
- **Expected artifacts:** contratos de domínio e testes.
- **Relevant source/reference:** NBR 3.4–3.7; modelo conceitual deste roadmap.

#### NBR-001 — Taxonomia formal de áreas

- **Status:** `PLANNED`.
- **Objective:** formalizar as dimensões normativas sem enumerações combinatórias ou categorias inventadas pelo template.
- **Why it exists:** uso, divisão e classe de custo são independentes e alimentam colunas diferentes.
- **Scope:** privativa/comum, principal/acessória, proporcional/não proporcional, coberta-padrão/diferente/descoberta e mapeamentos válidos.
- **Out of scope:** coeficientes escolhidos, fórmulas dos quadros e geometria.
- **Dependencies:** CORE-002, NBR-000.
- **Implementation boundary:** taxonomia e validadores de combinação no domínio NBR.
- **Acceptance criteria:** cada conceito cita regra; combinação inválida falha; `AreaRecord` não perde a categoria original; mapping para colunas é testável sem XLSX.
- **Tests/gates:** matriz de combinações, casos de uso comum/privativo e referências obrigatórias.
- **Expected artifacts:** taxonomy v1, mapping semântico de colunas e testes.
- **Relevant source/reference:** NBR 3.7.1–3.7.4 e 5.8.1–5.8.2.

#### NBR-COEF-001 — Coeficientes de equivalência e requisitos de decisão

- **Status:** `PLANNED`.
- **Objective:** representar coeficiente demonstrado, coeficiente médio permitido e coeficiente ainda não adotado.
- **Why it exists:** intervalos normativos não autorizam escolha automática de midpoint, mínimo ou máximo.
- **Scope:** faixa, unidade/categoria, justificativa de custo, referência, decisão requerida e cálculo `área real × coeficiente` após resolução.
- **Out of scope:** UI, política organizacional de escolha e OCR.
- **Dependencies:** CORE-001, CORE-004, NBR-001.
- **Implementation boundary:** regra determinística somente após coeficiente resolvido.
- **Acceptance criteria:** faixa sem decisão produz `REQUIRES_DECISION`; valor fora da faixa exige justificativa/autoridade explícita ou conflito; coeficiente zero não nasce de missing.
- **Tests/gates:** exemplos de varanda, garagem, terraço, barrilete e custo demonstrado.
- **Expected artifacts:** contrato de coeficientes, rule IDs e testes.
- **Relevant source/reference:** NBR 5.7.1–5.7.3.

### Phase 3 — Deterministic Quadro I engine

#### NBR-002 — Modelo e calculador determinístico do Quadro I

- **Status:** `PLANNED`.
- **Objective:** projetar `AreaRecord`s por pavimento nas colunas semânticas 1–18 e calcular totais globais.
- **Why it exists:** estabelece a primeira saída normativa independente do workbook.
- **Scope:** multiplicidade de pavimentos idênticos, áreas reais/equivalentes, colunas 2–18 e lineage de cada soma.
- **Out of scope:** Quadro II, rateio proporcional, células XLSX e resíduos de arredondamento.
- **Dependencies:** NBR-001, NBR-COEF-001, CORE-003, CORE-004.
- **Implementation boundary:** função pura `Project -> QuadroIModel | unresolved report`.
- **Acceptance criteria:** não calcula com coeficiente unresolved; totais seguem 5.8.1; entradas vazias não viram zero; cada total tem derivação.
- **Tests/gates:** exemplos pequenos manuais, multiplicidade, categorias completas, missing/conflict e invariantes de soma.
- **Expected artifacts:** `QuadroIModel`, calculador, JSON v1 e testes.
- **Relevant source/reference:** NBR 5.8.1, Anexo A/Quadro I.

### Phase 4 — Deterministic Quadro II engine

#### NBR-003 — Quadro II, distribuição proporcional e coeficientes

- **Status:** `PLANNED`.
- **Objective:** calcular colunas 19–38 e distribuir áreas comuns proporcionais por unidade/tipo.
- **Why it exists:** conecta unidades à área global e gera coeficientes de proporcionalidade.
- **Scope:** áreas privativas, comuns não proporcionais, coluna 30, coeficiente, rateio 32–36, totais 37–38 e quantidades.
- **Out of scope:** política final de resíduos, fórmulas Excel e IV-B.
- **Dependencies:** NBR-002, CORE-002, CORE-004.
- **Implementation boundary:** cálculo exato e apresentação separados; denominador zero é erro/unresolved tipado.
- **Acceptance criteria:** fórmula da coluna 31 segue 5.8.2; soma exata dos shares é verificável antes de quantização; totais reconciliam com Quadro I no modelo exato; nenhuma divisão por zero é mascarada.
- **Tests/gates:** unidades iguais/diferentes, quantidade, área proporcional zero, denominador zero, coeficientes e cross-table exact totals.
- **Expected artifacts:** `QuadroIIModel`, calculador, JSON v1 e testes.
- **Relevant source/reference:** NBR 3.14 e 5.8.2; Quadro II do template.

### Phase 5 — Quadro IV-B and cross-table invariants

#### NBR-004 — Projeção do Quadro IV-B

- **Status:** `PLANNED`.
- **Objective:** projetar áreas principal, acessória, comum, total e coeficiente por unidade.
- **Why it exists:** IV-B é a visão para registro/escrituração e exige semântica não contida integralmente no Quadro II.
- **Scope:** colunas A–G, quantidades, vagas nos três papéis e proveniência até Quadros I/II/domínio.
- **Out of scope:** terreno exclusivo/IV-B-1 e escrita XLSX.
- **Dependencies:** NBR-003, NBR-001.
- **Implementation boundary:** projection pura; área acessória nunca é inferida por subtração sem fato resolvido.
- **Acceptance criteria:** B+C=D, D+E=F; vagas vão à coluna correta conforme resolução; totais e coeficientes referenciam Quadro II.
- **Tests/gates:** unidade com/sem acessório, cada papel de vaga, conflito de vinculação e invariantes.
- **Expected artifacts:** `QuadroIVBModel`, projection e testes.
- **Relevant source/reference:** NBR 3.7.2.1–3.7.2.2 e 5.8.3; template `QUADRO IV B`.

#### NBR-005 — Seleção IV-B/IV-B-1 e invariantes cruzados

- **Status:** `PLANNED`.
- **Objective:** modelar áreas de terreno e selecionar explicitamente a variante correta.
- **Why it exists:** exportar ambos ou escolher por heurística contradiz 5.8.3.
- **Scope:** requisito de decisão/critério aplicável, colunas adicionais de terreno, projeção IV-B-1 e suíte de invariantes I/II/IV-B.
- **Out of scope:** manipulação de visibilidade de sheets e rateio de resíduos.
- **Dependencies:** NBR-004.
- **Implementation boundary:** seleção semântica anterior ao adapter XLSX.
- **Acceptance criteria:** exatamente uma variante aplicável; terreno total fecha; ausência de critério produz unresolved; inconsistências cross-table são reportadas, não corrigidas.
- **Tests/gates:** edifício comum, conjunto com terreno exclusivo, critério missing e totais incompatíveis.
- **Expected artifacts:** `RegistrationAreaSummary` e regras de validação.
- **Relevant source/reference:** NBR 5.8.3 nota 1; template `QUADRO IV B.1`.

### Phase 6 — XLSX template adapter

#### XLSX-001 — Mapa formal e fingerprint do template

- **Status:** `PLANNED`.
- **Objective:** transformar a inspeção manual em mapping versionado e testado.
- **Why it exists:** referências de células não podem se espalhar nem sobreviver silenciosamente a drift do template.
- **Scope:** sheets, regiões, células de input/fórmula/output, fórmulas, estilos/merges relevantes, capacidades, aliases IV-B.1 e fingerprint estrutural + SHA-256.
- **Out of scope:** preencher valores ou recalcular Excel.
- **Dependencies:** REPO-002, ARCH-001.
- **Implementation boundary:** módulo de introspecção/mapping OOXML; sem regra NBR.
- **Acceptance criteria:** checksum/fingerprint divergente bloqueia; 13 sheets e 1.300 fórmulas são inventariadas; limites 26/23 são explícitos; nenhuma célula mágica aparece fora do mapping.
- **Tests/gates:** template real read-only, cópia com alteração estrutural, sheet/célula ausente e fórmula alterada.
- **Expected artifacts:** `template-map` v1, relatório machine-readable e testes.
- **Relevant source/reference:** XLSX fornecido; instruções C12, C37, C54/C59/C61/C67.

#### XLSX-002 — WorkbookModel e binding semântico

- **Status:** `PLANNED`.
- **Objective:** mapear modelos NBR para campos conceituais do workbook antes de coordenadas físicas.
- **Why it exists:** separa domínio, modelo dos quadros e layout externo.
- **Scope:** chaves semânticas, tipo/formato, source/provenance ID, sheet variant e plano de escrita.
- **Out of scope:** I/O do XLSX, fórmulas e expansão de linhas.
- **Dependencies:** NBR-005, XLSX-001.
- **Implementation boundary:** `NBR models -> WorkbookModel`; coordenadas só no template binding.
- **Acceptance criteria:** todo primitivo tem provenance ID; campos unresolved não entram no write plan; overflow de capacidade falha fechado.
- **Tests/gates:** mappings I/II/IV-B/B.1, campo sem proveniência, variante incorreta e overflow.
- **Expected artifacts:** `WorkbookModel`, binding semântico e testes.
- **Relevant source/reference:** este §4.1; template sheets I, II, IV-B e IV-B.1.

#### XLSX-003 — Escritor não destrutivo do template

- **Status:** `PLANNED`.
- **Objective:** escrever uma cópia em diretório de output preservando o original e estruturas não mapeadas.
- **Why it exists:** exportação precisa ser auditável e não pode depender de edição manual.
- **Scope:** cópia verificada, writes allowlisted, seleção/omissão da variante IV-B, metadata de output e package digest determinístico.
- **Out of scope:** calcular fórmulas e expandir capacidade estrutural.
- **Dependencies:** XLSX-002.
- **Implementation boundary:** adapter OOXML; recebe somente `WorkbookModel` resolvido.
- **Acceptance criteria:** original mantém hash; só células/props allowlisted mudam; fórmulas/estilos não alvo permanecem; output repetido tem package digest estável.
- **Tests/gates:** diff estrutural OOXML, hash before/after, golden mínimo, path traversal e escrita proibida.
- **Expected artifacts:** exporter, output fixture e relatório de writes.
- **Relevant source/reference:** checksum do template; gate 1; NBR 5.8.3.

#### XLSX-004 — Read-back e confronto engine/workbook

- **Status:** `PLANNED`.
- **Objective:** reler o output e comparar engine, fórmulas e caches/recalculo do workbook.
- **Why it exists:** fórmula do template é evidência de compatibilidade, não autoridade do motor.
- **Scope:** valores escritos, fórmulas preservadas, cached values, backend opcional de recalculo isolado e relatório de diferenças.
- **Out of scope:** aceitar automaticamente divergência ou usar LibreOffice/Excel no motor.
- **Dependencies:** XLSX-003, VAL-001.
- **Implementation boundary:** validator/adapter; nenhum resultado de planilha alimenta cálculo normativo.
- **Acceptance criteria:** diferenças exatas e de apresentação são separadas; cache stale é detectado; recalculador indisponível gera status explícito, não sucesso falso.
- **Tests/gates:** workbook sem recalculo, cache alterado, fórmula alterada e comparação de valores conhecidos.
- **Expected artifacts:** read-back report e testes.
- **Relevant source/reference:** `calcChain.xml`, fórmulas `ROUND`, instruções C37.

### Phase 7 — PDF profiler and native extraction

#### PDF-001 — Profiler de todas as páginas do AY0410

- **Status:** `PLANNED`.
- **Objective:** caracterizar todas as páginas por texto, vetores, imagens, boxes, rotação e origem provável.
- **Why it exists:** a escolha de backend deve se basear em sinais mensuráveis, não no nome do arquivo ou em `word_count` isolado.
- **Scope:** interface de backend, métricas por página, thresholds configurados/explicados e output versionado sobre as 12 pranchas.
- **Out of scope:** extrair fatos, OCR e classificação normativa.
- **Dependencies:** REPO-002, ARCH-001.
- **Implementation boundary:** adapter PDF + profiler; sem domínio NBR ou regra AY0410.
- **Acceptance criteria:** cobre 12/12 páginas; distingue texto, paths e imagens; não classifica estacionamentos vetoriais como scans só por pouco texto; registra backend/versão.
- **Tests/gates:** PDFs sintéticos text/vector/raster/hybrid, determinismo, corpus completo e hash dos inputs inalterado.
- **Expected artifacts:** `page-profiles.json`, profiler e relatório do corpus.
- **Relevant source/reference:** achados §3.3; cascata §4.6.

#### PDF-002 — Texto nativo e coordenadas normalizadas

- **Status:** `PLANNED`.
- **Objective:** extrair glyph/word/span nativos com geometria e ordem preserváveis.
- **Why it exists:** áreas e rótulos das torres já são acessíveis sem OCR.
- **Scope:** interface `NativeTextBackend`, boxes originais/normalizados, rotação, Unicode, lineage e evidências por span/word.
- **Out of scope:** tabelas, inferência semântica, vetores em contorno e OCR.
- **Dependencies:** PDF-001, CORE-001.
- **Implementation boundary:** backend produz `Evidence`, não `AreaRecord`.
- **Acceptance criteria:** coordenadas round-trip; texto vazio é explícito; ordem não é tratada como verdade única; extrai casos reais `SACADA` e áreas sem hardcode de coordenadas.
- **Tests/gates:** PDFs sintéticos rotacionados/crop, Unicode, corpus torre 01/02 e determinismo.
- **Expected artifacts:** evidências de texto nativo e testes de conformance.
- **Relevant source/reference:** pranchas 0007–0012; este §4.6.

### Phase 8 — Structured evidence extraction

#### EXT-001 — Normalização e deduplicação de evidências

- **Status:** `PLANNED`.
- **Objective:** unificar outputs de backends sem apagar origem ou confiança.
- **Why it exists:** texto, vetor e OCR podem observar o mesmo rótulo e não devem criar fatos independentes silenciosos.
- **Scope:** normalization, fingerprints regionais, links `same-observation-candidate` e política conservadora de dedup.
- **Out of scope:** preferência automática por backend e resolução de conflito.
- **Dependencies:** CORE-001, PDF-002; interfaces GEO/OCR podem aderir depois.
- **Implementation boundary:** evidência normalizada; nenhuma autoridade normativa.
- **Acceptance criteria:** dedup mantém todas as fontes; evidências discordantes viram candidatos a conflito; confiança não decide valor.
- **Tests/gates:** observações coincidentes, sobrepostas, divergentes e backends diferentes.
- **Expected artifacts:** `extraction.json` v1 e testes.
- **Relevant source/reference:** distinção incerteza/indeterminação; CORE-001.

#### EXT-002 — Extração de candidatos textuais e tabelas explícitas

- **Status:** `PLANNED`.
- **Objective:** produzir candidatos tipados para rótulo, área, pavimento, unidade e metadados a partir de conteúdo explícito.
- **Why it exists:** memoriais e anotações são fontes prioritárias antes de reconstrução geométrica.
- **Scope:** parsers locale-aware, associação espacial, tabelas nativas quando disponíveis e evidências de linha/célula/região.
- **Out of scope:** declarar valor NBR, escolher coeficiente e heurística por filename/posição AY0410.
- **Dependencies:** EXT-001, CORE-004.
- **Implementation boundary:** candidatos/ObservedFacts; mapeamento para domínio ocorre depois.
- **Acceptance criteria:** `7,74 m²` preserva literal e Decimal; associação ambígua produz conflito/questão; tabela sem header confiável não é inventada.
- **Tests/gates:** layouts sintéticos, locale, múltiplos rótulos próximos e exemplos das torres.
- **Expected artifacts:** parsers, candidatos tipados e testes.
- **Relevant source/reference:** pranchas 0007–0010; memoriais 0005/0006 como futura entrada regional.

#### EXT-003 — Construção/reconciliação do modelo semântico

- **Status:** `PLANNED`.
- **Objective:** transformar fatos observados em `Project` parcial, preservando missing/conflict/decision requirements.
- **Why it exists:** múltiplas fontes precisam se encontrar antes do motor NBR.
- **Scope:** identity matching, constraints, reconciliação sem precedência silenciosa e relatório de cobertura.
- **Out of scope:** decisão humana, regra específica AY0410 e cálculo dos quadros.
- **Dependencies:** CORE-002, EXT-002, DEC-001.
- **Implementation boundary:** resolver semântico; backends e motor permanecem separados.
- **Acceptance criteria:** fonte duplicada não duplica unidade; valores incompatíveis viram `CONFLICT`; obrigações ausentes viram `MISSING`; nenhuma aproximação por tolerância é implícita.
- **Tests/gates:** merge consistente, conflito, missing, identidade ambígua e fixture sintética multi-source.
- **Expected artifacts:** `project.json` parcial e reconciliation report.
- **Relevant source/reference:** CORE-001/002; gates 2–5.

### Phase 9 — Geometry layer

#### GEO-001 — Extração de primitivas vetoriais PDF

- **Status:** `PLANNED`.
- **Objective:** expor paths, strokes, fills, clipping e transforms como evidência geométrica.
- **Why it exists:** seis pranchas relevantes têm texto/diagramas convertidos em vetores e pouco texto nativo.
- **Scope:** backend vetorial, limites de complexidade, coordenadas e provenance de objetos.
- **Out of scope:** reconhecer todos os glyphs, fechar polígonos NBR ou interpretar layers CAD ausentes.
- **Dependencies:** PDF-001, EXT-001.
- **Implementation boundary:** adapter PDF; nenhum conceito de parede/área NBR.
- **Acceptance criteria:** páginas complexas não explodem recursos; transforms/clips são aplicados corretamente; output é determinístico e limitado.
- **Tests/gates:** shapes sintéticos, curvas, clips, página memorial e resource limits.
- **Expected artifacts:** vector evidence v1, backend e testes.
- **Relevant source/reference:** memoriais 0005/0006 e estacionamentos 0002–0004.

#### GEO-002 — Escala, topologia e candidatos de ambientes

- **Status:** `PLANNED`.
- **Objective:** reconstruir segmentos/contornos candidatos com unidade e escala explícitas.
- **Why it exists:** primitives PDF não equivalem diretamente a paredes ou perímetros.
- **Scope:** calibração por cotas/escala resolvida, snapping parametrizado, topologia, holes e incertezas geométricas.
- **Out of scope:** aplicar faces/eixos NBR ou “consertar” contorno aberto por palpite.
- **Dependencies:** GEO-001, CORE-001.
- **Implementation boundary:** modelo geométrico intermediário; resultado ambíguo permanece unresolved.
- **Acceptance criteria:** escala tem evidência; contorno aberto/ambíguo não gera área; tolerâncias são parte da configuração/proveniência.
- **Tests/gates:** polígonos/holes, escalas, gaps abaixo/acima do limite e propriedades geométricas.
- **Expected artifacts:** geometry model v1 e testes.
- **Relevant source/reference:** NBR 5.2–5.6; pranchas vetoriais do corpus.

#### GEO-003 — Delimitação de áreas segundo 5.2–5.6

- **Status:** `PLANNED`.
- **Objective:** calcular áreas reais usando faces/eixos corretos para cada categoria resolvida.
- **Why it exists:** soma de rótulos de cômodos não substitui critério normativo de delimitação.
- **Scope:** regras de perímetro, paredes externas/contíguas, vazios/shafts e derivação geométrica auditável.
- **Out of scope:** inferir categoria de uso, coeficiente e reparar projeto incompleto.
- **Dependencies:** GEO-002, NBR-001, CORE-003.
- **Implementation boundary:** geometry + rule IDs -> `Observed/Derived area candidates`.
- **Acceptance criteria:** cada segmento de boundary explica regra/face/eixo; vazios são excluídos; conflito com memorial é reportado como constraint.
- **Tests/gates:** plantas sintéticas para 5.2–5.6, paredes compartilhadas, shafts e cross-check de áreas anotadas.
- **Expected artifacts:** area geometry engine e provenance detalhada.
- **Relevant source/reference:** NBR 5.2–5.6 e 5.7.2.1.1(b).

### Phase 10 — OCR fallback adapters

#### OCR-001 — Contrato de OCR regional

- **Status:** `PLANNED`.
- **Objective:** definir request/result de OCR para regiões justificadas pelo profiler/extrator.
- **Why it exists:** evita acoplamento a Tesseract e OCR indiscriminado de páginas gigantes.
- **Scope:** região, render transform, idioma, preprocessing declarado, tokens/boxes/confiança e backend metadata.
- **Out of scope:** escolher motor universal, classificar fatos ou executar OCR full-page por default.
- **Dependencies:** PDF-001, CORE-001, EXT-001.
- **Implementation boundary:** interface adapter; outputs são `Evidence` de extração.
- **Acceptance criteria:** mapeia boxes ao PDF; confiança não vira autoridade; request sem justificativa/limites falha; backend ausente é capability explícita.
- **Tests/gates:** fake backend, rotação/escala, limites de região e schema.
- **Expected artifacts:** OCR port, conformance suite e testes.
- **Relevant source/reference:** §4.6; achados dos memoriais.

#### OCR-002 — Primeiro adapter OCR e seleção localizada

- **Status:** `PLANNED`.
- **Objective:** implementar um adapter provisionado externamente e regras determinísticas de seleção de regiões.
- **Why it exists:** recuperar tabelas/rótulos em contornos/raster onde texto/vetor semântico não basta.
- **Scope:** capability probe, adapter (Tesseract somente se validado), render regional e comparação com evidência nativa/vetorial.
- **Out of scope:** fallback silencioso, download de modelos no run e decisão NBR.
- **Dependencies:** OCR-001, GEO-001, EXT-002.
- **Implementation boundary:** plugin/backend opcional; núcleo funciona e reporta ausência sem ele.
- **Acceptance criteria:** nenhum acesso de rede; versão/configuração registrada; regiões dos memoriais têm avaliação medida; erro/confiança baixa não preenche domínio.
- **Tests/gates:** fixtures raster, memoriais, fake failure, determinismo e limites de recursos.
- **Expected artifacts:** adapter, benchmark report e testes.
- **Relevant source/reference:** PDFs 0005/0006; gate 8.

### Phase 11 — Human decision/review boundary

#### DEC-001 — Manifest de requisitos de decisão

- **Status:** `PLANNED`.
- **Objective:** exportar questões técnicas/missing/conflicts de forma machine-readable.
- **Why it exists:** pipeline deve pausar com informação acionável, não com exceção opaca ou palpite.
- **Scope:** pergunta, contexto, alternativas/intervalos, evidências, rule IDs, criticidade e hash do estado base.
- **Out of scope:** UI web, assinatura criptográfica e sugestão automática de resposta.
- **Dependencies:** CORE-001, ARCH-001, NBR-COEF-001.
- **Implementation boundary:** boundary de saída; não resolve nada.
- **Acceptance criteria:** requisito tem contexto suficiente; não contém resposta default; muda de ID quando inputs materiais mudam.
- **Tests/gates:** coeficiente em faixa, vaga ambígua, missing obrigatório e conflito multi-source.
- **Expected artifacts:** `decision-requirements.json` v1 e testes.
- **Relevant source/reference:** estados mínimos; NBR 3.7.2.1.2 nota 2 e 5.7.3.

#### DEC-002 — Ingestão e aplicação de decisões externas

- **Status:** `PLANNED`.
- **Objective:** validar respostas explícitas e produzir `Resolution` auditável.
- **Why it exists:** decisão é input versionado, não mutação manual escondida no workbook.
- **Scope:** schema, autoridade/justificativa, binding ao requirement/input hash, revogação/substituição e provenance node.
- **Out of scope:** autenticação corporativa, UI e resolver automaticamente conflitos.
- **Dependencies:** DEC-001, CORE-003.
- **Implementation boundary:** ingestão separada; observações permanecem imutáveis.
- **Acceptance criteria:** decisão stale/fora de escopo falha; resolução aponta para autor e requirement; substituir decisão preserva histórico.
- **Tests/gates:** resposta válida, stale, requirement desconhecido, autor ausente e supersession.
- **Expected artifacts:** `decisions.json` v1, resolver e testes.
- **Relevant source/reference:** regra de proveniência; este §4.2.

### Phase 12 — Validation and reconciliation

#### VAL-001 — Motor de validação e relatório estruturado

- **Status:** `PLANNED`.
- **Objective:** executar invariantes com severidade, localização, lineage e resultado reproduzível.
- **Why it exists:** validação precisa ser produto auditável, não apenas assertions dispersos.
- **Scope:** catálogo de checks, pass/fail/unresolved/not-applicable, totals I/II, coeficientes, IDs, áreas e readiness de exportação.
- **Out of scope:** corrigir dados ou escolher tolerâncias/resíduos.
- **Dependencies:** NBR-005, CORE-003, ARCH-001.
- **Implementation boundary:** validator read-only sobre artifacts.
- **Acceptance criteria:** cada finding cita regra e nós; unresolved difere de fail; export bloqueia em severidades definidas; ordem do relatório é estável.
- **Tests/gates:** todos os invariantes conceituais, casos pass/fail/unresolved e golden report.
- **Expected artifacts:** `validation-report.json` v1, rule registry e testes.
- **Relevant source/reference:** gates; NBR 5.8.1–5.8.3.

#### ROUND-001 — Caracterização de arredondamento e resíduos

- **Status:** `PLANNED`.
- **Objective:** documentar empiricamente onde e como norma/template/apresentação divergem por quantização.
- **Why it exists:** o template avisa que seus próprios totais/coeficientes podem não fechar exatamente.
- **Scope:** reprodução das fórmulas 2/5 casas, cenários de resíduos, pesquisa normativa, comparação Excel/LibreOffice/engine e alternativas de política.
- **Out of scope:** selecionar ou implementar a política final.
- **Dependencies:** NBR-003, XLSX-001, CORE-004.
- **Implementation boundary:** pesquisa/test vectors; nenhuma correção em runtime.
- **Acceptance criteria:** demonstra casos de diferença I/II e soma ≠ 1,00000; separa exact/presented/workbook; registra se a norma é silenciosa.
- **Tests/gates:** vetores mínimos reproduzíveis, fórmulas do template e relatório revisável.
- **Expected artifacts:** relatório de decisão e dataset de casos.
- **Relevant source/reference:** instruções C12/C37; Quadro II N17:Q39; NBR 5.8.2.

#### ROUND-002 — Reconciliação determinística aprovada

- **Status:** `WAITING_DECISION`.
- **Objective:** implementar apenas a política explicitamente aprovada após ROUND-001.
- **Why it exists:** resíduos precisam de tratamento reproduzível sem alterar silenciosamente autoridade normativa.
- **Scope:** algoritmo, tie-break determinístico, provenance de ajustes, limites e apresentação.
- **Out of scope:** escolher a política durante implementação ou alterar valores observados.
- **Dependencies:** ROUND-001 e decisão registrada via DEC-002.
- **Implementation boundary:** camada de apresentação/reconciliação; exact result permanece disponível.
- **Acceptance criteria:** soma apresentada fecha conforme decisão; ajuste total e destinatários são explicáveis; mesmos inputs geram mesmos ajustes.
- **Tests/gates:** empates, sinais, múltiplos resíduos, propriedade de conservação e golden do decision record.
- **Expected artifacts:** reconciler, rule/decision ID e testes.
- **Relevant source/reference:** output de ROUND-001 e decisão externa vinculada.

#### PROV-001 — Gate de completude de proveniência

- **Status:** `PLANNED`.
- **Objective:** provar que nenhum primitivo exportável termina em origem desconhecida.
- **Why it exists:** provenance parcial falha o objetivo central mesmo com totais corretos.
- **Scope:** traversal completo, allowlist de constantes puramente algébricas/layout e relatório por campo/célula sem depender de coordenada espalhada.
- **Out of scope:** visualizar o grafo e validar semanticamente a decisão humana.
- **Dependencies:** CORE-003, XLSX-002, VAL-001, DEC-002.
- **Implementation boundary:** gate read-only antes do exporter.
- **Acceptance criteria:** todo leaf é fonte imutável, regra+operands ou decisão externa; nó órfão/ciclo bloqueia export; report responde por semantic field e célula mapeada.
- **Tests/gates:** workbook mínimo completo, leaf desconhecido, decisão stale e constante allowlisted.
- **Expected artifacts:** provenance completeness report e testes.
- **Relevant source/reference:** gates 5–6; regra “por que esta célula vale X?”.

### Phase 13 — AY0410 golden dataset

#### AY-001 — Curadoria da fixture e ground truth revisado

- **Status:** `PLANNED`.
- **Objective:** separar fontes, observações verificadas, expectativas e decisões específicas do AY0410.
- **Why it exists:** golden sem origem independente apenas congela bugs/heurísticas.
- **Scope:** manifest, amostra anotada, lineage, perguntas abertas e decision file separado com reviewer técnico identificado.
- **Out of scope:** promover nomes/coordenadas do AY0410 a regra geral e preencher lacunas por inferência.
- **Dependencies:** PDF-002, EXT-002, GEO-001, OCR-002, DEC-002.
- **Implementation boundary:** fixtures/test data; nenhuma regra em `src/` pode consultar project ID.
- **Acceptance criteria:** cada expected value aponta para fonte/decisão; ambiguidades permanecem explicitadas; licença/dados pessoais não são duplicados desnecessariamente.
- **Tests/gates:** linter anti-hardcode, manifest/hash, coverage report e revisão humana registrada.
- **Expected artifacts:** fixture metadata, annotations, decisions e ground-truth report.
- **Relevant source/reference:** `inputs/projetos_modelo/AY0410`; gate 9.

#### AY-002 — Golden dos modelos NBR e workbook

- **Status:** `PLANNED`.
- **Objective:** congelar outputs aprovados dos Quadros e exportação para o corpus.
- **Why it exists:** fornece regressão E2E auditável sobre caso real.
- **Scope:** `project/nbr/validation/workbook-model`, output XLSX semantic digest e provenance queries selecionadas.
- **Out of scope:** exigir resolução das questões ainda não decididas ou validar generalização.
- **Dependencies:** AY-001, ROUND-002, XLSX-004, PROV-001.
- **Implementation boundary:** golden tests; outputs regeneráveis, fontes permanecem em `inputs/`.
- **Acceptance criteria:** regeneração controlada; JSON canônico idêntico; XLSX estrutural/semanticamente idêntico; divergência exige review explícito.
- **Tests/gates:** full golden suite, duas execuções, hashes e queries “por quê?”.
- **Expected artifacts:** golden artifacts e relatório de atualização.
- **Relevant source/reference:** artifacts de AY-001 e template versionado.

### Phase 14 — Full E2E pipeline

#### PIPE-001 — Orquestrador de estágios como biblioteca

- **Status:** `PLANNED`.
- **Objective:** compor estágios explícitos, retomáveis e idempotentes sem esconder artifacts.
- **Why it exists:** o pipeline conceitual precisa de execução reproduzível sem acoplar regras a uma CLI prematura.
- **Scope:** API de aplicação, dependency checks, output dirs atômicos, cache por content hash, stop-on-unresolved e run manifest.
- **Out of scope:** CLI pública, fila distribuída, agentes/LLMs no runtime e decisão automática.
- **Dependencies:** ARCH-001, EXT-003, NBR-005, VAL-001, XLSX-003, PROV-001.
- **Implementation boundary:** application layer; cada estágio continua testável isoladamente.
- **Acceptance criteria:** pode executar/parar/recomeçar por artifact; unresolved bloqueia fases dependentes; output parcial não é publicado como completo.
- **Tests/gates:** fake stages, failure atomicity, cache invalidation, idempotência e ausência de writes em inputs.
- **Expected artifacts:** pipeline API, run manifest e testes.
- **Relevant source/reference:** este §1 e §4.4.

#### PIPE-002 — E2E AY0410 até XLSX auditável

- **Status:** `PLANNED`.
- **Objective:** executar todas as fases disponíveis sobre AY0410 e produzir output ou requisitos de decisão completos.
- **Why it exists:** valida integração real sem esconder gaps do corpus.
- **Scope:** preflight, extração, decisions, domínio, Quadros, validação, workbook, read-back e provenance queries.
- **Out of scope:** declarar sucesso se decisões/ground truth faltarem e generalizar com uma fixture.
- **Dependencies:** PIPE-001, AY-002.
- **Implementation boundary:** teste E2E; nenhum branch específico AY0410 em produção.
- **Acceptance criteria:** resultado reproduzível; zero findings críticos; originals intactos; cada workbook primitive explicável; runtime não usa LLM.
- **Tests/gates:** duas execuções isoladas, golden, checksum, structural XLSX diff e validation/provenance reports.
- **Expected artifacts:** bundle E2E versionado fora de `inputs/`.
- **Relevant source/reference:** AY-002 e todos os gates.

### Phase 15 — Generalization and adversarial fixtures

#### GEN-001 — Segundo empreendimento independente

- **Status:** `BLOCKED_EXTERNAL`.
- **Objective:** validar contratos e regras em corpus que não compartilhe estrutura/nomenclatura do AY0410.
- **Why it exists:** uma fixture não demonstra generalização.
- **Scope:** ingestão read-only, profiles, coverage/gaps, decisões e regressões de domínio.
- **Out of scope:** alterar regra geral para “fazer passar” o novo corpus sem base normativa.
- **Dependencies:** PIPE-002 e fornecimento autorizado de segundo corpus/ground truth.
- **Implementation boundary:** fixture externa e testes; mudanças no core exigem task própria com referência geral.
- **Acceptance criteria:** nenhum detector usa project ID; gaps são tipados; comparação documenta o que generalizou e o que não.
- **Tests/gates:** suíte E2E nos dois projetos, anti-hardcode e provenance.
- **Expected artifacts:** segunda fixture e generalization report.
- **Relevant source/reference:** gate 9; corpus externo ainda ausente.

#### GEN-002 — Fixtures adversariais e variantes de template

- **Status:** `PLANNED`.
- **Objective:** testar falha fechada em PDFs/workbooks/dados limítrofes.
- **Why it exists:** robustez auditável depende de recusar estados perigosos, não só aceitar happy paths.
- **Scope:** raster puro, híbrido, rotação, texto em contorno, unidades duplicadas, coeficiente missing/conflict, overflow 26/23, template drift e resíduos.
- **Out of scope:** fuzzing de segurança irrestrito e suporte automático a qualquer template.
- **Dependencies:** PIPE-002, XLSX-004, ROUND-002.
- **Implementation boundary:** fixtures sintéticas sem dados do AY0410.
- **Acceptance criteria:** cada caso tem erro/unresolved esperado; nenhum crash vira output parcial; variante não suportada informa capability.
- **Tests/gates:** matrix adversarial, property tests e resource limits.
- **Expected artifacts:** corpus sintético, expected reports e capability matrix.
- **Relevant source/reference:** riscos do §8 e limites observados do template/corpus.

## 8. Riscos, desconhecidos e decisões pendentes

1. **Ground truth técnico:** não foi fornecido um conjunto NBR preenchido/aprovado para AY0410. Os memoriais municipais não substituem validação por profissional habilitado.
2. **Coeficientes:** a norma oferece intervalos; as escolhas reais do empreendimento ainda não estão nas fontes identificadas.
3. **Papel das vagas:** desenho e contagem não determinam se cada vaga é acessória, autônoma ou comum.
4. **Geometria:** texto de áreas de ambientes não incorpora necessariamente projeções/eixos/shafts exigidos por 5.2–5.6.
5. **Texto vetorizado:** uma parte importante do corpus requer vetor/contorno ou OCR localizado, mesmo sem raster de página inteira.
6. **Arredondamento:** norma e template não fornecem, na inspeção inicial, uma política suficiente de reconciliação; o template admite diferenças.
7. **Capacidade XLSX:** 26 tipos de pavimento e 23 tipos de unidade podem ser insuficientes para outros projetos. O primeiro adapter deve bloquear overflow; expansão dinâmica é trabalho posterior.
8. **Autoria do template:** dados Tangram na capa e metadata exigem decisão sobre limpeza/substituição autorizada; não devem aparecer inadvertidamente em entrega final.
9. **Recalculo:** caches do workbook vazio têm `#DIV/0!`; bibliotecas OOXML normalmente não calculam fórmulas. Read-back deve distinguir cache stale de cálculo real.
10. **Ferramentas:** o host atual possui Poppler e LibreOffice, mas não possui `openpyxl`, PyMuPDF, pypdf ou pdfplumber no Python global. Dependências deverão ser fixadas e provisionadas fora dos runs, sem download implícito.
11. **Licença/privacidade:** a norma contém marca d'água de exemplar licenciado e as plantas contêm assinaturas/dados pessoais. Artefatos e logs devem minimizar reprodução desses dados.
12. **Única fixture:** thresholds e heurísticas do profiler/extrator não podem ser considerados gerais antes de GEN-001.

## 9. Divergências e reconciliações encontradas

- **Nome/metadata da norma:** o arquivo é corretamente NBR 12721:2006; “2021” no metadata reflete a versão corrigida 3/Errata 3, não uma nova edição normativa.
- **Invariante exata vs. template:** o domínio deve reconciliar Quadros I/II e shares exatos, enquanto o workbook arredonda e avisa que valores apresentados podem divergir. VAL-001 distingue exato/apresentado; ROUND-001 precede qualquer política.
- **IV-B vs. IV-B.1:** o prompt enfatiza IV-B; norma e template exigem também a variante IV-B-1 e seleção exclusiva conforme o empreendimento.
- **Template externo vs. template neutro:** o XLSX é externo e checksumado, mas contém branding/dados Tangram e limitações fixas; não pode ser tratado como formulário oficial neutro.
- **Pouco texto vs. scan:** as primeiras seis pranchas têm pouco texto nativo, mas várias são vetoriais. O profiler não pode usar `word_count` como decisão de OCR.
- **Áreas anotadas vs. áreas NBR:** o corpus confirma a necessidade de manter anotações/memoriais como evidência/constraint até que a delimitação normativa seja resolvida.

## 10. Ordem das próximas tasks

Estado da infraestrutura e sequência planejada:

1. `REPO-002` — registro/imutabilidade das fontes (**integrada em 2026-08-20 no commit `06487e1`**);
2. `DOCS-001` — documentação inicial e enforcement contínuo (**integrada em 2026-08-20 no commit `03098d5`**);
3. `CI-001` — validação privada e `artifact.zip` (**integrada; primeira execução remota verde em 2026-08-20**);
4. `REPO-003A` — preparação segura de fixtures privadas (**integrada localmente em 2026-08-20 no commit `eff97c1`**);
5. `REPO-003B` — remoção dos originais e árvore publicável (**candidate_complete em 2026-08-20; integração pendente do operador**);
6. `NBR-000` — registro de referências normativas (**materializada, bloqueada por integração de REPO-003B**);
7. `ARCH-001` — envelopes e versionamento;
8. `PDF-001` — profiler do corpus, após REPO-002/REPO-003B/ARCH-001;
9. `XLSX-001` — mapa formal do template, após REPO-002/REPO-003B/ARCH-001.

`CORE-001` é a primeira task de domínio e fica pronta assim que `ARCH-001` e `NBR-000` estiverem integradas. `NBR-002`, `NBR-003`, `NBR-004`, exportação XLSX, OCR e E2E não devem ser antecipadas.
