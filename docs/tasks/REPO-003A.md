---
id: REPO-003A
status: candidate_complete
depends_on:
  - REPO-001
  - REPO-002
  - DOCS-001
  - CI-001
private_fixtures: none
---

# REPO-003A — Adapter N+1 para fixtures privadas

## Objetivo

Instalar o mecanismo de Project Adapter que permitirá a runs futuros consumir
os 14 originais privados/licenciados a partir de um diretório local fora do
Git, sem rede e sem expor esses bytes no futuro repositório público.

Esta é a primeira metade de uma migração obrigatoriamente dividida:

- **REPO-003A:** cria inventário, configuração, materializador, marcador de task
  e adapter N+1, mantendo os originais rastreados intactos;
- **REPO-003B:** depois que esse adapter estiver integrado e congelado no
  commit-base, remove os originais rastreados e produz a árvore sanitizada.

Não remover, mover, renomear nem ignorar os 14 arquivos reais nesta task.

## Por que a divisão é obrigatória

O profile que controla um run vem do commit-base. O adapter atual executa
explicitamente:

```bash
sha256sum -c SHA256SUMS
```

Se REPO-003A apagasse os originais, esse gate congelado falharia antes que o
profile candidato pudesse ser integrado. `--allow-candidate-profile` permite
revisar o adapter N+1, mas não permite que ele controle o próprio run.

Portanto:

```text
adapter atual + originais rastreados
              |
              v
REPO-003A propõe adapter N+1, sem remover bytes
              |
              v
review + integração do operador
              |
              v
REPO-003B usa adapter congelado N+1 e remove os rastreados
```

Contornar o gate, editar state do harness ou ativar o profile candidato durante
o run é proibido.

## Contexto e fatos do baseline

O repositório ainda é privado e contém 14 originais rastreados:

- uma ABNT NBR licenciada em PDF;
- um template XLSX fornecido;
- doze PDFs reais do projeto AY0410.

Os bytes entraram no histórico no commit inicial `334af8f`. `.gitignore` e uma
deleção no `HEAD` não removem objetos de commits anteriores. O remoto atual
deve permanecer privado durante REPO-003A e REPO-003B.

Depois de REPO-003B, o operador executará OPR-PUBLIC-001: criará um histórico
novo a partir da árvore sanitizada, sem transportar ancestrais, branches, tags,
PR refs ou artifacts privados.

O harness externo inspecionado oferece:

- `[bootstrap].command`, executado dentro do candidate worktree antes do
  executor;
- contexto confiável `AGENT_LOOP_TASK_FILE` para o bootstrap;
- variáveis base `HOME` e `XDG_CONFIG_HOME` no ambiente reduzido;
- `[environment].required`, mas somente de forma global para todos os runs;
- permissão para o bootstrap criar arquivos regulares ignorados sem alterar
  rastreados;
- adapter congelado e `--allow-candidate-profile` para mudanças N+1.

Ele não oferece variável customizada opcional ou configuração de ambiente por
task. Não inventar profile keys para suprir essa ausência.

## Mecanismo arquitetural obrigatório

### 1. Configuração local do operador

Criar um helper rastreado, sem dependências externas, que o operador executa
fora do run:

```bash
NBR12721_PRIVATE_INPUTS="/caminho/absoluto/para/nbr12721-private-inputs" \
  bash scripts/private-fixtures/configure.sh
```

O helper deve:

- exigir `NBR12721_PRIVATE_INPUTS` não vazio e absoluto;
- resolver e validar um diretório real, sem symlink no root;
- rejeitar newline, NUL, root `/`, diretório do repositório e paths inseguros;
- não copiar, mover, renomear ou aplicar `chmod` aos originais;
- gravar atomicamente somente o path canônico em:

```text
${XDG_CONFIG_HOME:-$HOME/.config}/nbr12721/private-inputs-root
```

- criar diretórios de configuração com permissão privada e arquivo `0600`;
- nunca imprimir o path completo em logs de sucesso;
- oferecer comando read-only de verificação ou modo `--check`;
- ser testável com `HOME`/`XDG_CONFIG_HOME` temporários.

O helper é a ponte necessária entre a variável amigável ao operador e o
bootstrap sanitizado do harness. Não adicionar `NBR12721_PRIVATE_INPUTS` a
`[environment].required`, pois isso bloquearia tasks públicas.

### 2. Layout do store privado

O path configurado aponta para um root fora de qualquer checkout/worktree, com
o conteúdo relativo atualmente existente sob `inputs/`:

```text
<private-root>/
  normativa/ABNT NBR 12721-2006.pdf
  template/ABNT_NBR_12721-2006.xlsx
  projetos_modelo/AY0410/...
```

O projeto nunca escreve nesse root. O operador deve mantê-lo com acesso
restrito e read-only onde prático. A aplicação não deve alterar permissões do
store nem tentar “corrigir” arquivos divergentes.

### 3. Inventário público

Criar um inventário JSON canônico e versionado, preferencialmente:

```text
manifests/private-fixtures-v1.json
```

Ele pode expor nomes relativos, media type, tamanho e SHA-256, mas nunca bytes,
texto extraído, thumbnails, dados pessoais, páginas ou secrets.

Cada entrada deve distinguir:

- path relativo dentro do store externo;
- path de materialização sob `inputs/private/`;
- tamanho exato;
- media type allowlisted;
- SHA-256 exato;
- identidade estável, quando já fornecida pelo source registry.

O inventário deve ser derivado de `SHA256SUMS`,
`manifests/source-manifest.json` e dos bytes atuais, sem editar nenhum deles.
Ordenação, encoding e newline devem ser determinísticos.

Paths absolutos, vazios, com backslash, NUL, `.`/`..`, componentes vazios,
escape, duplicidade ou destino fora de `inputs/private/` devem falhar.

### 4. Marcador por task

O bootstrap deve ler somente o front matter do arquivo indicado por
`AGENT_LOOP_TASK_FILE` e reconhecer exatamente:

```yaml
private_fixtures: required
```

ou:

```yaml
private_fixtures: none
```

Regras:

- `required`: configuração/root/inventário válidos são obrigatórios e os
  arquivos são materializados;
- `none`: não ler configuração, não tocar no store e não criar
  `inputs/private/`;
- marcador ausente em tasks históricas equivale a `none` somente por
  compatibilidade;
- marcador duplicado, desconhecido ou fora do front matter falha;
- toda nova task criada depois de REPO-003A deve declarar o valor explicitamente.

O parser deve ser pequeno, determinístico e stdlib. Não adicionar PyYAML nem
interpretar YAML arbitrário.

### 5. Materialização no worktree

Para uma task `required`, o bootstrap congelado deve:

1. localizar a configuração XDG sem aceitar override do candidate;
2. validar config e root externo;
3. carregar o inventário rastreado e validá-lo fail-closed;
4. rejeitar symlink e arquivo especial no root, componentes e fontes;
5. abrir cada fonte somente para leitura e verificar tamanho/SHA-256 em
   streaming;
6. copiar para staging ignorado dentro do worktree, nunca por hardlink ou
   symlink;
7. verificar novamente tamanho/SHA-256 da cópia;
8. aplicar `0444` aos arquivos e permissões sem escrita aos diretórios onde
   prático;
9. promover o staging de forma atômica para `inputs/private/`;
10. emitir somente contagens/status, sem paths privados absolutos ou conteúdo.

A origem nunca é aberta com modo de escrita. Falha intermediária não deixa
materialização parcial apresentada como válida. Reexecução com o mesmo
inventário deve ser idempotente.

Adicionar `/inputs/private/` ancorado na raiz ao `.gitignore`. Isso não deve
ocultar `inputs/` inteiro, fixtures sintéticas, inventários, schemas,
documentação ou manifests.

### 6. Bootstrap e validação N+1

Evoluir `scripts/agent-loop/bootstrap.sh` e, se necessário, criar entrypoints
dedicados sob `scripts/private-fixtures/`.

Alterar `.agent-loop/project.toml` somente no necessário para substituir o gate
global que pressupõe bytes rastreados por um gate task-aware. Preservar schema,
approval, timeouts, limits, instructions, documentation e policies não
relacionados.

O profile candidato:

- continua usando um `bootstrap.command` suportado pelo schema v1;
- não adiciona keys desconhecidas;
- mantém `[environment].required` sem a variável privada;
- usa validação rastreada que, para `required`, verifica o corpus materializado;
- para `none`, valida somente gates públicos e não exige/copia o corpus;
- continua executando testes e `git diff --check`.

Como o run corrente usa o adapter congelado, os novos scripts precisam ser
testados diretamente por testes stdlib e comandos focados. Não declarar que o
bootstrap N+1 controlou REPO-003A.

### 7. Compatibilidade com reviewer e snapshot

O reviewer não recebe variáveis customizadas do profile. Isso é esperado: em
runs privados futuros, o bootstrap materializa primeiro as cópias ignoradas no
worktree; o reviewer pode inspecionar/verificar esses arquivos sem conhecer o
path do store.

O snapshot aprovado, diff, commit e artifact Git nunca incluem arquivos
ignorados. Testes devem provar que `git status`, snapshot e `git archive` não
transportam `inputs/private/`.

## Escopo permitido

REPO-003A pode criar ou alterar:

- `.agent-loop/project.toml`, somente como adapter N+1;
- `scripts/agent-loop/bootstrap.sh` e gate task-aware;
- `scripts/private-fixtures/`;
- `manifests/private-fixtures-v1.json` e schema, se adotado;
- `.gitignore`, somente para `/inputs/private/`;
- testes stdlib dedicados;
- README, ROADMAP, guias de operação/privacidade e esta task;
- instruções executor/reviewer apenas para refletir a nova boundary em runs
  futuros.

## Fora de escopo explícito

REPO-003A não pode:

- remover, mover, renomear ou modificar qualquer um dos 14 originais;
- remover ou alterar semanticamente `SHA256SUMS` ou o source manifest atual;
- copiar bytes reais para outro arquivo rastreado, fixture, teste, log ou doc;
- criar o store privado real em nome do operador;
- gravar configuração real fora do repo durante o run;
- executar REPO-003B ou produzir a árvore publicável final;
- reescrever Git, usar orphan branch, force-push ou apagar refs/objects;
- criar remoto, mudar visibilidade, publicar artifact ou tornar o repo público;
- apagar runs/artifacts privados existentes;
- modificar CI-001; a adaptação do artifact pertence a REPO-003B;
- implementar NBR, PDF, OCR, geometria, XLSX, CLI ou pipeline;
- acessar rede ou instalar pacotes;
- modificar/copiar `../codex-cursor-agent-loop`;
- testar ou mudar o modo de aprovação do harness;
- fazer commit, push, PR, merge, integração, deploy ou iniciar outra task.

## Dependências e precondições

- REPO-001, REPO-002, DOCS-001 e CI-001 integradas.
- Repositório e remoto permanecem privados.
- `docs/tasks/REPO-003A.md` rastreado no commit-base.
- Checkout canônico limpo e SHA-base explícito.
- Run com `--require-profile --allow-candidate-profile` e cinco iterações.
- Python 3.12+, Git, Bash e `sha256sum` já provisionados.
- Os 14 arquivos atuais existem e `sha256sum -c SHA256SUMS` passa antes do run.
- Nenhuma configuração externa real é necessária para REPO-003A; testes
  usam roots e XDG sintéticos temporários.

Qualquer divergência bloqueia o run. Não corrigir hashes ou originais.

## Limite de implementação

```text
NBR12721_PRIVATE_INPUTS (somente helper do operador)
              |
              v
config XDG local, fora do Git
              |
              v
bootstrap congelado + AGENT_LOOP_TASK_FILE
       |                         |
       | none                    | required
       v                         v
sem acesso ao store       valida inventário/store
                                 |
                                 v
                    inputs/private/ ignorado/read-only

REPO-003A: implementa e testa esse adapter N+1
REPO-003B: usa o adapter e remove os originais rastreados
```

## Artefatos obrigatórios

1. inventário público canônico das 14 fixtures privadas;
2. schema/validator fail-closed do inventário;
3. helper `configure.sh` ou equivalente, alimentado por
   `NBR12721_PRIVATE_INPUTS`;
4. parser estrito do marcador `private_fixtures`;
5. materializador stdlib seguro e idempotente;
6. bootstrap/gate task-aware para o adapter N+1;
7. `.gitignore` com `/inputs/private/` e nada mais amplo;
8. testes unitários e de integração totalmente sintéticos;
9. `.agent-loop/project.toml` candidato, somente se necessário ao N+1;
10. instruções executor/reviewer atualizadas para tasks futuras;
11. README e guias de privacidade/operação atualizados;
12. ROADMAP e `docs/tasks/REPO-003A.md` com evidência factual.

## Requisitos de imutabilidade e confidencialidade

1. Os 14 originais e `SHA256SUMS` permanecem byte a byte idênticos.
2. Nenhum teste abre original em modo de escrita.
3. Nenhum derivado, sidecar, cache ou temporário é criado sob `inputs/`.
4. Testes de cópia/corrupção usam bytes sintéticos em `tempfile`.
5. Inventário público contém somente metadata permitida.
6. Logs não exibem root privado absoluto nem conteúdo das fontes.
7. Configuração real XDG não é criada ou alterada durante o candidate.
8. `sha256sum -c SHA256SUMS` passa antes e depois: 14 sucessos, zero falhas.

## Critérios de aceite bloqueantes

1. O inventário novo corresponde exatamente às 14 entradas atuais por path,
   tamanho, media type e SHA-256.
2. Sua serialização é byte-estável, UTF-8 e sem campos voláteis/absolutos.
3. O helper rejeita env ausente, path relativo, root `/`, repo/worktree,
   symlink e diretório inexistente.
4. O helper escreve somente a configuração XDG, atomicamente e com permissão
   privada; testes usam XDG temporário.
5. Task `none` passa sem config/root e não cria `inputs/private/`.
6. Task `required` falha sem config, config inválida, root ausente ou entrada
   ausente.
7. Marcador duplicado/desconhecido/mal posicionado falha; ausência histórica é
   tratada como `none` e documentada.
8. Traversal, path absoluto, backslash, duplicata, symlink, FIFO/diretório,
   tamanho e digest divergentes falham antes da promoção.
9. Materialização válida usa cópias regulares, nunca link, com hash idêntico
   e modo sem escrita.
10. Falha parcial não expõe destino como completo; reexecução é idempotente.
11. `/inputs/private/` é ignorado; outras fixtures/manifests continuam visíveis.
12. `git status`, snapshot/diff e `git archive` sintético não incluem a cópia
    privada.
13. Profile candidato usa somente schema suportado e não exige a env privada
    globalmente.
14. O run comprova que o adapter candidato não controlou REPO-003A.
15. Nenhum dos 14 binários é removido, movido, renomeado ou modificado.
16. CI, source runtime e capacidades NBR/PDF/OCR/XLSX permanecem inalterados.
17. Documentação explica que o repo ainda não pode ser tornado público.
18. Todos os gates passam offline.
19. Não há commit, push, PR, merge, mudança de visibilidade ou próxima task.

## Testes e gates de verificação

Executar e registrar os gates congelados:

```bash
sha256sum -c SHA256SUMS
bash scripts/agent-loop/bootstrap.sh
bash scripts/agent-loop/test.sh
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py' -v
git diff --check
git status --short --untracked-files=all
```

Executar testes focados, com diretórios temporários, para:

- configuração XDG válida/inválida e permissões;
- parser de task `none`, `required`, ausente, duplicado e inválido;
- task pública sem root/config;
- task privada sem root/config;
- inventário e store sintético válidos;
- todos os negativos de path/tipo/symlink/tamanho/hash;
- atomicidade, idempotência e permissões da cópia;
- ausência de writes na origem;
- materialização ignorada por Git e ausente de archive sintético;
- consistência do inventário real com `SHA256SUMS` e source manifest, sem
  copiar os bytes.

Repetir `sha256sum -c SHA256SUMS` depois dos testes. O reviewer deve conferir
explicitamente que `git diff --name-status` não contém deleção/modificação de
originais.

## Restrições específicas do harness

1. Usar `--require-profile --allow-candidate-profile`, SHA-base explícito e
   cinco iterações.
2. O adapter congelado do base controla este run; o candidato é N+1.
3. Não alterar state, control-adapter, locks ou internals do harness.
4. Não adicionar profile key não documentada.
5. Não adicionar `NBR12721_PRIVATE_INPUTS` a `[environment].required`.
6. Não testar, fixar ou mudar `approval.mode`.
7. Executor trabalha somente no candidate; reviewer não edita.
8. Não acessar rede nem instalar dependência.
9. `../codex-cursor-agent-loop` permanece externo e inalterado.
10. Aprovação técnica não autoriza commit, PR, merge ou publicação.
11. REPO-003B somente pode ser materializada/executada após integração
    explícita deste adapter.

Comando esperado após commit desta especificação:

```bash
BASE_SHA="$(git rev-parse HEAD)"
../codex-cursor-agent-loop/agent-loop run \
  --repo "$PWD" \
  --require-profile \
  --allow-candidate-profile \
  docs/tasks/REPO-003A.md 5 "$BASE_SHA"
```

## Requisitos de conclusão e reporte

O candidate deve registrar:

- arquivos criados/modificados;
- shape e SHA-256 do inventário público, sem reproduzir conteúdo;
- contrato do marcador de task;
- local lógico da configuração XDG, sem path privado real;
- comportamento de tasks `none` e `required`;
- testes positivos/negativos, contagens pass/fail/skip;
- prova de atomicidade, read-only e ausência no snapshot/archive;
- 14 hashes válidos antes/depois;
- confirmação de que nenhum original, CI, runtime ou harness foi alterado;
- confirmação de que o adapter candidato não controlou o run;
- riscos residuais, especialmente worktrees privados preservados e necessidade
  de REPO-003B/OPR-PUBLIC-001;
- ausência de rede, commit, push, PR, merge, publicação e próxima task.

O status final permitido é `candidate_complete`, nunca `public` ou `integrated`
antes da ação do operador.

## Registro de execução (candidate)

- **Estado:** `candidate_complete` — aguardando review/integração pelo operador.
  Nenhum commit, push, PR, merge, deploy ou próxima task neste run.
- **Controle do run:** adapter **congelado** do commit-base (validation ainda
  inclui `sha256sum -c SHA256SUMS`). O profile candidato N+1 substitui esse gate
  por `python3 scripts/private-fixtures/validate-gate.py` e **não** controlou
  este run (`--allow-candidate-profile`).
- **Inventário público:** `manifests/private-fixtures-v1.json` — 14 fixtures,
  `schema_version: 1`, serialização canônica UTF-8 com newline final,
  6199 bytes, SHA-256
  `bb06d64eba3d8753a877ec27072188c5ad416f00fd627e1375896e50e9cd67d4`.
  Derivado de `SHA256SUMS` + `manifests/source-manifest.json` (metadata);
  schema em `schemas/private-fixtures-v1.schema.json`.
- **Marcador:** esta task declara `private_fixtures: none`. Tasks novas devem
  declarar `none` ou `required` explicitamente; ausência **da chave** histórica
  ⇒ `none`; declaração vazia (`private_fixtures:`), duplicada, indentada/mal
  posicionada (front matter ou corpo) ou malformada falha
  (bootstrap/`validate-gate` incluídos).
- **Config XDG (lógico):**
  `${XDG_CONFIG_HOME:-$HOME/.config}/nbr12721/private-inputs-root`. Nenhuma
  configuração real do operador foi criada neste candidate; testes usaram
  `HOME`/`XDG_CONFIG_HOME` temporários.
- **Local do adapter:** lógica Python em `scripts/private-fixtures/adapter/`;
  superfície pública de `nbr12721` permanece somente `sources` (sem
  `nbr12721.private_fixtures`).
- **Correções pós-review (CHANGES_REQUESTED — 5ª rodada):**
  - docs: `GETTING_STARTED`/`README` deixam de afirmar que a CI é controlada
    pelo Project Adapter congelado — o workflow executa os gates **diretos**
    do YAML no checkout e **não** lê `.agent-loop/project.toml`; após
    integração, os scripts N+1 rodam no checkout, enquanto o
    `sha256sum -c SHA256SUMS` separado no YAML preserva o gate de hash;
  - docs: bootstrap com `none`/quick start só confirma **existência** de
    `manifests/private-fixtures-v1.json`; parse/consistência canônica do
    inventário permanece em `validate-gate.py` (sucesso do bootstrap ≠
    validação de conteúdo).
- **Correções pós-review (CHANGES_REQUESTED — 4ª rodada):**
  - testes: `tests/test_private_fixtures.py` adiciona
    `scripts/private-fixtures` a `sys.path` para o gate congelado
    `PYTHONPATH=src` importar `adapter` (antes: `ModuleNotFoundError`);
  - materialização: verificação pós-promoção sem backup (primeira cópia)
    remove o destino incompleto; regressão dedicada cobre o caso;
  - evidência reexecutada nos **dois** entrypoints (congelado e candidato).
- **Correções pós-review (CHANGES_REQUESTED — 3ª rodada):**
  - materialização: escrita completa (`_write_all`), **releitura** do staging
    (tamanho/SHA-256) **antes** da promoção; backup preservado até verificação
    do destino — escrita curta/truncamento falha sem substituir destino válido;
  - `configure.sh` / `validate_private_root`: rejeitam symlink com barra final
    e CR/newline no path (write e `--check`);
  - marcador: chave indentada no front matter ou no corpo falha (não vira
    `none`);
  - runtime: adapter movido para caminhos autorizados; smoke/testes preservam
    API pública anterior de `nbr12721`.
- **Correções pós-review (CHANGES_REQUESTED — 2ª rodada):**
  - marcador: declaração vazia (`private_fixtures:`) e duplicatas que
    incluam vazia/malformada falham fail-closed (não viram `none` silencioso);
    bootstrap e `validate-gate` rejeitam;
  - docs: README/GETTING_STARTED distinguem bootstrap **task-aware** N+1 do
    gate congelado `sha256sum -c SHA256SUMS` (bootstrap `none` não verifica
    hashes rastreados);
  - `configure.sh --check` lê bytes (rejeita NUL embutido; não usa
    mapfile/truncamento Bash);
  - erros de root/componente inacessível sanitizados (sem path absoluto do
    store nem traceback `PermissionError`).
- **Correções pós-review (CHANGES_REQUESTED — 1ª rodada):**
  - promoção remove backups/stagings read-only com `_rmtree_force` (chmod
    top-down) e falha se a limpeza não completar — reexecução 2×/3× não deixa
    `.private-backup-*` / `.private-staging-*` sob `inputs/`;
  - `configure.sh` / `validate_private_root` rejeitam `/`/`//`, config
    multiline e qualquer checkout/worktree Git (não só o repo corrente);
  - `--check` rejeita multiline (agora via leitura byte a byte).
- **Comportamento observado:**
  - `none`: bootstrap não lê config/store e não cria `inputs/private/`;
    **não** executa `sha256sum -c SHA256SUMS`; confirma só existência do
    inventário (sem parse/consistência — isso é `validate-gate.py`);
  - `required` (sintético): falha sem config; com store/inventário válidos
    copia arquivos regulares `0444`, idempotente (2–3 materializações), sem
    hardlink/symlink e **sem** leftovers efêmeros;
  - marcador vazio/duplicado/indentado: parser, bootstrap e validate-gate
    falham (não selecionam ramo público);
  - falha parcial / escrita curta após destino válido: destino anterior
    permanece íntegro; nenhum staging/backup residual; `git status` sem bytes
    privados;
  - primeira materialização com falha na verificação **após** promoção: destino
    incompleto é removido (não permanece sob `inputs/private/`); sem leftovers
    `.private-*`;
  - testes do adapter importam com gate congelado `PYTHONPATH=src` (bootstrap
    de path em `tests/test_private_fixtures.py`) e com `test.sh` N+1;
  - negativos: relative/`/`/`//`, repo path, **outro** checkout Git, symlink
    root (com e sem `/` final), CR no path, FIFO, diretório no lugar de
    arquivo, path absoluto/backslash/`//`/`.`/`..`, digest/tamanho divergentes,
    marcador duplicado/desconhecido/mal posicionado/vazio/indentado, config
    multiline/NUL/CR embutido, root/componente inacessível com logs sanitizados;
  - `git status` / `git archive` / ZIP de archive **não** incluem
    `inputs/private/` nem leftovers `.private-*`.
- **Gates (comandos reais neste worktree, após 5ª rodada de correções):**
  - `sha256sum -c SHA256SUMS` **antes** → 14 `: SUCESSO`/`: OK`, 0 falhas;
  - `AGENT_LOOP_TASK_FILE=docs/tasks/REPO-003A.md bash scripts/agent-loop/bootstrap.sh`
    → OK (`private_fixtures=none`; sem `inputs/private/`; sem hash check;
    só existência do inventário);
  - `AGENT_LOOP_TASK_FILE=... python3 scripts/private-fixtures/validate-gate.py`
    → OK (`marker=none`; inventário consistente);
  - gate **congelado** `PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py'`
    → **104 passed** / 0 failed / 0 skipped (inclui adapter + docs);
  - gate **candidato** `bash scripts/agent-loop/test.sh` → **104 passed** /
    0 failed / 0 skipped;
  - `git diff --check` → OK;
  - validação local de links (docs de usuário) → 37 checados, 0 quebrados;
  - whitespace em 57 arquivos textuais do filesystem → 0 ofensores;
  - `sha256sum -c SHA256SUMS` **depois** → 14 sucessos, 0 falhas;
  - `git diff --name-status` sobre `inputs/`, `SHA256SUMS`,
    `manifests/source-manifest.json`, `.github/` → **nenhuma**
    deleção/modificação.
- **Confirmado intacto:** 14 binários em `inputs/`, `SHA256SUMS`,
  `manifests/source-manifest.json`, workflow CI-001 (YAML inalterado nesta
  rodada), harness externo `../codex-cursor-agent-loop` (não acessado para
  escrita); superfície pública `nbr12721` = `sources` (sem `private_fixtures`
  em `src/`).
- **Rede:** nenhuma. **Pacotes:** nenhum instalado.
- **Riscos residuais:** histórico/worktrees privados ainda contêm os originais;
  artifact CI ainda empacota `inputs/` rastreados até REPO-003B; OPR-PUBLIC-001
  continua obrigatório antes de qualquer publicação; integração do adapter N+1
  é pré-condição para executar REPO-003B; crash extremo a meio de `os.replace`
  ainda pode exigir limpeza manual de `.private-*` sob `inputs/` (não ignorados
  pelo `.gitignore`, que permanece somente `/inputs/private/`). O adapter
  candidato **ainda não** controla este run — só o congelado do base. A CI
  também **não** é dirigida pelo profile: após integração, scripts N+1
  entram via checkout, com hash gate preservado no YAML.

## Referências

- `ROADMAP.md`, gates e §§4.1, 5.3 e 5.4;
- `.agent-loop/project.toml` do commit-base;
- `scripts/agent-loop/bootstrap.sh` e `scripts/agent-loop/test.sh`;
- `SHA256SUMS` e `manifests/source-manifest.json`;
- documentação/schema reais do Project Profile no harness externo, somente
  leitura;
- `docs/tasks/REPO-001.md` e `docs/tasks/REPO-002.md`, como histórico.
