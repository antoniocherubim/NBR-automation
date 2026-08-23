#!/usr/bin/env python3
"""Valida artifact.zip contra tree Git sanitizado ou snapshot candidato."""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
import unicodedata
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts" / "ci"))

from candidate_snapshot import (  # noqa: E402
    PRIVATE_PREFIX,
    PublicTreeError,
    candidate_file_map,
    load_private_fixture_policy,
)


class ArtifactZipValidationError(Exception):
    """Erro de validação estrutural do pacote."""


def _normalize_path(path: str) -> str:
    return unicodedata.normalize("NFC", path)


def git_tracked_paths(repo_root: Path, commit: str) -> set[str]:
    result = subprocess.run(
        [
            "git",
            "-c",
            "core.quotePath=false",
            "ls-tree",
            "-r",
            "--name-only",
            "-z",
            commit,
        ],
        cwd=repo_root,
        capture_output=True,
        check=True,
    )
    paths = {
        _normalize_path(item.decode("utf-8"))
        for item in result.stdout.split(b"\0")
        if item
    }
    if not paths:
        raise ArtifactZipValidationError(
            f"nenhum path rastreado encontrado em {commit!r}"
        )
    return paths


def _is_unsafe_path(name: str) -> bool:
    if not name or name.startswith(("/", "\\")):
        return True
    normalized = PurePosixPath(name)
    if normalized.is_absolute():
        return True
    return any(part in {".", ".."} for part in normalized.parts)


def _is_prohibited_entry(name: str) -> bool:
    bare = name.rstrip("/")
    return bare == "artifact.zip" or bare == ".git" or name.startswith(".git/")


def _is_expected_directory(name: str, expected: set[str]) -> bool:
    prefix = name if name.endswith("/") else f"{name}/"
    return any(path.startswith(prefix) for path in expected)


def _is_private_path(name: str, historical_paths: set[str]) -> str | None:
    bare = name.rstrip("/")
    if bare == "inputs/private" or name.startswith(PRIVATE_PREFIX):
        return f"entrada sob inputs/private/: {name!r}"
    if bare in historical_paths or name.rstrip("/") in historical_paths:
        return f"path histórico privado no ZIP: {name!r}"
    return None


def validate_artifact_zip(
    zip_path: str,
    *,
    expected_paths: set[str],
    historical_paths: set[str],
    private_digests: set[str],
    label: str,
) -> dict[str, int | str]:
    seen: set[str] = set()
    zip_files: set[str] = set()

    overlap = expected_paths & historical_paths
    if overlap:
        sample = ", ".join(sorted(overlap)[:3])
        raise ArtifactZipValidationError(
            f"tree de referência ainda contém path(s) histórico(s) privado(s) "
            f"(ex.: {sample})"
        )

    try:
        archive = zipfile.ZipFile(zip_path, "r")
    except zipfile.BadZipFile as exc:
        raise ArtifactZipValidationError(f"ZIP inválido: {exc}") from exc

    with archive as zf:
        for info in zf.infolist():
            raw_name = info.filename
            name = _normalize_path(raw_name)
            if _is_unsafe_path(name):
                raise ArtifactZipValidationError(f"path inseguro no ZIP: {name!r}")
            if name in seen:
                raise ArtifactZipValidationError(f"path duplicado no ZIP: {name!r}")
            if _is_prohibited_entry(name):
                raise ArtifactZipValidationError(f"entrada proibida no ZIP: {name!r}")
            private_reason = _is_private_path(name, historical_paths)
            if private_reason is not None:
                raise ArtifactZipValidationError(private_reason)
            seen.add(name)
            try:
                payload = zf.read(raw_name)
            except zipfile.BadZipFile as exc:
                raise ArtifactZipValidationError(
                    f"CRC inválido para {name!r}: {exc}"
                ) from exc

            if info.is_dir():
                if not _is_expected_directory(name, expected_paths):
                    raise ArtifactZipValidationError(
                        f"entrada de diretório inesperada no ZIP: {name!r}"
                    )
                continue

            digest = hashlib.sha256(payload).hexdigest()
            if digest in private_digests:
                raise ArtifactZipValidationError(
                    f"digest de fixture privada no ZIP: {name!r}"
                )
            zip_files.add(name)

    missing = expected_paths - zip_files
    extra = zip_files - expected_paths
    if missing:
        sample = ", ".join(sorted(missing)[:5])
        raise ArtifactZipValidationError(
            f"{len(missing)} arquivo(s) esperado(s) ausente(s) no ZIP (ex.: {sample})"
        )
    if extra:
        sample = ", ".join(sorted(extra)[:5])
        raise ArtifactZipValidationError(
            f"{len(extra)} entrada(s) inesperada(s) no ZIP (ex.: {sample})"
        )

    return {
        "entry_count": len(zip_files),
        "expected_count": len(expected_paths),
        "label": label,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zip_path", help="caminho para artifact.zip")
    parser.add_argument(
        "tree_ref",
        help="commit Git (ex.: HEAD/SHA) ou a palavra CANDIDATE",
    )
    parser.add_argument(
        "--repo-root",
        default=str(ROOT),
        help="raiz do repositório",
    )
    args = parser.parse_args(argv)
    repo_root = Path(args.repo_root).resolve()

    try:
        historical_paths, private_digests = load_private_fixture_policy(repo_root)
        if args.tree_ref == "CANDIDATE":
            files = candidate_file_map(repo_root, base="HEAD")
            expected = set(files.keys())
            label = "CANDIDATE"
        else:
            expected = git_tracked_paths(repo_root, args.tree_ref)
            label = args.tree_ref
            # Commit ainda não sanitizado: o próprio expected pode conter
            # paths históricos; o scan das entradas do ZIP rejeita.
        summary = validate_artifact_zip(
            args.zip_path,
            expected_paths=expected,
            historical_paths=historical_paths,
            private_digests=private_digests,
            label=label,
        )
    except (
        ArtifactZipValidationError,
        PublicTreeError,
        subprocess.CalledProcessError,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(
        "artifact.zip OK:",
        f"{summary['entry_count']} entradas",
        f"({summary['label']})",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
