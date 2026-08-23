"""Erros fail-closed do índice normativo v1."""

from __future__ import annotations


class NormativeIndexError(ValueError):
    """Erro base do catálogo de referências normativas."""


class NormativeValidationError(NormativeIndexError):
    """Documento ou contrato inválido segundo o schema normativo v1."""


class NormativeDigestMismatchError(NormativeIndexError):
    """Digest da fonte normativa diverge do source-manifest público."""
