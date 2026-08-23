"""Montagem, serialização e checagens do índice normativo v1."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path

from nbr12721.normative.catalog import baseline_source_and_references
from nbr12721.normative.errors import (
    NormativeDigestMismatchError,
    NormativeValidationError,
)
from nbr12721.normative.reference import NormativeReference
from nbr12721.normative.schema import validate_index_document
from nbr12721.normative.source import NormativeSource
from nbr12721.sources.schema import validate_manifest_document
from nbr12721.normative.vocab import (
    EXPECTED_SHA256,
    LOGICAL_PATH,
    SCHEMA_VERSION,
)


def build_index_dict(
    *,
    source: NormativeSource,
    references: Sequence[NormativeReference],
) -> dict[str, object]:
    """Constrói documento ordenado e validado."""
    ordered = sorted(references, key=lambda item: item.id)
    document: dict[str, object] = {
        "references": [item.to_dict() for item in ordered],
        "schema_version": SCHEMA_VERSION,
        "source": source.to_dict(),
    }
    validate_index_document(document)
    return document


def serialize_index(document: dict[str, object]) -> str:
    """Serializa UTF-8 byte-estável com newline final."""
    validate_index_document(document)
    return (
        json.dumps(
            document,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    )


def parse_index(text: str) -> dict[str, object]:
    try:
        document = json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except json.JSONDecodeError as exc:
        raise NormativeValidationError(f"JSON inválido: {exc.msg}") from exc
    validate_index_document(document)
    return document


def baseline_index_document() -> dict[str, object]:
    """Reconstrói o índice baseline NBR-000."""
    source, references = baseline_source_and_references()
    return build_index_dict(source=source, references=list(references))


def assert_matches_source_manifest(
    document: Mapping[str, object],
    source_manifest: Mapping[str, object],
) -> None:
    """Confronta digest/path/media_type/size com o source-manifest público."""
    validate_index_document(dict(document))
    validate_manifest_document(dict(source_manifest))
    artifacts = source_manifest.get("artifacts")
    if not isinstance(artifacts, list):
        raise NormativeValidationError(
            "source-manifest.artifacts inválido"
        )
    matches = [
        item
        for item in artifacts
        if isinstance(item, dict) and item.get("path") == LOGICAL_PATH
    ]
    if len(matches) != 1:
        raise NormativeDigestMismatchError(
            f"fonte {LOGICAL_PATH!r} deve ocorrer exatamente uma vez no source-manifest"
        )
    match = matches[0]
    source = document.get("source")
    if not isinstance(source, dict):
        raise NormativeValidationError("document.source inválido")
    for key in ("sha256", "media_type", "size_bytes"):
        if source.get(key) != match.get(key):
            raise NormativeDigestMismatchError(
                f"source.{key} diverge do source-manifest"
            )
    if source.get("sha256") != EXPECTED_SHA256:
        raise NormativeDigestMismatchError(
            "sha256 diverge do digest autoritativo"
        )


def _reject_duplicate_keys(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise NormativeValidationError(f"chave JSON duplicada: {key!r}")
        result[key] = value
    return result


def load_versioned_index(repo_root: Path) -> dict[str, object]:
    """Lê e valida registries/normative-reference-index.json."""
    path = repo_root / "registries" / "normative-reference-index.json"
    return parse_index(path.read_text(encoding="utf-8"))
