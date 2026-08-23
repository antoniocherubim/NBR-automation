# Índice normativo v1 (NBR-000)

Status: **Disponível** (catálogo de autoridade; sem regras executáveis)

## Para que serve

O índice registra *onde* a norma autoriza conceitos futuros (seção, página PDF,
página impressa, tipo e estado), sem copiar o texto protegido e sem calcular
áreas ou preencher quadros.

## Artefatos

| Arquivo | Papel |
|---------|--------|
| [`registries/normative-reference-index.json`](../registries/normative-reference-index.json) | Índice canônico v1 |
| [`schemas/normative-reference-index-v1.schema.json`](../schemas/normative-reference-index-v1.schema.json) | JSON Schema Draft 2020-12 |
| Pacote `nbr12721.normative` | Contratos imutáveis e validação fail-closed (stdlib) |

## Identidade da fonte

- Organização: ABNT
- Designação: NBR 12721
- Ano da norma: **2006** (não 2021)
- Edição: segunda
- Versão corrigida: **3** (data 2021-01-19 / Errata 3)
- ID lógico: `inputs/normativa/ABNT NBR 12721-2006.pdf`
- SHA-256: `76b3c72fd5934867305b2440c3af66ef79004c07496c436095516c3afdc05674`

O metadado “2021” do PDF e a Errata 3 **não** criam uma edição “NBR 12721:2021”.

## Estados de formalização

| Estado | Significado |
|--------|-------------|
| `indexed` | Autoridade localizada; baseline NBR-000 |
| `formalized` | Exige `formal_artifact_ref` rastreável |
| `implemented` | Exige `formal_artifact_ref` e `implementation_ref` |

## Tipos controlados

`definition_classification`, `measurement_delimitation`,
`calculation_distribution`, `applicability_condition`, `form_table`.

## Uso rápido (stdlib)

A partir da raiz do repositório:

```bash
PYTHONPATH=src python3 - <<'PY'
from pathlib import Path
from nbr12721.normative import (
    baseline_index_document,
    load_versioned_index,
    serialize_index,
    assert_matches_source_manifest,
)
import json

root = Path('.')
doc = load_versioned_index(root)
assert serialize_index(doc) == serialize_index(baseline_index_document())
manifest = json.loads((root / 'manifests' / 'source-manifest.json').read_text())
assert_matches_source_manifest(doc, manifest)
print('referências:', len(doc['references']))
PY
```

O módulo **não** lê o store privado, **não** abre o PDF e **não** importa
adapters de fixtures. Conferência humana de localizadores usa a cópia
materializada somente leitura quando a task exige fixtures privadas.

## Compatibilidade

- `schema_version` atual: **1**
- Serialização canônica: UTF-8, chaves ordenadas, separators compactos,
  newline final
- Versão incompatível, campo desconhecido, enum inválido, página PDF ≤ 0,
  booleano como inteiro ou links `formalized`/`implemented` ausentes falham
  de forma determinística

## Fora deste módulo

Regras NBR, Quadros calculados, PDF/OCR/XLSX, Evidence/Resolution e envelopes
gerais de ARCH-001 permanecem **Planejados**.
