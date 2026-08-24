"""Vocabulário fechado e constantes do envelope v1."""

from __future__ import annotations

SCHEMA_VERSION = 1
SUPPORTED_SCHEMA_VERSIONS: tuple[int, ...] = (1,)

ARTIFACT_TYPES: frozenset[str] = frozenset(
    {
        "page-profiles",
        "extraction",
        "project",
        "decisions",
        "nbr",
        "validation-report",
        "workbook-model",
        "provenance-index",
    }
)

CONTENT_ID_PREFIX = "sha256:"
