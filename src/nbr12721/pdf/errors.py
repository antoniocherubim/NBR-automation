"""Erros tipados do boundary PDF (fail-closed, sem vazamento de conteúdo)."""

from __future__ import annotations


class PdfError(Exception):
    """Erro base do boundary PDF."""


class PdfBackendError(PdfError):
    """Falha do backend ou subprocesso Poppler."""


class PdfParseError(PdfError):
    """Saída de ferramenta Poppler ilegível ou inesperada."""


class PdfProfilerError(PdfError):
    """Falha na normalização ou montagem do payload page-profiles."""


class PdfSchemaError(PdfError):
    """Payload page-profiles incompatível com o contrato v1."""
