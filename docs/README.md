# Documentação do projeto NBR 12721

Índice organizado **por necessidade**, não pela estrutura interna do código.
Todos os links são relativos e funcionam offline.

## Quero começar agora

- [Voltar ao README da raiz](../README.md) — visão geral, estado do produto e
  início rápido
- [Primeiros passos](GETTING_STARTED.md) — confirmar Python, Git, Bash,
  gates públicos, fixtures privadas e testes

## Quero entender o produto sem programar

- [Conceitos](CONCEPTS.md) — arquitetura, determinismo, evidência, decisão e
  proveniência em linguagem acessível
- [Glossário](GLOSSARY.md) — definições de termos técnicos e da NBR
- [Roadmap](../ROADMAP.md) — o que está pronto, planejado ou bloqueado

## Algo deu errado

- [Solução de problemas](TROUBLESHOOTING.md) — inventário, árvore pública,
  materialização, Python, testes e artifact
- [Privacidade e dados sensíveis](PRIVACY.md) — inventário vs bytes, logs e
  artifacts sanitizados

## Quero acompanhar o desenvolvimento

- [Registro das tasks](tasks/REPO-003B.md) — especificações e evidências das implementações
- [Roadmap](../ROADMAP.md) — ordem, dependências e estado das próximas entregas

## Estado das funcionalidades

| Área | Status |
|------|--------|
| Verificação de fontes e manifest | **Disponível** |
| Adapter N+1 de fixtures privadas | **Disponível** |
| Árvore Git sem bytes privados | **Disponível** (`REPO-003B` candidate) |
| Documentação de usuário | **Disponível** |
| CI e artifact.zip sanitizado | **Disponível** (sem store; sem `sha256sum -c`) |
| Histórico / remoto publicável | **Bloqueada** (`OPR-PUBLIC-001`) |
| Extração PDF / OCR | **Planejada** |
| Motor NBR e Quadros | **Planejada** |
| Exportação XLSX | **Planejada** |
