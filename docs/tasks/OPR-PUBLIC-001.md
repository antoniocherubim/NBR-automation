---
id: OPR-PUBLIC-001
status: complete
depends_on:
  - REPO-003A
  - REPO-003B
private_fixtures: none
---

# OPR-PUBLIC-001 — Publicação com histórico sanitizado

## Objetivo

Registrar a conclusão da cerimônia manual que criou o repositório público a
partir da árvore sanitizada de REPO-003B, sem transportar o histórico privado.

## Resultado

- repositório público: `https://github.com/antoniocherubim/NBR-automation`;
- branch canônica: `main`;
- commit raiz público: `d8e6201` (`Initial public release`);
- quantidade de commits no momento da auditoria inicial: **1**;
- tags importadas: **0**;
- branches históricas importadas: **0**;
- paths históricos dos 14 PDFs/XLSX: **0**;
- gate da árvore pública: **65 arquivos**, zero paths ou digests privados.

O repositório privado anterior não foi conectado nem enviado ao novo remoto.
Seus commits, branches, tags, PR refs e artifacts não fazem parte do histórico
público.

## Verificação executada

```bash
git rev-list --all --count
git log --all --oneline --decorate
git tag
python3 scripts/ci/validate-public-tree.py --commit HEAD
git rev-list --objects --all
```

Resultado do gate:

```text
[public-tree] mode=commit=HEAD files=65 private_path_hits=0 historical_hits=0 digest_hits=0
```

## Boundary permanente

- os bytes reais continuam exclusivamente no store privado externo;
- `inputs/private/` permanece local, ignorado e somente leitura;
- o repositório público contém apenas IDs, nomes relativos, tamanhos, media
  types e SHA-256 necessários à integridade e proveniência;
- nenhum clone ou push do histórico privado deve ser feito para este remoto;
- fixtures sintéticas integralmente públicas continuam permitidas;
- qualquer regressão de path ou digest privado deve ser bloqueada pela CI.

## Controle operacional

A cerimônia não autoriza apagar ou publicar o repositório histórico, remover o
store privado, executar a próxima task automaticamente ou alterar os inputs.
Commits, pushes, releases, deploys e mudanças de visibilidade permanecem sob
controle do operador.
