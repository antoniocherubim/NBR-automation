"""Validador Python stdlib do payload page-profiles v1."""

from __future__ import annotations

import json
import re
from collections.abc import Set
from decimal import Decimal
from pathlib import Path
from typing import Any

from nbr12721.artifacts.decimal_string import is_canonical_decimal_string
from nbr12721.pdf.config import (
    ALLOWED_FLAGS,
    ALLOWED_PROBABLE_ORIGINS,
    ALLOWED_ROTATIONS,
)
from nbr12721.pdf.errors import PdfSchemaError

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[3] / "schemas" / "page-profiles-v1.schema.json"
)
_SCHEMA: dict[str, Any] | None = None


def _get_schema() -> dict[str, Any]:
    global _SCHEMA
    if _SCHEMA is None:
        _SCHEMA = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    return _SCHEMA


def validate_page_profiles_payload(
    payload: object,
    *,
    sources: Set[str],
) -> None:
    """Valida payload contra contrato v1 (campos, tipos, cobertura).

    ``sources`` deve conter exatamente os IDs lógicos esperados no envelope;
    cobertura incompleta, fonte extra ou duplicata falham fechado.
    """
    if type(payload) is not dict:
        raise PdfSchemaError("payload deve ser objeto")
    _validate_object(payload, _get_schema(), path="payload")
    _validate_source_coverage(payload, sources)


def _validate_source_coverage(payload: dict[str, Any], sources: Set[str]) -> None:
    documents = payload.get("documents")
    if not isinstance(documents, list):
        raise PdfSchemaError("payload.documents inválido")
    document_paths = {item["source_path"] for item in documents}
    if document_paths != sources:
        missing = sorted(sources - document_paths)
        extra = sorted(document_paths - sources)
        raise PdfSchemaError(
            "cobertura de fontes incompleta ou extra: "
            f"missing={missing!r} extra={extra!r}"
        )


def _validate_object(value: object, schema: dict[str, Any], *, path: str) -> None:
    if schema.get("type") == "object":
        if type(value) is not dict:
            raise PdfSchemaError(f"{path} deve ser objeto")
        if schema.get("additionalProperties") is False:
            extra = set(value.keys()) - set(schema.get("properties", {}))
            if extra:
                raise PdfSchemaError(
                    f"{path} contém campos desconhecidos: {sorted(extra)!r}"
                )
        for key in schema.get("required", []):
            if key not in value:
                raise PdfSchemaError(f"{path}.{key} obrigatório ausente")
        for key, subschema in schema.get("properties", {}).items():
            if key in value:
                _validate_value(value[key], subschema, path=f"{path}.{key}")
        return

    _validate_value(value, schema, path=path)


def _validate_value(value: object, schema: dict[str, Any], *, path: str) -> None:
    if "$ref" in schema:
        ref_name = schema["$ref"].split("/")[-1]
        target = _get_schema()["$defs"][ref_name]
        _validate_value(value, target, path=path)
        return

    if "const" in schema and value != schema["const"]:
        raise PdfSchemaError(f"{path} viola const")
    if "enum" in schema and value not in schema["enum"]:
        raise PdfSchemaError(f"{path} enum inválida: {value!r}")

    schema_type = schema.get("type")
    if schema_type == "string":
        if type(value) is not str:
            raise PdfSchemaError(f"{path} deve ser string")
        min_length = schema.get("minLength")
        if min_length is not None and len(value) < min_length:
            raise PdfSchemaError(f"{path} abaixo de minLength")
        pattern = schema.get("pattern")
        if pattern and re.fullmatch(pattern, value) is None:
            raise PdfSchemaError(f"{path} falha pattern")
        return
    if schema_type == "integer":
        if type(value) is not int or isinstance(value, bool):
            raise PdfSchemaError(f"{path} deve ser inteiro exato")
        if schema.get("minimum") is not None and value < schema["minimum"]:
            raise PdfSchemaError(f"{path} abaixo do mínimo")
        if path.endswith(".rotation") and value not in ALLOWED_ROTATIONS:
            raise PdfSchemaError(f"{path} rotação inválida")
        return
    if schema_type == "number":
        # Contrato page-profiles rejeita float; números JSON não-inteiros falham.
        raise PdfSchemaError(f"{path} float/number proibido")
    if schema_type == "boolean":
        if type(value) is not bool:
            raise PdfSchemaError(f"{path} deve ser boolean")
        return
    if schema_type == "array":
        if type(value) is not list:
            raise PdfSchemaError(f"{path} deve ser array")
        min_items = schema.get("minItems")
        if min_items is not None and len(value) < min_items:
            raise PdfSchemaError(f"{path} abaixo de minItems")
        if schema.get("uniqueItems") is True:
            seen_items: list[object] = []
            for item in value:
                if item in seen_items:
                    raise PdfSchemaError(f"{path} viola uniqueItems")
                seen_items.append(item)
        unique_property = schema.get("x-uniqueProperty")
        if unique_property is not None:
            seen_keys: set[object] = set()
            for index, item in enumerate(value):
                if type(item) is not dict:
                    raise PdfSchemaError(f"{path}[{index}] deve ser objeto")
                key_value = item.get(unique_property)
                if key_value in seen_keys:
                    raise PdfSchemaError(
                        f"{path} {unique_property} duplicado: {key_value!r}"
                    )
                seen_keys.add(key_value)
        item_schema = schema.get("items", {})
        for index, item in enumerate(value):
            item_path = f"{path}[{index}]"
            _validate_value(item, item_schema, path=item_path)
            if path.endswith(".flags") and type(item) is str:
                if item not in ALLOWED_FLAGS:
                    raise PdfSchemaError(f"{path} flag desconhecida: {item!r}")
            if path.endswith(".pages") and type(item) is dict:
                origin = item.get("probable_origin")
                if origin not in ALLOWED_PROBABLE_ORIGINS:
                    raise PdfSchemaError(f"{path} origem inválida")
        return
    if schema_type == "object":
        _validate_object(value, schema, path=path)
        if path.endswith("_box") or path.endswith(".media_box") or path.endswith(
            ".crop_box"
        ):
            _validate_box(value, path=path)
        return
    raise PdfSchemaError(f"{path} schema sem type suportado")


def _validate_box(value: object, *, path: str) -> None:
    if type(value) is not dict:
        raise PdfSchemaError(f"{path} box inválida")
    for key in ("x0", "y0", "x1", "y1", "width", "height"):
        token = value.get(key)
        if not is_canonical_decimal_string(token):
            raise PdfSchemaError(f"{path}.{key} decimal-string inválida")
    x0 = Decimal(str(value["x0"]))
    y0 = Decimal(str(value["y0"]))
    x1 = Decimal(str(value["x1"]))
    y1 = Decimal(str(value["y1"]))
    width = Decimal(str(value["width"]))
    height = Decimal(str(value["height"]))
    if x1 < x0 or y1 < y0:
        raise PdfSchemaError(f"{path} dimensões inconsistentes")
    if width != x1 - x0 or height != y1 - y0:
        raise PdfSchemaError(f"{path} width/height inconsistentes")
