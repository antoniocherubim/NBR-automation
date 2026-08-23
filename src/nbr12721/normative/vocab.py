"""Vocabulários fechados do índice normativo v1."""

from __future__ import annotations

REFERENCE_TYPES = frozenset(
    {
        "definition_classification",
        "measurement_delimitation",
        "calculation_distribution",
        "applicability_condition",
        "form_table",
    }
)

FORMALIZATION_STATES = frozenset(
    {
        "indexed",
        "formalized",
        "implemented",
    }
)

PRINTED_PAGE_KINDS = frozenset(
    {
        "arabic",
        "roman",
        "absent",
    }
)

# Identidade estável da edição fornecida (não inventa “NBR 12721:2021”).
SOURCE_ID = "abnt-nbr-12721-2006-vc3"
LOGICAL_PATH = "inputs/normativa/ABNT NBR 12721-2006.pdf"
EXPECTED_SHA256 = (
    "76b3c72fd5934867305b2440c3af66ef79004c07496c436095516c3afdc05674"
)
EXPECTED_MEDIA_TYPE = "application/pdf"
EXPECTED_SIZE_BYTES = 1_208_230
SCHEMA_VERSION = 1
