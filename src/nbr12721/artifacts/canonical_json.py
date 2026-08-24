"""Serialização e parsing JSON canônico compartilhados (stdlib)."""

from __future__ import annotations

import json
from typing import Any

from nbr12721.artifacts.errors import ArtifactCanonicalJsonError

_JSON_PRIMITIVES = (str, int, bool, type(None))


def dumps_canonical(document: object) -> str:
    """Serializa documento em JSON canônico UTF-8 com newline final.

    - ``ensure_ascii=false``;
    - chaves de objetos ordenadas recursivamente;
    - separadores compactos ``(',', ':')``;
    - arrays preservam ordem (coleções canônicas do envelope já devem
      chegar ordenadas);
    - exatamente uma newline ``\\n`` final;
    - rejeita ``float``, ``NaN``/infinitos, ``set``, ``bytes`` e tipos
      Python não representáveis em JSON (sem ``str()``).
    """
    sanitized = _sanitize_for_canonical(document, path="$")
    try:
        body = json.dumps(
            sanitized,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ArtifactCanonicalJsonError(
            f"falha na serialização canônica: {exc}"
        ) from exc
    try:
        body.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ArtifactCanonicalJsonError(
            f"string não codificável como UTF-8: {exc.reason}"
        ) from exc
    return body + "\n"


def loads_canonical(text: str | bytes) -> object:
    """Parseia JSON rejeitando BOM, chaves duplicadas e floats."""
    if isinstance(text, bytes):
        if text.startswith(b"\xef\xbb\xbf"):
            raise ArtifactCanonicalJsonError("BOM UTF-8 proibido")
        try:
            text = text.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ArtifactCanonicalJsonError(
                f"UTF-8 inválido: {exc.reason}"
            ) from exc
    elif type(text) is not str:
        raise ArtifactCanonicalJsonError(
            f"entrada deve ser str ou bytes, recebido {type(text).__name__}"
        )
    else:
        if text.startswith("\ufeff"):
            raise ArtifactCanonicalJsonError("BOM UTF-8 proibido")

    try:
        document = json.loads(
            text,
            parse_float=_reject_float,
            parse_constant=_reject_constant,
            object_pairs_hook=_reject_duplicate_keys,
        )
    except ArtifactCanonicalJsonError:
        raise
    except json.JSONDecodeError as exc:
        raise ArtifactCanonicalJsonError(
            f"JSON inválido: {exc.msg}"
        ) from exc
    _sanitize_for_canonical(document, path="$")
    return document


def assert_json_safe(value: object, *, path: str = "$") -> None:
    """Valida recursivamente que o valor é JSON-seguro sem float."""
    _sanitize_for_canonical(value, path=path)


def _sanitize_for_canonical(value: object, *, path: str) -> object:
    value_type = type(value)
    if value_type is float:
        raise ArtifactCanonicalJsonError(
            f"{path}: float é proibido no JSON canônico"
        )
    if value_type is str:
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ArtifactCanonicalJsonError(
                f"{path}: string não codificável como UTF-8: {exc.reason}"
            ) from exc
        return value
    if value_type in (bool, type(None)):
        return value
    if value_type is int:
        # bool é subclasse de int; já tratado acima por type() exact.
        return value
    if value_type is list:
        return [
            _sanitize_for_canonical(item, path=f"{path}[{index}]")
            for index, item in enumerate(value)
        ]
    if value_type is dict:
        result: dict[str, object] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise ArtifactCanonicalJsonError(
                    f"{path}: chave JSON deve ser str, "
                    f"recebido {type(key).__name__}"
                )
            result[key] = _sanitize_for_canonical(
                item, path=f"{path}.{key}"
            )
        return result
    if value_type in (set, frozenset, bytes, bytearray, complex):
        raise ArtifactCanonicalJsonError(
            f"{path}: tipo {value_type.__name__} não é JSON-seguro"
        )
    raise ArtifactCanonicalJsonError(
        f"{path}: tipo Python não representável em JSON: "
        f"{value_type.__name__}"
    )


def _reject_float(token: str) -> Any:
    raise ArtifactCanonicalJsonError(
        f"número fracionário/float proibido no JSON: {token!r}"
    )


def _reject_constant(token: str) -> Any:
    raise ArtifactCanonicalJsonError(
        f"constante JSON não finita proibida: {token!r}"
    )


def _reject_duplicate_keys(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ArtifactCanonicalJsonError(
                f"chave JSON duplicada: {key!r}"
            )
        result[key] = value
    return result
