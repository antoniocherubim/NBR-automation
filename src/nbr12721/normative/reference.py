"""Entrada imutável de referência normativa."""

from __future__ import annotations

from dataclasses import dataclass
import re

from nbr12721.normative.errors import NormativeValidationError
from nbr12721.normative.locator import PageLocator, page_locator_from_dict
from nbr12721.normative.vocab import (
    FORMALIZATION_STATES,
    REFERENCE_TYPES,
    SOURCE_ID,
)

_ID_PATTERN = re.compile(
    r"^nbr12721:2006:vc3:[a-z0-9]+(?:[-.:][a-z0-9]+)*$"
)
_ENTRY_KEYS = frozenset(
    {
        "id",
        "source_id",
        "section",
        "locator",
        "reference_type",
        "formalization_state",
        "description",
        "edition_notes",
        "cross_references",
        "authority_refs",
        "formal_artifact_ref",
        "implementation_ref",
    }
)


@dataclass(frozen=True, slots=True)
class NormativeReference:
    """Referência indexada: seção + localizador + tipo + estado."""

    id: str
    source_id: str
    section: str
    locator: PageLocator
    reference_type: str
    formalization_state: str
    description: str
    edition_notes: str
    cross_references: tuple[str, ...]
    authority_refs: tuple[str, ...]
    formal_artifact_ref: str | None = None
    implementation_ref: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not _ID_PATTERN.fullmatch(self.id):
            raise NormativeValidationError(f"id inválido: {self.id!r}")
        if not isinstance(self.source_id, str) or self.source_id != SOURCE_ID:
            raise NormativeValidationError(
                f"source_id desconhecido: {self.source_id!r}"
            )
        if not isinstance(self.section, str) or not self.section.strip():
            raise NormativeValidationError("section deve ser string não vazia")
        if not isinstance(self.locator, PageLocator):
            raise NormativeValidationError("locator deve ser PageLocator")
        if not isinstance(self.reference_type, str) or self.reference_type not in REFERENCE_TYPES:
            raise NormativeValidationError(
                f"reference_type inválido: {self.reference_type!r}"
            )
        if not isinstance(
            self.formalization_state, str
        ) or self.formalization_state not in FORMALIZATION_STATES:
            raise NormativeValidationError(
                f"formalization_state inválido: {self.formalization_state!r}"
            )
        if not isinstance(self.description, str) or not self.description.strip():
            raise NormativeValidationError(
                "description deve ser string não vazia"
            )
        if len(self.description) > 280:
            raise NormativeValidationError(
                "description excede 280 caracteres"
            )
        if not isinstance(self.edition_notes, str):
            raise NormativeValidationError("edition_notes deve ser string")
        if len(self.edition_notes) > 280:
            raise NormativeValidationError(
                "edition_notes excede 280 caracteres"
            )
        for label, values in (
            ("cross_references", self.cross_references),
            ("authority_refs", self.authority_refs),
        ):
            if not isinstance(values, tuple):
                raise NormativeValidationError(f"{label} deve ser tupla")
            seen: set[str] = set()
            for item in values:
                if not isinstance(item, str) or not _ID_PATTERN.fullmatch(item):
                    raise NormativeValidationError(
                        f"{label} contém id inválido: {item!r}"
                    )
                if item in seen:
                    raise NormativeValidationError(
                        f"{label} contém id duplicado: {item!r}"
                    )
                seen.add(item)
        self._validate_formalization_links()

    def _validate_formalization_links(self) -> None:
        state = self.formalization_state
        formal = self.formal_artifact_ref
        impl = self.implementation_ref
        if state == "indexed":
            if formal is not None or impl is not None:
                raise NormativeValidationError(
                    "estado indexed não admite formal_artifact_ref "
                    "nem implementation_ref"
                )
            return
        if not isinstance(formal, str) or not formal.strip():
            raise NormativeValidationError(
                f"estado {state} exige formal_artifact_ref não vazio"
            )
        if state == "formalized":
            if impl is not None:
                raise NormativeValidationError(
                    "estado formalized não admite implementation_ref"
                )
            return
        # implemented
        if not isinstance(impl, str) or not impl.strip():
            raise NormativeValidationError(
                "estado implemented exige implementation_ref não vazio"
            )

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "authority_refs": sorted(self.authority_refs),
            "cross_references": sorted(self.cross_references),
            "description": self.description,
            "edition_notes": self.edition_notes,
            "formalization_state": self.formalization_state,
            "id": self.id,
            "locator": self.locator.to_dict(),
            "reference_type": self.reference_type,
            "section": self.section,
            "source_id": self.source_id,
        }
        if self.formal_artifact_ref is not None:
            payload["formal_artifact_ref"] = self.formal_artifact_ref
        if self.implementation_ref is not None:
            payload["implementation_ref"] = self.implementation_ref
        return payload


def normative_reference_from_dict(data: object) -> NormativeReference:
    if not isinstance(data, dict):
        raise NormativeValidationError("reference deve ser objeto")
    extra = set(data.keys()) - _ENTRY_KEYS
    if extra:
        raise NormativeValidationError(
            f"reference campos desconhecidos: {sorted(extra)!r}"
        )
    required = _ENTRY_KEYS - {
        "formal_artifact_ref",
        "implementation_ref",
    }
    missing = required - set(data.keys())
    if missing:
        raise NormativeValidationError(
            f"reference campos ausentes: {sorted(missing)!r}"
        )

    def _string_tuple(field: str) -> tuple[str, ...]:
        raw = data[field]
        if not isinstance(raw, list):
            raise NormativeValidationError(f"{field} deve ser array")
        items: list[str] = []
        for item in raw:
            if not isinstance(item, str):
                raise NormativeValidationError(
                    f"{field} deve conter somente strings"
                )
            items.append(item)
        return tuple(items)

    formal = data.get("formal_artifact_ref")
    impl = data.get("implementation_ref")
    return NormativeReference(
        id=_require_string(data["id"], "reference.id"),
        source_id=_require_string(data["source_id"], "reference.source_id"),
        section=_require_string(data["section"], "reference.section"),
        locator=page_locator_from_dict(data["locator"]),
        reference_type=_require_string(data["reference_type"], "reference.reference_type"),
        formalization_state=_require_string(
            data["formalization_state"], "reference.formalization_state"
        ),
        description=_require_string(data["description"], "reference.description"),
        edition_notes=_require_string(data["edition_notes"], "reference.edition_notes"),
        cross_references=_string_tuple("cross_references"),
        authority_refs=_string_tuple("authority_refs"),
        formal_artifact_ref=(
            None if formal is None else _require_string(formal, "formal_artifact_ref")
        ),
        implementation_ref=(
            None if impl is None else _require_string(impl, "implementation_ref")
        ),
    )

def _require_string(value: object, context: str) -> str:
    if not isinstance(value, str):
        raise NormativeValidationError(f"{context} deve ser string")
    return value

