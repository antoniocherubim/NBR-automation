"""Parser estrito do marcador private_fixtures no front matter da task."""

from __future__ import annotations

import re
from pathlib import Path

from adapter.errors import TaskMarkerError

ALLOWED_VALUES = frozenset({"none", "required"})
# Captura declaração na coluna zero (aceita) e indentada (rejeita fail-closed).
_MARKER_LINE = re.compile(r"^(\s*)private_fixtures\s*:\s*(.*?)\s*$")


def parse_task_marker(task_text: str) -> str:
    """Extrai private_fixtures do front matter YAML mínimo.

    Regras fail-closed:
    - somente o primeiro bloco delimitado por --- no início do arquivo;
    - exatamente uma ocorrência de private_fixtures: none|required no front matter;
    - chave somente na coluna zero do front matter (indentação falha);
    - declaração YAML de marcador fora do front matter (fora de fences) falha;
    - marcador duplicado, vazio, malformado ou valor desconhecido falha;
    - ausência da chave (não declaração vazia) equivale a none (histórico).
    """
    if task_text.startswith("\ufeff"):
        task_text = task_text[1:]
    if not task_text.startswith("---"):
        _reject_misplaced_marker(task_text)
        return "none"

    rest = task_text[3:]
    if rest.startswith("\r\n"):
        rest = rest[2:]
    elif rest.startswith("\n"):
        rest = rest[1:]
    else:
        raise TaskMarkerError("front matter deve iniciar com --- seguido de newline")

    end = rest.find("\n---")
    if end < 0:
        raise TaskMarkerError("front matter sem delimitador de fechamento ---")

    after = rest[end + 1 :]
    closing_line, _, remainder = after.partition("\n")
    closing_line = closing_line.rstrip("\r")
    if closing_line != "---":
        raise TaskMarkerError("delimitador de fechamento do front matter inválido")

    front_matter = rest[:end]
    body = remainder

    values: list[str] = []
    for raw_line in front_matter.splitlines():
        line = raw_line.rstrip("\r")
        match = _MARKER_LINE.match(line)
        if match is None:
            continue
        if match.group(1) != "":
            raise TaskMarkerError(
                "private_fixtures mal posicionado no front matter"
            )
        normalized = _normalize_scalar(match.group(2))
        if normalized not in ALLOWED_VALUES:
            raise TaskMarkerError(
                f"valor desconhecido para private_fixtures: {normalized!r}"
            )
        values.append(normalized)

    _reject_misplaced_marker(body)

    if len(values) == 0:
        return "none"
    if len(values) > 1:
        raise TaskMarkerError("private_fixtures duplicado no front matter")
    return values[0]


def read_task_marker(task_path: Path) -> str:
    """Lê o arquivo da task e retorna none|required."""
    try:
        text = task_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise TaskMarkerError(f"task ilegível: {task_path}") from exc
    return parse_task_marker(text)


def _normalize_scalar(raw: str) -> str:
    normalized = raw.strip()
    if normalized == "" or normalized.startswith(("{", "[", "|", ">")):
        raise TaskMarkerError(
            f"valor inválido para private_fixtures: {normalized!r}"
        )
    if (
        len(normalized) >= 2
        and normalized[0] == normalized[-1]
        and normalized[0] in "'\""
    ):
        normalized = normalized[1:-1]
    return normalized


def _reject_misplaced_marker(text: str) -> None:
    """Rejeita declarações YAML de marcador fora do front matter e fora de fences."""
    in_fence = False
    for raw_line in text.splitlines():
        line = raw_line.rstrip("\r")
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if _MARKER_LINE.match(line) is not None:
            raise TaskMarkerError(
                "private_fixtures fora do front matter é proibido"
            )
