# Profiler PDF — guia operacional e técnico (PDF-001)

Status: **Disponível** no worktree candidato (PDF-001 `candidate_complete`;
integração pendente do operador). Backend Poppler, artefato `page-profiles` v1.

## Objetivo

O profiler caracteriza cada página de um PDF por sinais mensuráveis — texto nativo,
fontes, imagens raster, boxes, rotação, origem provável sanitizada e complexidade
estrutural de uma renderização SVG — **sem** extrair conteúdo, decidir OCR ou
inferir semântica arquitetônica.

Medição, flag descritiva e decisão de pipeline permanecem separadas.

## Boundary

```text
source-manifest + mapping lógico/físico verificado
        → backend Poppler (subprocessos locais)
        → sinais brutos normalizados por página
        → flags descritivas v1 (thresholds versionados)
        → envelope ARCH-001 artifact_type=page-profiles
```

- O pacote `nbr12721.pdf` **não** lê XDG, store privado nem variáveis de ambiente.
- O script `scripts/pdf/profile-ay0410.py` monta o mapping a partir do inventário
  público `manifests/private-fixtures-v1.json` (somente IDs lógicos e paths relativos
  esperados de materialização).
- `nbr12721.artifacts` e `nbr12721.sources` **não** importam Poppler.
- Falhas de verificação de fonte sobem como `PdfProfilerError` com **ID lógico**
  apenas — nunca path físico/`inputs/private/` nem path absoluto.

## Backend Poppler

Ferramentas provisionadas localmente (sem instalação em runtime):

| Comando | Uso |
|---------|-----|
| `pdfinfo` + `pdfinfo -box -f/-l` | contagem de páginas/produtor; media/crop box e rotação **por página** |
| `pdftotext -bbox-layout -f/-l` | contagens de palavras/codepoints (UTF-8 + entidades XML decodificadas)/bbox |
| `pdffonts -f/-l` | fontes por página via colunas à direita (`emb`/`sub`/`uni`/object ID) |
| `pdfimages -list` | contagens e agregados de largura/altura/pixels (página ≥ 1) |
| `pdftocairo -svg … -` | contagens estruturais do SVG renderizado (stdout em temp restritivo) |

Execução:

- lista de argumentos, `shell=False`;
- `LC_ALL=C`, ambiente mínimo;
- timeout aplicado **durante** a leitura de stdout/stderr (não só no `wait` final);
- em qualquer erro de parse/encoding do stream SVG, o filho é **morto** antes do
  retorno (não depende do `Popen.__exit__`/`wait` ilimitado);
- UTF-8 estrito (encoding inválido falha fechado; sem `errors="ignore"`);
- limites de stdout/stderr/stream e `assert_artifact_size` no temp restritivo;
- contagem SVG por tags completas (`<path …/>`), retendo markup incompleto entre
  chunks e exigindo `<svg` **e** `</svg>` **sem** lixo trailing após o close;
- `pdftotext` exige envelope HTML completo (`<html>`/`</html>`, `<body>`/`</body>`,
  `<doc>`/`</doc>`) e **exatamente uma** `<page>`/`</page>` por pedido de página
  (truncar após `</doc>` sem fechar body/html, ou combinar duas páginas, falha);
  `pdffonts` exige name/type/encoding + emb/sub/uni/IDs;
  `pdfimages` exige linha completa até `enc`/`interp`/object ID (truncar após
  width/height ou após `bpc` falha) e rejeita página fora de 1..N;
  `pdfinfo` rejeita `Pages:` duplicados/conflitantes e página duplicada ou fora
  de faixa em `-box`;
- entrada symlink é rejeitada no boundary do backend (antes de `resolve`);
- `pdfinfo -v` e os comandos de perfilamento usam diretório temporário restritivo
  como `cwd`;
- helper file-based `_count_rendered_svg_elements` e `assert_artifact_size`
  cobertos por testes unitários;
- erros fail-closed **sem** path absoluto, texto extraído ou stderr bruto nos logs.

A métrica `rendered_svg_path_count` (e correlatas `rendered_svg_*_count`) reflete a
renderização SVG temporária, **não** operadores internos do PDF.

## Thresholds v1 (provisórios para AY0410)

Persistidos no `producer.configuration.thresholds` e no payload:

| Threshold | Valor | Justificativa |
|-----------|-------|----------------|
| `low_native_text_word_count` | 150 | Implantação, estacionamentos e memoriais têm ~98–101 palavras; limite acima desse cluster |
| `high_rendered_svg_path_count` | 10000 | Memoriais e plantas densas excedem 10k paths na renderização SVG; estacionamentos vetoriais também |

### Flags descritivas (sobreponíveis)

| Flag | Condição |
|------|----------|
| `low_native_text` | `native_word_count <= low_native_text_word_count` |
| `has_images` | `image_count > 0` |
| `high_rendered_svg_complexity` | `rendered_svg_path_count >= high_rendered_svg_path_count` |

**Proibidas:** `is_scan`, `needs_ocr`, `text_page`, `vector_page` ou qualquer decisão
de pipeline. Uma prancha de estacionamento com pouco texto **e** muitos vetores recebe
**ambas** as flags aplicáveis; o profiler não a classifica como scan.

## Coordenadas

- unidade: `pt`
- origem: `bottom-left`
- eixos: x → direita, y → cima
- valores persistidos como **Decimal-string** canônica (sem `float`)

## Origem provável sanitizada

Vocabulário fechado: `autocad_pdfplot`, `pdfium`, `other`, `absent`, `unknown`.
Matching case-insensitive em tokens genéricos (`pdfplot`/`autocad`, `pdfium`); metadata
bruta nunca aparece no artefato. `absent` só quando o campo Producer **não existe**;
Producer presente vazio ou só whitespace é `unknown`.

## Schema e validador

- `schemas/page-profiles-v1.schema.json` (Draft 2020-12) e
  `nbr12721.pdf.schema.validate_page_profiles_payload(payload, sources=…)` concordam com
  `tests/page_profiles_schema_support.py` (Draft 2020-12 + extensão `x-uniqueProperty`):
  - `minItems` / `minLength` (documents/pages/source_path não vazios);
  - `uniqueItems` em flags;
  - `x-uniqueProperty` para `source_path` e `page_number` (same-key/different-body rejeitado);
  - cobertura exata de fontes exigida via argumento `sources`;
  - rejeição de campos desconhecidos, `float`, `bool` onde cabe inteiro, contagens
    negativas e enums inválidos.

## Comandos

Verificar/reconstruir o artefato versionado (requer fixtures materializadas):

```bash
bash scripts/private-fixtures/configure.sh --check
PYTHONPATH=src:scripts/private-fixtures python3 scripts/private-fixtures/materialize.py
PYTHONPATH=src python3 scripts/pdf/profile-ay0410.py --check
```

Regenerar o artefato rastreado (operador; não faz parte da CI pública):

```bash
PYTHONPATH=src python3 scripts/pdf/profile-ay0410.py --write
```

Suíte pública (PDFs sintéticos incl. multipágina, parsers fail-closed, schema Draft 2020-12,
limites de `run_command`/artefato temporário, symlink rejeitado, timeout SVG com
kill do filho, conformidade negativa, temp restritivo — **sem skip**). A descoberta
`unittest` **executa Poppler de verdade** sobre PDFs sintéticos; Poppler ausente
falha, não pula testes. Não usa store privado:

```bash
PYTHONPATH=src python3 -m unittest tests.test_pdf_profiler -v
```

## Artefatos

| Path | Descrição |
|------|-----------|
| `profiles/page-profiles.json` | Envelope ARCH-001 canônico |
| `schemas/page-profiles-v1.schema.json` | JSON Schema Draft 2020-12 do payload |

## Riscos residuais

- Thresholds v1 são provisórios para AY0410; generalização aguarda GEN-001.
- Contagens SVG dependem da versão Poppler instalada (observado: 24.02.0) e de
  tags completas que cruzam o limite de leitura de 64 KiB.
- PDFs com renderização SVG muito grande usam contagem via stream stdout dentro do temp
  restritivo (limite hard ~64 MiB por arquivo temporário no host impede saída file-based
  para PL-0001); helper file-based permanece disponível para outputs menores/testes.
- `profile-ay0410.py --check` valida sinais mínimos por prancha (estacionamento, memorial,
  híbrido) além de totais/origem — divergência material falha fechado.

## Referências

- [docs/PDF_CORPUS_PROFILE.md](PDF_CORPUS_PROFILE.md) — agregados do corpus AY0410
- [docs/tasks/PDF-001.md](tasks/PDF-001.md) — especificação e evidências
- [docs/ARTIFACT_VERSIONING.md](ARTIFACT_VERSIONING.md) — envelope comum v1
