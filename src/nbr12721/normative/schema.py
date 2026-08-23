"""Validação fail-closed do índice normativo v1 (stdlib)."""

from __future__ import annotations

import re

from nbr12721.normative.errors import NormativeValidationError
from nbr12721.normative.locator import page_locator_from_dict
from nbr12721.normative.reference import normative_reference_from_dict
from nbr12721.normative.source import normative_source_from_dict
from nbr12721.normative.vocab import SCHEMA_VERSION, SOURCE_ID

_ROOT_KEYS = frozenset({"schema_version", "source", "references"})
_ID_PATTERN = re.compile(
    r"^nbr12721:2006:vc3:[a-z0-9]+(?:[-.:][a-z0-9]+)*$"
)


def validate_index_document(document: object) -> None:
    """Valida estrutura, enums, unicidade e links internos do índice v1."""
    if not isinstance(document, dict):
        raise NormativeValidationError("índice deve ser objeto JSON")

    extra = set(document.keys()) - _ROOT_KEYS
    if extra:
        raise NormativeValidationError(
            f"campos desconhecidos no índice: {sorted(extra)!r}"
        )
    missing = _ROOT_KEYS - set(document.keys())
    if missing:
        raise NormativeValidationError(
            f"campos obrigatórios ausentes: {sorted(missing)!r}"
        )

    schema_version = document["schema_version"]
    if type(schema_version) is not int:
        raise NormativeValidationError("schema_version deve ser inteiro")
    if schema_version != SCHEMA_VERSION:
        raise NormativeValidationError(
            f"schema_version incompatível: {schema_version!r}"
        )

    source = normative_source_from_dict(document["source"])
    if source.id != SOURCE_ID:
        raise NormativeValidationError("source.id inesperado")

    references = document["references"]
    if not isinstance(references, list):
        raise NormativeValidationError("references deve ser array")
    if not references:
        raise NormativeValidationError("references não pode ser vazio")

    parsed = []
    seen_ids: set[str] = set()
    previous_id: str | None = None
    for index, item in enumerate(references):
        try:
            ref = normative_reference_from_dict(item)
        except NormativeValidationError as exc:
            raise NormativeValidationError(
                f"references[{index}]: {exc}"
            ) from exc
        # Revalida locator tipado (já feito no from_dict, mas garante path).
        page_locator_from_dict(item["locator"])
        if ref.id in seen_ids:
            raise NormativeValidationError(
                f"id duplicado: {ref.id!r}"
            )
        seen_ids.add(ref.id)
        if previous_id is not None and ref.id <= previous_id:
            raise NormativeValidationError(
                "references deve estar ordenado lexicograficamente por id"
            )
        previous_id = ref.id
        if ref.source_id != source.id:
            raise NormativeValidationError(
                f"references[{index}].source_id não corresponde à fonte"
            )
        parsed.append(ref)

    known = {ref.id for ref in parsed}
    for ref in parsed:
        for field, values in (
            ("cross_references", ref.cross_references),
            ("authority_refs", ref.authority_refs),
        ):
            for target in values:
                if target not in known:
                    raise NormativeValidationError(
                        f"{ref.id}: {field} aponta para id inexistente "
                        f"{target!r}"
                    )
                if target == ref.id:
                    raise NormativeValidationError(
                        f"{ref.id}: {field} não pode auto-referenciar"
                    )
