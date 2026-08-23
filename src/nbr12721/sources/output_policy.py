"""Policy fail-closed para destinos de output."""

from __future__ import annotations

import os
from pathlib import Path
import stat

from nbr12721.sources.errors import OutputPathPolicyError, PathSecurityError
from nbr12721.sources.paths import (
    is_under_allowed_root,
    is_under_inputs,
    resolve_under_root,
    validate_relative_posix_path,
)

DEFAULT_OUTPUT_ROOTS: tuple[str, ...] = ("outputs",)


def validate_output_destination(
    repo_root: Path,
    relative_path: str,
    *,
    allowed_roots: tuple[str, ...] = DEFAULT_OUTPUT_ROOTS,
) -> Path:
    """Valida destino relativo sob raízes allowlisted sem efeitos colaterais."""
    context = "output destination"
    try:
        validate_relative_posix_path(relative_path, context=context)
    except PathSecurityError as exc:
        raise OutputPathPolicyError(str(exc)) from exc

    if relative_path in {".", ""}:
        raise OutputPathPolicyError(
            f"{context}: destino na raiz do repositório proibido"
        )

    if is_under_inputs(relative_path):
        raise OutputPathPolicyError(
            f"{context}: destino sob inputs/ proibido"
        )

    if not any(
        is_under_allowed_root(relative_path, allowed_root)
        for allowed_root in allowed_roots
    ):
        raise OutputPathPolicyError(
            f"{context}: destino fora das raízes allowlisted: {relative_path!r}"
        )

    return _resolve_output_path(repo_root, relative_path, allowed_roots)


def _resolve_output_path(
    repo_root: Path,
    relative_path: str,
    allowed_roots: tuple[str, ...],
) -> Path:
    root = repo_root.resolve()
    current = root
    for component in relative_path.split("/"):
        if component in ("", ".", ".."):
            raise OutputPathPolicyError(
                f"output destination: componente inválido: {component!r}"
            )
        candidate = current / component
        if candidate.exists() or candidate.is_symlink():
            try:
                stat_result = os.lstat(candidate)
            except OSError as exc:
                raise OutputPathPolicyError(
                    f"output destination: path ilegível: {relative_path!r}"
                ) from exc
            if stat.S_ISLNK(stat_result.st_mode):
                link_target = os.readlink(candidate)
                if os.path.isabs(link_target):
                    resolved_link = Path(link_target)
                else:
                    resolved_link = (current / link_target).resolve()
                if not resolved_link.is_relative_to(root):
                    raise OutputPathPolicyError(
                        "output destination: symlink escapa da raiz do repositório"
                    )
                if not _is_under_any_allowed(resolved_link, root, allowed_roots):
                    raise OutputPathPolicyError(
                        "output destination: symlink escapa da raiz allowlisted"
                    )
                current = resolved_link
                continue
        current = candidate.resolve()
        if not current.is_relative_to(root):
            raise OutputPathPolicyError(
                "output destination: path escapa da raiz do repositório"
            )
        if not _is_under_any_allowed(current, root, allowed_roots):
            raise OutputPathPolicyError(
                "output destination: path escapa da raiz allowlisted"
            )

    if current == root:
        raise OutputPathPolicyError(
            "output destination: destino na raiz do repositório proibido"
        )

    # Confirma resolução final contra traversal/symlink usando a mesma API de fontes
    # apenas quando o caminho completo já existe; destinos novos permanecem lógicos.
    if current.exists():
        return resolve_under_root(
            repo_root,
            relative_path,
            context="output destination",
        )
    return current


def _is_under_any_allowed(
    resolved: Path,
    repo_root: Path,
    allowed_roots: tuple[str, ...],
) -> bool:
    relative = resolved.relative_to(repo_root).as_posix()
    return any(is_under_allowed_root(relative, allowed_root) for allowed_root in allowed_roots)
