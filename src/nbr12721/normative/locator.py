"""Localizadores de página física (PDF) e página impressa."""

from __future__ import annotations

from dataclasses import dataclass
import re

from nbr12721.normative.errors import NormativeValidationError
from nbr12721.normative.vocab import PRINTED_PAGE_KINDS

_ROMAN_PATTERN = re.compile(r"^[ivxlcdm]+$")
_ARABIC_PATTERN = re.compile(r"^[1-9][0-9]*$")
_LOCATOR_KEYS = frozenset({"pdf_page", "printed_page"})
_PRINTED_KEYS_PRESENT = frozenset({"kind", "label"})
_PRINTED_KEYS_ABSENT = frozenset({"kind", "reason"})


@dataclass(frozen=True, slots=True)
class PrintedPage:
    """Rótulo impresso distinto da página física do PDF."""

    kind: str
    label: str | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, str):
            raise NormativeValidationError("printed_page.kind deve ser string")
        if self.kind not in PRINTED_PAGE_KINDS:
            raise NormativeValidationError(
                f"printed_page.kind inválido: {self.kind!r}"
            )
        if self.kind == "absent":
            if self.label is not None:
                raise NormativeValidationError(
                    "printed_page absent não pode ter label"
                )
            if not isinstance(self.reason, str) or not self.reason.strip():
                raise NormativeValidationError(
                    "printed_page absent exige reason não vazia"
                )
            return
        if self.reason is not None:
            raise NormativeValidationError(
                "printed_page com label não pode ter reason"
            )
        if not isinstance(self.label, str) or not self.label.strip():
            raise NormativeValidationError(
                "printed_page com kind arabic/roman exige label"
            )
        if self.kind == "roman" and not _ROMAN_PATTERN.fullmatch(self.label):
            raise NormativeValidationError(
                "printed_page.roman label deve ser romano minúsculo"
            )
        if self.kind == "arabic" and not _ARABIC_PATTERN.fullmatch(self.label):
            raise NormativeValidationError(
                "printed_page.arabic label deve ser inteiro decimal positivo"
            )

    def to_dict(self) -> dict[str, str]:
        if self.kind == "absent":
            assert self.reason is not None
            return {"kind": self.kind, "reason": self.reason}
        assert self.label is not None
        return {"kind": self.kind, "label": self.label}


@dataclass(frozen=True, slots=True)
class PageLocator:
    """Página PDF 1-based e página impressa semanticamente separada."""

    pdf_page: int
    printed_page: PrintedPage

    def __post_init__(self) -> None:
        if type(self.pdf_page) is not int:
            raise NormativeValidationError("pdf_page deve ser inteiro")
        if self.pdf_page < 1:
            raise NormativeValidationError(
                "pdf_page deve ser inteiro >= 1 (1-based)"
            )
        if not isinstance(self.printed_page, PrintedPage):
            raise NormativeValidationError(
                "printed_page deve ser PrintedPage"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "pdf_page": self.pdf_page,
            "printed_page": self.printed_page.to_dict(),
        }


def page_locator_from_dict(data: object) -> PageLocator:
    if not isinstance(data, dict):
        raise NormativeValidationError("locator deve ser objeto")
    extra = set(data.keys()) - _LOCATOR_KEYS
    if extra:
        raise NormativeValidationError(
            f"locator campos desconhecidos: {sorted(extra)!r}"
        )
    missing = _LOCATOR_KEYS - set(data.keys())
    if missing:
        raise NormativeValidationError(
            f"locator campos ausentes: {sorted(missing)!r}"
        )
    pdf_page = data["pdf_page"]
    if type(pdf_page) is not int:
        raise NormativeValidationError("pdf_page deve ser inteiro")
    printed = data["printed_page"]
    if not isinstance(printed, dict):
        raise NormativeValidationError("printed_page deve ser objeto")
    kind = printed.get("kind")
    if kind == "absent":
        extra_p = set(printed.keys()) - _PRINTED_KEYS_ABSENT
        if extra_p:
            raise NormativeValidationError(
                f"printed_page campos desconhecidos: {sorted(extra_p)!r}"
            )
        missing_p = _PRINTED_KEYS_ABSENT - set(printed.keys())
        if missing_p:
            raise NormativeValidationError(
                f"printed_page ausentes: {sorted(missing_p)!r}"
            )
        return PageLocator(
            pdf_page=pdf_page,
            printed_page=PrintedPage(
                kind="absent",
                reason=_require_string(printed["reason"], "printed_page.reason"),
            ),
        )
    extra_p = set(printed.keys()) - _PRINTED_KEYS_PRESENT
    if extra_p:
        raise NormativeValidationError(
            f"printed_page campos desconhecidos: {sorted(extra_p)!r}"
        )
    missing_p = _PRINTED_KEYS_PRESENT - set(printed.keys())
    if missing_p:
        raise NormativeValidationError(
            f"printed_page ausentes: {sorted(missing_p)!r}"
        )
    return PageLocator(
        pdf_page=pdf_page,
        printed_page=PrintedPage(
            kind=_require_string(printed["kind"], "printed_page.kind"),
            label=_require_string(printed["label"], "printed_page.label"),
        ),
    )

def _require_string(value: object, context: str) -> str:
    if not isinstance(value, str):
        raise NormativeValidationError(f"{context} deve ser string")
    return value

