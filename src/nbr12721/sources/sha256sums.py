"""Parser estrito do formato SHA256SUMS versionado no repositório."""

from __future__ import annotations

import re

from nbr12721.sources.errors import Sha256SumsParseError
from nbr12721.sources.paths import PathSecurityError, validate_relative_posix_path

_HASH_LENGTH = 64
_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def parse_sha256sums(text: str) -> list[tuple[str, str]]:
    """Interpreta SHA256SUMS e retorna entradas ordenadas por path POSIX."""
    entries: dict[str, str] = {}
    if text == "":
        raise Sha256SumsParseError("SHA256SUMS vazio")

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        if raw_line == "":
            raise Sha256SumsParseError(
                f"linha {line_number}: linha vazia não permitida"
            )
        digest, path = _parse_line(raw_line, line_number)
        try:
            validate_relative_posix_path(
                path,
                context=f"SHA256SUMS linha {line_number}",
            )
        except PathSecurityError as exc:
            raise Sha256SumsParseError(str(exc)) from exc
        if path in entries:
            raise Sha256SumsParseError(
                f"linha {line_number}: path duplicado: {path!r}"
            )
        entries[path] = digest

    return sorted(entries.items(), key=lambda item: item[0])


def _parse_line(line: str, line_number: int) -> tuple[str, str]:
    if len(line) < _HASH_LENGTH + 2 + 1:
        raise Sha256SumsParseError(
            f"linha {line_number}: linha malformada (comprimento insuficiente)"
        )
    digest = line[:_HASH_LENGTH]
    delimiter = line[_HASH_LENGTH : _HASH_LENGTH + 2]
    if delimiter != "  ":
        raise Sha256SumsParseError(
            f"linha {line_number}: delimitador inválido (esperados dois espaços)"
        )
    path = line[_HASH_LENGTH + 2 :]
    if path == "" or path[0] == " ":
        raise Sha256SumsParseError(
            f"linha {line_number}: path vazio ou delimitador incorreto"
        )
    if not _HASH_PATTERN.fullmatch(digest):
        raise Sha256SumsParseError(
            f"linha {line_number}: hash inválido (64 hex lowercase exigidos)"
        )
    return digest, path
