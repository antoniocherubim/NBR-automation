"""Helpers para PDFs sintéticos mínimos em testes (stdlib, diretório temporário)."""

from __future__ import annotations

from pathlib import Path


def write_minimal_text_pdf(
    path: Path,
    *,
    text: str = "Hello",
    media_box: tuple[str, str, str, str] = ("0", "0", "200", "100"),
    crop_box: tuple[str, str, str, str] | None = None,
    producer: str | None = "pdfplot11.hdi 11.1.18.0",
    rotate: int = 0,
) -> None:
    """Grava PDF mínimo com uma página e texto nativo."""
    x0, y0, x1, y1 = media_box
    cx0, cy0, cx1, cy1 = crop_box or media_box
    content = f"BT /F1 12 Tf 10 50 Td ({text}) Tj ET"
    page_attrs = (
        f"/Type /Page /Parent 2 0 R /MediaBox [{x0} {y0} {x1} {y1}] "
        f"/CropBox [{cx0} {cy0} {cx1} {cy1}] /Contents 4 0 R "
        f"/Resources << /Font << /F1 5 0 R >> >>"
    )
    if rotate:
        page_attrs += f" /Rotate {rotate}"
    info = ""
    if producer is not None:
        info = (
            "6 0 obj << "
            + (f"/Producer ({producer}) " if producer else "")
            + ">> endobj\n"
        )
    body = f"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << {page_attrs} >> endobj
4 0 obj << /Length {len(content)} >> stream
{content}
endstream endobj
5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj
{info}xref
0 7
0000000000 65535 f
trailer << /Size 7 /Root 1 0 R >>
startxref
0
%%EOF
"""
    path.write_bytes(body.encode("latin-1"))


def write_minimal_vector_pdf(path: Path) -> None:
    """PDF sintético predominantemente vetorial (sem texto)."""
    content = "0 0 m 100 0 l 100 100 l 0 100 l h S"
    body = f"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200]
/Contents 4 0 R /Resources << >> >> endobj
4 0 obj << /Length {len(content)} >> stream
{content}
endstream endobj
6 0 obj << /Producer (pdfplot test) >> endobj
xref
0 7
trailer << /Size 7 /Root 1 0 R >>
startxref
0
%%EOF
"""
    path.write_bytes(body.encode("latin-1"))


def write_minimal_raster_pdf(path: Path) -> None:
    """PDF sintético com uma imagem raster embutida."""
    image_bytes = b"\xff\x00\x00"
    content = "q 50 0 0 50 20 20 cm /Im0 Do Q"
    stream = (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200]\n"
        b"/Contents 4 0 R /Resources << /XObject << /Im0 5 0 R >> >> >> endobj\n"
        b"4 0 obj << /Length "
        + str(len(content)).encode()
        + b" >> stream\n"
        + content.encode()
        + b"\nendstream endobj\n"
        b"5 0 obj << /Type /XObject /Subtype /Image /Width 1 /Height 1 "
        b"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Length "
        + str(len(image_bytes)).encode()
        + b" >> stream\n"
        + image_bytes
        + b"\nendstream endobj\n"
        b"6 0 obj << /Producer (PDFium) >> endobj\n"
        b"xref\n0 7\ntrailer << /Size 7 /Root 1 0 R /Info 6 0 R >>\n"
        b"startxref\n0\n%%EOF\n"
    )
    path.write_bytes(stream)


def write_minimal_hybrid_pdf(path: Path) -> None:
    """PDF sintético híbrido: texto nativo + vetor + imagem."""
    image_bytes = b"\x00\xff\x00"
    content = (
        "0 0 m 100 0 l S "
        "BT /F1 10 Tf 10 80 Td (Hybrid) Tj ET "
        "q 40 0 0 40 120 20 cm /Im0 Do Q"
    )
    stream = (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] "
        b"/CropBox [10 10 290 190] /Rotate 90 "
        b"/Contents 4 0 R /Resources << /Font << /F1 6 0 R >> "
        b"/XObject << /Im0 5 0 R >> >> >> endobj\n"
        b"4 0 obj << /Length "
        + str(len(content)).encode()
        + b" >> stream\n"
        + content.encode()
        + b"\nendstream endobj\n"
        b"5 0 obj << /Type /XObject /Subtype /Image /Width 1 /Height 1 "
        b"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Length "
        + str(len(image_bytes)).encode()
        + b" >> stream\n"
        + image_bytes
        + b"\nendstream endobj\n"
        b"6 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
        b"7 0 obj << /Producer (pdfplot hybrid) >> endobj\n"
        b"xref\n0 8\ntrailer << /Size 8 /Root 1 0 R /Info 7 0 R >>\n"
        b"startxref\n0\n%%EOF\n"
    )
    path.write_bytes(stream)


def write_multipage_mixed_pdf(path: Path) -> None:
    """PDF sintético de duas páginas com boxes, rotações, fontes e sinais distintos."""
    body = """%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R 8 0 R] /Count 2 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 200 100]
/CropBox [10 10 190 90] /Rotate 0 /Contents 4 0 R
/Resources << /Font << /F1 5 0 R >> >> >> endobj
4 0 obj << /Length 44 >> stream
BT /F1 12 Tf 12 40 Td (Page1) Tj ET
endstream endobj
5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj
6 0 obj << /Producer (pdfplot page1) >> endobj
8 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200]
/CropBox [0 0 250 150] /Rotate 90 /Contents 9 0 R
/Resources << /Font << /F2 10 0 R /F3 11 0 R >> >> >> endobj
9 0 obj << /Length 31 >> stream
0 0 m 120 0 l S
endstream endobj
10 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >> endobj
11 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Courier >> endobj
12 0 obj << /Producer (PDFium page2) >> endobj
xref
0 13
trailer << /Size 13 /Root 1 0 R /Info 12 0 R >>
startxref
0
%%EOF
"""
    path.write_bytes(body.encode("latin-1"))
