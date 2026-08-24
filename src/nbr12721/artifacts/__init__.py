"""Contrato comum v1 de envelopes de artefatos intermediários.

Pacote independente de PDF, OCR, XLSX, NBR, UI e fixtures privadas.
Define o recipiente versionado, JSON canônico, Decimal-string e identidade
por conteúdo. Payloads de domínio permanecem opacos até as tasks donas de
cada estágio.
"""

from __future__ import annotations

from nbr12721.artifacts.canonical_json import (
    assert_json_safe,
    dumps_canonical,
    loads_canonical,
)
from nbr12721.artifacts.decimal_string import (
    decimal_to_canonical_string,
    is_canonical_decimal_string,
    parse_canonical_decimal_string,
)
from nbr12721.artifacts.envelope import (
    build_envelope_dict,
    content_id,
    content_sha256_hex,
    load_envelope,
    parse_envelope,
    serialize_envelope,
)
from nbr12721.artifacts.errors import (
    ArtifactCanonicalJsonError,
    ArtifactDecimalError,
    ArtifactError,
    ArtifactSchemaVersionError,
    ArtifactValidationError,
)
from nbr12721.artifacts.models import (
    ArtifactEnvelope,
    InputRef,
    ProducerRef,
    SourceRef,
)
from nbr12721.artifacts.schema import (
    assert_supported_schema_version,
    envelope_from_document,
    validate_envelope_document,
)
from nbr12721.artifacts.vocab import (
    ARTIFACT_TYPES,
    CONTENT_ID_PREFIX,
    SCHEMA_VERSION,
    SUPPORTED_SCHEMA_VERSIONS,
)

__all__ = [
    "ARTIFACT_TYPES",
    "ArtifactCanonicalJsonError",
    "ArtifactDecimalError",
    "ArtifactEnvelope",
    "ArtifactError",
    "ArtifactSchemaVersionError",
    "ArtifactValidationError",
    "CONTENT_ID_PREFIX",
    "InputRef",
    "ProducerRef",
    "SCHEMA_VERSION",
    "SUPPORTED_SCHEMA_VERSIONS",
    "SourceRef",
    "assert_json_safe",
    "assert_supported_schema_version",
    "build_envelope_dict",
    "content_id",
    "content_sha256_hex",
    "decimal_to_canonical_string",
    "dumps_canonical",
    "envelope_from_document",
    "is_canonical_decimal_string",
    "load_envelope",
    "loads_canonical",
    "parse_canonical_decimal_string",
    "parse_envelope",
    "serialize_envelope",
    "validate_envelope_document",
]
