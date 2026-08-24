"""Parse, serialização canônica e identidade de conteúdo do envelope v1."""

from __future__ import annotations

import hashlib
from pathlib import Path

from nbr12721.artifacts.canonical_json import dumps_canonical, loads_canonical
from nbr12721.artifacts.errors import ArtifactValidationError
from nbr12721.artifacts.models import ArtifactEnvelope
from nbr12721.artifacts.schema import envelope_from_document, validate_envelope_document
from nbr12721.artifacts.vocab import CONTENT_ID_PREFIX


def build_envelope_dict(envelope: ArtifactEnvelope) -> dict[str, object]:
    """Documento ordenável/validado a partir do value object."""
    if not isinstance(envelope, ArtifactEnvelope):
        raise ArtifactValidationError(
            "build_envelope_dict exige ArtifactEnvelope"
        )
    document = envelope.to_dict()
    validate_envelope_document(document)
    return document


def serialize_envelope(envelope: ArtifactEnvelope | dict[str, object]) -> str:
    """Serializa envelope v1 em JSON canônico byte-estável."""
    if isinstance(envelope, ArtifactEnvelope):
        document = build_envelope_dict(envelope)
    elif type(envelope) is dict:
        # Reconstroi para aplicar ordenação canônica de sources/inputs.
        document = build_envelope_dict(envelope_from_document(envelope))
    else:
        raise ArtifactValidationError(
            "serialize_envelope exige ArtifactEnvelope ou dict"
        )
    return dumps_canonical(document)


def parse_envelope(text: str | bytes) -> ArtifactEnvelope:
    """Parseia bytes/texto JSON e valida o contrato v1."""
    document = loads_canonical(text)
    return envelope_from_document(document)


def content_sha256_hex(envelope: ArtifactEnvelope | dict[str, object] | str | bytes) -> str:
    """SHA-256 hexadecimal dos bytes canônicos (com newline final)."""
    canonical = _canonical_bytes(envelope)
    return hashlib.sha256(canonical).hexdigest()


def content_id(envelope: ArtifactEnvelope | dict[str, object] | str | bytes) -> str:
    """Identidade estável ``sha256:<64-hex-lowercase>``."""
    digest = content_sha256_hex(envelope)
    return f"{CONTENT_ID_PREFIX}{digest}"


def load_envelope(path: Path) -> ArtifactEnvelope:
    """Lê e valida um arquivo de envelope UTF-8."""
    raw = path.read_bytes()
    return parse_envelope(raw)


def _canonical_bytes(
    envelope: ArtifactEnvelope | dict[str, object] | str | bytes,
) -> bytes:
    if isinstance(envelope, (str, bytes)):
        # Re-serializa via parse para garantir forma canônica e contrato.
        parsed = parse_envelope(envelope)
        text = serialize_envelope(parsed)
    else:
        text = serialize_envelope(envelope)
    return text.encode("utf-8")
