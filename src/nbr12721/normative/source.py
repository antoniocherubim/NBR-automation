"""Identidade imutável da fonte normativa ABNT NBR 12721:2006 vc3."""

from __future__ import annotations

from dataclasses import dataclass
import re

from nbr12721.normative.errors import NormativeValidationError
from nbr12721.normative.vocab import (
    EXPECTED_MEDIA_TYPE,
    EXPECTED_SHA256,
    EXPECTED_SIZE_BYTES,
    LOGICAL_PATH,
    SOURCE_ID,
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_ISO_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SOURCE_KEYS = frozenset(
    {
        "id",
        "organization",
        "designation",
        "year",
        "edition",
        "corrected_version",
        "publication_date",
        "corrected_version_date",
        "errata",
        "logical_path",
        "sha256",
        "media_type",
        "size_bytes",
    }
)
_ERRATA_KEYS = frozenset({"label", "date", "note"})
_EXPECTED_PUBLICATION_DATE = "2006-08-28"
_EXPECTED_ERRATA = (
    ("Errata 1", "2007-01-29"),
    ("Errata 2", "2007-04-09"),
    ("Errata 3", "2021-01-19"),
)


@dataclass(frozen=True, slots=True)
class ErrataRecord:
    """Registro conciso de errata incorporada (sem texto normativo)."""

    label: str
    date: str
    note: str

    def __post_init__(self) -> None:
        if not isinstance(self.label, str) or not self.label.strip():
            raise NormativeValidationError("errata.label deve ser string não vazia")
        if not isinstance(self.date, str) or not _ISO_DATE_PATTERN.fullmatch(self.date):
            raise NormativeValidationError(
                "errata.date deve usar ISO 8601 (YYYY-MM-DD)"
            )
        if not isinstance(self.note, str) or not self.note.strip():
            raise NormativeValidationError("errata.note deve ser string não vazia")

    def to_dict(self) -> dict[str, str]:
        return {
            "date": self.date,
            "label": self.label,
            "note": self.note,
        }


@dataclass(frozen=True, slots=True)
class NormativeSource:
    """Identidade da edição/versão corrigida e vínculo ao SourceArtifact lógico."""

    id: str
    organization: str
    designation: str
    year: int
    edition: str
    corrected_version: int
    publication_date: str
    corrected_version_date: str
    errata: tuple[ErrataRecord, ...]
    logical_path: str
    sha256: str
    media_type: str
    size_bytes: int

    def __post_init__(self) -> None:
        if self.id != SOURCE_ID:
            raise NormativeValidationError(
                f"source.id deve ser {SOURCE_ID!r}"
            )
        if self.organization != "ABNT":
            raise NormativeValidationError("organization deve ser ABNT")
        if self.designation != "NBR 12721":
            raise NormativeValidationError("designation deve ser NBR 12721")
        if type(self.year) is not int or self.year != 2006:
            raise NormativeValidationError("year deve ser o inteiro 2006")
        if self.edition != "second":
            raise NormativeValidationError("edition deve ser 'second'")
        if type(self.corrected_version) is not int or self.corrected_version != 3:
            raise NormativeValidationError(
                "corrected_version deve ser o inteiro 3"
            )
        if not isinstance(self.publication_date, str) or not _ISO_DATE_PATTERN.fullmatch(
            self.publication_date
        ):
            raise NormativeValidationError(
                "publication_date deve usar ISO 8601"
            )
        if not isinstance(
            self.corrected_version_date, str
        ) or not _ISO_DATE_PATTERN.fullmatch(self.corrected_version_date):
            raise NormativeValidationError(
                "corrected_version_date deve usar ISO 8601"
            )
        if self.publication_date != _EXPECTED_PUBLICATION_DATE:
            raise NormativeValidationError(
                "publication_date deve ser 2006-08-28"
            )
        if self.corrected_version_date != "2021-01-19":
            raise NormativeValidationError(
                "corrected_version_date deve ser 2021-01-19 (Errata 3)"
            )
        if not isinstance(self.errata, tuple) or any(
            not isinstance(item, ErrataRecord) for item in self.errata
        ):
            raise NormativeValidationError(
                "errata deve ser tupla de ErrataRecord"
            )
        identity = tuple((item.label, item.date) for item in self.errata)
        if identity != _EXPECTED_ERRATA:
            raise NormativeValidationError(
                "errata deve registrar exatamente Erratas 1, 2 e 3"
            )
        if self.logical_path != LOGICAL_PATH:
            raise NormativeValidationError(
                f"logical_path deve ser {LOGICAL_PATH!r}"
            )
        if not isinstance(self.sha256, str) or not _SHA256_PATTERN.fullmatch(
            self.sha256
        ):
            raise NormativeValidationError("sha256 inválido")
        if self.sha256 != EXPECTED_SHA256:
            raise NormativeValidationError(
                "sha256 diverge do digest autoritativo da norma"
            )
        if self.media_type != EXPECTED_MEDIA_TYPE:
            raise NormativeValidationError("media_type deve ser application/pdf")
        if type(self.size_bytes) is not int or self.size_bytes != EXPECTED_SIZE_BYTES:
            raise NormativeValidationError(
                "size_bytes deve coincidir com o inventário público"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "corrected_version": self.corrected_version,
            "corrected_version_date": self.corrected_version_date,
            "designation": self.designation,
            "edition": self.edition,
            "errata": [item.to_dict() for item in self.errata],
            "id": self.id,
            "logical_path": self.logical_path,
            "media_type": self.media_type,
            "organization": self.organization,
            "publication_date": self.publication_date,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "year": self.year,
        }


def baseline_normative_source() -> NormativeSource:
    """Fonte canônica alinhada ao source-manifest e ao ROADMAP."""
    return NormativeSource(
        id=SOURCE_ID,
        organization="ABNT",
        designation="NBR 12721",
        year=2006,
        edition="second",
        corrected_version=3,
        publication_date="2006-08-28",
        corrected_version_date="2021-01-19",
        errata=(
            ErrataRecord(
                label="Errata 1",
                date="2007-01-29",
                note="Incorporada na versão corrigida 3; não cria edição 2007.",
            ),
            ErrataRecord(
                label="Errata 2",
                date="2007-04-09",
                note="Incorporada na versão corrigida 3; não cria edição 2007.",
            ),
            ErrataRecord(
                label="Errata 3",
                date="2021-01-19",
                note=(
                    "Define a data da versão corrigida 3; metadado 2021 não "
                    "renomeia a norma para NBR 12721:2021."
                ),
            ),
        ),
        logical_path=LOGICAL_PATH,
        sha256=EXPECTED_SHA256,
        media_type=EXPECTED_MEDIA_TYPE,
        size_bytes=EXPECTED_SIZE_BYTES,
    )


def normative_source_from_dict(data: object) -> NormativeSource:
    """Reconstrói NormativeSource a partir de objeto JSON validado estruturalmente."""
    if not isinstance(data, dict):
        raise NormativeValidationError("source deve ser objeto")
    extra = set(data.keys()) - _SOURCE_KEYS
    if extra:
        raise NormativeValidationError(
            f"source contém campos desconhecidos: {sorted(extra)!r}"
        )
    missing = _SOURCE_KEYS - set(data.keys())
    if missing:
        raise NormativeValidationError(
            f"source campos obrigatórios ausentes: {sorted(missing)!r}"
        )
    raw_errata = data["errata"]
    if not isinstance(raw_errata, list) or not raw_errata:
        raise NormativeValidationError("source.errata deve ser array não vazio")
    errata: list[ErrataRecord] = []
    for index, item in enumerate(raw_errata):
        if not isinstance(item, dict):
            raise NormativeValidationError(
                f"source.errata[{index}] deve ser objeto"
            )
        extra_e = set(item.keys()) - _ERRATA_KEYS
        if extra_e:
            raise NormativeValidationError(
                f"source.errata[{index}] campos desconhecidos: {sorted(extra_e)!r}"
            )
        missing_e = _ERRATA_KEYS - set(item.keys())
        if missing_e:
            raise NormativeValidationError(
                f"source.errata[{index}] ausentes: {sorted(missing_e)!r}"
            )
        errata.append(
            ErrataRecord(
                label=_require_string(item["label"], f"source.errata[{index}].label"),
                date=_require_string(item["date"], f"source.errata[{index}].date"),
                note=_require_string(item["note"], f"source.errata[{index}].note"),
            )
        )
    return NormativeSource(
        id=_require_string(data["id"], "source.id"),
        organization=_require_string(data["organization"], "source.organization"),
        designation=_require_string(data["designation"], "source.designation"),
        year=_require_exact_int(data["year"], "source.year"),
        edition=_require_string(data["edition"], "source.edition"),
        corrected_version=_require_exact_int(
            data["corrected_version"], "source.corrected_version"
        ),
        publication_date=_require_string(data["publication_date"], "source.publication_date"),
        corrected_version_date=_require_string(
            data["corrected_version_date"], "source.corrected_version_date"
        ),
        errata=tuple(errata),
        logical_path=_require_string(data["logical_path"], "source.logical_path"),
        sha256=_require_string(data["sha256"], "source.sha256"),
        media_type=_require_string(data["media_type"], "source.media_type"),
        size_bytes=_require_exact_int(data["size_bytes"], "source.size_bytes"),
    )


def _require_string(value: object, context: str) -> str:
    if not isinstance(value, str):
        raise NormativeValidationError(f"{context} deve ser string")
    return value


def _require_exact_int(value: object, context: str) -> int:
    if type(value) is not int:
        raise NormativeValidationError(f"{context} deve ser inteiro")
    return value
