"""Snapshot candidato da árvore Git sem exigir staging ou commit.

O snapshot é: paths do commit-base que ainda existem como arquivo regular no
working tree, mais arquivos não rastreados e não ignorados. Deleções no
disco removem o path do snapshot mesmo sem ``git add``/``git rm``.
"""

from __future__ import annotations

import hashlib
import json
import stat
import subprocess
import unicodedata
from pathlib import Path

from nbr12721.sources.manifest import parse_manifest
from nbr12721.sources.sha256sums import parse_sha256sums

_CHUNK_SIZE = 65536
INVENTORY_RELATIVE = "manifests/private-fixtures-v1.json"
SOURCE_MANIFEST_RELATIVE = "manifests/source-manifest.json"
SHA256SUMS_RELATIVE = "SHA256SUMS"
PRIVATE_PREFIX = "inputs/private/"


class PublicTreeError(Exception):
    """Violação do gate da árvore pública."""


def normalize_path(path: str) -> str:
    return unicodedata.normalize("NFC", path)


def git_ls_tree_paths(repo_root: Path, treeish: str) -> set[str]:
    result = subprocess.run(
        [
            "git",
            "-c",
            "core.quotePath=false",
            "ls-tree",
            "-r",
            "--name-only",
            "-z",
            treeish,
        ],
        cwd=repo_root,
        capture_output=True,
        check=True,
    )
    return {
        item.decode("utf-8")
        for item in result.stdout.split(b"\0")
        if item
    }


def git_candidate_paths(repo_root: Path) -> set[str]:
    result = subprocess.run(
        [
            "git",
            "-c",
            "core.quotePath=false",
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "-z",
        ],
        cwd=repo_root,
        capture_output=True,
        check=True,
    )
    raw = result.stdout.split(b"\0")
    paths: set[str] = set()
    for item in raw:
        if not item:
            continue
        paths.add(item.decode("utf-8"))
    return paths


def candidate_file_map(
    repo_root: Path,
    *,
    base: str = "HEAD",
) -> dict[str, Path]:
    """Mapeia path relativo → arquivo regular no snapshot candidato."""
    root = repo_root.resolve()
    files: dict[str, Path] = {}

    for relative in sorted(git_ls_tree_paths(root, base)):
        absolute = root / relative
        if _require_regular_file(absolute, relative, allow_missing=True):
            files[relative] = absolute

    for relative in sorted(git_candidate_paths(root)):
        absolute = root / relative
        if _require_regular_file(absolute, relative, allow_missing=True):
            files[relative] = absolute

    return files


def _require_regular_file(
    path: Path,
    relative: str,
    *,
    allow_missing: bool,
) -> bool:
    """Aceita somente arquivo regular; ausência rastreada representa deleção."""
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        if allow_missing:
            return False
        raise PublicTreeError(f"arquivo candidato ausente: {relative!r}")
    except OSError as exc:
        raise PublicTreeError(
            f"não foi possível inspecionar arquivo candidato {relative!r}: {exc}"
        ) from exc
    if stat.S_ISLNK(mode):
        raise PublicTreeError(f"symlink não permitido no snapshot: {relative!r}")
    if not stat.S_ISREG(mode):
        raise PublicTreeError(f"arquivo não regular no snapshot: {relative!r}")
    return True


def stream_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(_CHUNK_SIZE)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def load_private_fixture_policy(repo_root: Path) -> tuple[set[str], set[str]]:
    """Retorna (paths históricos, digests privados) após reconciliar inventários."""
    inventory_path = repo_root / INVENTORY_RELATIVE
    source_path = repo_root / SOURCE_MANIFEST_RELATIVE
    sums_path = repo_root / SHA256SUMS_RELATIVE

    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    fixtures = inventory.get("fixtures")
    if not isinstance(fixtures, list) or not fixtures:
        raise PublicTreeError("inventário privado ausente ou vazio")

    source_manifest = parse_manifest(source_path.read_text(encoding="utf-8"))
    sums = dict(parse_sha256sums(sums_path.read_text(encoding="utf-8")))

    historical_paths: set[str] = set()
    private_digests: set[str] = set()
    source_by_path = {
        str(item["path"]): item for item in source_manifest["artifacts"]
    }

    if len(fixtures) != len(sums) or len(fixtures) != len(source_by_path):
        raise PublicTreeError(
            "contagem diverge entre inventário privado, SHA256SUMS e source-manifest"
        )

    for item in fixtures:
        logical_id = normalize_path(str(item["id"]))
        digest = str(item["sha256"])
        size_bytes = int(item["size_bytes"])
        media_type = str(item["media_type"])

        if logical_id not in sums:
            raise PublicTreeError(f"id ausente em SHA256SUMS: {logical_id!r}")
        if sums[logical_id] != digest:
            raise PublicTreeError(
                f"sha256 diverge de SHA256SUMS para {logical_id!r}"
            )
        if logical_id not in source_by_path:
            raise PublicTreeError(
                f"id ausente no source-manifest: {logical_id!r}"
            )
        source_item = source_by_path[logical_id]
        if str(source_item["sha256"]) != digest:
            raise PublicTreeError(
                f"sha256 diverge do source-manifest para {logical_id!r}"
            )
        if int(source_item["size_bytes"]) != size_bytes:
            raise PublicTreeError(
                f"size_bytes diverge do source-manifest para {logical_id!r}"
            )
        if str(source_item["media_type"]) != media_type:
            raise PublicTreeError(
                f"media_type diverge do source-manifest para {logical_id!r}"
            )

        historical_paths.add(logical_id)
        private_digests.add(digest)

    return historical_paths, private_digests


def scan_public_tree(
    files: dict[str, Path],
    *,
    historical_paths: set[str],
    private_digests: set[str],
) -> dict[str, int]:
    """Varre o snapshot e falha se path/digest privado estiver presente."""
    private_path_hits = 0
    historical_hits = 0
    digest_hits = 0

    for relative, absolute in sorted(files.items()):
        normalized_relative = normalize_path(relative)
        if normalized_relative == "inputs/private" or normalized_relative.startswith(
            PRIVATE_PREFIX
        ):
            private_path_hits += 1
            raise PublicTreeError(
                f"path sob inputs/private/ no snapshot: {relative!r}"
            )
        if normalized_relative in historical_paths:
            historical_hits += 1
            raise PublicTreeError(
                f"path histórico privado no snapshot: {relative!r}"
            )
        digest = stream_sha256(absolute)
        if digest in private_digests:
            digest_hits += 1
            raise PublicTreeError(
                f"digest de fixture privada em {relative!r}"
            )

    return {
        "file_count": len(files),
        "private_path_hits": private_path_hits,
        "historical_hits": historical_hits,
        "digest_hits": digest_hits,
    }


def write_candidate_zip(repo_root: Path, zip_path: Path, files: dict[str, Path]) -> int:
    """Escreve ZIP do snapshot candidato (sem staging)."""
    import zipfile

    count = 0
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for relative in sorted(files):
            zf.write(files[relative], arcname=relative)
            count += 1
    return count
