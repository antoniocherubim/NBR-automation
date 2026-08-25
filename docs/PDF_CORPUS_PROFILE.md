# Relatório do corpus AY0410 — page-profiles v1

Status: **Disponível** no worktree candidato (PDF-001 `candidate_complete`;
integração pendente). Regenerado em 2026-08-23 após correção fail-closed do
stream SVG (tags completas que cruzam o limite de 64 KiB), parsers truncados,
cwd restritivo em `pdfinfo -v` e normalização de ordem de páginas.

Este relatório resume agregados públicos do artefato `profiles/page-profiles.json`.
Não reproduz texto das plantas, metadata bruta, paths físicos privados nem geometria
individual.

## Identidade do artefato

| Campo | Valor |
|-------|--------|
| `project_id` | `project:ay0410-dev-corpus` |
| `artifact_type` | `page-profiles` |
| `schema_version` | 1 |
| `payload_version` | 1.0.0 |
| content ID | `sha256:356090fb8586d51b912bdaebaf933fb3e4a50de92f2f4372a27e94c979412c7a` |
| Profiler | `nbr12721-pdf-profiler` 1.0.0 |
| Backend | Poppler 24.02.0 |

## Cobertura

- **12/12** documentos AY0410 selecionados via `manifests/source-manifest.json`
  (prefixo lógico `inputs/projetos_modelo/AY0410/`)
- **12/12** páginas (uma por prancha)
- **12/12** digests SHA-256 verificados antes da leitura
- `inputs = []` no envelope

## Origem provável sanitizada

| Valor | Contagem |
|-------|----------|
| `autocad_pdfplot` | 10 |
| `pdfium` | 2 |

Compatível com achados do ROADMAP (§3.3): dez pranchas AutoCAD/pdfplot, duas PDFium.
`absent` = campo Producer ausente; `unknown` = Producer presente vazio/ilegível.

## Agregados por prancha (ordem lógica)

Contagens de codepoints usam texto decodificado (`html.unescape`); fontes usam
`pdffonts -f/-l` por página; paths SVG contam somente tags `<path>` completas na
renderização (incluindo atributos longos que cruzam o chunk de 64 KiB).
Comparação independente Poppler: **12/12 OK**.

| Basename lógico (`source_path`) | Palavras | Codepoints | Fontes tot/emb/sub | Paths SVG | Imagens | Flags |
|----------------------------------|----------|------------|--------------------|-----------|---------|-------|
| `AY0410-ARQ-PL-0001-PLA-IMPLANTAÇÃO_TÉRREO-R08.pdf` | 99 | 677 | 3/1/0 | 332093 | 10 | `low_native_text`, `has_images`, `high_rendered_svg_complexity` |
| `AY0410-ARQ-PL-0002-PLA-ESTAC_575_582-R03.pdf` | 98 | 677 | 3/1/0 | 24597 | 0 | `low_native_text`, `high_rendered_svg_complexity` |
| `AY0410-ARQ-PL-0003-PLA-ESTAC_586_589-R04.pdf` | 100 | 677 | 3/1/0 | 16378 | 0 | `low_native_text`, `high_rendered_svg_complexity` |
| `AY0410-ARQ-PL-0004-PLA-ESTAC_COBERTURA-R02.pdf` | 101 | 677 | 4/2/0 | 8928 | 0 | `low_native_text` |
| `AY0410-ARQ-PL-0005-PLA-CALCULO_AREAS_COBERTAS-R02.pdf` | 100 | 677 | 4/2/0 | 100026 | 1 | `low_native_text`, `has_images`, `high_rendered_svg_complexity` |
| `AY0410-ARQ-PL-0006-PLA-CALCULO_AREAS_DESCOBERTAS-R03.pdf` | 100 | 677 | 3/1/0 | 100012 | 1 | `low_native_text`, `has_images`, `high_rendered_svg_complexity` |
| `AY0410-ARQ-PL-0007-PLA-TIPO_TORRE01-R02.pdf` | 1069 | 4607 | 6/3/0 | 16584 | 0 | `high_rendered_svg_complexity` |
| `AY0410-ARQ-PL-0008-PLA-COBERTURA_TORRE01-R02.pdf` | 817 | 3976 | 6/3/0 | 18890 | 0 | `high_rendered_svg_complexity` |
| `AY0410-ARQ-PL-0009-PLA-TIPO_TORRE02-R03.pdf` | 1060 | 4631 | 6/3/0 | 16128 | 0 | `high_rendered_svg_complexity` |
| `AY0410-ARQ-PL-0010-PLA-COBERTURA_TORRE02-R02.pdf` | 799 | 3969 | 6/3/0 | 18884 | 0 | `high_rendered_svg_complexity` |
| `AY0410-ARQ-PL-0011-COR-CORTE_CC_FACHADA-R02.pdf` | 726 | 3618 | 6/3/0 | 94869 | 164 | `has_images`, `high_rendered_svg_complexity` |
| `AY0410-ARQ-PL-0012-COR-CORTE_AA_CORTE_BB_CORTE_CC-R02.pdf` | 1248 | 5766 | 6/3/0 | 123779 | 0 | `high_rendered_svg_complexity` |

## Leituras compatíveis com o ROADMAP

1. **Pouco texto ≠ scan:** estacionamentos (PL-0002–0004) têm ~98–101 palavras e forte
   sinal vetorial; PL-0002/0003 também `high_rendered_svg_complexity`; zero imagens —
   flags sobrepostas, sem inferência OCR/scan.
2. **Memoriais híbridos:** PL-0005/0006 combinam ~100 palavras, imagem raster e
   **100.026** / **100.012** paths SVG renderizados (acima de 100 mil; alinhado à
   tabela deste relatório e ao artefato).
3. **Torres textuais:** PL-0007–0010 têm centenas a ~1069 palavras nativas.
4. **Corte com imagens:** PL-0011 reporta 164 objetos raster e alto path count.
5. **Nenhuma flag proibida** (`is_scan`, `needs_ocr`, etc.) foi emitida.

## Verificação

Reconstrução determinística confirmada:

```bash
PYTHONPATH=src python3 scripts/pdf/profile-ay0410.py --check
# documents=12 pages=12 content_id=sha256:356090fb8586d51b912bdaebaf933fb3e4a50de92f2f4372a27e94c979412c7a
```

## Limitações

- Paths SVG variam com versão/build Poppler; content ID amarra backend/versão no produtor.
- Thresholds v1 não devem ser tratados como regra geral fora deste corpus.
- Renderização SVG grande usa stdout em diretório temporário restritivo (limite hard de
  ~64 MiB por arquivo temporário observado no host impede saída file-based para PL-0001).

## Privacidade

Nenhum path sob `inputs/private/`, texto extraído ou metadata bruta aparece neste
relatório ou no artefato versionado.
