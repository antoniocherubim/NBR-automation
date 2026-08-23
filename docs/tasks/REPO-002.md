---
id: REPO-002
status: candidate_complete
depends_on:
  - REPO-001
---

# REPO-002 — Registro de fontes e guarda de imutabilidade

## Objetivo

Implementar o registro determinístico e somente leitura das fontes originais, representando cada arquivo listado em `SHA256SUMS` por caminho seguro, tamanho em bytes, tipo de mídia e SHA-256 verificado.

Também deve ser criada uma policy fail-closed para impedir que callers selecionem `inputs/` como destino de artefatos gerados.

## Contexto

`REPO-001` está integrado e forneceu o scaffold Python 3.12, o Project Adapter e os gates offline. Este é o primeiro módulo funcional do projeto, mas continua pertencendo à infraestrutura de fontes: ele identifica bytes e protege boundaries de filesystem sem interpretar o conteúdo arquitetônico, normativo ou tabular.

O arquivo `SHA256SUMS` é o inventário autoritativo do corpus atual. Ele contém 14 entradas:

- a norma;
- o template XLSX; e
- 12 PDFs do projeto-modelo AY0410.

Todo acesso desta task aos arquivos originais é estritamente para metadata, abertura read-only e cálculo/verificação de digest. O fato de uma fonte ter extensão PDF ou XLSX não autoriza parse, renderização ou inspeção semântica.

O run deve usar o profile integrado e um SHA-base explícito:

```bash
../codex-cursor-agent-loop/agent-loop run \
  --repo "$PWD" \
  --require-profile \
  docs/tasks/REPO-002.md 3 "$BASE_SHA"
```

Não usar `--allow-candidate-profile`: esta task não altera `.agent-loop/project.toml` nem qualquer outra parte do Project Adapter.

## Princípios preservados

- `inputs/` é imutável e nunca é destino de output.
- Hash divergente, fonte ausente, path inseguro ou tipo de arquivo inesperado bloqueia a operação.
- Ausência não é convertida em registro vazio, zero ou placeholder.
- O manifest contém somente dados estáveis; não contém path absoluto, timestamp de execução ou metadata volátil.
- AY0410 é identificado como fonte, não usado para criar regra específica.
- O módulo não conhece NBR, domínio, PDF, OCR, geometria, workbook ou pipeline.
- O harness permanece externo, inalterado e sob controle do operador.

## Escopo permitido

### 1. Contrato `SourceArtifact`

Criar um value object imutável de infraestrutura, conceitualmente chamado `SourceArtifact`, com no mínimo:

- `path`: caminho POSIX relativo à raiz do repositório, normalizado e preservando Unicode;
- `sha256`: digest hexadecimal lowercase com exatamente 64 caracteres;
- `size_bytes`: inteiro não negativo obtido do mesmo arquivo regular verificado;
- `media_type`: valor determinístico obtido por mapping explícito e versionado das extensões atualmente suportadas.

Nesta versão, os tipos suportados são:

- `.pdf` → `application/pdf`;
- `.xlsx` → `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`.

Extensão desconhecida deve falhar com diagnóstico explícito. Não usar detecção dependente do host/locale nem interpretar o conteúdo para descobrir o tipo.

O contrato não inclui estado de resolução, confiança, conteúdo extraído, regra normativa ou provenance graph. Esses elementos pertencem a tasks posteriores.

### 2. Parser estrito de `SHA256SUMS`

Implementar parser determinístico para o formato realmente versionado no repositório:

```text
<64 hex lowercase><dois espaços><caminho relativo UTF-8>
```

O parser deve:

- preservar espaços e caracteres Unicode do path;
- rejeitar linha malformada, hash inválido, path vazio, path duplicado e entrada duplicada;
- rejeitar path absoluto, `.`/`..`, componente vazio anômalo, NUL, backslash usado como separador e qualquer path que escape da raiz;
- não executar shell expansion, glob, variável, escape ou command substitution;
- ordenar o manifest pelo path POSIX usando regra determinística, independentemente da ordem das entradas recebidas.

Não implementar parser genérico de todos os formatos possíveis do GNU `sha256sum`; aceitar somente o subset documentado e testado acima.

### 3. Verificação fail-closed das fontes

Para cada entrada:

- resolver o path sob a raiz real do repositório;
- exigir arquivo regular;
- rejeitar symlink no alvo e escape por symlink em componente de diretório;
- abrir somente para leitura e, quando suportado pelo host, usar mecanismo no-follow;
- calcular SHA-256 em streaming, sem carregar arquivos grandes integralmente em memória;
- obter `size_bytes` do arquivo efetivamente aberto/verificado;
- comparar digest calculado com o digest declarado usando comparação apropriada;
- falhar antes de publicar manifest quando qualquer entrada estiver ausente, ilegível, não regular ou divergente.

O resultado nunca pode conter artifact parcialmente verificado.

### 4. Manifest canônico v1

Criar um manifest versionado com estrutura mínima:

```json
{
  "schema_version": 1,
  "artifacts": [
    {
      "path": "inputs/...",
      "sha256": "...",
      "size_bytes": 123,
      "media_type": "application/pdf"
    }
  ]
}
```

Requisitos de serialização desta versão:

- UTF-8;
- `ensure_ascii = false` ou resultado semanticamente equivalente;
- chaves de objeto em ordem estável;
- artifacts ordenados por `path`;
- separadores compactos e exatamente uma newline final;
- nenhum timestamp, hostname, usuário, cwd absoluto, mtime, inode ou dado operacional;
- duas construções sobre os mesmos bytes produzem conteúdo byte a byte idêntico.

Este formato é específico do source manifest v1. `ARCH-001` poderá generalizar envelopes e canonicalização posteriormente, mas não deve ser antecipada nesta task.

Criar:

- um JSON Schema versionado e fail-closed, com `additionalProperties: false` nos objetos relevantes;
- um `source-manifest.json` versionado, gerado a partir do corpus atual e localizado fora de `inputs/`;
- round-trip/library validation suficiente para verificar o manifest sem dependência externa de JSON Schema.

Paths recomendados, salvo impedimento técnico demonstrado:

- `schemas/source-manifest-v1.schema.json`;
- `manifests/source-manifest.json`.

### 5. Policy de destino de outputs

Implementar uma API pura de validação/resolução de destino que:

- aceite apenas paths relativos a raízes de output explicitamente allowlisted;
- use `outputs/` como raiz de output local inicial;
- rejeite path absoluto, vazio, traversal, destino igual à raiz do repositório, destino sob `inputs/` e escape por symlink existente;
- não crie diretórios ou arquivos como efeito colateral da validação;
- retorne um path seguro somente depois de todas as verificações.

Adicionar `outputs/` ao `.gitignore` sem esconder fixtures, manifests, schemas, `inputs/`, `SHA256SUMS`, `INPUTS.md`, `ROADMAP.md` ou `docs/tasks/`.

A policy não escreve artifacts e não constitui o orquestrador do pipeline.

## Fora de escopo explícito

REPO-002 não pode:

- modificar, copiar, converter, normalizar, reparar ou recomprimir fontes;
- analisar texto, imagem, vetor, página, metadata semântica ou conteúdo de PDFs;
- abrir o XLSX como workbook ou inspecionar sheets, células, fórmulas ou estilos;
- implementar `Evidence`, `ObservedFact`, `Resolution`, `DecisionRequirement` ou provenance graph;
- implementar entidades do empreendimento, taxonomia ou fórmulas NBR;
- criar envelopes gerais de todos os estágios — isso pertence a `ARCH-001`;
- implementar profiler, extractor, OCR, geometria, workbook adapter, validação normativa ou pipeline;
- criar CLI pública, daemon, serviço, banco ou cache;
- inferir categoria pelo nome `AY0410` ou codificar a lista de 14 arquivos no código de produção;
- aceitar path inseguro por normalização silenciosa;
- usar `mimetypes` ou configuração do sistema como autoridade variável para os tipos suportados;
- adicionar dependência de runtime/teste ou acessar rede;
- modificar `.agent-loop/project.toml`, instruções do harness ou scripts do Project Adapter;
- modificar `../codex-cursor-agent-loop`;
- criar commit, push, PR, deploy, integração ou iniciar a próxima task.

## Dependências e pré-condições

### Dependência integrada

- `REPO-001` deve estar presente no commit-base, incluindo `.agent-loop/project.toml`, scaffold e gates.

### Precondições do run

- `docs/tasks/REPO-002.md` rastreado no commit-base;
- checkout canônico limpo;
- SHA-base explícito;
- `agent-loop run --require-profile`;
- Python 3.12+, Git, Bash e `sha256sum` já provisionados;
- 14 entradas atuais de `SHA256SUMS` verificando com sucesso antes do executor.

Ausência de qualquer precondição bloqueia o run; não instalar nem baixar ferramenta.

## Boundary de implementação

```text
SHA256SUMS + bytes em inputs/       autoridades imutáveis, read-only
               |
               v
nbr12721.sources                    parser + verificador + value objects
               |
               +--> manifest canônico v1
               |
               +--> output path policy (sem escrita)

PDF/XLSX/domain/NBR/OCR             fora desta boundary
```

O módulo deve permanecer na camada de infraestrutura de fontes e usar somente a biblioteca padrão do Python nesta task. Não importar adapters, domain models ou internals do harness.

## Artefatos obrigatórios

O candidate worktree deve conter, no mínimo:

1. módulo de source registry sob `src/nbr12721/sources/`;
2. value objects e exceções/diagnósticos tipados necessários;
3. `schemas/source-manifest-v1.schema.json`;
4. `manifests/source-manifest.json` com exatamente as 14 fontes atuais;
5. testes unitários dedicados sob `tests/`;
6. `.gitignore` atualizado apenas para a raiz de outputs aprovada, se necessário;
7. `docs/tasks/REPO-002.md` atualizado com evidência factual do run;
8. `ROADMAP.md` atualizado com estado/evidência factual de REPO-002, sem antecipar dependências.

Não criar output derivado em `inputs/` nem placeholders de `ARCH-001`, `NBR-000`, `PDF-001` ou tasks seguintes.

## Requisitos de imutabilidade dos inputs

1. `inputs/` deve permanecer byte a byte idêntico durante toda a task.
2. `SHA256SUMS` não pode ser alterado.
3. Nenhum arquivo temporário, manifest, cache, lock ou sidecar pode ser criado sob `inputs/`.
4. A biblioteca abre originais somente em modo read-only.
5. Uma fonte divergente bloqueia o manifest inteiro e não é reparada/substituída.
6. O gate `sha256sum -c SHA256SUMS` deve passar antes e depois da implementação: 14 OK, zero failures.
7. Testes de corrupção/symlink usam somente diretórios temporários e cópias sintéticas fora de `inputs/`.
8. Testes nunca truncam, chmod, rename, touch ou substituem original real.

## Critérios de aceite bloqueantes

1. O parser lê o `SHA256SUMS` real e produz exatamente 14 entradas verificadas.
2. Cada artifact contém somente path relativo normalizado, SHA-256 lowercase, tamanho correto e media type explícito.
3. O manifest versionado é regenerável byte a byte e não contém dado volátil ou path absoluto.
4. O manifest versionado corresponde exatamente à reconstrução a partir de `SHA256SUMS` e dos bytes atuais.
5. JSON Schema rejeita campos desconhecidos e descreve todas as restrições estruturais representáveis.
6. Hash divergente, arquivo ausente, target não regular, symlink e path inseguro falham com diagnóstico específico.
7. Parser rejeita malformed line, hash inválido, duplicidade, absoluto, traversal, NUL e separador proibido.
8. Paths com espaços e Unicode presentes no corpus são preservados e verificados corretamente.
9. Verificação de arquivo é streaming e não depende de `float`, locale, cwd implícito ou ordem do filesystem.
10. Output path policy aceita destino sob `outputs/` e rejeita `inputs/`, raiz do repo, absoluto, traversal e symlink escape sem criar nada.
11. Código de produção não contém lista hardcoded das 14 fontes nem branches para AY0410.
12. Nenhum PDF/XLSX é interpretado semanticamente; nenhuma lógica NBR/domain/extraction é adicionada.
13. A task usa somente stdlib e não modifica o Project Adapter ou o harness.
14. Todos os testes e gates passam offline; `inputs/` e `SHA256SUMS` permanecem intactos.
15. Documentação registra resultados reais e não alega integração antes da ação do operador.

## Testes obrigatórios

Cobrir no mínimo:

### Parser

- arquivo real com paths contendo espaço e Unicode;
- linha malformada e delimitador incorreto;
- hash com tamanho/caractere/case inválido;
- path vazio, duplicado, absoluto, traversal, NUL e backslash;
- ordenação determinística independente da ordem das entradas.

### Verificador

- arquivo regular correto;
- digest divergente;
- arquivo ausente;
- diretório/FIFO ou outro tipo não regular;
- symlink de arquivo e symlink de diretório escapando da raiz;
- leitura em chunks e tamanho correto;
- nenhum artifact parcial quando uma entrada falha.

### Manifest

- exatamente 14 artifacts no corpus real;
- round-trip sem perda;
- duas serializações byte-idênticas;
- regeneração igual ao arquivo versionado;
- ausência de paths absolutos e campos voláteis;
- rejeição de `schema_version` incompatível, campo extra, tipo errado e Decimal/float onde inteiro é exigido.

### Output policy

- destino válido sob `outputs/`;
- destino em `inputs/`;
- path absoluto, vazio, repo root e traversal;
- symlink existente que escapa da raiz allowlisted;
- validação sem efeitos colaterais.

Todos os casos destrutivos usam `tempfile`/diretório temporário fora dos originais.

## Gates de verificação

Executar e registrar, no mínimo:

```bash
sha256sum -c SHA256SUMS
bash scripts/agent-loop/bootstrap.sh
bash scripts/agent-loop/test.sh
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py' -v
git diff --check
git status --short
```

O gate configurado no profile congelado já executa hash, `scripts/agent-loop/test.sh` e `git diff --check`. O comando focado de `unittest` serve como evidência detalhada, não como substituto do gate.

O reviewer deve ainda:

- confrontar o manifest versionado com uma reconstrução independente pela API;
- inspecionar o diff para confirmar ausência de interpretação PDF/XLSX e hardcode do corpus;
- confirmar que `.agent-loop/` e `scripts/agent-loop/` não mudaram;
- confirmar que somente `outputs/` foi adicionado ao `.gitignore`, se essa alteração foi necessária;
- repetir `sha256sum -c SHA256SUMS` após os testes.

Falha, skip inesperado, hash divergente, manifest não reprodutível ou teste que toque original bloqueia aprovação.

## Restrições específicas do harness

1. A task deve rodar via harness com `--require-profile` e SHA-base explícito.
2. Não usar `--allow-candidate-profile`.
3. Não modificar profile, instruções, bootstrap ou gate estável do commit-base.
4. O executor trabalha somente no candidate worktree, não cria commit e não move `HEAD`.
5. O reviewer não edita arquivos.
6. Não acessar state root, locks ou internals do harness.
7. `approval.mode = "none"` permanece inalterado.
8. `APPROVED` não integra automaticamente.
9. `verify`, `integrate`, limpeza, commit local resultante, push, PR, deploy e próxima task são decisões exclusivas do operador.
10. Não modificar nem copiar `../codex-cursor-agent-loop`.

## Requisitos de conclusão e reporte

Antes de declarar o candidate completo, atualizar este arquivo e `ROADMAP.md` com fatos do run, sem alegar integração ainda não realizada.

O registro deve informar:

- arquivos criados/modificados;
- API/contratos implementados;
- path e contagem do manifest;
- comandos executados e contagens pass/fail/skip;
- resultado do hash antes/depois (`14 OK`, zero failures);
- confirmação de determinismo byte a byte do manifest;
- confirmação de que testes negativos usaram somente temporários;
- confirmação de que não houve parse semântico de PDF/XLSX, rede ou nova dependência;
- confirmação de que `inputs/`, `SHA256SUMS`, Project Adapter e harness não foram modificados;
- confirmação de ausência de commit, push, deploy, integração e próxima task;
- riscos ou limitações residuais.

Não inserir commit hash futuro, branch remota ou URL inexistente. O estado documental do run deve ser `candidate completo`/`aguardando integração`, nunca `integrado` antes da ação do operador.

## Registro de execução

Esta seção foi preenchida pelo executor durante o run de REPO-002 (inclui correções do feedback de review, rodada 6).

- **Estado:** candidate completo — aguardando integração pelo operador (sem commit, push, PR ou merge neste run).
- **Arquivos criados/modificados:**
  - **Criados:** `src/nbr12721/sources/` (`__init__.py`, `artifact.py`, `errors.py`, `manifest.py`, `media_types.py`, `output_policy.py`, `paths.py`, `schema.py`, `sha256sums.py`, `verify.py`); `schemas/source-manifest-v1.schema.json`; `manifests/source-manifest.json`; `tests/json_schema_support.py`; `tests/test_sha256sums_parser.py`, `tests/test_verify.py`, `tests/test_manifest.py`, `tests/test_output_policy.py`.
  - **Modificados:** `.gitignore` (entrada `/outputs/` ancorada na raiz); `src/nbr12721/__init__.py` (expõe submódulo `sources` na superfície pública raiz); `tests/test_smoke.py` (assertion de superfície `sources` e locale `SUCESSO`/`OK` do `sha256sum`); `docs/tasks/REPO-002.md` (este registro); `ROADMAP.md` (estado/evidência REPO-002).
  - **Não modificados:** `inputs/`, `SHA256SUMS`, `.agent-loop/`, `scripts/agent-loop/`, harness externo.
- **API/contratos implementados:**
  - `SourceArtifact` (value object imutável: `path`, `sha256`, `size_bytes`, `media_type`; valida path relativo seguro, correspondência extensão/media_type e tipos exatos).
  - `parse_sha256sums`, `verify_source`, `verify_all_sources`, `load_verified_manifest`, `build_manifest_dict`, `serialize_manifest`, `parse_manifest`, `artifacts_from_manifest`, `validate_manifest_document`, `validate_output_destination`.
  - Exceções tipadas: `Sha256SumsParseError`, `PathSecurityError`, `SourceVerificationError`, `ManifestValidationError`, `OutputPathPolicyError`, `MediaTypeError`.
  - Superfície raiz `nbr12721`: expõe `sources` e `__version__` (verificado em interpreter limpo).
- **Manifest:** `manifests/source-manifest.json` — 14 artifacts; regeneração byte a byte idêntica (`3254` bytes); sem paths absolutos nem campos voláteis.
- **Correções pós-review (rodada 2):**
  - JSON Schema v1: pattern de `path` rejeita `.`, `./`, `/./` e `/.`; `oneOf` vincula extensão (`.pdf`/`.xlsx`, case-insensitive) a `media_type` correspondente, rejeitando extensão desconhecida e divergência extensão/tipo.
  - `.gitignore`: `/outputs/` ancorado na raiz — somente `outputs/` local é ignorado; `tests/fixtures/outputs/`, `manifests/outputs/` e `inputs/outputs/` permanecem visíveis (`git check-ignore --no-index`).
  - Cobertura de teste: `tests/json_schema_support.py` valida artifacts contra patterns/`oneOf` do schema versionado; `test_output_policy.TestGitignoreOutputsRoot` verifica escopo da regra de ignore.
- **Correções pós-review (rodada 3):**
  - JSON Schema Draft 2020-12: patterns `oneOf` de extensão passaram de `(?i)\\.pdf$` / `(?i)\\.xlsx$` (inválidos em ECMA-262, `Invalid group`) para `\\.[Pp][Dd][Ff]$` e `\\.[Xx][Ll][Ss][Xx]$`.
- **Correções pós-review (rodada 4):**
  - `tests/json_schema_support.py` deixou de procurar/executar `node`. A prova de dialeto recusa grupos Python-only (`(?i)`, etc.) com parser stdlib e compila os `pattern`s com `re`; o gate não depende de Node.
  - JSON Schema `path`: o lookahead `(?!\\.)` (rejeitava qualquer path iniciado por ponto) foi substituído por `(?!\\.(/|$))`, alinhado a `validate_relative_posix_path`/`SourceArtifact`. `.well-known/source.pdf` é aceito; `.`, `./a.pdf` e `inputs/./a.pdf` continuam rejeitados.
- **Correções pós-review (rodada 5):**
  - `_suffix_lower` extrai o sufixo do último componente POSIX; ponto no índice zero do filename (`path sem extensão suportada`) rejeita `.pdf` e `.xlsx`.
  - JSON Schema `oneOf`: patterns `(?:^|/)[^/]+\\.[Pp][Dd][Ff]$` e `(?:^|/)[^/]+\\.[Xx][Ll][Ss][Xx]$` exigem stem no último componente, alinhados ao contrato Python e ao helper de teste.
  - Regressão: `SourceArtifact`, `validate_manifest_document` e `validate_artifact_against_json_schema` rejeitam `.pdf`/`.xlsx`; `.well-known/source.pdf` permanece aceito pelos três caminhos.
- **Correções pós-review (rodada 6):**
  - JSON Schema `artifacts` declara `uniqueItems: true`, alinhado ao contrato da biblioteca (paths estritamente crescentes / itens idênticos rejeitados).
  - Helper de teste `validate_manifest_against_json_schema` aplica `uniqueItems` lido do schema versionado; dois objetos de artifact idênticos falham no schema e em `validate_manifest_document`; o manifest canônico continua aceito.
- **Testes/gates (2026-08-20, rodada 6):**
  - `sha256sum -c SHA256SUMS` (antes e depois) → **14 OK / 0 failures** (locale PT: `SUCESSO`).
  - `bash scripts/agent-loop/bootstrap.sh` → **OK**.
  - `bash scripts/agent-loop/test.sh` → **40 passed / 0 failed / 0 skipped**.
  - `PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py' -v` → **40 passed / 0 failed / 0 skipped**.
  - Reconstrução independente do manifest via `load_verified_manifest` + `serialize_manifest` → **3254 bytes**, idêntica a `manifests/source-manifest.json` (14 artifacts).
  - `git diff --check` → **OK**.
  - `git diff --check 68b48ab44574cb6357f70765af6f74791e10e74d` (após correção documental desta revisão) → **OK** (exit 0).
  - `git status --short` / `git status --short --untracked-files=all` (após correção documental desta revisão; HEAD destacado, sem commit neste run) → 5 modificados, 17 untracked; `inputs/`, `SHA256SUMS`, `.agent-loop/` e `scripts/agent-loop/` ausentes da lista:
    ```text
     M .gitignore
     M ROADMAP.md
     M docs/tasks/REPO-002.md
     M src/nbr12721/__init__.py
     M tests/test_smoke.py
    ?? manifests/source-manifest.json
    ?? schemas/source-manifest-v1.schema.json
    ?? src/nbr12721/sources/__init__.py
    ?? src/nbr12721/sources/artifact.py
    ?? src/nbr12721/sources/errors.py
    ?? src/nbr12721/sources/manifest.py
    ?? src/nbr12721/sources/media_types.py
    ?? src/nbr12721/sources/output_policy.py
    ?? src/nbr12721/sources/paths.py
    ?? src/nbr12721/sources/schema.py
    ?? src/nbr12721/sources/sha256sums.py
    ?? src/nbr12721/sources/verify.py
    ?? tests/json_schema_support.py
    ?? tests/test_manifest.py
    ?? tests/test_output_policy.py
    ?? tests/test_sha256sums_parser.py
    ?? tests/test_verify.py
    ```
- **Correção documental pós-review (consistência da evidência da rodada 6):** o registro passou a incluir o `git status` mandatório; `ROADMAP.md` §10 deixou de citar rodada 5 para o mesmo snapshot.
- **Confirmações:**
  - Determinismo byte a byte do manifest verificado por dupla serialização e confronto com arquivo versionado.
  - Testes destrutivos (digest divergente, symlink, FIFO, corrupção) usaram somente `tempfile`/diretórios temporários fora de `inputs/`.
  - Nenhum parse semântico de PDF/XLSX; somente stdlib; nenhuma dependência de rede; nenhuma lista hardcoded das 14 fontes nem branch AY0410 no código de produção.
  - Nenhum commit, push, deploy, integração ou início da próxima task.
- **Riscos residuais:**
  - Validação JSON Schema em produção permanece na implementação stdlib (`validate_manifest_document`). O helper de teste cobre um subconjunto (keys, types, `pattern`, `oneOf`, `uniqueItems`) e rejeita grupos `(?)` incompatíveis com ECMA-262 por análise sintática, sem motor JavaScript; não é um validador Draft 2020-12 completo até eventual generalização em `ARCH-001`.
  - Policy de output valida destinos lógicos sob `outputs/` sem criar diretórios; symlink escape é verificado apenas para componentes existentes no filesystem.
  - Media types limitados a `.pdf` e `.xlsx` por mapping explícito; filenames sem stem (`.pdf`, `.xlsx`) são rejeitados pelo contrato e pelo schema; extensões futuras exigem task dedicada.
  - Superfície raiz expõe apenas `sources`; APIs detalhadas permanecem em `nbr12721.sources`.

## Referências

- `ROADMAP.md`, gates não negociáveis, arquitetura §4.4, política de execução §5 e task REPO-002.
- `INPUTS.md`.
- `SHA256SUMS`.
- `.agent-loop/project.toml` integrado por REPO-001.
- `docs/tasks/REPO-001.md`, apenas como precedente operacional do harness.
- `../codex-cursor-agent-loop/README.md`.
- `../codex-cursor-agent-loop/docs/PROJECT_PROFILE.md`.
- `../codex-cursor-agent-loop/docs/AGENT_ORCHESTRATION.md`.

