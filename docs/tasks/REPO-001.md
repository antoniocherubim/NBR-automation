---
id: REPO-001
status: ready_after_opr_000
depends_on: []
---

# REPO-001 — Bootstrap do projeto e Project Adapter

## Objetivo

Criar o scaffold mínimo, offline e verificável de um projeto Python 3.12 e o primeiro Project Adapter versionado para o `codex-cursor-agent-loop`.

Esta task prepara a infraestrutura para as tasks posteriores. Ela não implementa o runtime, o domínio ou qualquer regra da ABNT NBR 12721.

## Contexto

Este é o primeiro run de implementação do projeto. Antes dele, a cerimônia de operador OPR-000 deve ter:

1. inicializado este diretório como repositório Git;
2. escolhido a branch canônica;
3. versionado o baseline contendo, no mínimo, os originais, `INPUTS.md`, `SHA256SUMS`, `ROADMAP.md` e este arquivo;
4. deixado o checkout limpo; e
5. registrado um SHA-base explícito.

O commit-base de REPO-001 ainda não possui `.agent-loop/project.toml`. Por isso, esta task é a única exceção planejada ao uso de `--require-profile`. O run deve ser iniciado pelo operador com autorização explícita para criar o profile candidato:

```bash
../codex-cursor-agent-loop/agent-loop run \
  --repo "$PWD" \
  --allow-candidate-profile \
  docs/tasks/REPO-001.md 3 "$BASE_SHA"
```

O profile criado nesta task é conteúdo candidato para runs futuros. Ele não controla o bootstrap, as validações, as instruções nem a política do próprio run que o produz. O controller desse run continua sendo o harness e a visão de controle do commit-base.

Depois de review e integração local explicitamente autorizada pelo operador, as tasks posteriores devem usar `--require-profile` e um SHA-base explícito.

## Princípios que esta task deve preservar

- `inputs/` é imutável.
- O scaffold não contém lógica NBR, domínio, PDF, OCR, geometria ou XLSX.
- O bootstrap e os gates não acessam rede nem instalam dependências.
- O harness permanece externo e não é copiado nem modificado.
- O Project Adapter pertence a este repositório e contém apenas policy, instruções e gates locais.
- `approval.mode` é `none`.
- Aprovação técnica não implica commit ou integração.
- Commit, push, PR, deploy, integração, limpeza do worktree e execução da próxima task permanecem ações do operador.

## Escopo permitido

### 1. Scaffold Python mínimo

Criar:

- `pyproject.toml`, declarando Python `>=3.12`, metadata mínima e nenhuma dependência de runtime nesta fase;
- `src/nbr12721/__init__.py`, suficiente para tornar o pacote importável, sem lógica de negócio;
- uma suíte smoke mínima em `tests/`, preferencialmente baseada somente na biblioteca padrão, que prove o import do pacote e a baseline de testes;
- `.gitignore` mínimo para ambientes virtuais, caches Python, artefatos de teste/build e arquivos operacionais locais.

O nome importável inicial é `nbr12721`. Não criar módulos que antecipem contratos de domínio ou adapters futuros.

### 2. Project Adapter do harness

Criar:

- `.agent-loop/project.toml` com schema versão 1;
- `.agent-loop/executor.md`;
- `.agent-loop/reviewer.md`;
- `scripts/agent-loop/bootstrap.sh`;
- `scripts/agent-loop/test.sh`.

O profile deve declarar, no mínimo:

- `[approval].mode = "none"`;
- bootstrap via `bash scripts/agent-loop/bootstrap.sh`;
- nenhuma variável de ambiente secreta ou obrigatória nesta fase;
- validação direta de `SHA256SUMS`;
- execução de `bash scripts/agent-loop/test.sh`;
- `git diff --check`;
- instruções versionadas para executor e reviewer;
- documentação obrigatória em `docs/tasks/{task_id}.md` e `ROADMAP.md`;
- `policy.missing_profile = "deny"`;
- timeouts, heartbeat e limites finitos compatíveis com o schema v1 do harness.

Os valores de timeout/limites podem usar os defaults documentados pelo harness, desde que sejam explícitos ou comprovadamente preservados pelo parser e não relaxem os limites de segurança.

### 3. Bootstrap offline

`scripts/agent-loop/bootstrap.sh` deve:

- usar modo shell estrito;
- validar a disponibilidade e versão mínima do Python;
- validar as ferramentas locais necessárias aos gates;
- executar ou verificar a integridade via `sha256sum -c SHA256SUMS` antes do executor em runs futuros;
- encerrar com diagnóstico acionável quando o ambiente não estiver provisionado;
- não instalar, baixar, atualizar ou resolver dependências pela rede;
- não criar nem alterar arquivo rastreado;
- criar somente artefatos ignorados quando isso for estritamente necessário — a preferência desta task é não criar artefato algum.

### 4. Gate de teste

`scripts/agent-loop/test.sh` deve:

- usar modo shell estrito;
- validar sintaxe/compilação Python do scaffold;
- executar a suíte smoke de forma offline;
- validar a sintaxe dos scripts shell relevantes;
- retornar código diferente de zero em qualquer falha;
- não modificar `inputs/` nem produzir artefatos rastreados.

O comando `sha256sum -c SHA256SUMS` deve permanecer também como validation command explícito do profile, de modo que a integridade posterior ao executor seja visível separadamente no log de validação.

### 5. Instruções de executor e reviewer

As instruções locais devem reforçar, sem duplicar o engine:

- leitura completa da task e do `ROADMAP.md` relevante;
- preservação estrita de escopo e dos exclusions;
- proibição de escrita em `inputs/`;
- proibição de lógica NBR/domínio/PDF/OCR/XLSX nesta task;
- testes e evidências reais antes de declarar conclusão;
- ausência de commits, push, PR, deploy, integração ou próxima task pelo agente;
- executor altera apenas o candidate worktree;
- reviewer atua somente como reviewer, não edita arquivos e confronta relatório com diff/gates;
- ausência de secrets e de instalação/download implícitos.

## Fora de escopo explícito

REPO-001 não pode:

- implementar `Evidence`, `ObservedFact`, `Resolution` ou `DecisionRequirement`;
- implementar `Project`, `Building`, `Floor`, `Unit`, `AreaRecord` ou `ParkingSpace`;
- formalizar taxonomias, coeficientes, fórmulas ou Quadros da NBR;
- ler, interpretar, extrair, renderizar ou alterar qualquer PDF;
- inspecionar ou manipular semanticamente o workbook XLSX;
- implementar OCR, geometria, extração estruturada ou pipeline E2E;
- criar uma CLI de produto;
- adicionar LLM/VLM/agentes ao runtime;
- criar manifest de fontes, schemas intermediários ou grafo de proveniência — esses itens pertencem a tasks posteriores;
- preencher valores do AY0410 ou adicionar regra/heurística específica desse empreendimento;
- instalar pacotes ou baixar modelos/ferramentas;
- criar container, banco, serviço ou integração remota;
- modificar `../codex-cursor-agent-loop` ou copiar qualquer parte do harness para este repositório;
- inicializar Git, criar branch, commit, tag, push, PR, deploy ou executar `agent-loop integrate`;
- iniciar ou materializar a implementação de REPO-002 ou qualquer task seguinte.

## Dependências e pré-condições

### Dependência de operador

- OPR-000 concluída conforme a seção **Contexto**.
- Este arquivo rastreado no commit-base.
- Checkout canônico limpo no início do run.
- SHA-base explícito e válido.

### Ambiente previamente provisionado

- Python 3.12 ou posterior;
- Git, Bash e `sha256sum`;
- Cursor Agent e Codex CLI autenticados conforme os pré-requisitos do harness;
- `flock`, `systemd --user` e demais ferramentas exigidas pelo harness;
- harness disponível externamente em `../codex-cursor-agent-loop` no checkout canônico.

A ausência de ferramenta deve bloquear com diagnóstico. Ela não autoriza instalação ou acesso de rede pelo bootstrap, executor ou gates.

## Boundary de implementação

```text
../codex-cursor-agent-loop     controller externo, somente leitura nesta task
            |
            v
.agent-loop/                  policy/instruções versionadas do projeto
scripts/agent-loop/           bootstrap e gates locais, offline
            |
            v
pyproject.toml + src/ + tests/ scaffold vazio de domínio

inputs/                       bytes originais, somente leitura
```

O adapter local não deve importar internals do harness, chamar helpers internos `scripts/agents/dx/` nem depender da estrutura privada de state/runs. Sua interface é exclusivamente o contrato público documentado do profile, das variáveis `AGENT_LOOP_*`, dos comandos de validação e dos exit codes.

## Artefatos obrigatórios

Ao fim do candidate worktree, devem existir e estar coerentes:

1. `pyproject.toml`;
2. `src/nbr12721/__init__.py`;
3. ao menos um teste smoke sob `tests/`;
4. `.gitignore`;
5. `.agent-loop/project.toml`;
6. `.agent-loop/executor.md`;
7. `.agent-loop/reviewer.md`;
8. `scripts/agent-loop/bootstrap.sh`;
9. `scripts/agent-loop/test.sh`;
10. este `docs/tasks/REPO-001.md` atualizado com evidência real do run;
11. `ROADMAP.md` atualizado somente com o estado/evidência factual de REPO-001, sem antecipar tasks nem alegar integração ainda não realizada.

Não criar arquivos placeholder para fases posteriores.

## Requisitos de imutabilidade dos inputs

1. Não abrir arquivo em `inputs/` com modo de escrita.
2. Não sobrescrever, normalizar, converter, renomear, mover, truncar, recomprimir ou alterar permissões dos originais.
3. Não criar arquivos derivados, temporários, caches ou sidecars sob `inputs/`.
4. Não remover nem alterar entradas de `SHA256SUMS`.
5. `.gitignore` não pode esconder `inputs/`, `SHA256SUMS`, `INPUTS.md`, `ROADMAP.md` ou `docs/tasks/`.
6. Executar `sha256sum -c SHA256SUMS` antes e depois das alterações da task; todos os 14 arquivos devem retornar `OK`.
7. Qualquer divergência de hash bloqueia imediatamente a task. Não tentar “reparar” o original.

## Critérios de aceite bloqueantes

1. O scaffold declara Python `>=3.12`, é importável como `nbr12721` e não contém lógica de produção ou de domínio.
2. A suíte smoke passa offline em checkout limpo/candidate worktree.
3. `.agent-loop/project.toml` é válido no schema v1 e usa `approval.mode = "none"`.
4. O profile referencia apenas caminhos relativos seguros existentes no repositório.
5. O profile executa bootstrap offline, gate de integridade, teste do projeto e `git diff --check`.
6. `documentation.required = true` exige este arquivo e `ROADMAP.md`.
7. `policy.missing_profile = "deny"` está declarado, e a documentação operacional determina `--require-profile` para todos os runs posteriores.
8. Bootstrap não altera arquivos rastreados e não produz untracked não ignorado.
9. Nenhum script executa gerenciador de pacotes, download, `curl`, `wget`, Git remoto ou equivalente.
10. Todos os hashes de `SHA256SUMS` conferem antes e depois.
11. O diff não contém implementação de NBR, domínio, PDF, OCR, geometria, XLSX ou pipeline.
12. O harness externo permanece byte a byte fora do diff e não é copiado para o target.
13. Instruções do executor/reviewer preservam candidate isolation, review sem mutação e controle do operador sobre integração/publicação.
14. O candidate profile é validado como conteúdo futuro, sem alegação de que controlou o próprio run.
15. A documentação registra comandos/resultados reais, limitações e riscos residuais sem inventar commit hash, branch remota ou integração.

## Testes e gates de verificação

Como o candidate profile não governa este primeiro run, o executor deve executar diretamente seus novos scripts/comandos como evidência focada. O reviewer deve conferir o diff e repetir verificações seguras quando possível.

Gate mínimo esperado no candidate worktree:

```bash
sha256sum -c SHA256SUMS
bash scripts/agent-loop/bootstrap.sh
bash scripts/agent-loop/test.sh
bash -n scripts/agent-loop/bootstrap.sh scripts/agent-loop/test.sh
git diff --check
git status --short
```

Além disso:

- o harness deve aceitar/validar o candidate profile pelo mecanismo de `--allow-candidate-profile`;
- quando `AGENT_LOOP_TOOL_ROOT` estiver disponível, o profile pode ser inspecionado de forma read-only com o entrypoint público do harness, sem usar internals;
- o relatório deve registrar versões de Python e ferramentas relevantes, sem despejar ambiente ou secrets;
- `git status --short` deve conter somente os artefatos autorizados desta task;
- o gate de hash deve listar 14 resultados `OK` e nenhum failure;
- nenhum teste pode depender da rede, de um arquivo fora do repositório ou de estado mutável compartilhado.

Falha, skip inesperado, ferramenta ausente, output vazio ou hash divergente bloqueia a conclusão. Não reduzir o gate para obter aprovação.

## Restrições específicas do harness

1. Executar esta task somente via `agent-loop run` com `--allow-candidate-profile`, conforme o comando da seção **Contexto**.
2. Não usar `--require-profile` neste primeiro run, porque o profile ainda não existe no commit-base.
3. Não assumir que arquivos candidatos controlam o run atual; bootstrap, instructions e validations candidatos são apenas conteúdo sob teste.
4. Não modificar o profile para fazê-lo controlar retroativamente o próprio run.
5. Não acessar ou alterar state root, locks, manifests, hashes ou worktrees gerenciados pelo harness fora das interfaces públicas.
6. Executor não pode commitar ou mover `HEAD` no worktree.
7. Reviewer não pode editar o candidate worktree.
8. `APPROVED` é somente aceite técnico vinculado ao conteúdo; não autoriza integração.
9. Somente o operador pode executar `verify`, `integrate`, limpeza, commit resultante, push, PR, deploy ou próxima task.
10. Não modificar o harness nesta task, mesmo que uma melhoria pareça útil; registrar eventual limitação como risco separado.

## Requisitos de conclusão e reporte

Antes de declarar o candidate completo, o executor deve atualizar este documento com um registro factual contendo:

- lista exata de arquivos criados/modificados;
- resumo do scaffold e do Project Adapter;
- comandos executados e resultados, incluindo quantidade de testes pass/fail/skip;
- resultado completo do gate `SHA256SUMS` em forma resumida (`14 OK`, zero failures);
- confirmação de que não houve rede nem instalação;
- confirmação de que `inputs/` e o harness não foram modificados;
- confirmação de que nenhum commit, push, deploy, integração ou próxima task foi executado;
- limitações/riscos residuais;
- observação explícita de que o candidate profile não controlou este run e só se torna elegível para controlar runs futuros após integração pelo operador.

`ROADMAP.md` deve receber apenas evidência/estado factual coerente com esse registro. Não marcar a task como integrada enquanto o operador não tiver executado a integração fora do run. Não inserir hash ou URL inexistente.

O relatório final do executor ao harness deve repetir, de forma concisa:

1. arquivos alterados;
2. documentação alterada;
3. testes passados, falhos e ignorados;
4. gates não executados e motivo, se houver;
5. riscos residuais.

## Registro de execução

Esta seção foi preenchida pelo executor durante o run de REPO-001 (2026-08-20).

- **Estado:** candidate completo; aguardando review/integração pelo operador (não integrado).
- **Profile candidato:** não controlou este run; só será elegível após integração explícita. Runs posteriores devem usar `--require-profile`.
- **Arquivos criados/modificados:**
  - `.agent-loop/executor.md` (criado)
  - `.agent-loop/project.toml` (criado)
  - `.agent-loop/reviewer.md` (criado)
  - `.gitignore` (criado)
  - `pyproject.toml` (criado)
  - `scripts/agent-loop/bootstrap.sh` (criado)
  - `scripts/agent-loop/test.sh` (criado)
  - `src/nbr12721/__init__.py` (criado)
  - `tests/test_smoke.py` (criado)
  - `docs/tasks/REPO-001.md` (atualizado — este registro)
  - `ROADMAP.md` (atualizado — evidência factual de REPO-001)
- **Resumo do scaffold:** pacote `nbr12721` importável (`__version__ = "0.0.0"`), `pyproject.toml` com `requires-python >= 3.12` e zero dependências de runtime; smoke tests com `unittest` da stdlib.
- **Resumo do Project Adapter:** schema v1, `approval.mode = "none"`, `policy.missing_profile = "deny"`, bootstrap offline, validações `sha256sum -c SHA256SUMS`, `bash scripts/agent-loop/test.sh` e `git diff --check`; documentação obrigatória em `docs/tasks/{task_id}.md` e `ROADMAP.md`.
- **Comandos executados e resultados:**

  | Comando | Resultado |
  |---|---|
  | `sha256sum -c SHA256SUMS` (antes e depois) | 14 SUCESSO, 0 falhas |
  | `bash scripts/agent-loop/bootstrap.sh` | exit 0; Python 3.12.3; ferramentas `git`, `bash`, `sha256sum` presentes |
  | `bash scripts/agent-loop/test.sh` | exit 0; 2 passed, 0 failed, 0 skipped |
  | `bash -n scripts/agent-loop/bootstrap.sh scripts/agent-loop/test.sh` | exit 0 |
  | `git diff --check` | exit 0 |
  | `agent-loop profile --repo "$PWD"` (harness externo) | exit 0; schema v1 válido |
  | `git status --short` | somente artefatos autorizados (`??` em `.agent-loop/`, `.gitignore`, `pyproject.toml`, `scripts/`, `src/`, `tests/`) |

- **Versões de ferramentas observadas:** Python 3.12.3; Git, Bash, sha256sum, flock e systemd presentes no host; harness inspecionado via entrypoint público `agent-loop profile`.
- **SHA256SUMS:** 14 arquivos OK (zero failures).
- **Rede/instalação:** nenhum pacote instalado, nenhum download, nenhum acesso de rede pelos scripts desta task.
- **Imutabilidade:** `inputs/` e harness externo não modificados; nenhuma entrada de `SHA256SUMS` alterada.
- **Git/integração:** nenhum commit, push, PR, deploy, `integrate` ou próxima task executados.
- **Riscos residuais:**
  - O profile candidato ainda não está no commit-base; runs futuros dependem de integração pelo operador e uso de `--require-profile`.
  - Smoke tests usam apenas stdlib; dependências de runtime serão fixadas em tasks posteriores, fora deste bootstrap.
  - Outro processo do mesmo usuário ainda pode alterar o worktree fora do lock do harness; `sha256sum -c SHA256SUMS` permanece gate permanente.
  - Bootstrap não provisiona venv nem pytest; quando tasks posteriores exigirem dependências, o operador deve provisioná-las offline antes do run.

## Referências

- `ROADMAP.md`, gates não negociáveis, §§ 3.2, 5 e task REPO-001.
- `INPUTS.md` e `SHA256SUMS`.
- `../codex-cursor-agent-loop/README.md`.
- `../codex-cursor-agent-loop/docs/PROJECT_PROFILE.md`.
- `../codex-cursor-agent-loop/docs/AGENT_ORCHESTRATION.md`.
- `../codex-cursor-agent-loop/docs/ARCHITECTURE.md`.
- `../codex-cursor-agent-loop/docs/examples/project.toml`.
- `../codex-cursor-agent-loop/docs/examples/task.md`.

