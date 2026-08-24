"""Decimal finito como string decimal canônica (sem float)."""

from __future__ import annotations

from decimal import Decimal
import re

from nbr12721.artifacts.errors import ArtifactDecimalError

# Forma canônica produzida por decimal_to_canonical_string.
_DECIMAL_STRING_PATTERN = re.compile(
    r"^(?:0|-?(?:0\.[0-9]*[1-9]|[1-9][0-9]*(?:\.[0-9]*[1-9])?))$"
)


def decimal_to_canonical_string(value: Decimal) -> str:
    """Converte Decimal finito em string decimal canônica.

    Regras:
    - sem expoente, sinal ``+``, separador local ou whitespace;
    - sem zeros à esquerda não significativos;
    - sem zeros fracionários finais não significativos;
    - zero negativo normaliza para ``\"0\"``;
    - parte fracionária somente quando necessária;
    - ``NaN`` e infinitos falham;
    - nenhuma conversão intermediária por ``float``.
    """
    if type(value) is not Decimal:
        raise ArtifactDecimalError(
            f"esperado Decimal, recebido {type(value).__name__}"
        )
    if not value.is_finite():
        raise ArtifactDecimalError(
            f"Decimal não finito rejeitado: {value!r}"
        )

    if value == 0:
        return "0"

    # `normalize()` respeita o context Decimal corrente e poderia arredondar
    # valores com mais dígitos que a precisão configurada. `format(..., "f")`
    # expande a escala diretamente, sem aplicar context nem usar float.
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text in {"", "-"}:
        return "0"
    if text == "-0":
        return "0"
    return text


def parse_canonical_decimal_string(text: str) -> Decimal:
    """Interpreta somente strings já canônicas (sem coerção frouxa)."""
    if type(text) is not str:
        raise ArtifactDecimalError(
            f"decimal-string deve ser str, recebido {type(text).__name__}"
        )
    if not _DECIMAL_STRING_PATTERN.fullmatch(text):
        raise ArtifactDecimalError(
            f"decimal-string não canônica: {text!r}"
        )
    return Decimal(text)


def is_canonical_decimal_string(text: object) -> bool:
    return type(text) is str and _DECIMAL_STRING_PATTERN.fullmatch(text) is not None
