"""Mapeamento explícito entre ID lógico e path físico de fonte."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from nbr12721.sources.errors import PathMappingError, PathSecurityError
from nbr12721.sources.paths import validate_relative_posix_path

_PHYSICAL_PREFIX = "inputs/private/"


def validate_path_mapping(
    expected_logical_ids: Sequence[str],
    mapping: Mapping[str, str],
) -> dict[str, str]:
    """Valida mapeamento total e bijetivo lógico → físico sob inputs/private/.

    O chamador fornece o dicionário; este módulo não lê XDG, store externo
    nem inventário privado. Symlinks e tipo de arquivo são rejeitados na
    verificação dos bytes, não aqui.
    """
    expected = list(expected_logical_ids)
    for logical_id in expected:
        if not isinstance(logical_id, str):
            raise PathMappingError("ID lógico esperado deve ser string")
        try:
            validate_relative_posix_path(logical_id, context="ID lógico")
        except PathSecurityError as exc:
            raise PathMappingError(str(exc)) from exc
    expected_set = set(expected)
    if len(expected) != len(expected_set):
        raise PathMappingError("IDs lógicos esperados contêm duplicata")

    mapping_keys = set(mapping.keys())
    if any(not isinstance(key, str) for key in mapping_keys):
        raise PathMappingError("chaves do mapeamento devem ser strings")
    missing = expected_set - mapping_keys
    if missing:
        sample = sorted(missing)[0]
        raise PathMappingError(f"chave lógica ausente no mapeamento: {sample!r}")
    extra = mapping_keys - expected_set
    if extra:
        sample = sorted(extra)[0]
        raise PathMappingError(f"chave lógica extra no mapeamento: {sample!r}")

    result: dict[str, str] = {}
    seen_physical: set[str] = set()
    for logical_id in expected:
        physical = mapping[logical_id]
        if not isinstance(physical, str):
            raise PathMappingError(
                f"path físico deve ser string para {logical_id!r}"
            )
        try:
            validate_relative_posix_path(
                physical, context=f"path físico de {logical_id!r}"
            )
        except PathSecurityError as exc:
            raise PathMappingError(str(exc)) from exc
        if physical == "inputs/private" or not physical.startswith(
            _PHYSICAL_PREFIX
        ):
            raise PathMappingError(
                f"destino fora de inputs/private/: {physical!r}"
            )
        if physical in seen_physical:
            raise PathMappingError(
                f"path físico duplicado no mapeamento: {physical!r}"
            )
        seen_physical.add(physical)
        result[logical_id] = physical
    return result
