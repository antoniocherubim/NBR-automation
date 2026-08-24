# Conceitos essenciais

Este texto explica **como o produto foi pensado**, em linguagem acessível.
Capacidades ainda não implementadas aparecem como **Planejadas**.

## Propósito

Transformar plantas, memoriais e demais fontes arquitetônicas em quadros da
ABNT NBR 12721:2006 **sem esconder incertezas**. Cada número exportado deve
poder ser explicado: de onde veio, qual regra ou decisão o sustenta.

Produzir uma planilha preenchida **sem** essa explicação não é considerado
sucesso.

## Fontes imutáveis

As 14 fontes oficiais (norma PDF, template XLSX e PDFs AY0410) são tratadas
como **originais sagrados**:

- IDs lógicos estáveis em `SHA256SUMS` / manifests (paths históricos públicos);
- bytes no store privado externo do operador;
- cópias verificadas em `inputs/private/` somente para tasks `required`.

O sistema **registra** cada fonte por ID lógico, tamanho, tipo e SHA-256
(**Disponível** em `nbr12721.sources`). O chamador fornece o mapeamento para o
path físico; o módulo genérico não lê XDG nem o store. Alterar bytes quebra a
verificação e invalida qualquer manifest derivado.

Após REPO-003B, os originais **não** estão mais na árvore Git rastreada. A
imutabilidade e a verificação por SHA-256 permanecem. OPR-PUBLIC-001 criou o histórico público sanitizado; o histórico privado anterior permanece separado.

## Evidência

**Evidência** é uma observação bruta ligada a uma fonte: por exemplo, um
trecho de texto nativo em um PDF, com página e coordenadas. Evidência **não**
é ainda uma área normativa nem um valor de quadro.

Extração de PDF, OCR e geometria são **Planejadas**.

## Fato observado e resolução

Um **fato observado** interpreta evidências sem apagar a origem. A
**resolução** diz como aquele fato será usado:

- observado diretamente;
- derivado por regra determinística;
- exige decisão humana antes de prosseguir;
- ausente (sem inventar zero ou placeholder);
- em conflito (valores incompatíveis preservados).

O motor normativo **nunca** deve preencher silenciosamente lacunas ou
conflitos.

## Decisão

Algumas escolhas de engenharia (por exemplo, coeficiente dentro de um intervalo
permitido pela norma) **não** podem ser adivinhadas pelo software. Quando
necessário, o pipeline deve parar e registrar uma **decisão** pendente, com
contexto e alternativas — não uma resposta default.

## Proveniência

**Proveniência** é a cadeia auditável até a fonte ou decisão: “por que esta
célula vale X?”. No estado atual do repositório, o manifest de fontes e os
testes de imutabilidade são a base dessa cadeia; o grafo completo de
derivação é **Planejado**.

## Determinismo

Dados os mesmos inputs e a mesma versão do código, o sistema deve produzir os
mesmos artefatos intermediários (manifest, JSON canônico, relatórios). Timestamps
voláteis e paths absolutos do computador **não** entram no conteúdo estável.

O envelope comum v1 (`nbr12721.artifacts`, ARCH-001) está **Disponível**:
serialização canônica, Decimal-string e identidade `sha256:<digest>` sobre os
bytes persistidos. Os **payloads** de cada estágio (extração, projeto, NBR,
etc.) ainda são **Planejados**.

## Gates

**Gates** são verificações bloqueantes: consistência do inventário público,
gate da árvore pública, testes, diff sem whitespace acidental, documentação
atualizada. Falhar um gate impede integração da alteração. A CI pública não
depende do store privado.

## Tasks e integração

Cada task versionada delimita objetivo, escopo, critérios de aceite e evidências. A implementação só entra na branch canônica após revisão e integração explícita pelo operador. As ferramentas usadas durante o desenvolvimento não fazem parte da arquitetura do produto.

## O que existe hoje vs. o roadmap

| Camada | Status |
|--------|--------|
| Registro e verificação das 14 fontes | **Disponível** |
| Manifest canônico e policy de output | **Disponível** |
| Índice normativo v1 (autoridade por seção) | **Disponível** |
| Documentação de usuário | **Disponível** |
| Extração PDF, domínio NBR, Quadros, XLSX | **Planejadas** |

Detalhes por milestone: [ROADMAP.md](../ROADMAP.md).
