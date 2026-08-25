"""Configuração versionada v1 do profiler (thresholds e metadados estáveis)."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

PAYLOAD_VERSION = "1.0.0"
PROFILER_NAME = "nbr12721-pdf-profiler"
PROFILER_VERSION = "1.0.0"
PROJECT_ID_AY0410 = "project:ay0410-dev-corpus"

# Baseline provisório para o corpus AY0410 (não generalizado antes de GEN-001).
LOW_NATIVE_TEXT_WORD_COUNT = 150
HIGH_RENDERED_SVG_PATH_COUNT = 10000

ALLOWED_FLAGS: frozenset[str] = frozenset(
    {
        "low_native_text",
        "has_images",
        "high_rendered_svg_complexity",
    }
)

ALLOWED_ROTATIONS: frozenset[int] = frozenset({0, 90, 180, 270})

ALLOWED_PROBABLE_ORIGINS: frozenset[str] = frozenset(
    {
        "autocad_pdfplot",
        "pdfium",
        "other",
        "absent",
        "unknown",
    }
)


@dataclass(frozen=True, slots=True)
class ProfilerThresholdsV1:
    """Thresholds nomeados persistidos no produtor do envelope."""

    low_native_text_word_count: int
    high_rendered_svg_path_count: int

    def __post_init__(self) -> None:
        for name, value in (
            ("low_native_text_word_count", self.low_native_text_word_count),
            ("high_rendered_svg_path_count", self.high_rendered_svg_path_count),
        ):
            if type(value) is not int or isinstance(value, bool) or value < 0:
                raise ValueError(
                    f"{name} deve ser inteiro não negativo exato, "
                    f"recebido {value!r}"
                )

    def to_dict(self) -> dict[str, int]:
        return {
            "high_rendered_svg_path_count": self.high_rendered_svg_path_count,
            "low_native_text_word_count": self.low_native_text_word_count,
        }

    @classmethod
    def baseline(cls) -> ProfilerThresholdsV1:
        return cls(
            low_native_text_word_count=LOW_NATIVE_TEXT_WORD_COUNT,
            high_rendered_svg_path_count=HIGH_RENDERED_SVG_PATH_COUNT,
        )


DEFAULT_THRESHOLDS = ProfilerThresholdsV1.baseline()

COORDINATE_SYSTEM: MappingProxyType[str, str] = MappingProxyType(
    {
        "origin": "bottom-left",
        "unit": "pt",
        "x_axis": "right",
        "y_axis": "up",
    }
)


def producer_configuration(
    *,
    backend_name: str,
    backend_version: str,
    thresholds: ProfilerThresholdsV1 | None = None,
) -> dict[str, Any]:
    """Configuração estável serializada no envelope."""
    active = thresholds or DEFAULT_THRESHOLDS
    return {
        "backend": backend_name,
        "backend_version": backend_version,
        "payload_version": PAYLOAD_VERSION,
        "thresholds": active.to_dict(),
    }
