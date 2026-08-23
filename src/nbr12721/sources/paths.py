"""Validação e resolução segura de paths relativos POSIX."""

from __future__ import annotations

import os
from pathlib import Path

from nbr12721.sources.errors import PathSecurityError

_INPUTS_PREFIX = "inputs/"


def validate_relative_posix_path(relative_path: str, *, context: str) -> str:
    """Valida path relativo UTF-8 sem normalização silenciosa."""
    if relative_path == "":
        raise PathSecurityError(f"{context}: path vazio")
    if "\x00" in relative_path:
        raise PathSecurityError(f"{context}: path contém NUL")
    if "\\" in relative_path:
        raise PathSecurityError(f"{context}: backslash proibido como separador")
    if relative_path.startswith("/"):
        raise PathSecurityError(f"{context}: path absoluto proibido")
    if relative_path.startswith("./") or relative_path == ".":
        raise PathSecurityError(f"{context}: componente '.' proibido")
    if "/./" in relative_path or relative_path.endswith("/."):
        raise PathSecurityError(f"{context}: componente '.' proibido")
    if relative_path.startswith("../") or relative_path == "..":
        raise PathSecurityError(f"{context}: componente '..' proibido")
    if "/../" in relative_path or relative_path.endswith("/.."):
        raise PathSecurityError(f"{context}: componente '..' proibido")
    if relative_path.startswith("//") or "//" in relative_path:
        raise PathSecurityError(f"{context}: componente vazio proibido")
    if relative_path.endswith("/"):
        raise PathSecurityError(f"{context}: path não pode terminar com '/'")
    return relative_path


def resolve_under_root(
    repo_root: Path,
    relative_path: str,
    *,
    context: str,
    reject_final_symlink: bool = False,
) -> Path:
    """Resolve path sob a raiz real, rejeitando escape por symlink."""
    validate_relative_posix_path(relative_path, context=context)
    root = repo_root.resolve()
    current = root
    components = relative_path.split("/")
    for index, component in enumerate(components):
        if component in ("", ".", ".."):
            raise PathSecurityError(
                f"{context}: componente de path inválido: {component!r}"
            )
        candidate = current / component
        is_final = index == len(components) - 1
        try:
            stat_result = os.lstat(candidate)
        except FileNotFoundError as exc:
            raise PathSecurityError(
                f"{context}: componente ausente no filesystem: {relative_path!r}"
            ) from exc
        if stat_result.st_mode & 0o170000 == 0o120000:
            if is_final and reject_final_symlink:
                raise PathSecurityError(
                    f"{context}: symlink proibido no alvo: {relative_path!r}"
                )
            link_target = os.readlink(candidate)
            if os.path.isabs(link_target):
                resolved_link = Path(link_target)
            else:
                resolved_link = (current / link_target).resolve()
            if not resolved_link.is_relative_to(root):
                raise PathSecurityError(
                    f"{context}: symlink escapa da raiz: {relative_path!r}"
                )
            current = resolved_link
            continue
        current = candidate.resolve()
        if not current.is_relative_to(root):
            raise PathSecurityError(
                f"{context}: path escapa da raiz do repositório: {relative_path!r}"
            )
    return current


def is_under_inputs(relative_path: str) -> bool:
    return relative_path == "inputs" or relative_path.startswith(_INPUTS_PREFIX)


def is_under_allowed_root(relative_path: str, allowed_root: str) -> bool:
    validate_relative_posix_path(relative_path, context="output path")
    prefix = f"{allowed_root}/"
    return relative_path == allowed_root or relative_path.startswith(prefix)
