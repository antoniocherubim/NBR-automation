---
id: CORE-001
status: ready
depends_on:
  - ARCH-001
  - NBR-000
private_fixtures: none
---

# CORE-001 — Evidence, ObservedFact, Resolution e DecisionRequirement

## Objetivo

Implementar os contratos puros e imutáveis que separam:

1. o que foi observado em uma fonte;
2. a interpretação dessa observação como fato;
3. o estado explícito de resolução de um campo;
4. uma questão que exige decisão externa.

O resultado deve impedir que ausência, conflito ou decisão pendente sejam
representados como valor comum. Deve também preservar a distinção entre
confiança de extração, confiança semântica e autoridade normativa.

CORE-001 cria somente os value objects e contratos persistíveis de base. Não
cria entidades do empreendimento, regras NBR, extração PDF, decisões adotadas
nem o grafo de proveniência.

## Contexto

O projeto já possui:

- `nbr12721.sources`, com identidade lógica e SHA-256 das fontes;
- `nbr12721.normative`, com referências normativas indexadas;
- `nbr12721.artifacts`, com JSON canônico, Decimal-string, `SourceRef`,
  `ProducerRef`, envelope v1 e content ID;
- `nbr12721.pdf`, com sinais técnicos por página, sem fatos semânticos.

Esses componentes não respondem ainda:

- qual conteúdo bruto sustenta uma observação;
- qual fato foi interpretado a partir de uma ou mais evidências;
- se um campo está observado, derivado, ausente, conflitante ou depende de
  decisão;
- qual pergunta deve ser respondida por uma autoridade humana.

O ROADMAP estabelece cinco estados mínimos e mutuamente exclusivos:

```text
OBSERVED
DERIVED
REQUIRES_DECISION
MISSING
CONFLICT
```

Esses estados não são níveis de confiança. Uma evidência com confiança alta
continua sem autoridade normativa; uma evidência com confiança baixa não vira
ausência; um conflito não pode escolher vencedor; uma decisão pendente não
carrega valor adotado.

## Escopo

### 1. Pacote de domínio puro

Criar um pacote independente, preferencialmente
`src/nbr12721/core/`, contendo:

- value objects profundamente imutáveis;
- erros tipados;
- construção e validação fail-closed;
- parsing e serialização canônica;
- geração e verificação de IDs determinísticos;
- validação referencial básica de um conjunto de registros.

O pacote pode reutilizar contratos públicos de `nbr12721.artifacts`, como
`SourceRef`, `ProducerRef`, JSON canônico e Decimal-string. Ele não importa
`nbr12721.pdf`, adapters, OCR, geometria, XLSX, UI, fixtures privadas nem
regras executáveis da NBR.

### 2. Identidade determinística

Cada registro persistível possui `schema_version = 1`, `record_type` e um ID
content-addressed com prefixo de tipo:

```text
evidence:sha256:<64-hex-lowercase>
observed-fact:sha256:<64-hex-lowercase>
resolution:sha256:<64-hex-lowercase>
decision-requirement:sha256:<64-hex-lowercase>
```

O digest é calculado sobre os bytes JSON canônicos do registro sem o próprio
campo `id`, com exatamente uma newline final. O parser recalcula e rejeita ID
divergente. Não usar posição em lista, contador global, UUID aleatório,
timestamp, hostname, cwd ou path físico.

Fornecer uma única operação compartilhada para calcular IDs. Não duplicar a
implementação canônica de ARCH-001 nem criar hash circular com placeholder.

### 3. Valor tipado

Criar um `TypedValue` fechado, suficiente para primitivos observados e
derivados, com variantes explícitas:

- `text`: string não vazia, sem coerção;
- `integer`: inteiro exato, aceitando zero e rejeitando `bool`;
- `decimal`: Decimal-string canônica, sem passagem por `float`;
- `boolean`: booleano exato;
- `code`: string não vazia acompanhada do identificador não vazio do
  vocabulário.

Valores numéricos podem carregar uma unidade não vazia e estável. Unidade é
metadata do valor, não conversão ou regra de cálculo. Unidade ausente deve ser
omitida, não preenchida com string vazia.

Cada variante rejeita campos de outras variantes e campos desconhecidos.
`null`, `float`, NaN, infinito, string vazia como sentinela e objetos/arrays
arbitrários não são valores válidos.

Zero, `false` e texto legítimo não vazio são observações válidas. Eles nunca
devem ser confundidos com `MISSING`.

### 4. Localização da evidência

Definir uma união fechada `EvidenceLocator` sem importar adapters:

- `document`: fonte inteira, sem coordenadas inventadas;
- `pdf-region`: página 1-based, rotação `0/90/180/270`, coordinate-system ID
  explícito e bbox opcional em Decimal-string;
- `xlsx-cell`: nome de sheet não vazio e endereço A1 canônico.

Uma bbox PDF, quando presente, contém `x0`, `y0`, `x1`, `y1` e unidade `pt`.
O contrato Python rejeita limites invertidos usando `Decimal`, sem `float`.
A ausência de bbox significa evidência de página inteira e é representada
pela omissão do campo.

CORE-001 somente define esses localizadores. Não abre PDF/XLSX, não transforma
coordenadas e não valida se uma sheet/célula existe no arquivo.

### 5. Confianças distintas

Definir um value object de confiança com:

- `score` como Decimal-string canônica no intervalo fechado `0..1`;
- `basis` não vazia, curta e estável;
- nenhum `float`, percentual implícito ou default.

`Evidence` pode ter `extraction_confidence`; `ObservedFact` pode ter
`semantic_confidence`. Os campos são opcionais por omissão e semanticamente
distintos. Não criar campo genérico `confidence` nem qualquer conversão de
score em autoridade, resolução, precedência ou estado.

### 6. Evidence

`Evidence` representa uma observação bruta e contém exatamente:

- `schema_version`, `record_type` e ID verificável;
- `source` como `SourceRef` lógico (`path` + SHA-256);
- `locator` tipado;
- `producer` como `ProducerRef` com nome, versão e configuração estável;
- `observed_value` como `TypedValue`;
- `extraction_confidence`, somente quando conhecida.

Não persistir `SourceArtifact` físico, path de materialização, timestamp de
execução, hostname, PID, run ID ou log. O contrato não verifica bytes da fonte;
ele preserva a identidade de uma fonte que deve ter sido verificada no
boundary anterior.

### 7. ObservedFact

`ObservedFact` interpreta uma ou mais evidências sem apagá-las e contém:

- identidade/versionamento;
- `subject_id` opaco, estável, não vazio e sem whitespace nas extremidades;
- `predicate` estável em formato documentado;
- `value` como `TypedValue`;
- uma coleção não vazia, ordenada e sem duplicatas de `evidence_ids`;
- `semantic_confidence`, somente quando conhecida.

O mesmo valor observado em evidências diferentes mantém todas as referências.
Discordância entre valores não é resolvida por ordem, backend, score ou nome
da fonte; facts distintos poderão alimentar uma resolução `CONFLICT`.

CORE-001 não define `Project`, `Building`, `Floor`, `Unit`, `AreaRecord` nem
vocabulários de predicates de negócio. Isso pertence a CORE-002/NBR-001.

### 8. Resolution

Criar uma união discriminada pelo campo `status`, com os cinco valores
uppercase do ROADMAP. Todas as variantes contêm identidade, `subject_id` e
`predicate`, mas seus demais campos são exclusivos.

#### `OBSERVED`

- referencia exatamente um `observed_fact_id`;
- não duplica o valor do fato;
- não possui regra, decisão, candidatos, reason ou valor adotado.

#### `DERIVED`

- contém `value` tipado;
- contém `rule_id` estável e não vazio;
- contém um ou mais `operand_ids` únicos;
- contém `rule_authority` com enum `normative` ou `non-normative`;
- contém `authority_refs` explícitas: ao menos uma quando `rule_authority` é
  `normative` e array vazio quando é `non-normative`;
- não possui confiança usada como autoridade.

CORE-001 valida shape e referências. A semântica da regra e a travessia do
grafo pertencem a tasks posteriores.

#### `REQUIRES_DECISION`

- referencia exatamente um `decision_requirement_id`;
- não possui `value`, default, suggestion, selected option, autor ou decisão
  adotada.

#### `MISSING`

- contém `obligation_id` estável e `reason` não vazia;
- pode listar `searched_evidence_ids`, ordenados e sem duplicatas;
- não possui `value`, zero, string vazia, fact selecionado ou decisão.

#### `CONFLICT`

- contém ao menos dois `observed_fact_ids` distintos;
- preserva todos os fatos candidatos relevantes;
- contém `reason` não vazia;
- não possui winner, selected, preferred, precedence, adopted value ou
  desempate implícito.

Shape Python e JSON Schema usam variantes fechadas. Campos proibidos não são
silenciosamente ignorados.

### 9. DecisionRequirement

`DecisionRequirement` representa somente a pergunta pendente:

- identidade/versionamento;
- `subject_id` e `predicate`;
- `question` não vazia;
- zero ou mais alternativas explícitas, cada uma com ID/label e `TypedValue`;
- zero ou mais constraints textuais não vazias;
- referências ordenadas e únicas a evidências, fatos e autoridades;
- contexto suficiente: ao menos uma alternativa, constraint ou referência.

Não contém resposta, opção sugerida/default, autor, aprovação, justificativa
de resposta, timestamp, revogação ou substituição. Esses dados pertencem a
DEC-001/DEC-002.

Uma alternativa é possibilidade documentada, não escolha automática. A ordem
das alternativas não concede preferência e deve ser canonicalizada por ID.

### 10. Validação referencial básica

Fornecer uma operação explícita sobre um conjunto finito de registros que:

- rejeita IDs duplicados ou digest inconsistente;
- exige que todo `ObservedFact.evidence_ids` exista e aponte para `Evidence`;
- exige que `OBSERVED` aponte para fato com mesmo subject/predicate;
- exige que `REQUIRES_DECISION` aponte para requirement com mesmo
  subject/predicate;
- exige que candidatos de `CONFLICT` existam, sejam facts do mesmo
  subject/predicate e preservem a união de evidências;
- exige que referências de evidência/fato de `DecisionRequirement` existam
  quando fornecidas; authority refs permanecem IDs públicos opacos;
- exige que todos os operands `DERIVED` existam no conjunto completo validado.

Esta operação recebe um conjunto completo e fechado. Validar subconjunto com
referências externas não é suportado por CORE-001; esse boundary será
definido com os artifacts/grafo de CORE-003.

Não implementar DAG, detecção de ciclos, traversal, nós de exportação ou
`provenance-index`; esse trabalho é CORE-003. A validação desta task é apenas
de identidade, tipo e referências locais imediatas.

### 11. Schema, parsing e goldens

Criar JSON Schema Draft 2020-12, preferencialmente:

```text
schemas/core-record-v1.schema.json
```

O schema tem raiz `oneOf` para `Evidence`, `ObservedFact`, `Resolution` e
`DecisionRequirement`, com `$defs` reutilizáveis. Ele deve:

- fechar todos os objetos com `additionalProperties: false`;
- discriminar todas as variantes;
- rejeitar campos proibidos por estado;
- rejeitar `float`, `null`, booleano como inteiro, arrays vazios quando a
  coleção é obrigatória e valores fora de enum/pattern;
- expressar as restrições estruturais possíveis em Draft 2020-12;
- documentar claramente invariantes relacionais verificadas somente pelo
  validador Python.

Criar oito goldens sintéticos, um para:

1. `Evidence`;
2. `ObservedFact`;
3. `OBSERVED`;
4. `DERIVED`;
5. `REQUIRES_DECISION`;
6. `MISSING`;
7. `CONFLICT`;
8. `DecisionRequirement`.

Os goldens ficam sob `tests/fixtures/core/v1/`, não contêm dados, nomes,
digests ou trechos do corpus real e são reconstruíveis byte a byte.

## Fora de escopo

- ler ou perfilar PDF, OCR, imagem, vetor, geometria ou XLSX;
- implementar Evidence real do AY0410 ou persistir conteúdo das plantas;
- implementar entidades `Project`, `Building`, `Floor`, `Unit`, `AreaRecord`
  ou `ParkingSpace`;
- criar taxonomia de áreas, coeficientes, fórmulas ou Quadros NBR;
- interpretar labels, áreas, vagas, pavimentos ou unidades;
- implementar grafo de proveniência, ciclos ou traversal (CORE-003);
- implementar política Decimal/quantização/locale (CORE-004);
- exportar manifest de decisões ou ingerir decisão adotada (DEC-001/DEC-002);
- criar artifact `extraction`, `project`, `decisions` ou
  `provenance-index` real;
- alterar envelope/artifact types de ARCH-001;
- alterar source manifest, índice normativo, page-profiles ou seus schemas;
- usar banco, UI, CLI de produto, rede ou dependência externa;
- abrir ou materializar fixtures privadas;
- modificar configuração do mecanismo de execução;
- commit, push, PR, merge, release, deploy, publicação ou próxima task.

## Dependências e precondições

- ARCH-001 integrada no commit `706ddaa`;
- NBR-000 integrada no commit `8898c97`;
- PDF-001 integrada na branch canônica no commit `8bb22eb`; não é dependência
  funcional, mas seus contratos devem permanecer sem regressão;
- o commit-base da run contém esta especificação;
- branch canônica limpa e sincronizada com o remoto antes de iniciar a run;
- Python 3.12+, Git, Bash, `sha256sum` e Poppler já provisionados;
- nenhuma instalação ou rede necessária;
- profile integrado válido com `approval.mode = "telegram"`;
- `private_fixtures: none` reconhecido pelo bootstrap sem consultar o store.

Poppler é exigido apenas porque a suíte pública completa já contém testes
sintéticos de PDF-001. `nbr12721.core` não pode invocá-lo nem importá-lo.

## Boundary de implementação

```text
SourceRef + ProducerRef + JSON/Decimal canônicos (ARCH-001)
                          |
                          v
Evidence -> ObservedFact -> Resolution
                          |
                          +-> DecisionRequirement pendente

PDF/OCR/XLSX adapters                     fora do boundary
Project/Building/AreaRecord               fora do boundary
regra ou cálculo NBR                      fora do boundary
decisão respondida/aplicada               fora do boundary
provenance DAG/traversal                   fora do boundary
```

Dependências de import permitidas:

```text
nbr12721.core -> nbr12721.artifacts
nbr12721.core -> contratos genéricos de identidade de source
```

Imports reversos ou de adapters são proibidos. `nbr12721.artifacts`,
`nbr12721.sources`, `nbr12721.normative` e `nbr12721.pdf` não passam a
importar `nbr12721.core`.

## Artefatos obrigatórios

1. pacote `src/nbr12721/core/`;
2. erros e value objects profundamente imutáveis;
3. TypedValue, EvidenceLocator e Confidence fechados;
4. Evidence, ObservedFact, cinco variantes Resolution e
   DecisionRequirement;
5. IDs content-addressed e serialização/parsing canônicos;
6. validador referencial local;
7. `schemas/core-record-v1.schema.json`;
8. oito goldens em `tests/fixtures/core/v1/`;
9. testes stdlib focados;
10. `docs/CORE_MODEL.md`;
11. atualização material de `README.md`, `docs/README.md`,
    `docs/CONCEPTS.md`, `docs/GLOSSARY.md`, `ROADMAP.md` e desta task.

Não produzir registro do AY0410, decisão humana, artifact de estágio ou
fixture binária.

## Critérios de aceitação

1. Os quatro record types e cinco estados têm shape fechado e documentado.
2. IDs são determinísticos, recalculáveis e alteram quando qualquer conteúdo
   estável material muda.
3. Parser rejeita ID divergente, versão incompatível, campo extra, chave JSON
   duplicada, UTF-8 inválido e tipo incorreto.
4. Value objects permanecem inalterados após mutação das coleções fornecidas
   pelo chamador.
5. `TypedValue` não aceita `float`, `null`, sentinela vazia ou coerção.
6. Zero inteiro, Decimal zero e `false` continuam valores válidos.
7. Decimal-string não depende do context global e nunca passa por `float`.
8. Bbox invertida, página zero/booleana, rotação inválida, sheet vazia e A1
   inválido falham.
9. Confiança ausente não vira zero; scores fora de `0..1` falham.
10. Confiança de extração e semântica não são intercambiáveis nem concedem
    autoridade.
11. Evidence usa apenas path lógico/digest, nunca path físico ou absoluto.
12. Todo ObservedFact referencia ao menos uma Evidence preservada.
13. `OBSERVED` referencia fato e não duplica valor.
14. `DERIVED` exige valor, rule ID, authority mode consistente e operands; não
    aceita derivação sem regra.
15. `REQUIRES_DECISION` não carrega valor nem resposta.
16. `MISSING` não admite zero, string vazia, `null` ou qualquer `value`.
17. `CONFLICT` preserva ao menos dois facts e não admite vencedor implícito.
18. DecisionRequirement não contém default, suggestion ou resposta adotada.
19. Alternativas são canonicalizadas sem transformar ordem em preferência.
20. Validação referencial rejeita ID ausente, tipo errado e subject/predicate
    divergente.
21. Validação referencial não se apresenta como DAG nem detecção de ciclo.
22. Schema e Python concordam nos casos estruturais exercitados; invariantes
    somente Python estão documentadas.
23. Oito goldens são sintéticos, canônicos e byte-idênticos à reconstrução.
24. Duas serializações equivalentes produzem os mesmos bytes e IDs.
25. Locale, timezone, cwd, hash seed e ordem de filesystem não alteram output.
26. Nenhum timestamp ou metadata operacional entra nos registros.
27. Nenhum adapter, regra NBR, entidade de projeto ou artifact real é criado.
28. Suíte pública passa sem configuração/store/fixtures privadas.
29. Inputs, manifests, registries, schemas e artifacts preexistentes ficam
    byte a byte intactos.
30. Documentação separa capacidade implementada de trabalho futuro.
31. Todos os gates passam offline.
32. Nenhuma operação controlada pelo operador ocorre automaticamente.

## Testes e gates de verificação

### Testes focados

Cobrir no mínimo:

- construção, igualdade, imutabilidade e round-trip de cada record type;
- cada variante `TypedValue`, incluindo zero/false e negativos de
  float/null/vazio/bool-como-int;
- locators document, pdf-region e xlsx-cell;
- bbox Decimal válida/invertida, páginas e rotações;
- confidence nos valores `0`, `1`, entre limites e fora dos limites;
- diferença entre extraction/semantic confidence;
- IDs repetíveis, tamper, prefixo/tipo errado e alteração de cada campo;
- referências Evidence -> Fact -> Resolution/DecisionRequirement;
- fact sem evidência, referência ausente/tipo errado e subject/predicate
  divergente;
- conflito com um candidato, duplicado, dois candidatos e preservação das
  evidências;
- presença proibida de value/default/winner em estados sem valor;
- DERIVED sem rule/operand, authority mode inválido, regra normativa sem
  authority ref e regra não normativa com authority ref;
- decisão com alternativas/constraints/contexto e decisão vazia;
- permutation tests com seed fixa para collections tratadas como sets;
- schema/Python parity para positivos e negativos estruturais;
- schema desconhecido, campo extra, duplicate JSON key e Unicode inválido;
- reconstrução dos oito goldens;
- ausência de imports de PDF/OCR/XLSX/normative no pacote core;
- ausência de qualquer leitura ou criação sob `inputs/private/`.

Testes usam somente biblioteca padrão e dados sintéticos. Não usar exemplos
copiados da NBR, plantas ou workbook.

### Gates públicos

```bash
python3 scripts/private-fixtures/validate-gate.py
python3 -m compileall -q src tests scripts/private-fixtures scripts/ci scripts/pdf
PYTHONPATH=src:scripts/private-fixtures python3 -m unittest discover -s tests -p 'test_*.py' -v
PYTHONPATH=src:scripts/private-fixtures python3 -m unittest tests.test_core_contracts -v
python3 scripts/ci/validate-public-tree.py --candidate
git diff --check
git status --short --untracked-files=all
```

O primeiro gate, sem contexto privado, deve registrar `marker=none` e não
consultar o store. A revisão deve também:

- reconstruir todos os goldens em diretório temporário;
- recalcular IDs independentemente;
- comparar hashes before/after dos artifacts, manifests, registries e schemas
  preexistentes;
- verificar a árvore completa por whitespace e links locais;
- inspecionar imports do pacote core.

## Requisitos de inputs imutáveis

- `private_fixtures: none` impede consulta à configuração XDG/store;
- `inputs/private/` não deve ser criado pelo bootstrap desta task;
- nenhum PDF/XLSX real é aberto, copiado, perfilado ou inspecionado;
- `SHA256SUMS`, `INPUTS.md`, `manifests/`, `registries/`,
  `profiles/page-profiles.json` e schemas preexistentes não são reescritos;
- goldens são JSON textual integralmente sintético;
- testes destrutivos usam diretórios temporários fora de `inputs/`;
- nenhum cache, lock, sidecar ou output é criado sob `inputs/`;
- a árvore pública termina com zero hits privados.

Se um teste parecer exigir uma fixture real, o teste ou o boundary está
incorreto para CORE-001. Não alterar o marcador para `required`.

## Restrições do mecanismo de execução

- `.agent-loop/project.toml`, scripts e instruções de execução integrados são
  inputs imutáveis;
- o profile integrado controla bootstrap/validação; o candidate não controla
  a própria run;
- não usar `--allow-candidate-profile`;
- preservar `approval.mode = "telegram"`;
- limite inicial de cinco iterações; ao atingi-lo, parar para reavaliar ou
  dividir a task antes de autorizar trabalho adicional;
- não editar ferramenta externa, run state ou outra worktree;
- não acessar rede nem instalar pacote;
- não usar staging/commit para fabricar o snapshot candidato;
- aprovação técnica não autoriza commit, push, PR, merge, publicação, deploy,
  integração ou próxima task.

## Conclusão e reporte

O relatório final deve informar:

- arquivos criados/modificados;
- shape final de cada record/value object e eventuais desvios justificados;
- formato e cálculo dos IDs;
- diferenças entre Evidence, ObservedFact e Resolution;
- invariantes específicas dos cinco estados;
- boundary de DecisionRequirement sem resposta;
- regras de confidence e TypedValue;
- schema e invariantes relacionais exclusivas do Python;
- goldens e reconstrução byte a byte;
- contagens/resultados de todos os testes e gates;
- confirmação de nenhum acesso/materialização privada;
- hashes before/after dos arquivos preexistentes protegidos;
- confirmação de ausência de PDF/OCR/XLSX/NBR/domain entities/provenance DAG;
- confirmação de ausência de rede e dependências novas;
- ambiguidades e riscos residuais;
- ausência de commit, push, publicação e próxima task.

O único status permitido ao fim da implementação é `candidate_complete`.
Integração e mudança para `COMPLETE` permanecem ações do operador.

## Referências autoritativas

- `ROADMAP.md`, gates 2–6, 10–12, seções 4.2, 4.4 e CORE-001;
- `docs/ARTIFACT_VERSIONING.md`;
- `schemas/artifact-envelope-v1.schema.json`;
- `registries/normative-reference-index.json`, somente identidade pública;
- `manifests/source-manifest.json`, somente identidade pública;
- contratos públicos `nbr12721.artifacts` e `nbr12721.sources`.
