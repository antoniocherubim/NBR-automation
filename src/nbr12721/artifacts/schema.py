"""Validação fail-closed do documento envelope v1."""

from __future__ import annotations

from nbr12721.artifacts.errors import (
    ArtifactSchemaVersionError,
    ArtifactValidationError,
)
from nbr12721.artifacts.models import (
    ArtifactEnvelope,
    InputRef,
    ProducerRef,
    SourceRef,
)
from nbr12721.artifacts.vocab import (
    ARTIFACT_TYPES,
    SCHEMA_VERSION,
    SUPPORTED_SCHEMA_VERSIONS,
)

_ROOT_KEYS = frozenset(
    {
        "schema_version",
        "artifact_type",
        "project_id",
        "sources",
        "producer",
        "inputs",
        "payload",
    }
)


def validate_envelope_document(document: object) -> None:
    """Valida estrutura e tipos do envelope v1 (fail-closed)."""
    envelope_from_document(document)


def envelope_from_document(document: object) -> ArtifactEnvelope:
    """Constrói ArtifactEnvelope a partir de documento JSON já parseado."""
    if type(document) is not dict:
        raise ArtifactValidationError(
            f"envelope deve ser objeto JSON, recebido {type(document).__name__}"
        )

    extra = set(document.keys()) - _ROOT_KEYS
    if extra:
        raise ArtifactValidationError(
            f"campos desconhecidos no envelope: {sorted(extra)!r}"
        )
    missing = _ROOT_KEYS - set(document.keys())
    if missing:
        raise ArtifactValidationError(
            f"campos obrigatórios ausentes: {sorted(missing)!r}"
        )

    raw_version = document["schema_version"]
    if type(raw_version) is not int:
        raise ArtifactSchemaVersionError(received=raw_version)
    if raw_version != SCHEMA_VERSION:
        raise ArtifactSchemaVersionError(received=raw_version)

    artifact_type = document["artifact_type"]
    if type(artifact_type) is not str or artifact_type not in ARTIFACT_TYPES:
        raise ArtifactValidationError(
            f"artifact_type desconhecido: {artifact_type!r}; "
            f"suportados={sorted(ARTIFACT_TYPES)!r}"
        )

    project_id = document["project_id"]
    if type(project_id) is not str:
        raise ArtifactValidationError(
            f"project_id deve ser string, recebido {type(project_id).__name__}"
        )

    sources_raw = document["sources"]
    if type(sources_raw) is not list:
        raise ArtifactValidationError("sources deve ser array")
    sources = [
        SourceRef.from_dict(item, context=f"sources[{index}]")
        for index, item in enumerate(sources_raw)
    ]

    producer = ProducerRef.from_dict(document["producer"], context="producer")

    inputs_raw = document["inputs"]
    if type(inputs_raw) is not list:
        raise ArtifactValidationError("inputs deve ser array")
    inputs = [
        InputRef.from_dict(item, context=f"inputs[{index}]")
        for index, item in enumerate(inputs_raw)
    ]

    payload = document["payload"]
    if type(payload) is not dict:
        raise ArtifactValidationError(
            f"payload deve ser objeto JSON, recebido {type(payload).__name__}"
        )

    return ArtifactEnvelope(
        schema_version=raw_version,
        artifact_type=artifact_type,
        project_id=project_id,
        sources=tuple(sources),
        producer=producer,
        inputs=tuple(inputs),
        payload=payload,
    )


def assert_supported_schema_version(value: object) -> int:
    """Diagnóstico explícito de compatibilidade de schema_version."""
    if type(value) is not int:
        raise ArtifactSchemaVersionError(
            received=value,
            supported=SUPPORTED_SCHEMA_VERSIONS,
        )
    if value not in SUPPORTED_SCHEMA_VERSIONS:
        raise ArtifactSchemaVersionError(
            received=value,
            supported=SUPPORTED_SCHEMA_VERSIONS,
        )
    return value
