# Glossário

Definições curtas dos termos usados na documentação e no roadmap. Quando uma
capacidade ainda não existe no código, ela aparece como **Planejada**.

## Termos do projeto

### input

Arquivo original imutável. Identificado por **ID lógico** (path histórico em
`SHA256SUMS`/manifests) e SHA-256. Os bytes vivem no store externo e, quando
materializados, em `inputs/private/`. Não estão mais rastreados na árvore Git
após REPO-003B.

### fixture privada

Original licenciado/sensível listado em
`manifests/private-fixtures-v1.json`. O inventário público expõe apenas
metadata (path relativo no store, path de materialização, tamanho, media type,
SHA-256 e id estável). **Disponível**.

### mapeamento lógico → físico

Dicionário total e bijetivo que o chamador passa a `nbr12721.sources` para
abrir bytes em `materialize_path` sem alterar o ID lógico no
`SourceArtifact`. Rejeita chave ausente/extra/duplicada, path inseguro e
destino fora de `inputs/private/`. **Disponível** (REPO-003B).

### árvore sanitizada

Working tree / commit sem os 14 PDFs/XLSX reais nem digests privados
rastreados. Diferente de **histórico sanitizado** (OPR-PUBLIC-001).

### private_fixtures

Marcador obrigatório no front matter das tasks novas: `none` ou `required`.
Ausência da **chave** em tasks históricas equivale a `none`. Declaração vazia
(`private_fixtures:`), duplicada, indentada/mal posicionada ou malformada
**falha** (não desativa o corpus em silêncio). Controla se a preparação local materializa o corpus privado.

### store privado

Diretório local fora do Git, configurado pelo operador via
`NBR12721_PRIVATE_INPUTS` →
`${XDG_CONFIG_HOME:-$HOME/.config}/nbr12721/private-inputs-root`. O projeto
nunca escreve nele.

### SHA-256

Função de hash criptográfica que produz uma “impressão digital” de 64
caracteres hexadecimais. Usada para detectar qualquer alteração nos originais.

### manifest

Arquivo JSON canônico (`manifests/source-manifest.json`) que lista todas as
fontes registradas com path, digest, tamanho e tipo de mídia. **Disponível**
após REPO-002.

### índice normativo

Catálogo v1 (`registries/normative-reference-index.json`) que liga seções da
ABNT NBR 12721:2006 (versão corrigida 3) a página PDF, página impressa, tipo e
estado de formalização, sem transcrever a norma. Pacote `nbr12721.normative`.
**Disponível** (NBR-000).

### envelope de artefato

Recipiente JSON versionado (`schema_version`, tipo, projeto, fontes, produtor,
inputs e payload) usado pelos estágios intermediários. Pacote
`nbr12721.artifacts`. **Disponível** (ARCH-001). O conteúdo semântico de cada
`payload` permanece **Planejado**.

### content ID

Identidade estável `sha256:<64-hex>` calculada sobre os bytes canônicos
completos do envelope (incluindo a newline final). Não é gravada dentro do
próprio documento. **Disponível** (ARCH-001).

### Decimal-string

Representação textual canônica de um `Decimal` finito (sem expoente, sem
`float`). Usada em contratos persistidos. Política de escala/rounding de
domínio: **Planejada** (CORE-004).

### artifact

Arquivo produzido pelo pipeline (manifest, envelope intermediário, relatório,
pacote CI). Diferente de **input**: artifacts são gerados; inputs são
preservados.

### determinismo

Propriedade de reproduzir o mesmo resultado com os mesmos inputs e versão do
código, sem depender de horário, path absoluto ou estado aleatório.

### evidência

Observação bruta extraída de uma fonte (texto, região, metadado) com
referência à origem. Ainda não é valor normativo. Extração ampla: **Planejada**.

### proveniência

Cadeia explicável desde um valor exportado até fontes, regras ou decisões
humanas registradas.

### decisão

Escolha explícita de engenharia registrada com autor, justificativa e escopo.
O sistema não infere decisões para destravar o pipeline.

### gate

Verificação obrigatória (inventário, árvore pública, teste, diff, documentação)
que bloqueia integração se falhar.

### integração

Ação explícita do operador que incorpora uma implementação revisada à branch canônica. Commit, push, publicação e execução da próxima task não ocorrem automaticamente.

## Termos normativos (NBR 12721:2006)

### NBR 12721

Norma ABNT que define método de cálculo de áreas em edificações e condomínios.
O PDF de referência está em `inputs/normativa/`. Este repositório **não**
reproduz o texto integral da norma.

### Quadro I / Quadro II / Quadro IV-B

Tabelas da norma para áreas por pavimento, por unidade e para registro. Cálculo
automático: **Planejado**.

### área privativa / área comum

Classificações de uso de área conforme a norma (seção 3.7). Modelagem completa:
**Planejada**.

### coeficiente de equivalência / proporcionalidade

Fatores que convertem áreas reais em equivalentes ou distribuem áreas comuns.
Escolhas dentro de intervalos normativos exigem **decisão** explícita.
