---
id: REPO-003B
status: implemented_pending_commit
depends_on:
  - REPO-003A
private_fixtures: required
---

# REPO-003B — Remoção dos originais e árvore publicável

## Objetivo

Remover da árvore Git rastreada os 14 arquivos privados/licenciados, migrar o
registro de fontes para as cópias locais verificadas em `inputs/private/` e
adaptar os gates e a CI para que funcionem sem acesso ao store privado.

Ao final desta task, o `HEAD` deve ser uma árvore apta a originar um novo
histórico público. O histórico e o remoto atuais continuam privados até a
cerimônia manual OPR-PUBLIC-001.

## Contexto

REPO-003A já integrou:

- `manifests/private-fixtures-v1.json`, com os 14 paths, tamanhos, media types
  e SHA-256 esperados, sem os bytes privados;
- configuração local XDG do store externo;
- materialização verificada e read-only em `inputs/private/`;
- o marcador de task `private_fixtures`;
- `/inputs/private/` ancorado no `.gitignore`.

O baseline ainda rastreia uma norma ABNT em PDF, um template XLSX e doze PDFs
AY0410 sob `inputs/`. Eles também existem em commits antigos. Removê-los do
`HEAD` é necessário, mas não elimina os objetos do histórico privado.

Esta task declara `private_fixtures: required`. Antes do executor iniciar, os
14 arquivos devem estar materializados em `inputs/private/` a partir do store
externo, com tamanho e SHA-256 verificados. A ausência de configuração, de
qualquer arquivo ou de correspondência exata deve interromper a execução.

## Resultado arquitetural obrigatório

```text
store privado externo (somente leitura)
        |
        | verificação de tipo, tamanho e SHA-256
        v
inputs/private/ (ignorado, cópias read-only)
        |
        +--> resolver explícito de path físico
                    |
                    +--> source registry preserva o ID lógico

árvore Git pública
        |
        +--> inventários, schemas, hashes, código, testes e docs
        +--> CI e artifact sem bytes privados
        +--> fixtures sintéticas públicas, quando existirem
```

As identidades `id` existentes em `manifests/private-fixtures-v1.json` devem
permanecer estáveis. `store_path` continua relativo ao store externo e
`materialize_path` continua sendo o path físico autorizado no checkout.

## Escopo

### 1. Remoção dos arquivos rastreados

- Remover exatamente os 14 PDFs/XLSX reais atualmente rastreados sob
  `inputs/normativa/`, `inputs/template/` e
  `inputs/projetos_modelo/AY0410/`.
- Não remover, truncar, renomear, sobrescrever, mover ou alterar permissões dos
  arquivos no store privado externo.
- Não adicionar ao Git nenhuma cópia de `inputs/private/`.
- Manter o `.gitignore` restrito ao boundary necessário; não ignorar `inputs/`
  inteiro nem esconder futuras fixtures sintéticas públicas.
- Não substituir os arquivos removidos por placeholders com extensão
  `.pdf`/`.xlsx`, conteúdo parcial, thumbnails, texto extraído ou amostras dos
  originais.

### 2. Registro de fontes após a migração

- Preservar publicamente os 14 SHA-256, tamanhos, media types, nomes relativos
  e IDs já aprovados.
- Preservar **byte a byte** `SHA256SUMS`,
  `manifests/source-manifest.json` e
  `manifests/private-fixtures-v1.json`. Seus paths são IDs lógicos públicos,
  não uma promessa de que os bytes continuam rastreados nesses locais.
- Usar `materialize_path` do inventário como localização física autorizada,
  sem substituir o ID lógico no `SourceArtifact` ou no source manifest.
- Introduzir uma fronteira pequena e explícita para verificar um ID lógico em
  um path físico diferente. O código genérico de `nbr12721.sources` recebe o
  mapeamento do chamador; ele não lê XDG, não conhece o store externo e não
  importa o adapter privado.
- O mapeamento deve ser total e bijetivo para as 14 entradas e rejeitar chave
  ausente/extra/duplicada, path inseguro, symlink e destino fora de
  `inputs/private/`.
- A verificação retorna metadata com o ID lógico original; o path físico serve
  somente para abrir e verificar os bytes.
- Manter o módulo `nbr12721.sources` genérico, somente leitura e independente
  de PDF, XLSX, OCR e regras NBR.
- Testes públicos do registro devem usar arquivos temporários/sintéticos. A
  suíte pública completa não pode depender do store real.

Essa estabilidade é obrigatória porque o gate congelado do commit-base
reconstrói o inventário a partir do source manifest e procura cada `id` em
`SHA256SUMS`. Alterar qualquer um desses três arquivos tornaria a task
incompatível com o próprio gate que a controla.

### 3. Gate da árvore pública

Criar ou adaptar um gate stdlib, offline e testável que examine tanto um commit
quanto o snapshot candidato (base rastreada menos deleções, mais alterações e
arquivos novos), sem exigir `git add`, e falhe quando encontrar:

- qualquer entrada rastreada sob `inputs/private/`;
- qualquer um dos 14 paths históricos privados;
- qualquer blob rastreado cujo SHA-256 seja igual ao de uma fixture privada,
  mesmo que o arquivo tenha sido renomeado;
- alteração ou divergência entre inventário privado, `SHA256SUMS` e source
  manifest;
- arquivo privado copiado para documentação, fixture, output ou outro path.

O gate não deve proibir genericamente fixtures públicas sintéticas. Uma futura
fixture PDF/XLSX integralmente sintética, com digest diferente e localização
pública explícita, continua permitida.

### 4. CI e `artifact.zip`

- Remover da CI a verificação direta `sha256sum -c SHA256SUMS`, porque runners
  públicos não recebem o store privado.
- Executar na CI somente validações que funcionem em checkout sanitizado, sem
  configuração privada, secrets, downloads ou rede adicional.
- Executar o gate da árvore pública antes de criar o artifact.
- Manter Python 3.12+, permissões mínimas, actions pinadas, timeout,
  concorrência, `git diff --check` e verificação de worktree limpo.
- Continuar criando `artifact.zip` a partir do commit exato e comparando suas
  entradas ao tree Git.
- Adaptar o validador do ZIP: ele não pode mais exigir conteúdo sob `inputs/`;
  deve rejeitar `inputs/private/`, os 14 paths históricos e qualquer entrada
  cujo conteúdo tenha digest de fixture privada.
- Atualizar o summary para afirmar que o pacote contém somente a árvore
  sanitizada. Remover afirmações de que norma, template ou plantas estão no
  artifact.
- Os testes da CI devem ensaiar ZIP sanitizado e casos negativos de path e
  digest privados, sem incorporar bytes reais às fixtures de teste.
- A integração do gate público ocorre na workflow e nos comandos próprios do
  projeto. Não alterar `.agent-loop/project.toml` para registrar o gate.

### 5. Documentação

Atualizar `README.md`, `ROADMAP.md`, `INPUTS.md`, `docs/PRIVACY.md`,
`docs/GETTING_STARTED.md`, `docs/README.md`, `docs/CONCEPTS.md`,
`docs/GLOSSARY.md` e `docs/TROUBLESHOOTING.md` quando afetados para explicar:

- que os originais não estão mais na árvore rastreada;
- como configurar e verificar o store privado;
- a diferença entre inventário público e bytes privados;
- que testes públicos e CI não dependem do store;
- que tasks privadas usam cópias verificadas em `inputs/private/`;
- que o artifact contém somente arquivos rastreados sanitizados;
- que o remoto atual ainda não pode ser tornado público por causa do histórico;
- que OPR-PUBLIC-001, e não esta task, cria o novo histórico publicável.

A documentação do produto não deve explicar a operação de ferramentas externas
de execução. Comandos documentados devem ser comandos próprios do projeto.

## Fora de escopo

- Reescrever, filtrar, apagar ou fazer garbage collection do histórico Git.
- Criar um novo repositório, branch órfã, remoto ou histórico público.
- Alterar a visibilidade do remoto atual.
- Force-push, apagar branches/tags/PR refs ou artifacts privados existentes.
- Apagar, mover ou modificar o store privado externo.
- Copiar qualquer byte real para arquivo rastreado, teste, log, relatório,
  documentação ou artifact.
- Extrair texto/imagem, renderizar thumbnails ou inspecionar semanticamente os
  PDFs/XLSX.
- Implementar PDF, OCR, geometria, workbook, regras NBR, CLI ou pipeline.
- Acessar rede, instalar pacotes ou adicionar dependências.
- Modificar a ferramenta externa de execução.
- Executar OPR-PUBLIC-001, NBR-000 ou qualquer task seguinte.

## Dependências e precondições

- REPO-003A integrada no commit-base.
- `docs/tasks/REPO-003B.md` rastreado no commit-base.
- Checkout do operador limpo e sincronizado antes de iniciar.
- Store privado estável fora de qualquer checkout Git contendo exatamente os
  14 arquivos nos `store_path` do inventário.
- Configuração criada por `scripts/private-fixtures/configure.sh` e validada
  por `scripts/private-fixtures/configure.sh --check`.
- Materialização inicial deve comprovar 14 arquivos, zero ausências e zero
  divergências antes de qualquer remoção rastreada.
- Python 3.12, Git, Bash e `sha256sum` já provisionados.
- Nenhuma rede é necessária ou permitida durante a execução.

Se qualquer precondição privada falhar, a task deve encerrar sem remover
arquivos rastreados.

## Boundary de implementação

- Alterações ficam no repositório da aplicação: registro de fontes, manifests,
  gates, CI, testes e documentação.
- A fonte privada é aberta somente para leitura pelo mecanismo já integrado.
- `inputs/private/` é ambiente local descartável, não artefato do projeto.
- O inventário público é metadata; ele não concede autorização para distribuir
  os bytes correspondentes.
- A árvore candidata pode remover paths rastreados somente depois de confirmar
  que as cópias privadas materializadas correspondem ao inventário.
- A remoção Git não é evidência de sanitização histórica.

## Artefatos obrigatórios

- deleção rastreada dos 14 originais;
- `SHA256SUMS`, `manifests/source-manifest.json` e inventário privado
  preservados byte a byte;
- resolver lógico → físico e source registry adaptados ao novo layout;
- gate offline da árvore pública e seus testes negativos;
- workflow e validador de `artifact.zip` sanitizados;
- documentação de usuário e status do roadmap atualizados;
- este arquivo atualizado ao final com evidências reais, sem paths absolutos
  privados ou conteúdo dos originais.

## Critérios de aceitação

1. Na árvore integrada, `git ls-files` não lista nenhum dos 14 PDFs/XLSX reais;
   durante a execução, o gate candidato comprova que todos estão marcados como
   removidos do snapshot proposto sem exigir staging.
2. `git ls-files inputs/private` não produz saída.
3. Nenhum blob rastreado possui um dos 14 digests privados.
4. O inventário público continua com 14 IDs, paths, tamanhos, media types e
   SHA-256 esperados, sem bytes ou conteúdo derivado.
5. `SHA256SUMS`, source manifest e inventário privado são byte a byte idênticos
   ao commit-base e continuam reconciliando IDs/digests/tamanhos/media types.
6. Com materialização válida, o source registry verifica os 14 arquivos pelos
   `materialize_path`, preserva os IDs lógicos nos resultados e não escreve nos
   arquivos.
7. Hashes do store e das cópias materializadas são iguais antes e depois da
   execução.
8. Sem store/configuração, todos os testes e gates públicos passam e não criam
   `inputs/private/`.
9. Uma operação que exige fixtures privadas falha fechada sem configuração,
   arquivo, tamanho ou digest correto.
10. A CI não consulta store, secret ou rede adicional e não executa
    `sha256sum -c SHA256SUMS`.
11. `artifact.zip` corresponde exatamente ao tree Git sanitizado e não contém
    path nem digest de fixture privada.
12. Casos negativos comprovam rejeição de arquivo privado renomeado, path
    histórico e entrada sob `inputs/private/` usando somente dados sintéticos
    ou digests públicos.
13. Nenhum comportamento de domínio, PDF, OCR, XLSX ou NBR é implementado.
14. A documentação distingue árvore sanitizada de histórico sanitizado e
    mantém OPR-PUBLIC-001 bloqueante.
15. Nenhum commit, push, merge, deploy, mudança de visibilidade ou próxima task
    é executado automaticamente.

## Testes e gates de verificação

O relatório final deve registrar comandos, contagens e status, sem imprimir o
path absoluto do store ou conteúdo privado:

```bash
# No início e no fim, verifica materialização pelo inventário:
PYTHONPATH=src:scripts/private-fixtures python3 scripts/private-fixtures/materialize.py

# Gates públicos finais, sem configuração/store:
python3 scripts/private-fixtures/validate-gate.py
PYTHONPATH=src:scripts/private-fixtures python3 -m unittest discover -s tests -p 'test_*.py' -v
git diff --check

# Ausência de material privado na árvore integrada e evidência das deleções no candidate:
git diff --name-status
git ls-files --deleted
git ls-files inputs/private

# Ensaio local do artifact a partir da árvore candidata sanitizada:
git archive --format=zip --output=<arquivo-temporario> <commit-ou-tree-testado>
python3 scripts/ci/validate-artifact-zip.py <arquivo-temporario> <commit-ou-tree-testado>
```

Como a task altera paths rastreados ainda não commitados, os testes não devem
usar `HEAD`, `git ls-files` ou `git archive HEAD` como se representassem o
snapshot novo. O ensaio deve construir uma árvore temporária representativa do
snapshot candidato ou usar um helper que aceite explicitamente essa visão, sem
staging e sem criar commit.

Gates negativos obrigatórios:

- configuração/store ausente para operação privada;
- source ausente, symlink, arquivo especial, tamanho ou hash divergente;
- path `inputs/private/` rastreado;
- path histórico privado rastreado;
- digest privado reaparecendo em outro path;
- ZIP com path privado, digest privado, duplicata, traversal ou CRC inválido;
- CI ou suíte pública tentando acessar fixture privada.
- qualquer alteração em `SHA256SUMS`, `manifests/source-manifest.json`,
  `manifests/private-fixtures-v1.json` ou `.agent-loop/`.

## Requisitos de inputs imutáveis

- O store externo é a fonte privada autoritativa e nunca é aberto para escrita.
- As cópias em `inputs/private/` são verificadas, read-only e ignoradas.
- A remoção ocorre somente na árvore Git candidata; não no store.
- Não usar `mv` entre o checkout e o store, hardlink, symlink ou reflink não
  verificado.
- Não alterar bytes para satisfazer hash, teste, ZIP ou policy pública.
- Logs exibem somente contagens, IDs/path relativos públicos e digests já
  publicados; nunca o path absoluto do store.

## Restrições da execução isolada

- O perfil integrado no commit-base controla a preparação e as validações.
- A task deve usar as fixtures já materializadas; não deve ler ou modificar
  estado interno da ferramenta externa.
- `.agent-loop/project.toml`, `.agent-loop/executor.md` e
  `.agent-loop/reviewer.md` devem permanecer byte a byte idênticos ao
  commit-base. Em particular, não adicionar `validate-public-tree.py` a
  `[validation].commands`; o profile congelado não pode ser ampliado por esta
  task.
- `approval.mode` permanece `github_branch` por consequência, sem edição.
- Não modificar o projeto externo `../codex-cursor-agent-loop`.
- Não acessar rede nem instalar dependências.
- Não contornar gates, limites, revisão ou isolamento.
- Não executar `git add`, `git commit` ou outra mutação do histórico/índice para
  fabricar uma árvore testável; os gates devem compreender o snapshot candidato.
- A aprovação técnica não autoriza integração, PR, merge, push, publicação ou
  execução da próxima task.

## Conclusão e relatório

**Status final:** `implemented_pending_commit` (2026-08-23).

Não declara o repositório `public` nem `history_sanitized`. Integração
(commit/push/merge), mudança de visibilidade e OPR-PUBLIC-001 permanecem com o
operador. Nenhuma rede, alteração do store, commit, push, merge ou próxima task foi executada automaticamente.

### Arquivos removidos (14)

Deleções no working tree (sem `git add` / sem commit), IDs lógicos:

- `inputs/normativa/ABNT NBR 12721-2006.pdf`
- `inputs/template/ABNT_NBR_12721-2006.xlsx`
- 12 PDFs sob `inputs/projetos_modelo/AY0410/` (implantação, estacionamentos,
  memoriais, torres e cortes — mesmos IDs do inventário)

`git ls-files --deleted` → **14**. `git ls-files inputs/private` → **vazio**.

### Arquivos alterados / adicionados (código, CI, docs, testes)

- **Novos:** `src/nbr12721/sources/mapping.py`,
  `scripts/ci/candidate_snapshot.py`, `scripts/ci/validate-public-tree.py`,
  `tests/test_mapping.py`, `tests/test_public_tree.py`
- **Alterados:** `src/nbr12721/sources/{__init__,errors,manifest,verify}.py`,
  `scripts/ci/validate-artifact-zip.py`,
  `.github/workflows/validate-and-package.yml`,
  `tests/test_{ci_workflow,manifest,private_fixtures,smoke}.py`,
  `README.md`, `ROADMAP.md`, `INPUTS.md`,
  `docs/{README,GETTING_STARTED,CONCEPTS,GLOSSARY,PRIVACY,TROUBLESHOOTING}.md`,
  `docs/tasks/REPO-003B.md`

### Hashes congelados (antes = depois; zero alteração)

| Path | SHA-256 |
|------|---------|
| `SHA256SUMS` | `058f41d3f7de2c31c74e63928ac9ee45cd7ceab8b76d520d46edbd2e9c377183` |
| `manifests/source-manifest.json` | `92b7e7ae0b32c52ba5b971de3fec37896b13912e89028ae9c68f1f866631035d` |
| `manifests/private-fixtures-v1.json` | `bb06d64eba3d8753a877ec27072188c5ad416f00fd627e1375896e50e9cd67d4` |
| `.agent-loop/project.toml` | `7a812e50872ad4b0e38bc95b9976f608f7cdba6370b7a80fe688e060b2916891` |
| `.agent-loop/executor.md` | `4233878a9fa15b75d6c64a6db18037fb67c56f112319170aacd9a92a5d10c653` |
| `.agent-loop/reviewer.md` | `23391ae8a634b5a9862b913eab9fd5a8764e67393838d454750940009be0b05a` |

### Varredura da árvore pública (snapshot candidato)

```text
[public-tree] mode=candidate files=65 private_path_hits=0 historical_hits=0 digest_hits=0
```

- paths sob `inputs/private/` rastreados: **0**
- paths históricos privados no snapshot: **0**
- blobs com digest de fixture privada: **0**
- `validate-public-tree.py --commit HEAD` ainda **falha** (esperado: HEAD
  pré-integração ainda lista os 14 originais)

### Fixtures privadas

- Antes da remoção: `materialize.py` → `materializados=14 verificados=14`
- Depois da remoção: idem `14/14`; cópias read-only; sem path absoluto nos logs
- `load_verified_manifest(..., path_mapping=...)` → **14** artefatos com IDs
  lógicos preservados

### Testes e gates

| Comando | Resultado |
|---------|-----------|
| `python3 scripts/private-fixtures/validate-gate.py` | OK (`marker=none`; inventário canônico) |
| `python3 scripts/ci/validate-public-tree.py --candidate` | OK (65 files, hits=0) |
| `PYTHONPATH=src:scripts/private-fixtures python3 -m unittest discover` | **127 passed** / 0 failed / 0 skipped |
| `git diff --check` | OK |
| Ensaio ZIP `CANDIDATE` | **65 entradas**; validate-artifact-zip exit 0; zero paths/digests privados |

Suíte pública sem store: OK (validate-gate `none` + unittest). Verificação
privada materializada: 14/14 + registry com mapping.

### CI / documentação

- Workflow removeu `sha256sum -c SHA256SUMS`; adicionou
  `validate-public-tree.py --commit` antes do archive.
- Summary afirma árvore sanitizada e que o artifact **não** sanitiza histórico.
- Docs distinguem árvore sanitizada de histórico sanitizado; OPR-PUBLIC-001
  permanece **Bloqueada**.

### Riscos residuais / checklist OPR-PUBLIC-001

- Histórico Git atual e remoto ainda contêm os 14 objetos.
- Commit desta implementação ainda não ocorreu.
- Pendente do operador: revisar/integrar; executar OPR-PUBLIC-001 (histórico
  novo sem ancestrais privados); não force-push no remoto atual; não alterar
  visibilidade antes da cerimônia.
