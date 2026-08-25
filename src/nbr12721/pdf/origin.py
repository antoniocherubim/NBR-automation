"""Classificação sanitizada de origem provável (vocabulário fechado)."""

from __future__ import annotations

import re

from nbr12721.pdf.config import ALLOWED_PROBABLE_ORIGINS

_AUTOCAD_PDFPLOT = re.compile(r"(?i)(pdfplot|autocad)")
_PDFIUM = re.compile(r"(?i)pdfium")
_PRINTABLE = re.compile(r"[\x20-\x7e\u00a0-\ufffd]+")


def classify_probable_origin(producer_raw: str | None) -> str:
    """Mapeia metadata bruta de produtor para enum sanitizada.

    O valor bruto usado no match é descartado e não aparece no output.
    """
    if producer_raw is None:
        return "absent"
    if type(producer_raw) is not str:
        return "unknown"
    trimmed = producer_raw.strip()
    if trimmed == "":
        return "unknown"
    if _AUTOCAD_PDFPLOT.search(trimmed):
        return "autocad_pdfplot"
    if _PDFIUM.search(trimmed):
        return "pdfium"
    if _PRINTABLE.fullmatch(trimmed) is None:
        return "unknown"
    return "other"


def assert_probable_origin(value: str) -> str:
    if value not in ALLOWED_PROBABLE_ORIGINS:
        raise ValueError(f"origem provável inválida: {value!r}")
    return value
