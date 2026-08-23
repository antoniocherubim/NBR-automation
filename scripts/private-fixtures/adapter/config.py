"""Configuração local XDG do root de fixtures privadas."""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

from adapter.errors import ConfigError

CONFIG_RELATIVE = Path("nbr12721") / "private-inputs-root"


def config_file_path(*, xdg_config_home: str | None = None, home: str | None = None) -> Path:
    """Retorna o path lógico do arquivo de configuração XDG."""
    if xdg_config_home is None:
        xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config_home:
        base = Path(xdg_config_home)
    else:
        if home is None:
            home = os.environ.get("HOME")
        if not home:
            raise ConfigError("HOME ausente e XDG_CONFIG_HOME não definido")
        base = Path(home) / ".config"
    return base / CONFIG_RELATIVE


def read_private_root(
    *,
    xdg_config_home: str | None = None,
    home: str | None = None,
    repo_root: Path | None = None,
) -> Path:
    """Lê e valida o root privado configurado (sem override do candidate)."""
    path = config_file_path(xdg_config_home=xdg_config_home, home=home)
    if not path.is_file():
        raise ConfigError("configuração de fixtures privadas ausente")
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError("configuração de fixtures privadas ilegível") from exc
    if raw.endswith("\n"):
        raw = raw[:-1]
    if raw == "" or "\n" in raw or "\r" in raw or "\x00" in raw:
        raise ConfigError("configuração de fixtures privadas inválida")
    root = Path(raw)
    if not root.is_absolute():
        raise ConfigError("root privado deve ser path absoluto")
    return validate_private_root(root, repo_root=repo_root)


def validate_private_root(root: Path, *, repo_root: Path | None = None) -> Path:
    """Valida diretório real, sem symlink no root, fora de qualquer checkout."""
    if not root.is_absolute():
        raise ConfigError("root privado deve ser path absoluto")
    text = _strip_trailing_slashes(str(root))
    if _is_filesystem_root_path(text):
        raise ConfigError("root privado não pode ser /")
    if "\n" in text or "\r" in text or "\x00" in text:
        raise ConfigError("root privado contém caracteres proibidos")

    candidate = Path(text)
    try:
        st = candidate.lstat()
    except FileNotFoundError as exc:
        raise ConfigError("root privado inexistente") from exc
    except OSError as exc:
        raise ConfigError("root privado inacessível") from exc

    if stat.S_ISLNK(st.st_mode):
        raise ConfigError("root privado não pode ser symlink")
    if not stat.S_ISDIR(st.st_mode):
        raise ConfigError("root privado deve ser diretório")

    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        # Não incluir str(root)/exc com path absoluto nos logs.
        raise ConfigError("root privado inacessível") from exc
    if resolved == Path("/"):
        raise ConfigError("root privado não pode ser /")

    if _is_inside_git_worktree(resolved):
        raise ConfigError("root privado não pode ser um checkout/worktree Git")

    if repo_root is not None:
        repo_resolved = repo_root.resolve()
        if resolved == repo_resolved or resolved.is_relative_to(repo_resolved):
            raise ConfigError("root privado não pode ficar dentro do repositório")

    return resolved


def _strip_trailing_slashes(text: str) -> str:
    """Remove barras finais (exceto o root `/` / `//` …)."""
    if _is_filesystem_root_path(text):
        return "/"
    return text.rstrip("/")


def _is_filesystem_root_path(text: str) -> bool:
    """True para /, //, ///, etc. (somente barras)."""
    return bool(text) and set(text) == {"/"}


def _is_inside_git_worktree(path: Path) -> bool:
    """Detecta se o path está dentro de algum checkout/worktree Git."""
    try:
        result = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return False
    return result.returncode == 0 and result.stdout.strip() == "true"
