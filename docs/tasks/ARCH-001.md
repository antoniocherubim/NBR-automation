---
id: ARCH-001
status: ready
depends_on:
  - REPO-001
  - REPO-002
private_fixtures: none
---

# ARCH-001 — Envelopes e versionamento dos artefatos

## Objetivo

Implementar o contrato comum v1 dos artefatos intermediários do projeto:
envelope persistível, referências de lineage, identidade determinística por
conteúdo, política de compatibilidade e serialização JSON canônica.

O resultado deve permitir que extração, resolução, cálculo, validação e
exportação troquem documentos versionados sem depender de classes internas
umas das outras. ARCH-001 define o recipiente e suas invariantes; não define
os payloads de domínio que serão implementados pelas tasks posteriores.

## Contexto

O projeto já possui dois documentos públicos versionados e byte-estáveis:

- `manifests/source-manifest.json`, contrato específico de
  `nbr12721.sources`;
- `registries/normative-reference-index.json`, contrato específico de
  `nbr12721.normative`.

Esses formatos continuam autoritativos e não devem ser migrados, embrulhados
ou regenerados nesta task. Eles demonstram algumas propriedades que o
contrato comum deve generalizar: `schema_version`, rejeição de campos
desconhecidos, validação fail-closed, UTF-8 e serialização byte-estável.

O ROADMAP planeja os seguintes artefatos intermediários:

```text
page-profiles.json
extraction.json
project.json
decisions.json
nbr.json
validation-report.json
workbook-model.json
provenance-index.json
```

`source-manifest.json` é o registro fundacional já existente.
`resultado.xlsx` é um binário de saída e não deve ser encapsulado nem
implementado por ARCH-001. Tasks futuras poderão referenciá-lo por identidade
e digest em um payload próprio.

Os envelopes precisam preservar os gates arquiteturais:

- ausência, conflito e decisão não podem ser escondidos pelo recipiente;
- confiança de extração não representa autoridade normativa;
- referências de lineage são explícitas;
- valores de engenharia não passam por `float`;
- timestamps e estado do computador não alteram identidade de conteúdo;
- o mesmo documento lógico produz os mesmos bytes e o mesmo digest.

## Escopo

### 1. Pacote de contratos

Criar um pacote independente, preferencialmente
`src/nbr12721/artifacts/`, contendo value objects imutáveis, erros tipados,
validação, parsing, serialização canônica e cálculo de identidade.

O pacote usa somente a biblioteca padrão. Ele não importa adapters, PDF, OCR,
XLSX, UI, geometria, regras NBR, modelos de empreendimento nem configuração
de fixtures privadas.

### 2. Envelope comum v1

O documento persistido deve representar, com nomes estáveis e documentados:

- `schema_version`, inteiro exato igual a `1`;
- tipo do artefato;
- identidade estável do projeto;
- referências às fontes originais por ID lógico e SHA-256;
- produtor por nome, versão e configuração estável relevante;
- referências aos artefatos intermediários de entrada;
- payload JSON do estágio.

O shape conceitual mínimo é:

```json
{
  "schema_version": 1,
  "artifact_type": "extraction",
  "project_id": "project:synthetic-demo",
  "sources": [
    {
      "path": "inputs/synthetic/demo.pdf",
      "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    }
  ],
  "producer": {
    "name": "synthetic-producer",
    "version": "1.0.0",
    "configuration": {}
  },
  "inputs": [
    {
      "artifact_type": "page-profiles",
      "content_sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    }
  ],
  "payload": {}
}
```

O executor pode ajustar nomes internos se encontrar impedimento técnico real,
mas deve preservar essa informação, justificar a alteração no registro da
task e manter schema, código, testes e documentação em acordo.

### 3. Tipos de artefato

Definir um vocabulário fechado v1 para os estágios já previstos:

- `page-profiles`;
- `extraction`;
- `project`;
- `decisions`;
- `nbr`;
- `validation-report`;
- `workbook-model`;
- `provenance-index`.

O vocabulário identifica o tipo do recipiente, não autoriza implementar o
conteúdo do estágio. Tipo desconhecido falha com diagnóstico. Acrescentar um
novo tipo exige alteração versionada e testes; não aceitar string arbitrária
silenciosamente.

### 4. Fontes e lineage

Referências a fontes devem usar somente path lógico POSIX relativo e SHA-256
lowercase com 64 caracteres. Devem ser compatíveis com a identidade pública
de `SourceArtifact`, sem ler bytes ou configuração local.

Referências de entrada devem conter, no mínimo, tipo do artefato e SHA-256 dos
bytes canônicos do documento referenciado. Elas:

- são ordenadas deterministicamente;
- não admitem duplicatas;
- não aceitam digest, tipo ou path malformado;
- não usam path absoluto, timestamp, posição em lista ou estado local como
  identidade;
- não precisam abrir ou resolver o artefato referenciado nesta task.

Não implementar o grafo de proveniência, traversal ou detecção de ciclos;
isso pertence a CORE-003. ARCH-001 fornece apenas a referência estável que o
grafo usará.

### 5. Identidade por conteúdo

Fornecer uma operação explícita que calcule SHA-256 sobre os bytes canônicos
completos do envelope persistido, incluindo a newline final. A identidade
retornada deve ter representação estável e inequívoca, por exemplo
`sha256:<64-hex-lowercase>`.

O digest atual não deve ser armazenado dentro da região que ele próprio
resume. Uma referência externa usa o digest calculado; não se cria contrato
circular com placeholder ou segunda serialização implícita.

Documentos semanticamente iguais após a normalização contratada devem gerar o
mesmo digest. Alteração de payload, fonte, configuração estável, produtor,
projeto, tipo ou lineage deve alterar o digest.

### 6. JSON canônico

Definir uma única implementação compartilhada de serialização:

- UTF-8 estrito, sem BOM;
- `ensure_ascii=false`;
- chaves de objetos ordenadas recursivamente;
- separadores compactos;
- arrays preservam ordem, salvo coleções declaradas como conjuntos
  canônicos pelo envelope;
- fontes e referências de input ordenadas por chave estável documentada;
- exatamente uma newline `\n` final;
- nenhuma dependência de locale, timezone, cwd ou ordem do filesystem;
- chaves JSON duplicadas falham no parsing;
- `NaN`, `Infinity`, `-Infinity` e qualquer `float` falham;
- tipos Python não representáveis em JSON falham, sem coerção por `str()`.

Serialização não quantiza, arredonda ou escolhe escala de engenharia.

### 7. Decimal-string

Criar um helper e uma definição reutilizável de schema para representar
`Decimal` finito como string decimal canônica:

- sem expoente, sinal `+`, separador local ou whitespace;
- sem zeros à esquerda não significativos;
- sem zeros fracionários finais não significativos;
- zero negativo normaliza para `"0"`;
- parte fracionária aparece somente quando necessária;
- `NaN` e infinitos falham;
- nenhuma conversão intermediária por `float`.

Exemplos mínimos:

| Entrada `Decimal` | String canônica |
|---|---|
| `Decimal("0")` | `"0"` |
| `Decimal("-0.000")` | `"0"` |
| `Decimal("12.3400")` | `"12.34"` |
| `Decimal("1E+3")` | `"1000"` |
| `Decimal("0.00100")` | `"0.001"` |

Escala, unidade, quantização, locale de entrada e rounding pertencem a
CORE-004. O helper desta task representa valor exato; não define política
numérica de domínio.

### 8. Metadata operacional

Separar conteúdo canônico de informações operacionais como:

- instante de execução;
- hostname, usuário, PID e cwd;
- path absoluto de checkout/store;
- duração, memória e status de processo;
- IDs de run, logs e detalhes de notificação.

Essas informações não entram no envelope persistido, no payload golden nem no
hash de conteúdo. A task pode documentar um boundary para logs/relatórios
operacionais, mas não deve criar um segundo pipeline ou um schema de
orquestração.

Datas que sejam fatos estáveis do domínio ou da fonte não são proibidas em
payloads futuros; o proibido é incorporar metadata volátil de execução à
identidade canônica.

### 9. Compatibilidade

Implementar e documentar política fail-closed:

- leitor v1 aceita somente `schema_version = 1`;
- versão ausente, booleana, fracionária, zero, negativa ou desconhecida falha
  com diagnóstico que informa versão recebida e versões suportadas;
- campos desconhecidos no envelope e em seus objetos de infraestrutura
  falham;
- producer version não substitui schema version;
- mudanças incompatíveis exigem nova versão de schema;
- leitores não descartam campos futuros para “tentar continuar”;
- payload só é confiável quando também validado pelo schema específico do
  estágio.

ARCH-001 não cria schemas semânticos de fatos, projeto, NBR, validação,
workbook ou proveniência. Nesta versão, o payload do envelope é um objeto JSON
opaco e canônico; tasks donas de cada estágio devem fechar seus campos em
schemas próprios.

### 10. Schema e exemplos golden

Criar JSON Schema Draft 2020-12, preferencialmente:

```text
schemas/artifact-envelope-v1.schema.json
```

O schema deve usar `additionalProperties: false` em todos os objetos do
envelope, expor `$defs` reutilizáveis para SHA-256, path lógico,
Decimal-string, referência de fonte, produtor e referência de lineage, e
descrever todas as invariantes estruturalmente representáveis.

Criar exemplos integralmente sintéticos, um para cada tipo de artefato, sob um
path público de testes como:

```text
tests/fixtures/envelopes/v1/
```

Os exemplos não contêm dados, nomes, trechos, digests reais ou paths privados
do AY0410, da norma licenciada ou do XLSX fornecido. Payloads mínimos podem ser
vazios; eles demonstram o envelope, não o domínio.

A validação de produção equivalente permanece stdlib e deve concordar com o
schema nos casos cobertos. Não implementar um motor JSON Schema genérico.

## Fora de escopo explícito

ARCH-001 não pode:

- alterar ou migrar `source-manifest.json` e seu schema;
- alterar ou migrar o índice normativo NBR-000 e seu schema;
- definir `Evidence`, `ObservedFact`, `Resolution`,
  `DecisionRequirement` ou decisões resolvidas;
- definir Project, Building, Floor, Unit, AreaRecord ou ParkingSpace;
- implementar taxonomias, fórmulas, medições, coeficientes ou Quadros NBR;
- implementar grafo de proveniência, traversal, ciclos ou explicação de
  células;
- implementar profiler, parser, renderizador, OCR ou geometria de PDF;
- abrir, mapear, preencher, recalcular ou exportar XLSX;
- criar orquestrador, CLI pública, serviço, banco, cache ou fila;
- escolher política de escala, rounding, quantização ou resíduos;
- criar payloads fictícios como placeholders de tasks futuras;
- ler ou materializar fixtures privadas;
- modificar `inputs/`, store externo, hashes ou inventários;
- adicionar dependência, instalar pacote ou acessar rede;
- modificar configuração de execução, validações externas ou ferramenta
  externa ao repositório;
- executar commit, push, PR, merge, release, deploy ou próxima task.

## Dependências e precondições

- REPO-001 e REPO-002 integradas no commit-base;
- NBR-000 pode coexistir como contrato específico, mas não é dependência
  funcional de ARCH-001;
- checkout público canônico limpo e sincronizado;
- `docs/tasks/ARCH-001.md` rastreado no commit-base;
- Python 3.12+, Git e Bash já provisionados;
- profile integrado com aprovação por Telegram;
- nenhuma dependência de rede durante bootstrap, execução, teste ou revisão;
- gates públicos existentes aprovados antes da implementação.

Se o profile candidato divergir do profile do commit-base, se uma dependência
não estiver integrada ou se os gates públicos falharem, a execução deve
bloquear sem tentar reparar o ambiente.

## Boundary de implementação

```text
SourceArtifact / manifest específico --------+
                                              |
payload futuro de cada estágio ---------------+-- referências estáveis
                                              |
                                              v
                               ArtifactEnvelope v1
                               + compatibilidade
                               + JSON canônico
                               + Decimal-string
                               + content SHA-256
                                              |
                                              v
                               bytes persistíveis e lineage refs

domínio / NBR / PDF / OCR / XLSX / pipeline   fora do boundary
metadata operacional                          fora do hash canônico
```

## Artefatos obrigatórios

O candidate deve conter, no mínimo:

1. pacote público de contratos sob `src/nbr12721/artifacts/` ou nome
   equivalente justificado;
2. value objects imutáveis e erros tipados;
3. parser, validador e serializador canônico v1;
4. helper Decimal-string sem `float`;
5. cálculo de identidade SHA-256 e referências de lineage;
6. `schemas/artifact-envelope-v1.schema.json`;
7. oito goldens sintéticos, um por tipo de artefato v1;
8. testes unitários positivos, negativos e de invariantes;
9. `docs/ARTIFACT_VERSIONING.md` com compatibilidade e exemplos;
10. `README.md`, `ROADMAP.md`, documentação de usuário afetada e esta task
    atualizados materialmente com evidência real.

Não alterar artefatos específicos já integrados apenas para fazê-los usar o
novo envelope.

## Critérios de aceitação

1. O envelope representa versão, tipo, projeto, fontes, produtor,
   configuração, inputs e payload sem campo operacional volátil.
2. Contratos são imutáveis e rejeitam tipos incorretos sem coerção silenciosa.
3. `schema_version` incompatível falha com diagnóstico explícito.
4. Tipo desconhecido, campo desconhecido, digest/path inválido e duplicata de
   fonte/input falham deterministicamente.
5. Source refs usam IDs lógicos relativos e SHA-256, sem abrir fixtures.
6. Lineage refs usam tipo e digest canônico, sem resolver grafo nesta task.
7. Fontes e inputs têm ordenação canônica independente da ordem recebida.
8. Ordem de arrays do payload é preservada; ordem de chaves não muda bytes.
9. JSON duplicado, BOM, encoding inválido, valor não finito, `float` ou tipo
   Python não suportado falha.
10. Duas serializações equivalentes são byte a byte idênticas e terminam com
    exatamente uma newline.
11. O content SHA-256 é calculado sobre esses bytes e muda quando conteúdo
    estável relevante muda.
12. Decimal-string atende aos exemplos, preserva valor exato e nunca passa
    por `float`.
13. Schema Draft 2020-12 e validação Python concordam nos casos positivos e
    negativos cobertos.
14. Os oito goldens são canônicos, validam e reconstroem byte a byte.
15. Nenhum golden ou log contém bytes, metadata privada ou digest real das 14
    fixtures.
16. Manifests, registries e schemas existentes permanecem byte a byte
    inalterados.
17. Nenhum modelo de domínio, regra NBR, PDF, OCR, XLSX ou orquestração é
    implementado.
18. README e guias distinguem claramente a infraestrutura disponível dos
    payloads ainda planejados.
19. Todos os gates passam offline usando somente dependências provisionadas.
20. Nenhuma operação reservada ao operador é executada automaticamente.

## Testes e gates

Gates públicos obrigatórios:

```bash
python3 scripts/private-fixtures/validate-gate.py
python3 -m compileall -q src tests scripts/private-fixtures scripts/ci
PYTHONPATH=src:scripts/private-fixtures python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 scripts/ci/validate-public-tree.py --candidate
git diff --check
git status --short --untracked-files=all
```

Não executar configuração ou materialização de fixtures: o marcador desta task
é `private_fixtures: none`.

Testes focados devem cobrir no mínimo:

### Construção e validação

- envelope mínimo válido de cada tipo;
- value objects imutáveis;
- versão ausente, booleana, fracionária, zero, negativa e desconhecida;
- tipo de artefato desconhecido;
- campos ausentes e extras em todos os objetos de infraestrutura;
- strings vazias/whitespace e coerções indevidas;
- path absoluto, traversal, backslash, NUL e SHA-256 inválido;
- fontes e inputs duplicados;
- payload não objeto.

### Canonicalização e identidade

- permutações de ordem de chaves produzem os mesmos bytes;
- permutações de fontes/inputs produzem os mesmos bytes;
- ordem de arrays dentro do payload permanece significativa;
- serialização repetida e parse/serialize são byte-estáveis;
- exatamente uma newline final e UTF-8 sem BOM;
- chave JSON duplicada e UTF-8 inválido falham;
- `float`, NaN, infinidades, sets, bytes e objetos arbitrários falham;
- alteração de cada campo estável relevante modifica o content SHA-256;
- content ID tem formato canônico e corresponde a cálculo independente.

### Decimal-string

- casos da tabela desta task;
- positivos, negativos, inteiros, frações e expoentes de entrada;
- zero negativo;
- valores muito grandes/pequenos sem notação exponencial;
- NaN e infinidades rejeitados;
- teste comprova ausência de conversão por `float`.

### Schema, goldens e regressão

- todos os oito goldens validam;
- goldens versionados são iguais à reconstrução canônica;
- schema incompatível e campos desconhecidos falham;
- patterns usados pelo JSON Schema são compatíveis com ECMA-262;
- casos representáveis produzem o mesmo aceite/rejeição no schema e Python;
- randomized/property tests stdlib com seed fixa exercitam permutações e
  Decimal sem adicionar dependência;
- source manifest e índice normativo existentes continuam validando e
  byte-idênticos.

## Requisitos de inputs imutáveis

- `private_fixtures: none`: não consultar configuração XDG, store externo ou
  `inputs/private/`;
- `inputs/`, `SHA256SUMS`, `INPUTS.md`,
  `manifests/source-manifest.json`,
  `manifests/private-fixtures-v1.json` e
  `registries/normative-reference-index.json` permanecem intactos;
- schemas existentes de source manifest, fixtures e índice normativo não são
  reescritos;
- goldens e testes usam somente dados sintéticos em paths públicos;
- testes destrutivos usam diretórios temporários fora de `inputs/`;
- nenhum cache, sidecar, lock, output ou temporário é criado sob `inputs/`;
- o gate público deve terminar com zero path/digest privado encontrado.

## Restrições de execução

- preservar `.agent-loop/project.toml` exatamente como está no commit-base,
  inclusive `approval.mode = "telegram"`;
- não usar profile candidato para controlar o próprio bootstrap;
- não alterar scripts ou instruções de execução para fazer a task passar;
- execução e testes são offline; nenhuma instalação ou download é permitido;
- não usar `git add`, staging ou commit para ocultar diferença do snapshot
  candidato;
- não escrever fora da worktree, salvo temporários de teste sob diretório
  temporário do sistema;
- aprovação técnica não autoriza integração, push, publicação ou início da
  próxima task;
- limite padrão do operador é cinco iterações; atingir o limite encerra a run
  para revisão de escopo, sem ampliar a task silenciosamente.

## Conclusão e reporte

O candidate só pode ser reportado como `candidate_complete`. O relatório
final deve registrar:

- arquivos criados/modificados;
- shape final do envelope e justificativa de eventual desvio do shape
  conceitual;
- tipos v1 suportados;
- regra exata de JSON canônico, Decimal-string e content SHA-256;
- boundary entre conteúdo estável, payload e metadata operacional;
- política de compatibilidade e diagnóstico de versões;
- goldens produzidos sem reproduzir conteúdo privado;
- comandos, contagens e resultados reais de todos os testes/gates;
- confirmação de que nenhum fixture privado foi solicitado/materializado;
- confirmação byte a byte dos manifests, registries e schemas preexistentes;
- ausência de rede, instalação e dependências novas;
- limitações e riscos residuais;
- confirmação de que não houve commit, push, merge, deploy, publicação ou
  execução da próxima task.

Falha em qualquer critério bloqueante mantém a task incompleta. Não reduzir
testes, afrouxar schema, alterar inputs ou expandir escopo para obter
aprovação.
