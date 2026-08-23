"""Mapeamento versionado de extensões para media types."""

from __future__ import annotations

from nbr12721.sources.errors import MediaTypeError

SUPPORTED_MEDIA_TYPES: dict[str, str] = {
    ".pdf": "application/pdf",
    ".xlsx": (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ),
}


def media_type_for_path(relative_path: str) -> str:
    """Retorna o media type determinístico para a extensão do path."""
    lower_suffix = _suffix_lower(relative_path)
    try:
        return SUPPORTED_MEDIA_TYPES[lower_suffix]
    except KeyError as exc:
        raise MediaTypeError(
            f"extensão não suportada para media type: {lower_suffix!r}"
        ) from exc


def _suffix_lower(relative_path: str) -> str:
    """Extrai o sufixo do último componente POSIX.

    O ponto da extensão não pode estar no índice zero do filename: paths
    como `.pdf` e `.xlsx` (e `dir/.pdf`) não têm stem e são rejeitados.
    `.well-known/source.pdf` permanece válido.
    """
    filename = relative_path.rsplit("/", 1)[-1]
    dot = filename.rfind(".")
    if dot <= 0 or dot == len(filename) - 1:
        raise MediaTypeError(
            f"path sem extensão suportada: {relative_path!r}"
        )
    return filename[dot:].lower()
