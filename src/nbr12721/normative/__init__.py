"""Índice normativo v1: autoridade localizada sem regras executáveis.

Módulo independente de PDF, OCR, XLSX, rede e do mecanismo de fixtures
privadas. Consome apenas identidade pública alinhada ao SourceArtifact
lógico da norma.
"""

from __future__ import annotations

from nbr12721.normative.catalog import (
    baseline_references,
    baseline_source_and_references,
)
from nbr12721.normative.errors import (
    NormativeDigestMismatchError,
    NormativeIndexError,
    NormativeValidationError,
)
from nbr12721.normative.index import (
    assert_matches_source_manifest,
    baseline_index_document,
    build_index_dict,
    load_versioned_index,
    parse_index,
    serialize_index,
)
from nbr12721.normative.locator import PageLocator, PrintedPage
from nbr12721.normative.reference import NormativeReference
from nbr12721.normative.schema import validate_index_document
from nbr12721.normative.source import ErrataRecord, NormativeSource
from nbr12721.normative.vocab import (
    FORMALIZATION_STATES,
    REFERENCE_TYPES,
    SCHEMA_VERSION,
    SOURCE_ID,
)

__all__ = [
    "ErrataRecord",
    "FORMALIZATION_STATES",
    "NormativeDigestMismatchError",
    "NormativeIndexError",
    "NormativeReference",
    "NormativeSource",
    "NormativeValidationError",
    "PageLocator",
    "PrintedPage",
    "REFERENCE_TYPES",
    "SCHEMA_VERSION",
    "SOURCE_ID",
    "assert_matches_source_manifest",
    "baseline_index_document",
    "baseline_references",
    "baseline_source_and_references",
    "build_index_dict",
    "load_versioned_index",
    "parse_index",
    "serialize_index",
    "validate_index_document",
]
