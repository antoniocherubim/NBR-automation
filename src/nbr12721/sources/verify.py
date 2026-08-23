"""Verificação fail-closed de fontes sob a raiz do repositório."""

from __future__ import annotations

import hashlib
import hmac
import os
from collections.abc import Mapping
from pathlib import Path
import stat

from nbr12721.sources.artifact import SourceArtifact
from nbr12721.sources.errors import SourceVerificationError
from nbr12721.sources.mapping import validate_path_mapping
from nbr12721.sources.media_types import media_type_for_path
from nbr12721.sources.paths import PathSecurityError, resolve_under_root

_CHUNK_SIZE = 65536


def verify_source(
    repo_root: Path,
    relative_path: str,
    expected_digest: str,
    *,
    physical_relative_path: str | None = None,
) -> SourceArtifact:
    """Verifica bytes, tamanho e tipo de mídia de uma fonte.

    ``relative_path`` é o ID lógico preservado no ``SourceArtifact``. Quando
    ``physical_relative_path`` é informado, os bytes são abertos nesse path
    físico; o ID lógico não muda.
    """
    open_relative = physical_relative_path or relative_path
    try:
        resolved = resolve_under_root(
            repo_root,
            open_relative,
            context="verificação de fonte",
            reject_final_symlink=True,
        )
    except PathSecurityError as exc:
        raise SourceVerificationError(str(exc)) from exc
    try:
        stat_result = os.lstat(resolved)
    except OSError as exc:
        raise SourceVerificationError(
            f"fonte ilegível: {open_relative!r}"
        ) from exc

    if stat.S_ISLNK(stat_result.st_mode):
        raise SourceVerificationError(
            f"symlink proibido no alvo: {open_relative!r}"
        )
    if not stat.S_ISREG(stat_result.st_mode):
        raise SourceVerificationError(
            f"alvo não é arquivo regular: {open_relative!r}"
        )

    digest, size_bytes = _stream_digest(resolved)
    if not hmac.compare_digest(digest, expected_digest):
        raise SourceVerificationError(
            f"digest divergente para {relative_path!r}"
        )

    return SourceArtifact(
        path=relative_path,
        sha256=digest,
        size_bytes=size_bytes,
        media_type=media_type_for_path(relative_path),
    )


def verify_all_sources(
    repo_root: Path,
    entries: list[tuple[str, str]],
    *,
    path_mapping: Mapping[str, str] | None = None,
) -> list[SourceArtifact]:
    """Verifica todas as entradas; falha antes de publicar manifest parcial.

    ``entries`` é uma lista de ``(expected_digest, logical_id)``. Com
    ``path_mapping``, a verificação abre o path físico mapeado e preserva o
    ID lógico nos artefatos retornados.
    """
    mapping: dict[str, str] | None = None
    if path_mapping is not None:
        logical_ids = [relative_path for _digest, relative_path in entries]
        mapping = validate_path_mapping(logical_ids, path_mapping)

    artifacts: list[SourceArtifact] = []
    for expected_digest, relative_path in entries:
        physical = None if mapping is None else mapping[relative_path]
        artifacts.append(
            verify_source(
                repo_root,
                relative_path,
                expected_digest,
                physical_relative_path=physical,
            )
        )
    return artifacts


def _stream_digest(path: Path) -> tuple[str, int]:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise SourceVerificationError(
            f"falha ao abrir fonte read-only: {path}"
        ) from exc

    hasher = hashlib.sha256()
    size_bytes = 0
    try:
        file_stat = os.fstat(fd)
        if not stat.S_ISREG(file_stat.st_mode):
            raise SourceVerificationError(
                f"descriptor aberto não é arquivo regular: {path}"
            )
        while True:
            chunk = os.read(fd, _CHUNK_SIZE)
            if not chunk:
                break
            hasher.update(chunk)
            size_bytes += len(chunk)
    finally:
        os.close(fd)

    return hasher.hexdigest(), size_bytes
