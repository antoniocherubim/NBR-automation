# Instruções do executor (NBR 12721)

Trabalhe somente neste worktree candidato e somente no escopo da task versionada.
Leia a task completa e o trecho relevante de `ROADMAP.md` antes de alterar arquivos.

## Escopo e exclusões

- Preserve estritamente o escopo e as seções **Fora de escopo** da task.
- Não escreva em `inputs/` rastreado; os originais são imutáveis. Cópias sob
  `inputs/private/` só existem quando o bootstrap N+1 materializa uma task com
  `private_fixtures: required` e são ignoradas pelo Git.
- Não implemente lógica NBR, domínio, PDF, OCR, geometria, XLSX, CLI de produto,
  LLM/VLM, pipeline E2E, manifest de fontes ou heurísticas AY0410 nesta fase.
- Não copie nem modifique o harness externo em `../codex-cursor-agent-loop`.
- Não instale pacotes, baixe modelos/ferramentas nem acesse a rede.
- Não grave configuração real em XDG durante o candidate; testes usam
  `HOME`/`XDG_CONFIG_HOME` temporários.
- Toda task nova deve declarar explicitamente `private_fixtures: none` ou
  `private_fixtures: required` no front matter.

## Validação e evidência

- Execute os gates disponíveis (`sha256sum -c SHA256SUMS` enquanto os originais
  rastreados existirem, bootstrap, testes, `git diff --check`) e registre
  comandos, contagens e falhas reais.
- O adapter N+1 de fixtures privadas é task-aware: tasks `none` não exigem
  store/config; tasks `required` materializam e verificam `inputs/private/`.
- Não declare conclusão sem evidência de teste.
- Não invente hash de commit, URL de branch ou integração inexistente.

## Documentação

- Leia `.agent-loop/project.toml` e atualize **cada** caminho listado em
  `[documentation].required_paths`, incluindo `README.md`.
- Em toda task, atualize factualmente o `README.md` quando o comportamento,
  estado ou limites do produto mudarem; atualize também os guias em `docs/`
  afetados pelo escopo.
- Use português claro, distinção explícita entre **Disponível**, **Planejada** e
  **Bloqueada**, comandos copiáveis a partir da raiz e links relativos válidos.
- Não reproduza conteúdo sensível de `inputs/` (páginas, screenshots, trechos
  extensos da norma ou plantas). Paths e hashes podem ser citados.
- Registre comportamento observado, testes e riscos residuais em
  `docs/tasks/{task_id}.md` e `ROADMAP.md`.
- Alteração cosmética, timestamp isolado ou texto vazio não satisfaz o gate
  documental; exija mudança material com evidência real.

## Integração e Git

- Altere apenas o candidate worktree; não mova `HEAD`, não faça commit, push,
  PR, merge, tag, deploy nem execute a próxima task.
- Aprovação técnica não autoriza integração; isso permanece com o operador.
