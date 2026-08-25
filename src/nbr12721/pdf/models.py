"""Value objects imutáveis para sinais brutos e normalizados do profiler."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from nbr12721.artifacts.decimal_string import decimal_to_canonical_string
from nbr12721.pdf.config import ALLOWED_FLAGS, ALLOWED_ROTATIONS
from nbr12721.pdf.origin import assert_probable_origin


def _require_nonneg_int(value: object, *, context: str) -> int:
    if type(value) is not int or isinstance(value, bool):
        raise ValueError(
            f"{context} deve ser inteiro não negativo exato, "
            f"recebido {value!r}"
        )
    if value < 0:
        raise ValueError(f"{context} não pode ser negativo: {value!r}")
    return value


def _decimal_coord(value: Decimal | str, *, context: str) -> str:
    if isinstance(value, str):
        from nbr12721.artifacts.decimal_string import parse_canonical_decimal_string

        decimal_value = parse_canonical_decimal_string(value)
    elif type(value) is Decimal:
        decimal_value = value
    else:
        raise ValueError(f"{context} deve ser Decimal ou decimal-string")
    return decimal_to_canonical_string(decimal_value)


@dataclass(frozen=True, slots=True)
class PageBox:
    """Caixa de página em pontos PDF (origem bottom-left)."""

    x0: Decimal
    y0: Decimal
    x1: Decimal
    y1: Decimal

    @property
    def width(self) -> Decimal:
        return self.x1 - self.x0

    @property
    def height(self) -> Decimal:
        return self.y1 - self.y0

    def to_dict(self) -> dict[str, str]:
        return {
            "height": _decimal_coord(self.height, context="box.height"),
            "width": _decimal_coord(self.width, context="box.width"),
            "x0": _decimal_coord(self.x0, context="box.x0"),
            "x1": _decimal_coord(self.x1, context="box.x1"),
            "y0": _decimal_coord(self.y0, context="box.y0"),
            "y1": _decimal_coord(self.y1, context="box.y1"),
        }

    @classmethod
    def from_coords(
        cls,
        x0: Decimal,
        y0: Decimal,
        x1: Decimal,
        y1: Decimal,
    ) -> PageBox:
        if x1 < x0 or y1 < y0:
            raise ValueError("box inválida: x1/y1 devem ser >= x0/y0")
        return cls(x0=x0, y0=y0, x1=x1, y1=y1)


@dataclass(frozen=True, slots=True)
class RenderedSvgSignals:
    """Contagens estruturais da renderização SVG (não operadores internos PDF)."""

    path_count: int
    line_count: int
    rect_count: int
    polyline_count: int
    polygon_count: int
    circle_count: int
    ellipse_count: int

    def __post_init__(self) -> None:
        for name in (
            "path_count",
            "line_count",
            "rect_count",
            "polyline_count",
            "polygon_count",
            "circle_count",
            "ellipse_count",
        ):
            _require_nonneg_int(getattr(self, name), context=name)

    def to_dict(self) -> dict[str, int]:
        return {
            "rendered_svg_circle_count": self.circle_count,
            "rendered_svg_ellipse_count": self.ellipse_count,
            "rendered_svg_line_count": self.line_count,
            "rendered_svg_path_count": self.path_count,
            "rendered_svg_polygon_count": self.polygon_count,
            "rendered_svg_polyline_count": self.polyline_count,
            "rendered_svg_rect_count": self.rect_count,
        }


@dataclass(frozen=True, slots=True)
class PageRawSignals:
    """Sinais brutos normalizados de uma página (sem conteúdo persistido)."""

    page_number: int
    media_box: PageBox
    crop_box: PageBox
    rotation: int
    native_word_count: int
    native_codepoint_count: int
    native_word_with_bbox_count: int
    font_count: int
    embedded_font_count: int
    subset_font_count: int
    image_count: int
    image_width_sum: int
    image_height_sum: int
    image_pixel_sum: int
    rendered_svg: RenderedSvgSignals
    probable_origin: str

    def __post_init__(self) -> None:
        if self.page_number < 1:
            raise ValueError("page_number deve ser >= 1")
        if self.rotation not in ALLOWED_ROTATIONS:
            raise ValueError(f"rotation inválida: {self.rotation!r}")
        for name in (
            "native_word_count",
            "native_codepoint_count",
            "native_word_with_bbox_count",
            "font_count",
            "embedded_font_count",
            "subset_font_count",
            "image_count",
            "image_width_sum",
            "image_height_sum",
            "image_pixel_sum",
        ):
            _require_nonneg_int(getattr(self, name), context=name)
        assert_probable_origin(self.probable_origin)


@dataclass(frozen=True, slots=True)
class DocumentRawSignals:
    """Perfil bruto de um documento PDF."""

    source_path: str
    pages: tuple[PageRawSignals, ...]

    def __post_init__(self) -> None:
        if self.source_path == "":
            raise ValueError("source_path não pode ser vazio")
        if not self.pages:
            raise ValueError("documento deve conter ao menos uma página")
        ordered = tuple(sorted(self.pages, key=lambda page: page.page_number))
        object.__setattr__(self, "pages", ordered)
        numbers = [page.page_number for page in self.pages]
        if len(numbers) != len(set(numbers)):
            raise ValueError("page_number duplicado no documento")
        if tuple(numbers) != tuple(range(1, len(numbers) + 1)):
            raise ValueError("page_number deve ser sequencial 1..N")


def derive_flags(
    page: PageRawSignals,
    *,
    low_native_text_word_count: int,
    high_rendered_svg_path_count: int,
) -> tuple[str, ...]:
    """Flags descritivas sobreponíveis (sem decisão de pipeline)."""
    flags: list[str] = []
    if page.native_word_count <= low_native_text_word_count:
        flags.append("low_native_text")
    if page.image_count > 0:
        flags.append("has_images")
    if page.rendered_svg.path_count >= high_rendered_svg_path_count:
        flags.append("high_rendered_svg_complexity")
    for flag in flags:
        if flag not in ALLOWED_FLAGS:
            raise ValueError(f"flag interna inválida: {flag!r}")
    return tuple(sorted(flags))


def page_to_payload_dict(
    page: PageRawSignals,
    *,
    flags: tuple[str, ...],
) -> dict[str, Any]:
    payload = {
        "crop_box": page.crop_box.to_dict(),
        "embedded_font_count": page.embedded_font_count,
        "flags": list(flags),
        "font_count": page.font_count,
        "image_count": page.image_count,
        "image_height_sum": page.image_height_sum,
        "image_pixel_sum": page.image_pixel_sum,
        "image_width_sum": page.image_width_sum,
        "media_box": page.media_box.to_dict(),
        "native_codepoint_count": page.native_codepoint_count,
        "native_word_count": page.native_word_count,
        "native_word_with_bbox_count": page.native_word_with_bbox_count,
        "page_number": page.page_number,
        "probable_origin": page.probable_origin,
        "rotation": page.rotation,
        "subset_font_count": page.subset_font_count,
    }
    payload.update(page.rendered_svg.to_dict())
    return payload
