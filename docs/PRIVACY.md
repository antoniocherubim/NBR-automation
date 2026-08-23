# Privacidade e classificação de dados

Este repositório é **privado**. Privacidade **não** substitui controle de
acesso: apenas pessoas autorizadas devem clonar ou receber cópias.

Ele **não está pronto para mudança de visibilidade**. Os originais aparecem no
histórico desde o commit inicial; `.gitignore` ou deleção no `HEAD` não os
remove de commits antigos. REPO-003B sanitizou a **árvore** rastreada;
OPR-PUBLIC-001 (cerimônia manual) criará um **histórico** público novo.

## Inventário público vs bytes privados

| Camada | Conteúdo | Distribuição |
|--------|----------|--------------|
| `SHA256SUMS`, `manifests/source-manifest.json`, `manifests/private-fixtures-v1.json` | IDs, tamanhos, media types, SHA-256 | públicos no Git |
| Store externo do operador | 14 PDFs/XLSX reais | nunca no Git |
| `inputs/private/` | cópias verificadas, read-only | ignoradas; só local |

Os IDs lógicos (`inputs/normativa/...`, etc.) permanecem estáveis. Eles **não**
prometem que os bytes estejam rastreados nesses paths.

## Boundary privado (REPO-003A + REPO-003B)

**Disponível:**

- inventário público (somente metadata);
- helper `scripts/private-fixtures/configure.sh` via `NBR12721_PRIVATE_INPUTS`;
- materialização task-aware em `inputs/private/`;
- mapeamento explícito ID lógico → path físico em `nbr12721.sources`
  (sem ler XDG no módulo genérico);
- gate `scripts/ci/validate-public-tree.py`;
- CI e `artifact.zip` sem bytes privados.

Tasks `private_fixtures: none` não consultam store nem criam `inputs/private/`.
Tasks `required` falham fechado sem config, arquivo, tamanho ou digest corretos.

## O que a documentação pode mencionar

Permitido: paths relativos, nomes de arquivo, hashes SHA-256, contagens, path
lógico XDG.

**Proibido:** páginas/screenshots de plantas, trechos extensos da norma, dados
pessoais das pranchas, path absoluto real do store.

## Logs e artifacts

- A CI **não** consulta store, secret ou rede adicional e **não** executa
  `sha256sum -c SHA256SUMS`. A workflow está **Disponível**; a primeira
  execução remota do baseline CI-001 terminou com sucesso após o merge do
  operador. Após integração de REPO-003B, o artifact passará a refletir somente
  a árvore sanitizada.
- `artifact.zip` contém somente a árvore sanitizada. **Não** inclui norma,
  template ou plantas. Retenção: **7 dias**.
- Quem tem leitura no repositório privado pode baixar o artifact enquanto
  existir — ainda assim trate-o como material interno (código + inventários).
- Cópias em `inputs/private/` **não** entram em `git archive`/artifact.
- O artifact **não** equivale a histórico sanitizado.

## Minimização

Até OPR-PUBLIC-001: **mantenha o remoto atual privado**. Árvore limpa no `HEAD`
candidato não apaga objetos de commits anteriores.
