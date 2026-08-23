"""Manifest canônico source-manifest v1."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from nbr12721.sources.artifact import SourceArtifact
from nbr12721.sources.schema import validate_manifest_document
from nbr12721.sources.sha256sums import parse_sha256sums
from nbr12721.sources.verify import verify_all_sources

SCHEMA_VERSION = 1


def build_manifest_dict(artifacts: list[SourceArtifact]) -> dict[str, object]:
    """Constrói o documento de manifest ordenado deterministicamente."""
    sorted_artifacts = sorted(artifacts, key=lambda item: item.path)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "artifacts": [item.to_manifest_item() for item in sorted_artifacts],
    }
    validate_manifest_document(manifest)
    return manifest


def serialize_manifest(manifest: dict[str, object]) -> str:
    """Serializa manifest v1 com forma canônica byte-estável."""
    validate_manifest_document(manifest)
    return (
        json.dumps(
            manifest,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    )


def parse_manifest(text: str) -> dict[str, object]:
    """Interpreta JSON e valida contra source-manifest v1."""
    document = json.loads(text)
    validate_manifest_document(document)
    return document


def load_verified_manifest(
    repo_root: Path,
    *,
    path_mapping: Mapping[str, str] | None = None,
) -> tuple[list[SourceArtifact], dict[str, object]]:
    """Lê SHA256SUMS, verifica fontes e produz manifest v1.

    Com ``path_mapping``, cada ID lógico de ``SHA256SUMS`` é verificado no
    path físico correspondente; o manifest continua emitindo o ID lógico.
    """
    sums_path = repo_root / "SHA256SUMS"
    entries = parse_sha256sums(sums_path.read_text(encoding="utf-8"))
    digest_path_pairs = [(digest, path) for path, digest in entries]
    artifacts = verify_all_sources(
        repo_root,
        digest_path_pairs,
        path_mapping=path_mapping,
    )
    manifest = build_manifest_dict(artifacts)
    return artifacts, manifest


def artifacts_from_manifest(manifest: dict[str, object]) -> list[SourceArtifact]:
    """Reconstrói SourceArtifact a partir de manifest validado."""
    raw_items = manifest["artifacts"]
    assert isinstance(raw_items, list)
    artifacts = [
        SourceArtifact(
            path=str(item["path"]),
            sha256=str(item["sha256"]),
            size_bytes=int(item["size_bytes"]),
            media_type=str(item["media_type"]),
        )
        for item in raw_items
    ]
    return sorted(artifacts, key=lambda item: item.path)
