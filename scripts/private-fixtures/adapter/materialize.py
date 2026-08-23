"""Materialização segura e idempotente de fixtures privadas."""

from __future__ import annotations

import hashlib
import hmac
import os
import stat
import tempfile
from pathlib import Path

from adapter.errors import MaterializeError
from adapter.inventory import PrivateFixture

_CHUNK_SIZE = 65536
_PRIVATE_DIR = Path("inputs") / "private"


def materialize_fixtures(
    *,
    repo_root: Path,
    private_root: Path,
    fixtures: list[PrivateFixture],
) -> dict[str, int]:
    """Copia fixtures do store externo para inputs/private/ de forma atômica.

    Retorna contagens: copied, verified. Nunca usa hardlink/symlink.
    A origem é aberta somente para leitura. Staging é relido e verificado
    antes da promoção; falha intermediária restaura o destino anterior ou,
    na primeira materialização, remove o destino incompleto promovido.
    """
    if not fixtures:
        raise MaterializeError("lista de fixtures vazia")

    repo_root = repo_root.resolve()
    private_root = private_root.resolve()
    destination_root = repo_root / _PRIVATE_DIR

    staging_parent = repo_root / "inputs"
    staging_parent.mkdir(parents=True, exist_ok=True)

    staging = Path(
        tempfile.mkdtemp(
            prefix=".private-staging-",
            dir=str(staging_parent),
        )
    )
    backup: Path | None = None
    try:
        _ensure_not_writable_world(staging)
        for fixture in fixtures:
            _materialize_one(
                private_root=private_root,
                staging_root=staging,
                fixture=fixture,
            )
        # Verificação pré-promoção: relê bytes do staging (não confia só no hash
        # acumulado durante a escrita).
        _verify_fixture_tree(staging, fixtures, label="staging")
        backup = _promote_staging(
            staging=staging,
            destination_root=destination_root,
        )
        staging = None  # promovido; não remover como staging
        _verify_fixture_tree(destination_root, fixtures, label="destino")
        _chmod_tree_readonly(destination_root)
        if backup is not None:
            _rmtree_force(backup)
            backup = None
    except Exception:
        if backup is not None and backup.exists():
            try:
                if destination_root.exists() or destination_root.is_symlink():
                    _rmtree_force(destination_root)
                os.replace(backup, destination_root)
                backup = None
            except OSError as exc:
                raise MaterializeError(
                    "falha ao restaurar destino após promoção incompleta"
                ) from exc
        elif staging is None:
            # Primeira materialização: promoção sem backup e verificação do
            # destino falhou — não deixar destino incompleto exposto.
            if destination_root.exists() or destination_root.is_symlink():
                _rmtree_force(destination_root)
        if staging is not None and staging.exists():
            _rmtree_force(staging)
        if backup is not None and backup.exists():
            _rmtree_force(backup)
        _cleanup_ephemeral_inputs(staging_parent)
        raise

    _cleanup_ephemeral_inputs(staging_parent)

    for fixture in fixtures:
        dest = repo_root / fixture.materialize_path
        _assert_readonly_file(dest)

    return {"copied": len(fixtures), "verified": len(fixtures)}


def verify_materialized(
    *,
    repo_root: Path,
    fixtures: list[PrivateFixture],
) -> dict[str, int]:
    """Verifica cópias já materializadas sob inputs/private/."""
    repo_root = repo_root.resolve()
    private_dir = repo_root / _PRIVATE_DIR
    if not private_dir.is_dir():
        raise MaterializeError("inputs/private/ ausente")

    _verify_fixture_tree(private_dir, fixtures, label="destino")
    return {"verified": len(fixtures)}


def _verify_fixture_tree(
    tree_root: Path,
    fixtures: list[PrivateFixture],
    *,
    label: str,
) -> None:
    """Relê cada fixture sob tree_root (store_path relativo) e confere digest."""
    for fixture in fixtures:
        dest = tree_root / fixture.store_path
        try:
            st = dest.lstat()
        except FileNotFoundError as exc:
            raise MaterializeError(
                f"fixture ausente no {label}: {fixture.store_path!r}"
            ) from exc
        if stat.S_ISLNK(st.st_mode):
            raise MaterializeError(
                f"symlink proibido no {label}: {fixture.store_path!r}"
            )
        if not stat.S_ISREG(st.st_mode):
            raise MaterializeError(
                f"{label} não é arquivo regular: {fixture.store_path!r}"
            )
        digest, size = _stream_digest(dest)
        if size != fixture.size_bytes:
            raise MaterializeError(
                f"tamanho divergente no {label}: {fixture.store_path!r}"
            )
        if not hmac.compare_digest(digest, fixture.sha256):
            raise MaterializeError(
                f"digest divergente no {label}: {fixture.store_path!r}"
            )


def _materialize_one(
    *,
    private_root: Path,
    staging_root: Path,
    fixture: PrivateFixture,
) -> None:
    source = _resolve_store_source(private_root, fixture.store_path)
    dest = staging_root / fixture.store_path
    dest.parent.mkdir(parents=True, exist_ok=True)

    # Cópia via open read-only + write em arquivo novo (sem link).
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        src_fd = os.open(source, flags)
    except OSError as exc:
        raise MaterializeError(
            f"falha ao abrir fonte read-only: {fixture.store_path!r}"
        ) from exc

    hasher = hashlib.sha256()
    size = 0
    try:
        src_stat = os.fstat(src_fd)
        if not stat.S_ISREG(src_stat.st_mode):
            raise MaterializeError(
                f"fonte não é arquivo regular: {fixture.store_path!r}"
            )
        if src_stat.st_size != fixture.size_bytes:
            raise MaterializeError(
                f"tamanho divergente na fonte: {fixture.store_path!r}"
            )

        dest_fd = os.open(
            dest,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o644,
        )
        try:
            while True:
                chunk = os.read(src_fd, _CHUNK_SIZE)
                if not chunk:
                    break
                _write_all(dest_fd, chunk)
                hasher.update(chunk)
                size += len(chunk)
        finally:
            os.close(dest_fd)
    finally:
        os.close(src_fd)

    if size != fixture.size_bytes:
        raise MaterializeError(
            f"tamanho divergente na cópia: {fixture.store_path!r}"
        )
    digest = hasher.hexdigest()
    if not hmac.compare_digest(digest, fixture.sha256):
        raise MaterializeError(
            f"digest divergente na cópia: {fixture.store_path!r}"
        )

    os.chmod(dest, 0o444)


def _write_all(fd: int, data: bytes) -> None:
    """Escreve todos os bytes; rejeita escrita curta residual/zero."""
    offset = 0
    length = len(data)
    while offset < length:
        written = os.write(fd, data[offset:])
        if written <= 0:
            raise MaterializeError("escrita curta na cópia staging")
        offset += written


def _resolve_store_source(private_root: Path, store_path: str) -> Path:
    current = private_root
    for index, component in enumerate(store_path.split("/")):
        if component in ("", ".", ".."):
            raise MaterializeError(
                f"componente de path inválido: {component!r}"
            )
        candidate = current / component
        is_final = index == len(store_path.split("/")) - 1
        try:
            st = candidate.lstat()
        except FileNotFoundError as exc:
            raise MaterializeError(
                f"entrada ausente no store: {store_path!r}"
            ) from exc
        except OSError as exc:
            # PermissionError e afins: nunca incluir path absoluto do store.
            raise MaterializeError(
                f"entrada inacessível no store: {store_path!r}"
            ) from exc
        if stat.S_ISLNK(st.st_mode):
            raise MaterializeError(
                f"symlink proibido no store: {store_path!r}"
            )
        if is_final:
            if not stat.S_ISREG(st.st_mode):
                raise MaterializeError(
                    f"fonte não é arquivo regular: {store_path!r}"
                )
            return candidate
        if not stat.S_ISDIR(st.st_mode):
            raise MaterializeError(
                f"componente intermediário não é diretório: {store_path!r}"
            )
        current = candidate
    raise MaterializeError(f"path de store inválido: {store_path!r}")


def _promote_staging(*, staging: Path, destination_root: Path) -> Path | None:
    """Promove staging; retorna backup a preservar até verificação do destino."""
    destination_root.parent.mkdir(parents=True, exist_ok=True)
    backup: Path | None = None
    try:
        if destination_root.exists() or destination_root.is_symlink():
            backup = destination_root.with_name(
                f".private-backup-{os.getpid()}-{destination_root.name}"
            )
            os.replace(destination_root, backup)
        os.replace(staging, destination_root)
    except Exception:
        if backup is not None and backup.exists():
            try:
                if destination_root.exists() or destination_root.is_symlink():
                    _rmtree_force(destination_root)
                os.replace(backup, destination_root)
            except OSError as exc:
                raise MaterializeError(
                    "falha ao restaurar destino após promoção incompleta"
                ) from exc
        raise
    return backup


def _chmod_tree_readonly(root: Path) -> None:
    for dirpath, dirnames, filenames in os.walk(root):
        try:
            os.chmod(dirpath, 0o555)
        except OSError:
            pass
        for name in filenames:
            path = Path(dirpath) / name
            try:
                os.chmod(path, 0o444)
            except OSError:
                pass
        _ = dirnames


def _rmtree_force(root: Path) -> None:
    """Remove árvore mesmo com arquivos/dirs read-only; falha não é silenciada."""
    if root.is_symlink():
        root.unlink()
        return
    if root.is_file():
        try:
            os.chmod(root, 0o600)
        except OSError:
            pass
        root.unlink()
        return
    if not root.exists():
        return
    # Diretórios 0555 impedem unlink dos filhos: liberar escrita top-down.
    for dirpath, _dirnames, filenames in os.walk(root, topdown=True):
        try:
            os.chmod(dirpath, 0o700)
        except OSError:
            pass
        for name in filenames:
            path = Path(dirpath) / name
            try:
                if not path.is_symlink():
                    os.chmod(path, 0o600)
            except OSError:
                pass
    for dirpath, dirnames, filenames in os.walk(root, topdown=False):
        for name in filenames:
            (Path(dirpath) / name).unlink()
        for name in dirnames:
            path = Path(dirpath) / name
            if path.is_symlink():
                path.unlink()
            else:
                path.rmdir()
    try:
        os.chmod(root, 0o700)
    except OSError:
        pass
    root.rmdir()


def _cleanup_ephemeral_inputs(inputs_dir: Path) -> None:
    """Remove leftovers .private-staging-* / .private-backup-* sob inputs/."""
    if not inputs_dir.is_dir():
        return
    for child in inputs_dir.iterdir():
        name = child.name
        if name.startswith(".private-staging-") or name.startswith(
            ".private-backup-"
        ):
            _rmtree_force(child)


def _stream_digest(path: Path) -> tuple[str, int]:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise MaterializeError(f"falha ao abrir cópia read-only: {path}") from exc
    hasher = hashlib.sha256()
    size = 0
    try:
        while True:
            chunk = os.read(fd, _CHUNK_SIZE)
            if not chunk:
                break
            hasher.update(chunk)
            size += len(chunk)
    finally:
        os.close(fd)
    return hasher.hexdigest(), size


def _assert_readonly_file(path: Path) -> None:
    mode = path.stat().st_mode
    if mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH):
        raise MaterializeError(f"arquivo materializado ainda gravável: {path}")


def _ensure_not_writable_world(path: Path) -> None:
    mode = path.stat().st_mode
    os.chmod(path, mode & ~stat.S_IWOTH)
