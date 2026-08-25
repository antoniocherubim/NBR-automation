"""Validação Draft 2020-12 do payload page-profiles v1 (stdlib, sem Node).

Implementa o subconjunto do schema versionado exercitado pelos testes, incluindo
a extensão documentada ``x-uniqueProperty`` (ignorada por validadores genéricos).
"""

from __future__ import annotations

import json
import re
from collections.abc import Set
from decimal import Decimal
from pathlib import Path
from typing import Any

from nbr12721.artifacts.decimal_string import is_canonical_decimal_string

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SCHEMA_PATH = _PROJECT_ROOT / "schemas" / "page-profiles-v1.schema.json"
_SCHEMA: dict[str, Any] = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))

_ALLOWED_FLAGS = frozenset(_SCHEMA["$defs"]["flag"]["enum"])
_ALLOWED_ORIGINS = frozenset(_SCHEMA["$defs"]["probable_origin"]["enum"])
_ALLOWED_ROTATIONS = frozenset(_SCHEMA["$defs"]["page"]["properties"]["rotation"]["enum"])


class PageProfilesSchemaError(ValueError):
    """Payload não satisfaz o JSON Schema page-profiles v1."""


def validate_page_profiles_against_json_schema(
    payload: object,
    *,
    sources: Set[str],
) -> None:
    """Valida payload + cobertura de fontes contra o schema versionado."""
    if type(payload) is not dict:
        raise PageProfilesSchemaError("payload deve ser objeto")
    _validate_node(payload, _SCHEMA, path="payload")
    _validate_source_coverage(payload, sources)


def _validate_source_coverage(payload: dict[str, Any], sources: Set[str]) -> None:
    documents = payload.get("documents")
    if not isinstance(documents, list):
        raise PageProfilesSchemaError("payload.documents inválido")
    document_paths = {item["source_path"] for item in documents if isinstance(item, dict)}
    if document_paths != sources:
        missing = sorted(sources - document_paths)
        extra = sorted(document_paths - sources)
        raise PageProfilesSchemaError(
            "cobertura de fontes incompleta ou extra: "
            f"missing={missing!r} extra={extra!r}"
        )


def _resolve_ref(schema: dict[str, Any]) -> dict[str, Any]:
    if "$ref" not in schema:
        return schema
    ref_name = schema["$ref"].split("/")[-1]
    return _SCHEMA["$defs"][ref_name]


def _validate_node(value: object, schema: dict[str, Any], *, path: str) -> None:
    schema = _resolve_ref(schema)
    if "const" in schema and value != schema["const"]:
        raise PageProfilesSchemaError(f"{path} viola const")
    if "enum" in schema and value not in schema["enum"]:
        raise PageProfilesSchemaError(f"{path} enum inválida: {value!r}")

    schema_type = schema.get("type")
    if schema_type == "object":
        if type(value) is not dict:
            raise PageProfilesSchemaError(f"{path} deve ser objeto")
        if schema.get("additionalProperties") is False:
            extra = set(value.keys()) - set(schema.get("properties", {}))
            if extra:
                raise PageProfilesSchemaError(
                    f"{path} contém campos desconhecidos: {sorted(extra)!r}"
                )
        for key in schema.get("required", []):
            if key not in value:
                raise PageProfilesSchemaError(f"{path}.{key} obrigatório ausente")
        for key, subschema in schema.get("properties", {}).items():
            if key in value:
                _validate_node(value[key], subschema, path=f"{path}.{key}")
        if path.endswith("_box") or path.endswith(".media_box") or path.endswith(
            ".crop_box"
        ):
            _validate_box(value, path=path)
        return

    if schema_type == "string":
        if type(value) is not str:
            raise PageProfilesSchemaError(f"{path} deve ser string")
        min_length = schema.get("minLength")
        if min_length is not None and len(value) < min_length:
            raise PageProfilesSchemaError(f"{path} abaixo de minLength")
        pattern = schema.get("pattern")
        if pattern and re.fullmatch(pattern, value) is None:
            raise PageProfilesSchemaError(f"{path} falha pattern")
        return

    if schema_type == "integer":
        if type(value) is not int or isinstance(value, bool):
            raise PageProfilesSchemaError(f"{path} deve ser inteiro exato")
        minimum = schema.get("minimum")
        if minimum is not None and value < minimum:
            raise PageProfilesSchemaError(f"{path} abaixo do mínimo")
        if path.endswith(".rotation") and value not in _ALLOWED_ROTATIONS:
            raise PageProfilesSchemaError(f"{path} rotação inválida")
        return

    if schema_type == "number":
        raise PageProfilesSchemaError(f"{path} float/number proibido")

    if schema_type == "array":
        if type(value) is not list:
            raise PageProfilesSchemaError(f"{path} deve ser array")
        min_items = schema.get("minItems")
        if min_items is not None and len(value) < min_items:
            raise PageProfilesSchemaError(f"{path} abaixo de minItems")
        if schema.get("uniqueItems") is True:
            seen_items: list[object] = []
            for item in value:
                if item in seen_items:
                    raise PageProfilesSchemaError(f"{path} viola uniqueItems")
                seen_items.append(item)
        unique_property = schema.get("x-uniqueProperty")
        if unique_property is not None:
            seen_keys: set[object] = set()
            for index, item in enumerate(value):
                if type(item) is not dict:
                    raise PageProfilesSchemaError(
                        f"{path}[{index}] deve ser objeto"
                    )
                key_value = item.get(unique_property)
                if key_value in seen_keys:
                    raise PageProfilesSchemaError(
                        f"{path} {unique_property} duplicado: {key_value!r}"
                    )
                seen_keys.add(key_value)
        item_schema = schema.get("items", {})
        for index, item in enumerate(value):
            item_path = f"{path}[{index}]"
            _validate_node(item, item_schema, path=item_path)
            if path.endswith(".flags") and type(item) is str:
                if item not in _ALLOWED_FLAGS:
                    raise PageProfilesSchemaError(
                        f"{path} flag desconhecida: {item!r}"
                    )
            if path.endswith(".pages") and type(item) is dict:
                origin = item.get("probable_origin")
                if origin not in _ALLOWED_ORIGINS:
                    raise PageProfilesSchemaError(f"{path} origem inválida")
        return

    raise PageProfilesSchemaError(f"{path} schema sem type suportado")


def _validate_box(value: object, *, path: str) -> None:
    if type(value) is not dict:
        raise PageProfilesSchemaError(f"{path} box inválida")
    for key in ("x0", "y0", "x1", "y1", "width", "height"):
        token = value.get(key)
        if not is_canonical_decimal_string(token):
            raise PageProfilesSchemaError(f"{path}.{key} decimal-string inválida")
    x0 = Decimal(str(value["x0"]))
    y0 = Decimal(str(value["y0"]))
    x1 = Decimal(str(value["x1"]))
    y1 = Decimal(str(value["y1"]))
    width = Decimal(str(value["width"]))
    height = Decimal(str(value["height"]))
    if x1 < x0 or y1 < y0:
        raise PageProfilesSchemaError(f"{path} dimensões inconsistentes")
    if width != x1 - x0 or height != y1 - y0:
        raise PageProfilesSchemaError(f"{path} width/height inconsistentes")
