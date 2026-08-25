"""Execução segura de subprocessos Poppler (sem shell, ambiente mínimo)."""

from __future__ import annotations

import os
import resource
import shutil
import stat
import subprocess
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from nbr12721.pdf.errors import PdfBackendError

DEFAULT_TIMEOUT_SECONDS = 300
DEFAULT_MAX_STDOUT_BYTES = 64 * 1024 * 1024
DEFAULT_MAX_STDERR_BYTES = 1024 * 1024
DEFAULT_MAX_ARTIFACT_BYTES = 256 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class CommandResult:
    returncode: int
    stdout: bytes
    stderr: bytes


def minimal_subprocess_env() -> dict[str, str]:
    """Ambiente mínimo documentado para saída parseável."""
    return {
        "LC_ALL": "C",
        "LANG": "C",
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
    }


def run_command(
    args: Sequence[str],
    *,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    max_stdout_bytes: int = DEFAULT_MAX_STDOUT_BYTES,
    max_stderr_bytes: int = DEFAULT_MAX_STDERR_BYTES,
    env: Mapping[str, str] | None = None,
    cwd: Path | None = None,
    raise_file_size_limit: int | None = None,
) -> CommandResult:
    """Executa comando por lista de argumentos (fail-closed, sem shell)."""
    if not args:
        raise PdfBackendError("lista de argumentos vazia")
    if any(not isinstance(arg, str) for arg in args):
        raise PdfBackendError("argumentos devem ser strings")
    if args[0] == "":
        raise PdfBackendError("executável vazio")

    merged_env = dict(minimal_subprocess_env())
    if env is not None:
        merged_env.update(env)

    previous_fsize = _raise_file_size_limit(raise_file_size_limit)
    try:
        try:
            completed = subprocess.run(
                list(args),
                capture_output=True,
                timeout=timeout_seconds,
                env=merged_env,
                cwd=str(cwd) if cwd is not None else None,
                check=False,
                shell=False,
            )
        except FileNotFoundError as exc:
            raise PdfBackendError("comando Poppler ausente") from exc
        except subprocess.TimeoutExpired as exc:
            raise PdfBackendError("timeout do subprocesso Poppler") from exc
        except PermissionError as exc:
            # Execução negada ou kill pós-timeout em ambiente restritivo.
            raise PdfBackendError(
                "subprocesso Poppler inacessível ou não terminável"
            ) from exc
    finally:
        _restore_file_size_limit(previous_fsize)

    stdout = completed.stdout or b""
    stderr = completed.stderr or b""
    if len(stdout) > max_stdout_bytes:
        raise PdfBackendError("stdout acima do limite configurado")
    if len(stderr) > max_stderr_bytes:
        raise PdfBackendError("stderr acima do limite configurado")

    return CommandResult(
        returncode=completed.returncode,
        stdout=stdout,
        stderr=stderr,
    )


class RestrictedTempDirectory:
    """Diretório temporário de permissão restritiva com limpeza garantida."""

    def __init__(self, *, prefix: str = "nbr12721-pdf-") -> None:
        self._prefix = prefix
        self._path: Path | None = None

    @property
    def path(self) -> Path:
        if self._path is None:
            raise PdfBackendError("diretório temporário não inicializado")
        return self._path

    def __enter__(self) -> RestrictedTempDirectory:
        base = Path(tempfile.mkdtemp(prefix=self._prefix))
        os.chmod(base, stat.S_IRWXU)
        self._path = base
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.cleanup()

    def cleanup(self) -> None:
        if self._path is not None and self._path.exists():
            shutil.rmtree(self._path, ignore_errors=True)
        self._path = None

    def assert_artifact_size(self, path: Path, *, limit: int) -> None:
        try:
            size = path.stat().st_size
        except OSError as exc:
            raise PdfBackendError("artefato temporário ilegível") from exc
        if size > limit:
            raise PdfBackendError("artefato temporário acima do limite")


def require_success(result: CommandResult, *, tool: str) -> bytes:
    if result.returncode != 0:
        raise PdfBackendError(f"{tool} retornou código não zero")
    return result.stdout


def _raise_file_size_limit(limit: int | None) -> tuple[int, int] | None:
    if limit is None:
        return None
    try:
        previous = resource.getrlimit(resource.RLIMIT_FSIZE)
        resource.setrlimit(resource.RLIMIT_FSIZE, (limit, limit))
        return previous
    except (ValueError, OSError):
        return None


def _restore_file_size_limit(previous: tuple[int, int] | None) -> None:
    if previous is None:
        return
    try:
        resource.setrlimit(resource.RLIMIT_FSIZE, previous)
    except (ValueError, OSError):
        pass
