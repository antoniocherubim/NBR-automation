"""Validação fail-closed de source-manifest v1 sem dependência externa."""

from __future__ import annotations

import re

from nbr12721.sources.errors import ManifestValidationError, MediaTypeError
from nbr12721.sources.media_types import SUPPORTED_MEDIA_TYPES, media_type_for_path
from nbr12721.sources.paths import PathSecurityError, validate_relative_posix_path

_ALLOWED_MEDIA_TYPES = frozenset(SUPPORTED_MEDIA_TYPES.values())
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_ARTIFACT_KEYS = frozenset({"media_type", "path", "sha256", "size_bytes"})
_ROOT_KEYS = frozenset({"artifacts", "schema_version"})


def validate_manifest_document(document: object) -> None:
    """Valida estrutura e tipos do manifest v1.

    Artifacts devem ser únicos e estritamente crescentes por path
    (equivalente a uniqueItems + ordenação do JSON Schema v1).
    """
    if not isinstance(document, dict):
        raise ManifestValidationError("manifest deve ser objeto JSON")

    extra_root = set(document.keys()) - _ROOT_KEYS
    if extra_root:
        raise ManifestValidationError(
            f"campos desconhecidos no manifest: {sorted(extra_root)!r}"
        )
    missing_root = _ROOT_KEYS - set(document.keys())
    if missing_root:
        raise ManifestValidationError(
            f"campos obrigatórios ausentes: {sorted(missing_root)!r}"
        )

    schema_version = _require_exact_int(
        document["schema_version"], "schema_version"
    )
    if schema_version != 1:
        raise ManifestValidationError(
            f"schema_version incompatível: {schema_version!r}"
        )

    artifacts = document["artifacts"]
    if not isinstance(artifacts, list):
        raise ManifestValidationError("artifacts deve ser array")

    previous_path: str | None = None
    for index, item in enumerate(artifacts):
        _validate_artifact(item, index)
        path = item["path"]
        assert isinstance(path, str)
        if previous_path is not None and path <= previous_path:
            raise ManifestValidationError(
                "artifacts deve estar ordenado lexicograficamente por path"
            )
        previous_path = path


def _validate_artifact(item: object, index: int) -> None:
    if not isinstance(item, dict):
        raise ManifestValidationError(
            f"artifacts[{index}] deve ser objeto"
        )

    extra = set(item.keys()) - _ARTIFACT_KEYS
    if extra:
        raise ManifestValidationError(
            f"artifacts[{index}] contém campos desconhecidos: {sorted(extra)!r}"
        )
    missing = _ARTIFACT_KEYS - set(item.keys())
    if missing:
        raise ManifestValidationError(
            f"artifacts[{index}] campos obrigatórios ausentes: {sorted(missing)!r}"
        )

    path = item["path"]
    if not isinstance(path, str) or path == "":
        raise ManifestValidationError(
            f"artifacts[{index}].path deve ser string não vazia"
        )
    try:
        validate_relative_posix_path(
            path, context=f"artifacts[{index}].path"
        )
    except PathSecurityError as exc:
        raise ManifestValidationError(str(exc)) from exc

    digest = item["sha256"]
    if not isinstance(digest, str) or not _SHA256_PATTERN.fullmatch(digest):
        raise ManifestValidationError(
            f"artifacts[{index}].sha256 inválido"
        )

    size_bytes = _require_exact_int(
        item["size_bytes"], f"artifacts[{index}].size_bytes"
    )
    if size_bytes < 0:
        raise ManifestValidationError(
            f"artifacts[{index}].size_bytes deve ser não negativo"
        )

    media_type = item["media_type"]
    if not isinstance(media_type, str) or media_type not in _ALLOWED_MEDIA_TYPES:
        raise ManifestValidationError(
            f"artifacts[{index}].media_type inválido"
        )
    try:
        expected_media_type = media_type_for_path(path)
    except MediaTypeError as exc:
        raise ManifestValidationError(str(exc)) from exc
    if media_type != expected_media_type:
        raise ManifestValidationError(
            f"artifacts[{index}].media_type não corresponde à extensão do path"
        )


def _require_exact_int(value: object, context: str) -> int:
    if type(value) is not int:
        raise ManifestValidationError(f"{context} deve ser inteiro")
    return value
