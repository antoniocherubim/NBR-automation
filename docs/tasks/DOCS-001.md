---
id: DOCS-001
status: candidate_complete
depends_on:
  - REPO-001
  - REPO-002
---

# DOCS-001 — Documentação inicial e policy de atualização contínua

## Objetivo

Criar a base documental do projeto em português, orientada prioritariamente a pessoas sem conhecimento de programação, e tornar sua manutenção um gate bloqueante das tasks futuras.

Ao final, uma pessoa nova deve conseguir entender o propósito e os limites do produto, distinguir o que já funciona do que está planejado, validar o ambiente com comandos copiáveis, localizar ajuda e compreender as regras de privacidade dos arquivos originais.

## Contexto

REPO-001 e REPO-002 estão integradas. O repositório já possui scaffold Python, Project Adapter, registro determinístico das 14 fontes, manifest canônico e testes, mas não possui `README.md` nem navegação documental voltada ao usuário.

O público futuro inclui pessoas sem experiência em programação. Documentação não é material promocional nem comentário opcional: é parte do produto e deve acompanhar cada mudança funcional.

O repositório e os artifacts da futura CI são privados. `inputs/` contém norma, template e plantas com conteúdo licenciado, assinaturas e dados pessoais. A documentação pode mencionar paths, nomes e hashes, mas não deve incorporar páginas, screenshots, thumbnails, texto extenso da norma ou reproduções das plantas.

O profile integrado usa `approval.mode = "telegram"`. Esta task deve preservar esse valor. Ela altera o Project Adapter para runs futuros e, portanto, o candidate profile não pode controlar o run que o produz.

### Histórico do retry

O primeiro run de DOCS-001 recebeu review técnico `APPROVED`, mas não foi integrado. O integrador recusou corretamente o tree completo porque `docs/GETTING_STARTED.md` continha whitespace final em uma linha nova. O gate `git diff --check` executado no worktree não detectou o problema porque arquivos untracked não pertencem ao diff comum até serem materializados no tree temporário de integração.

Esse candidate não deve ser integrado manualmente nem ter seu hash aprovado contornado. O run permanece como evidência e o worktree foi descartado. Este retry deve reconstruir os artefatos a partir do commit-base e adicionar cobertura que examine arquivos textuais novos, modificados e rastreados antes de declarar conclusão.

Comando esperado, com SHA-base explícito e cinco iterações:

```bash
../codex-cursor-agent-loop/agent-loop run \
  --repo "$PWD" \
  --require-profile \
  --allow-candidate-profile \
  docs/tasks/DOCS-001.md 5 "$BASE_SHA"
```

## Público e princípios editoriais

A documentação deve:

- começar pela necessidade do usuário, não pela estrutura interna do código;
- usar português claro e explicar termos inevitáveis no glossário;
- oferecer comandos completos, copiáveis e executáveis a partir da raiz;
- marcar funcionalidades como `Disponível`, `Planejada`, `Bloqueada` ou equivalente inequívoco;
- não prometer cálculo NBR, leitura de PDF, OCR, preenchimento XLSX ou CI antes dessas capacidades existirem;
- explicar erros esperados e próximos passos sem exigir leitura do código;
- separar instruções de usuário, operação do harness e detalhes arquiteturais;
- evitar afirmações jurídicas ou normativas além do que está evidenciado;
- manter links relativos e navegação entre README e guias.

## Escopo permitido

### 1. README raiz

Criar `README.md` como porta de entrada, contendo no mínimo:

1. nome e resumo do projeto;
2. aviso visível de estado inicial/experimental;
3. “O que já funciona”, baseado apenas no commit-base;
4. “O que ainda não funciona” ou roadmap resumido;
5. explicação simples do fluxo futuro de fontes até XLSX;
6. pré-requisitos já provisionados, sem download durante runs;
7. início rápido para hashes, bootstrap e testes;
8. explicação de `inputs/` imutável e privado;
9. mapa da documentação;
10. como relatar problema sem expor fontes;
11. referência ao roadmap e à licença, sem inventar licença inexistente.

Se não houver licença, declarar que os termos de distribuição ainda não estão definidos. Não criar licença nesta task.

### 2. Índice e guias essenciais

Criar sob `docs/`, preferencialmente:

- `docs/README.md`: índice por necessidade do leitor;
- `docs/GETTING_STARTED.md`: preparação e validação passo a passo;
- `docs/CONCEPTS.md`: arquitetura, determinismo, evidência, decisão e proveniência em linguagem acessível;
- `docs/GLOSSARY.md`: termos técnicos, do harness e da NBR usados pelo projeto;
- `docs/TROUBLESHOOTING.md`: falhas conhecidas, diagnóstico e recuperação segura;
- `docs/PRIVACY.md`: classificação, acesso e cuidados com inputs, logs e artifacts.

Os nomes podem mudar somente por justificativa clara, preservando cobertura equivalente e links previsíveis.

### 3. Conteúdo operacional mínimo

O guia inicial deve cobrir:

- confirmar Python 3.12+, Git, Bash e `sha256sum`;
- executar `sha256sum -c SHA256SUMS` e interpretar sucesso/falha;
- executar `bash scripts/agent-loop/bootstrap.sh`;
- executar `bash scripts/agent-loop/test.sh`;
- explicar que bootstrap e testes são offline;
- explicar que `inputs/` nunca deve ser editado para corrigir uma falha;
- indicar que commit, integração e push são ações do operador;
- explicar que o artifact da CI ainda é planejado em `CI-001`.

Não ensinar instalação de dependências inexistentes nem exigir rede.

### 4. Policy de manutenção documental

Alterar `.agent-loop/project.toml` para que, depois da integração, `[documentation].required_paths` inclua no mínimo:

```toml
required_paths = [
  "docs/tasks/{task_id}.md",
  "ROADMAP.md",
  "README.md",
]
```

Preservar schema, gates, limites, bootstrap, `policy.missing_profile` e `approval.mode = "telegram"`.

Atualizar `.agent-loop/executor.md` para exigir atualização factual de `README.md` em toda task, atualização dos guias afetados, linguagem acessível, links válidos, ausência de conteúdo sensível reproduzido e evidências reais sem churn vazio.

Atualizar `.agent-loop/reviewer.md` para bloquear README ausente ou cosmeticamente alterado, documentação contraditória/inexecutável, links quebrados, reprodução desnecessária de inputs e alegação de integração, CI ou capacidade futura inexistente.

O profile e as instruções candidatos são conteúdo N+1. O run atual continua controlado pela cópia congelada do commit-base.

### 5. Gate documental offline

Adicionar teste stdlib sob `tests/` que valide no mínimo:

- presença e UTF-8 dos documentos obrigatórios;
- headings essenciais do README;
- links Markdown locais para arquivos existentes no subset adotado;
- ausência de paths absolutos específicos do host nos documentos de usuário;
- marcação clara de funcionalidades disponíveis e planejadas;
- profile parseável e `README.md` listado em `required_paths`;
- `approval.mode = "telegram"` preservado;
- instruções executor/reviewer contendo a policy documental.
- ausência de espaço ou tab no fim de qualquer linha em todos os arquivos textuais relevantes, inclusive arquivos ainda untracked no candidate.

Para o gate de whitespace, descobrir arquivos pelo filesystem e pelo conjunto de extensões textuais realmente mantidas pelo projeto, sem depender apenas de `git diff`. Cobrir no mínimo `.md`, `.py`, `.toml`, `.json`, `.sh`, `.txt` e `.gitignore`; excluir `.git/`, `inputs/`, caches, ambientes virtuais, outputs e state externo. Arquivo UTF-8 inválido dentro desse conjunto deve falhar com path explícito.

O teste deve ser determinístico e não deve tentar criar um linter Markdown genérico.

## Fora de escopo explícito

DOCS-001 não pode:

- alterar source registry, manifest, output policy ou código de domínio;
- implementar PDF, OCR, geometria, XLSX, NBR, pipeline, CLI ou interface;
- criar GitHub Actions, `artifact.zip`, release, deploy ou entrega — isso pertence a CI-001;
- copiar, editar, renderizar ou incorporar conteúdo de `inputs/`;
- publicar o repositório ou alterar sua visibilidade/permissões;
- criar licença, política jurídica ou garantia normativa;
- instalar dependência, acessar rede ou depender de ferramenta não provisionada;
- alterar scripts de bootstrap/teste, salvo impedimento real demonstrado;
- modificar `../codex-cursor-agent-loop`;
- criar commit, push, PR, integração ou iniciar a próxima task.

## Dependências e pré-condições

- REPO-001 e REPO-002 integradas no commit-base.
- `docs/tasks/DOCS-001.md` rastreado no commit-base.
- Checkout canônico limpo e SHA-base explícito.
- Profile existente e válido.
- Run com `--require-profile --allow-candidate-profile` e limite inicial `5`.
- Python 3.12+, Git, Bash e `sha256sum` provisionados.
- `sha256sum -c SHA256SUMS` retorna 14 sucessos antes do executor.

Ausência de precondição bloqueia o run. Não instalar nem baixar ferramenta.

## Limite de implementação

```text
estado integrado + ROADMAP
            |
            v
README -> índice docs -> guias acessíveis
            |
            +--> teste documental stdlib
            |
            +--> Project Adapter N+1 exige README em toda task

runtime NBR/PDF/OCR/XLSX/CI       fora desta boundary
inputs/                           somente leitura, sem reprodução
harness externo                   inalterado
```

## Artefatos obrigatórios

O candidate deve conter:

1. `README.md`;
2. `docs/README.md`;
3. guia de início rápido;
4. visão conceitual acessível;
5. glossário;
6. troubleshooting;
7. guia de privacidade;
8. teste documental stdlib;
9. `.agent-loop/project.toml` com `README.md` obrigatório para runs futuros;
10. instruções executor/reviewer atualizadas;
11. este arquivo com registro factual;
12. `ROADMAP.md` com estado/evidência factual.

Não criar placeholders vazios para CI-001 ou funcionalidades posteriores.

## Requisitos de imutabilidade e privacidade

1. `inputs/` e `SHA256SUMS` permanecem byte a byte intactos.
2. Nenhum documento incorpora página, imagem, thumbnail ou trecho extenso das fontes.
3. Paths e hashes podem ser mencionados; conteúdo sensível não é copiado para exemplos.
4. Exemplos usam dados sintéticos e identificados.
5. Troubleshooting não instrui anexar originais ou secrets a issues públicas.
6. O repositório é descrito como privado no estado atual sem tratar privacidade como substituto de controle de acesso.
7. A futura CI é planejada e seu artifact é potencialmente sensível por incluir arquivos rastreados.
8. O gate de hash passa antes e depois: 14 OK, zero failures.

## Critérios de aceite bloqueantes

1. README permite entender propósito, estado, limites e primeiro passo sem abrir o código.
2. “Disponível” corresponde apenas a REPO-001/REPO-002; capacidades futuras estão marcadas como planejadas.
3. Comandos documentados existem e funcionam offline a partir da raiz.
4. Navegação README → índice → guias não possui links locais quebrados.
5. Glossário explica pelo menos input, SHA-256, manifest, artifact, determinismo, evidência, proveniência, decisão, gate, worktree, candidate e integração.
6. Troubleshooting cobre hash divergente, Python incompatível, teste falho, worktree preservado e limite de cinco iterações sem ação destrutiva automática.
7. Privacidade explica que plantas/originais não devem ser publicados e que artifacts podem conter arquivos rastreados.
8. Documentação não reproduz inputs nem inventa licença/capacidade.
9. Teste documental stdlib detecta arquivo, link ou policy obrigatória ausente.
10. Teste documental falha ao injetar whitespace final em fixture textual temporária ou em helper puro e verifica arquivos novos diretamente no filesystem.
11. Nenhum arquivo textual novo/modificado contém whitespace final; a verificação não depende somente de `git diff --check`.
12. Profile candidato inclui `README.md`, preserva `approval.mode = "telegram"` e não muda gates/limites/policy fora do necessário.
13. Executor/reviewer exigem atualização material, não alteração vazia.
14. O run demonstra que o candidate profile não controlou o próprio run.
15. Nenhum código funcional, CI, harness ou input foi alterado.
16. Todos os gates passam sem rede.
17. Registro não alega commit, push ou integração antes do operador.

## Testes e gates de verificação

Executar e registrar:

```bash
sha256sum -c SHA256SUMS
bash scripts/agent-loop/bootstrap.sh
bash scripts/agent-loop/test.sh
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py' -v
git diff --check
git status --short --untracked-files=all
```

Também validar links locais, comandos contra paths reais, ausência de paths privados/tokens nos documentos de usuário, parsing TOML com `tomllib`, diff do profile limitado à policy documental e hash novamente após os testes.

Antes do review final, executar o teste de whitespace sobre o filesystem completo do candidate e registrar a quantidade de arquivos textuais examinados. `git diff --check` continua obrigatório, mas não serve como evidência única para arquivos novos. O reviewer deve inspecionar explicitamente untracked files e repetir esse teste.

Não usar dois espaços finais como hard break Markdown. Preferir parágrafo, lista ou `<br>` somente quando semanticamente necessário e permitido pelo subset documentado.

O reviewer deve ler a documentação como usuário não técnico. Texto gramaticalmente válido mas operacionalmente ambíguo bloqueia o aceite.

## Restrições específicas do harness

1. Usar `--require-profile --allow-candidate-profile` e SHA-base explícito.
2. O profile candidato não controla o próprio run e vale somente após integração.
3. O adapter congelado do commit-base é a autoridade do run atual.
4. `approval.mode = "telegram"` permanece inalterado.
5. Não modificar bootstrap, validations ou limites do profile.
6. Executor trabalha somente no candidate worktree e não cria commit.
7. Reviewer não edita arquivos.
8. Não acessar state root, locks ou internals do harness.
9. `APPROVED` não integra automaticamente.
10. Verify, integrate, commit resultante, push, CI e próxima task são decisões do operador.
11. Não modificar nem copiar `../codex-cursor-agent-loop`.

## Requisitos de conclusão e reporte

Antes de declarar o candidate completo, atualizar este arquivo, `ROADMAP.md` e `README.md` com fatos do run, sem alegar integração.

Registrar arquivos, estrutura entregue, mudança exata do Adapter N+1, comandos e contagens, links, quantidade de textos verificados sem whitespace final, status de todos os untracked files, hashes antes/depois, ausência de reprodução dos inputs, ausência de mudanças funcionais/harness, confirmação de adapter congelado, riscos residuais e ausência de commit/push/integração/CI/próxima task.

O estado deve ser `candidate completo`/`aguardando integração`, nunca `integrado` antes da ação do operador.

## Registro de execução

- **Estado:** `candidate_complete` — aguardando integração pelo operador. Nenhum commit, push, merge ou CI executados neste run.
- **Retry pós-review:** corrigidos três achados — diagnóstico UTF-8 com path explícito, interpretação locale-independente de `sha256sum`, contagem de untracked (6 guias em `docs/`, 8 arquivos untracked no total).
- **Commit-base do run:** `d2d852cc8d69b9fc205b999dfca93c4f51614b6d` (profile congelado; alterações em `.agent-loop/project.toml` são N+1).
- **Arquivos criados:**
  - `README.md`
  - `docs/README.md`, `docs/GETTING_STARTED.md`, `docs/CONCEPTS.md`, `docs/GLOSSARY.md`, `docs/TROUBLESHOOTING.md`, `docs/PRIVACY.md`
  - `tests/test_documentation.py`
- **Arquivos modificados:**
  - `.agent-loop/project.toml` — adicionado `README.md` em `[documentation].required_paths`; `approval.mode = "telegram"` preservado; demais gates/limites inalterados
  - `.agent-loop/executor.md` — policy documental material (README, guias, linguagem acessível, sem reprodução de inputs)
  - `.agent-loop/reviewer.md` — bloqueios documentais (README ausente/cosmético, links, whitespace em untracked, promessas indevidas)
  - `docs/tasks/DOCS-001.md`, `ROADMAP.md` — registro factual deste run
- **Adapter N+1 (diff exato):** somente `README.md` incluído em `required_paths`; schema, bootstrap, validation, limits e `policy.missing_profile` intactos.
- **Testes/gates (evidência repetível):**

  | Comando | Resultado |
  |---------|-----------|
  | `sha256sum -c SHA256SUMS` (antes) | 14 linhas `: OK` com `LC_ALL=C.UTF-8`; 0 falhas |
  | `bash scripts/agent-loop/bootstrap.sh` | OK (python=3.12.3; hash repete com `: SUCESSO` no locale do host) |
  | `bash scripts/agent-loop/test.sh` | 51 passed / 0 failed / 0 skipped |
  | `PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py' -v` | 51 OK |
  | `sha256sum -c SHA256SUMS` (depois) | 14 linhas `: OK` com `LC_ALL=C.UTF-8`; 0 falhas |
  | `git diff --check` | OK (sem whitespace em tracked modificados) |
  | Gate whitespace filesystem (`test_no_trailing_whitespace_in_text_files`) | 39 arquivos textuais examinados, 0 linhas com trailing whitespace |

- **Untracked no candidate (`git status --short --untracked-files=all`):** `README.md`, seis guias em `docs/` (`README.md`, `GETTING_STARTED.md`, `CONCEPTS.md`, `GLOSSARY.md`, `TROUBLESHOOTING.md`, `PRIVACY.md`), `tests/test_documentation.py` (8 arquivos untracked no total).
- **Links locais:** subset de documentos de usuário validado por `test_local_markdown_links_resolve` (7 arquivos); links apontam para arquivos existentes (não diretórios).
- **Inputs/harness:** `inputs/` e `SHA256SUMS` byte a byte intactos; harness externo não modificado; bootstrap/test.sh inalterados.
- **Riscos residuais:**
  - `pyproject.toml` ainda referencia `readme = "ROADMAP.md"` (fora do escopo desta task); integração futura pode alinhar metadata do pacote ao `README.md` de usuário.
  - Validador de links cobre o subset adotado de docs de usuário, não todo Markdown do repositório (incl. tasks históricas).
  - Revisão humana ainda necessária para tom operacional ambíguo apesar de gramática correta.
  - Profile candidato não controlou este run; só passará a exigir `README.md` após integração.
- **Integração/CI:** não alegada. Próxima task operacional após integração: `CI-001` (planejada).

## Referências

- `ROADMAP.md`, especialmente gates, §5 e DOCS-001.
- `INPUTS.md` e `SHA256SUMS`.
- `.agent-loop/project.toml`, `.agent-loop/executor.md` e `.agent-loop/reviewer.md`.
- `docs/tasks/REPO-001.md` e `docs/tasks/REPO-002.md`.
- `../codex-cursor-agent-loop/docs/PROJECT_PROFILE.md`.
- `../codex-cursor-agent-loop/docs/AGENT_ORCHESTRATION.md`.
