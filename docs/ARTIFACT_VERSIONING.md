# Versionamento de artefatos intermediários (ARCH-001)

Status: **Disponível** (envelope comum v1; payloads de domínio ainda
**Planejados**)

## Para que serve

O envelope comum v1 é o recipiente persistível que estágios futuros
(extração, resolução, NBR, validação, workbook, proveniência) usarão para
trocar documentos versionados sem depender de classes internas uns dos
outros.

ARCH-001 define o **recipiente** e suas invariantes. Não define o conteúdo
semântico de cada estágio.

## Artefatos

| Arquivo | Papel |
|---------|--------|
| Pacote `nbr12721.artifacts` | Value objects, validação, JSON canônico, Decimal-string, content ID |
| [`schemas/artifact-envelope-v1.schema.json`](../schemas/artifact-envelope-v1.schema.json) | JSON Schema Draft 2020-12 |
| [`tests/fixtures/envelopes/v1/`](../tests/fixtures/envelopes/v1/) | Oito goldens sintéticos (um por tipo v1) |

Contratos específicos já existentes **não** foram migrados para este
envelope:

- `manifests/source-manifest.json` (`nbr12721.sources`)
- `registries/normative-reference-index.json` (`nbr12721.normative`)

## Shape do envelope v1

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

Campos:

| Campo | Significado |
|-------|-------------|
| `schema_version` | Inteiro exato `1` (não confundir com `producer.version`) |
| `artifact_type` | Vocabulário fechado v1 (abaixo) |
| `project_id` | Identidade lógica estável do projeto |
| `sources` | Fontes originais por path lógico POSIX relativo + SHA-256 |
| `producer` | Nome, versão e configuração **estável** do produtor |
| `inputs` | Lineage: tipo + SHA-256 dos bytes canônicos do artefato de entrada |
| `payload` | Objeto JSON opaco do estágio (schema semântico: tasks futuras) |

### Tipos v1 suportados

`page-profiles`, `extraction`, `project`, `decisions`, `nbr`,
`validation-report`, `workbook-model`, `provenance-index`.

Tipo desconhecido falha com diagnóstico. Acrescentar tipo exige mudança
versionada e testes.

### Ordenação canônica

- `sources`: ordenados por `(path, sha256)`; path duplicado é erro.
- `inputs`: ordenados por `(artifact_type, content_sha256)`; par duplicado é erro.
- Arrays **dentro** de `payload` preservam ordem.
- Chaves de objetos são ordenadas na serialização; a ordem de inserção não
  altera bytes.

## JSON canônico

Uma única implementação (`dumps_canonical` / `loads_canonical`):

- UTF-8 estrito, sem BOM;
- `ensure_ascii=false`;
- chaves ordenadas recursivamente;
- separadores compactos `,` / `:`;
- exatamente uma newline `\n` final;
- chave duplicada, BOM, UTF-8 inválido, `float`, `NaN`, infinitos, `set`,
  `bytes`, surrogate isolado e tipos Python não JSON-representáveis falham
  (sem `str()`).

Os value objects congelam `payload` e `producer.configuration`
recursivamente. Alterar os dicionários/listas fornecidos pelo chamador depois
da construção não altera o envelope nem seu content ID.

## Identidade de conteúdo

```text
content_id = "sha256:" + SHA256(bytes_canônicos_do_envelope)
```

O digest é calculado sobre a serialização canônica completa, incluindo a
newline final. **Não** é armazenado dentro da região que resume (sem
contrato circular).

## Decimal-string

Helper `decimal_to_canonical_string(Decimal)`:

- sem expoente, sinal `+`, locale ou whitespace;
- sem zeros à esquerda/fracionários não significativos;
- zero negativo → `"0"`;
- nunca passa por `float`;
- não arredonda nem depende da precisão do contexto Decimal corrente.

Escala, rounding e quantização de domínio permanecem em CORE-004.

## Metadata operacional (fora do envelope)

Não entram no envelope persistido nem no hash de conteúdo:

- instante de execução, hostname, usuário, PID, cwd;
- paths absolutos de checkout/store;
- duração, memória, status de processo;
- IDs de run, logs e notificações.

Datas que forem **fatos estáveis de domínio** em payloads futuros não são
proibidas; o proibido é metadata volátil de execução na identidade canônica.

## Compatibilidade fail-closed

- Leitor v1 aceita somente `schema_version = 1`.
- Versão ausente, booleana, fracionária, zero, negativa ou desconhecida falha
  com diagnóstico `recebido=…; suportado=[1]`.
- Campos desconhecidos no envelope e em objetos de infraestrutura falham.
- `producer.version` **não** substitui `schema_version`.
- Leitores não descartam campos futuros para “continuar”.
- Payload só é confiável após validação pelo schema específico do estágio
  (ainda **Planejado** por task dona).

## Uso rápido (stdlib)

A partir da raiz do repositório:

```bash
PYTHONPATH=src python3 - <<'PY'
from nbr12721.artifacts import (
    ArtifactEnvelope, SourceRef, ProducerRef,
    serialize_envelope, parse_envelope, content_id,
)

env = ArtifactEnvelope(
    schema_version=1,
    artifact_type='extraction',
    project_id='project:synthetic-demo',
    sources=(SourceRef(path='inputs/synthetic/demo.pdf', sha256='a'*64),),
    producer=ProducerRef(name='synthetic-producer', version='1.0.0', configuration={}),
    inputs=(),
    payload={},
)
text = serialize_envelope(env)
assert parse_envelope(text).artifact_type == 'extraction'
print(content_id(env))
PY
```

## O que ainda não está neste contrato

| Item | Status |
|------|--------|
| Schemas semânticos de facts/project/NBR/validation/workbook | **Planejada** |
| Grafo de proveniência / ciclos (CORE-003) | **Planejada** |
| Política numérica de escala/rounding (CORE-004) | **Planejada** |
| Orquestrador / CLI / pipeline E2E | **Planejada** |
| Encapsular `resultado.xlsx` | Fora de escopo (binário de saída) |
