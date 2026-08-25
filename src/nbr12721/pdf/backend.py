"""Backend Poppler por subprocessos locais (interface + implementação)."""

from __future__ import annotations

import html
import os
import re
import select
import subprocess
import time
from collections.abc import Sequence
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Protocol

from nbr12721.pdf.errors import PdfBackendError, PdfParseError
from nbr12721.pdf.models import (
    DocumentRawSignals,
    PageBox,
    PageRawSignals,
    RenderedSvgSignals,
)
from nbr12721.pdf.origin import classify_probable_origin
from nbr12721.pdf.subprocess_runner import (
    CommandResult,
    DEFAULT_MAX_ARTIFACT_BYTES,
    DEFAULT_MAX_STDERR_BYTES,
    DEFAULT_TIMEOUT_SECONDS,
    RestrictedTempDirectory,
    minimal_subprocess_env,
    require_success,
    run_command,
)

_DECIMAL_TOKEN = re.compile(r"^-?\d+(?:\.\d+)?$")
_PAGE_BOX_LINE = re.compile(
    r"^Page\s+(\d+)\s+(MediaBox|CropBox):\s+"
    r"([\d.+-]+)\s+([\d.+-]+)\s+([\d.+-]+)\s+([\d.+-]+)\s*$"
)
_DOC_BOX_LINE = re.compile(
    r"^(MediaBox|CropBox):\s+"
    r"([\d.+-]+)\s+([\d.+-]+)\s+([\d.+-]+)\s+([\d.+-]+)\s*$"
)
_PAGE_ROT_LINE = re.compile(r"^Page\s+(\d+)\s+rot:\s+(\d+)\s*$")
_DOC_ROT_LINE = re.compile(r"^Page rot:\s+(\d+)\s*$")
_PRODUCER_LINE = re.compile(r"^Producer:(.*)$")
_PAGES_LINE = re.compile(r"^Pages:\s+(\d+)\s*$")
_POPPLER_VERSION = re.compile(r"^pdfinfo version (\S+)", re.MULTILINE)


class PdfBackend(Protocol):
    """Interface de backend capaz de perfilar documento e páginas."""

    @property
    def name(self) -> str: ...

    @property
    def version(self) -> str: ...

    def profile_document(
        self,
        pdf_path: Path,
        *,
        source_path: str,
    ) -> DocumentRawSignals: ...


class PopplerBackend:
    """Adapter Poppler: pdfinfo, pdftotext, pdffonts, pdfimages, pdftocairo."""

    def __init__(
        self,
        *,
        pdfinfo: str = "pdfinfo",
        pdftotext: str = "pdftotext",
        pdffonts: str = "pdffonts",
        pdfimages: str = "pdfimages",
        pdftocairo: str = "pdftocairo",
        runner=run_command,
    ) -> None:
        self._commands = {
            "pdfinfo": pdfinfo,
            "pdftotext": pdftotext,
            "pdffonts": pdffonts,
            "pdfimages": pdfimages,
            "pdftocairo": pdftocairo,
        }
        self._runner = runner
        self._version = self._detect_version()

    @property
    def name(self) -> str:
        return "poppler"

    @property
    def version(self) -> str:
        return self._version

    def profile_document(
        self,
        pdf_path: Path,
        *,
        source_path: str,
    ) -> DocumentRawSignals:
        if pdf_path.is_symlink():
            raise PdfBackendError("symlink rejeitado no PDF de entrada")
        if not pdf_path.is_file():
            raise PdfBackendError("PDF ilegível para perfilamento")
        try:
            resolved = pdf_path.resolve(strict=True)
        except FileNotFoundError as exc:
            raise PdfBackendError("PDF ilegível para perfilamento") from exc
        if not resolved.is_file() or resolved.is_symlink():
            raise PdfBackendError("PDF ilegível para perfilamento")

        with RestrictedTempDirectory(prefix="nbr12721-pdf-") as temp:
            return self._profile_document_in_temp(
                resolved,
                source_path=source_path,
                temp=temp,
            )

    def _profile_document_in_temp(
        self,
        pdf_path: Path,
        *,
        source_path: str,
        temp: RestrictedTempDirectory,
    ) -> DocumentRawSignals:
        cwd = temp.path
        summary_text = self._pdfinfo_summary(pdf_path, cwd=cwd)
        page_count = _parse_page_count(summary_text)
        producer_raw = _parse_producer(summary_text)
        probable_origin = classify_probable_origin(producer_raw)
        box_text = self._pdfinfo_boxes(
            pdf_path,
            first_page=1,
            last_page=page_count,
            cwd=cwd,
        )
        boxes, rotations = _parse_page_boxes_and_rotations(box_text, page_count)
        image_stats_by_page = self._parse_pdfimages(
            pdf_path, cwd=cwd, page_count=page_count
        )

        pages: list[PageRawSignals] = []
        for page_number in range(1, page_count + 1):
            text_stats = self._parse_pdftotext_bbox(
                pdf_path, page_number, cwd=cwd
            )
            rendered = self._count_rendered_svg(
                pdf_path,
                page_number,
                cwd=cwd,
                temp=temp,
            )
            font_stats = self._parse_pdffonts_page(
                pdf_path, page_number, cwd=cwd
            )
            image_stats = image_stats_by_page.get(
                page_number,
                _ImageStats.empty(),
            )
            media_box, crop_box = boxes[page_number]
            pages.append(
                PageRawSignals(
                    page_number=page_number,
                    media_box=media_box,
                    crop_box=crop_box,
                    rotation=rotations[page_number],
                    native_word_count=text_stats.word_count,
                    native_codepoint_count=text_stats.codepoint_count,
                    native_word_with_bbox_count=text_stats.word_with_bbox_count,
                    font_count=font_stats.font_count,
                    embedded_font_count=font_stats.embedded_font_count,
                    subset_font_count=font_stats.subset_font_count,
                    image_count=image_stats.image_count,
                    image_width_sum=image_stats.width_sum,
                    image_height_sum=image_stats.height_sum,
                    image_pixel_sum=image_stats.pixel_sum,
                    rendered_svg=rendered,
                    probable_origin=probable_origin,
                )
            )

        return DocumentRawSignals(source_path=source_path, pages=tuple(pages))

    def _detect_version(self) -> str:
        with RestrictedTempDirectory(prefix="nbr12721-pdf-") as temp:
            result = self._runner(
                [self._commands["pdfinfo"], "-v"],
                cwd=temp.path,
            )
        if result.returncode != 0:
            raise PdfBackendError("versão Poppler ilegível")
        combined = result.stdout + result.stderr
        text = _decode_output(combined)
        match = _POPPLER_VERSION.search(text)
        if match is None:
            raise PdfBackendError("versão Poppler ilegível")
        return match.group(1)

    def _pdfinfo_summary(self, pdf_path: Path, *, cwd: Path) -> str:
        args = [self._commands["pdfinfo"], str(pdf_path)]
        result = self._runner(args, cwd=cwd)
        stdout = require_success(result, tool="pdfinfo")
        return _decode_output(stdout)

    def _pdfinfo_boxes(
        self,
        pdf_path: Path,
        *,
        first_page: int,
        last_page: int,
        cwd: Path,
    ) -> str:
        args = [
            self._commands["pdfinfo"],
            "-box",
            "-f",
            str(first_page),
            "-l",
            str(last_page),
            str(pdf_path),
        ]
        result = self._runner(args, cwd=cwd)
        stdout = require_success(result, tool="pdfinfo")
        return _decode_output(stdout)

    def _parse_pdffonts_page(
        self,
        pdf_path: Path,
        page_number: int,
        *,
        cwd: Path,
    ) -> _FontStats:
        args = [
            self._commands["pdffonts"],
            "-f",
            str(page_number),
            "-l",
            str(page_number),
            str(pdf_path),
        ]
        result = self._runner(args, cwd=cwd)
        stdout = require_success(result, tool="pdffonts")
        return _parse_pdffonts_output(_decode_output(stdout))

    def _parse_pdfimages(
        self,
        pdf_path: Path,
        *,
        cwd: Path,
        page_count: int,
    ) -> dict[int, _ImageStats]:
        result = self._runner(
            [self._commands["pdfimages"], "-list", str(pdf_path)],
            cwd=cwd,
        )
        stdout = require_success(result, tool="pdfimages")
        return _parse_pdfimages_output(
            _decode_output(stdout),
            page_count=page_count,
        )

    def _parse_pdftotext_bbox(
        self,
        pdf_path: Path,
        page_number: int,
        *,
        cwd: Path,
    ) -> _TextStats:
        args = [
            self._commands["pdftotext"],
            "-bbox-layout",
            "-f",
            str(page_number),
            "-l",
            str(page_number),
            str(pdf_path),
            "-",
        ]
        result = self._runner(args, cwd=cwd)
        stdout = require_success(result, tool="pdftotext")
        return _parse_pdftotext_bbox_output(_decode_output(stdout))

    def _count_rendered_svg(
        self,
        pdf_path: Path,
        page_number: int,
        *,
        cwd: Path,
        temp: RestrictedTempDirectory,
    ) -> RenderedSvgSignals:
        if self._runner is run_command:
            args = [
                self._commands["pdftocairo"],
                "-svg",
                "-f",
                str(page_number),
                "-l",
                str(page_number),
                str(pdf_path),
                "-",
            ]
            return _stream_rendered_svg_counts(
                args,
                timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
                max_stream_bytes=512 * 1024 * 1024,
                cwd=cwd,
            )
        args = [
            self._commands["pdftocairo"],
            "-svg",
            "-f",
            str(page_number),
            "-l",
            str(page_number),
            str(pdf_path),
            "-",
        ]
        result = self._runner(args, cwd=cwd)
        stdout = require_success(result, tool="pdftocairo")
        return _count_rendered_svg_from_text(_decode_output(stdout))


def _decode_output(data: bytes) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PdfParseError("encoding inválido na saída Poppler") from exc


def _parse_decimal(token: str, *, context: str) -> Decimal:
    if _DECIMAL_TOKEN.fullmatch(token) is None:
        raise PdfParseError(f"{context}: decimal inválido")
    try:
        return Decimal(token)
    except InvalidOperation as exc:
        raise PdfParseError(f"{context}: decimal inválido") from exc


def _parse_page_count(info_text: str) -> int:
    counts: list[int] = []
    for line in info_text.splitlines():
        match = _PAGES_LINE.match(line.strip())
        if match:
            count = int(match.group(1))
            if count < 1:
                raise PdfParseError("contagem de páginas inválida")
            counts.append(count)
    if not counts:
        raise PdfParseError("contagem de páginas ausente")
    if len(counts) > 1:
        # Duplicata (mesmo valor ou conflito) não é resumo confiável.
        raise PdfParseError("contagem de páginas duplicada")
    return counts[0]


def _parse_producer(info_text: str) -> str | None:
    for line in info_text.splitlines():
        match = _PRODUCER_LINE.match(line)
        if match:
            return match.group(1)
    return None


def _parse_page_boxes_and_rotations(
    info_text: str,
    page_count: int,
) -> tuple[dict[int, tuple[PageBox, PageBox]], dict[int, int]]:
    media: dict[int, PageBox] = {}
    crop: dict[int, PageBox] = {}
    rotations: dict[int, int] = {}
    doc_media: PageBox | None = None
    doc_crop: PageBox | None = None
    doc_rotation: int | None = None
    for line in info_text.splitlines():
        stripped = line.strip()
        box_match = _PAGE_BOX_LINE.match(stripped)
        if box_match:
            page_number = int(box_match.group(1))
            if page_number < 1 or page_number > page_count:
                raise PdfParseError("página fora do intervalo em pdfinfo")
            box_kind = box_match.group(2)
            coords = [
                _parse_decimal(token, context=box_kind)
                for token in box_match.groups()[2:]
            ]
            try:
                box = PageBox.from_coords(*coords)
            except ValueError as exc:
                raise PdfParseError(f"{box_kind} inválida") from exc
            if box_kind == "MediaBox":
                if page_number in media:
                    raise PdfParseError("media box duplicada")
                media[page_number] = box
            else:
                if page_number in crop:
                    raise PdfParseError("crop box duplicada")
                crop[page_number] = box
            continue
        doc_box_match = _DOC_BOX_LINE.match(stripped)
        if doc_box_match:
            box_kind = doc_box_match.group(1)
            coords = [
                _parse_decimal(token, context=box_kind)
                for token in doc_box_match.groups()[1:]
            ]
            try:
                box = PageBox.from_coords(*coords)
            except ValueError as exc:
                raise PdfParseError(f"{box_kind} inválida") from exc
            if box_kind == "MediaBox":
                if doc_media is not None:
                    raise PdfParseError("media box duplicada")
                doc_media = box
            else:
                if doc_crop is not None:
                    raise PdfParseError("crop box duplicada")
                doc_crop = box
            continue
        rot_match = _PAGE_ROT_LINE.match(stripped)
        if rot_match:
            page_number = int(rot_match.group(1))
            if page_number < 1 or page_number > page_count:
                raise PdfParseError("página fora do intervalo em pdfinfo")
            rotation = int(rot_match.group(2))
            if rotation not in (0, 90, 180, 270):
                raise PdfParseError("rotação inválida")
            if page_number in rotations:
                raise PdfParseError("rotação duplicada")
            rotations[page_number] = rotation
            continue
        doc_rot_match = _DOC_ROT_LINE.match(stripped)
        if doc_rot_match:
            rotation = int(doc_rot_match.group(1))
            if rotation not in (0, 90, 180, 270):
                raise PdfParseError("rotação inválida")
            if doc_rotation is not None:
                raise PdfParseError("rotação duplicada")
            doc_rotation = rotation

    if page_count == 1 and doc_media is not None and doc_crop is not None:
        media.setdefault(1, doc_media)
        crop.setdefault(1, doc_crop)
        if doc_rotation is not None:
            rotations.setdefault(1, doc_rotation)

    boxes: dict[int, tuple[PageBox, PageBox]] = {}
    for page_number in range(1, page_count + 1):
        if page_number not in media or page_number not in crop:
            raise PdfParseError("media/crop box ausente")
        if page_number not in rotations:
            raise PdfParseError("rotação ausente")
        boxes[page_number] = (media[page_number], crop[page_number])
    return boxes, rotations


class _TextStats:
    __slots__ = ("word_count", "codepoint_count", "word_with_bbox_count")

    def __init__(
        self,
        *,
        word_count: int,
        codepoint_count: int,
        word_with_bbox_count: int,
    ) -> None:
        self.word_count = word_count
        self.codepoint_count = codepoint_count
        self.word_with_bbox_count = word_with_bbox_count


_WORD_TAG = re.compile(
    r'<word\b([^>]*?)>(.*?)</word>',
    re.DOTALL,
)
_BBOX_ATTRS = ("xMin", "yMin", "xMax", "yMax")
_INCOMPLETE_OPEN_TAG = re.compile(
    r"<(?:word|path|line|rect|polyline|polygon|circle|ellipse|svg|doc|page|html|body)\b[^>]*$"
    r"|<(?:word|path|line|rect|polyline|polygon|circle|ellipse|doc|page)\b(?![^>]*>)",
    re.IGNORECASE | re.DOTALL,
)
_PDFTOTXT_OPEN_PAGE = re.compile(r"<page\b", re.IGNORECASE)
_PDFTOTXT_CLOSE_PAGE = re.compile(r"</page>", re.IGNORECASE)
_PDFTOTXT_OPEN_DOC = re.compile(r"<doc\b", re.IGNORECASE)
_PDFTOTXT_CLOSE_DOC = re.compile(r"</doc>", re.IGNORECASE)


def _assert_no_incomplete_markup(text: str, *, context: str) -> None:
    if _INCOMPLETE_OPEN_TAG.search(text):
        raise PdfParseError(f"{context} malformado")


def _assert_pdftotext_structure(text: str) -> None:
    stripped = text.strip()
    if not stripped:
        raise PdfParseError("pdftotext output malformado")
    lower = stripped.lower()
    # Envelope HTML externo completo: truncar logo após </doc> (sem </body></html>)
    # ou combinar múltiplas <page> de um pedido de página única falha fechado.
    for token in (
        "<html",
        "</html>",
        "<body",
        "</body>",
        "<doc",
        "</doc>",
        "<page",
        "</page>",
    ):
        if token not in lower:
            raise PdfParseError("pdftotext output malformado")
    if (
        len(_PDFTOTXT_OPEN_PAGE.findall(lower)) != 1
        or len(_PDFTOTXT_CLOSE_PAGE.findall(lower)) != 1
        or len(_PDFTOTXT_OPEN_DOC.findall(lower)) != 1
        or len(_PDFTOTXT_CLOSE_DOC.findall(lower)) != 1
    ):
        raise PdfParseError("pdftotext output malformado")
    html_open = lower.find("<html")
    body_open = lower.find("<body")
    doc_open = lower.find("<doc")
    page_open = lower.find("<page")
    page_close = lower.find("</page>")
    doc_close = lower.find("</doc>")
    body_close = lower.find("</body>")
    html_close = lower.find("</html>")
    if not (
        html_open
        < body_open
        < doc_open
        < page_open
        < page_close
        < doc_close
        < body_close
        < html_close
    ):
        raise PdfParseError("pdftotext output malformado")
    trailing = stripped[html_close + len("</html>") :].strip()
    if trailing:
        raise PdfParseError("pdftotext output malformado")
    pos = 0
    while True:
        index = lower.find("<word", pos)
        if index < 0:
            break
        end_tag = lower.find("</word>", index)
        if end_tag < 0:
            raise PdfParseError("pdftotext output malformado")
        pos = end_tag + len("</word>")
    _assert_no_incomplete_markup(stripped, context="pdftotext output")


def _parse_pdftotext_bbox_output(text: str) -> _TextStats:
    _assert_pdftotext_structure(text)
    word_count = 0
    codepoint_count = 0
    word_with_bbox_count = 0
    for match in _WORD_TAG.finditer(text):
        word_count += 1
        content = html.unescape(match.group(2))
        if content:
            codepoint_count += len(content)
        attrs = match.group(1)
        if all(f'{key}="' in attrs for key in _BBOX_ATTRS):
            try:
                for key in _BBOX_ATTRS:
                    token_match = re.search(rf'{key}="([^"]+)"', attrs)
                    if token_match is None:
                        raise PdfParseError("word bbox incompleto")
                    _parse_decimal(token_match.group(1), context=f"word.{key}")
                word_with_bbox_count += 1
            except PdfParseError:
                pass

    return _TextStats(
        word_count=word_count,
        codepoint_count=codepoint_count,
        word_with_bbox_count=word_with_bbox_count,
    )


class _FontStats:
    __slots__ = ("font_count", "embedded_font_count", "subset_font_count")

    def __init__(
        self,
        *,
        font_count: int,
        embedded_font_count: int,
        subset_font_count: int,
    ) -> None:
        self.font_count = font_count
        self.embedded_font_count = embedded_font_count
        self.subset_font_count = subset_font_count


_YES_NO = frozenset({"yes", "no"})
_PDFFONTS_SEPARATOR = re.compile(r"^[\s\-]+$")


def _parse_pdffonts_output(text: str) -> _FontStats:
    """Parseia pdffonts com colunas de largura variável (type/encoding multiword).

    ``emb``/``sub``/``uni`` e o object ID ficam à direita; tipos como
    ``Type 1`` ou ``CID TrueType`` não podem ser lidos por índices fixos de
    ``str.split()``.
    """
    lines = [line.rstrip() for line in text.splitlines()]
    data_started = False
    saw_separator = False
    font_count = 0
    embedded_font_count = 0
    subset_font_count = 0
    for line in lines:
        if not data_started:
            if line.startswith("name ") and "emb" in line and "sub" in line:
                data_started = True
            continue
        stripped = line.strip()
        if stripped == "":
            continue
        if _PDFFONTS_SEPARATOR.fullmatch(stripped):
            saw_separator = True
            continue
        parts = stripped.split()
        # name + type + encoding + emb + sub + uni + object_num + object_gen
        if len(parts) < 8:
            raise PdfParseError("pdffonts output inesperado")
        uni = parts[-3].lower()
        sub = parts[-4].lower()
        emb = parts[-5].lower()
        if emb not in _YES_NO or sub not in _YES_NO or uni not in _YES_NO:
            raise PdfParseError("pdffonts output inesperado")
        try:
            int(parts[-2])
            int(parts[-1])
        except ValueError as exc:
            raise PdfParseError("pdffonts output inesperado") from exc
        # Após remover as 5 colunas à direita, restam name/type/encoding.
        if len(parts) - 5 < 3:
            raise PdfParseError("pdffonts output inesperado")
        font_count += 1
        if emb == "yes":
            embedded_font_count += 1
        if sub == "yes":
            subset_font_count += 1
    if not data_started or not saw_separator:
        raise PdfParseError("pdffonts output malformado")
    return _FontStats(
        font_count=font_count,
        embedded_font_count=embedded_font_count,
        subset_font_count=subset_font_count,
    )


class _ImageStats:
    __slots__ = ("image_count", "width_sum", "height_sum", "pixel_sum")

    def __init__(
        self,
        *,
        image_count: int,
        width_sum: int,
        height_sum: int,
        pixel_sum: int,
    ) -> None:
        self.image_count = image_count
        self.width_sum = width_sum
        self.height_sum = height_sum
        self.pixel_sum = pixel_sum

    @classmethod
    def empty(cls) -> _ImageStats:
        return cls(image_count=0, width_sum=0, height_sum=0, pixel_sum=0)


def _parse_pdfimages_output(
    text: str,
    *,
    page_count: int | None = None,
) -> dict[int, _ImageStats]:
    by_page: dict[int, _ImageStats] = {}
    counts: dict[int, int] = {}
    width_sums: dict[int, int] = {}
    height_sums: dict[int, int] = {}
    pixel_sums: dict[int, int] = {}
    saw_header = False
    saw_separator = False
    if not text.strip():
        raise PdfParseError("pdfimages output malformado")
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "":
            continue
        if stripped.startswith("page ") and "width" in stripped.lower():
            saw_header = True
            continue
        if set(stripped) <= {"-", " "} and len(stripped) >= 4:
            saw_separator = True
            continue
        parts = stripped.split()
        # page num type width height color comp bpc enc interp object gen …
        # Truncar após bpc (8 tokens) ou sem object ID não é métrica válida.
        if len(parts) < 12 or not parts[0].isdigit():
            raise PdfParseError("pdfimages output inesperado")
        page_number = int(parts[0])
        if page_number < 1:
            raise PdfParseError("pdfimages output inesperado")
        if page_count is not None and page_number > page_count:
            raise PdfParseError("pdfimages output inesperado")
        try:
            width = int(parts[3])
            height = int(parts[4])
            int(parts[6])  # comp
            int(parts[7])  # bpc
            enc = parts[8]
            interp = parts[9].lower()
            int(parts[10])  # object
            int(parts[11])  # generation
        except (ValueError, IndexError) as exc:
            raise PdfParseError("pdfimages output inesperado") from exc
        if not enc or interp not in {"yes", "no"}:
            raise PdfParseError("pdfimages output inesperado")
        if width < 0 or height < 0:
            raise PdfParseError("pdfimages output inesperado")
        counts[page_number] = counts.get(page_number, 0) + 1
        width_sums[page_number] = width_sums.get(page_number, 0) + width
        height_sums[page_number] = height_sums.get(page_number, 0) + height
        pixel_sums[page_number] = pixel_sums.get(page_number, 0) + (width * height)
    if not saw_header or not saw_separator:
        raise PdfParseError("pdfimages output malformado")
    for page_number, image_count in counts.items():
        by_page[page_number] = _ImageStats(
            image_count=image_count,
            width_sum=width_sums[page_number],
            height_sum=height_sums[page_number],
            pixel_sum=pixel_sums[page_number],
        )
    return by_page


_SVG_TAGS = (
    ("<path", "path_count"),
    ("<line", "line_count"),
    ("<rect", "rect_count"),
    ("<polyline", "polyline_count"),
    ("<polygon", "polygon_count"),
    ("<circle", "circle_count"),
    ("<ellipse", "ellipse_count"),
)
_SVG_TAG_FIELD = {
    "path": "path_count",
    "line": "line_count",
    "rect": "rect_count",
    "polyline": "polyline_count",
    "polygon": "polygon_count",
    "circle": "circle_count",
    "ellipse": "ellipse_count",
}
_SVG_OPEN_TAG = re.compile(
    r"<(polyline|polygon|ellipse|circle|rect|path|line)\b"
    r'(?:[^>"\']|"[^"]*"|\'[^\']*\')*\/?>',
    re.IGNORECASE,
)


def _assert_svg_structure(text: str) -> None:
    stripped = text.strip()
    if not stripped:
        return
    lower = stripped.lower()
    if "<svg" not in lower:
        raise PdfParseError("SVG renderizado malformado")
    close_idx = lower.rfind("</svg>")
    if close_idx < 0:
        raise PdfParseError("SVG renderizado malformado")
    trailing = stripped[close_idx + len("</svg>") :].strip()
    if trailing:
        raise PdfParseError("SVG renderizado malformado")
    _assert_no_incomplete_markup(stripped, context="SVG renderizado")


def _reject_svg_trailing_garbage(text: str, state: dict[str, bool]) -> None:
    """Rejeita conteúdo após </svg>; atualiza bounds open/close."""
    if not text:
        return
    if state["close"]:
        if text.strip():
            raise PdfParseError("SVG renderizado malformado")
        return
    lower = text.lower()
    if "<svg" in lower:
        state["open"] = True
    close_idx = lower.find("</svg>")
    if close_idx < 0:
        return
    state["close"] = True
    if text[close_idx + len("</svg>") :].strip():
        raise PdfParseError("SVG renderizado malformado")


def _count_rendered_svg_from_text(text: str) -> RenderedSvgSignals:
    if text.strip():
        _assert_svg_structure(text)
    return _count_tags_without_overlap(text)


def _count_tags_without_overlap(text: str) -> RenderedSvgSignals:
    counts = {name: 0 for _tag, name in _SVG_TAGS}
    _accumulate_svg_tag_counts(counts, text)
    return RenderedSvgSignals(
        path_count=counts["path_count"],
        line_count=counts["line_count"],
        rect_count=counts["rect_count"],
        polyline_count=counts["polyline_count"],
        polygon_count=counts["polygon_count"],
        circle_count=counts["circle_count"],
        ellipse_count=counts["ellipse_count"],
    )


def _decode_utf8_stream_chunk(
    byte_carry: bytes,
    chunk: bytes,
) -> tuple[str, bytes]:
    """Decodifica UTF-8 estrito preservando sequência incompleta no fim."""
    data = byte_carry + chunk
    if not data:
        return "", b""
    try:
        return data.decode("utf-8"), b""
    except UnicodeDecodeError as exc:
        if exc.start > 0:
            text = data[: exc.start].decode("utf-8")
            remainder = data[exc.start :]
            if len(remainder) > 4:
                raise PdfParseError("encoding inválido na saída Poppler") from exc
            return text, remainder
        if len(data) > 4:
            raise PdfParseError("encoding inválido na saída Poppler") from exc
        return "", data


def _accumulate_svg_tag_counts(counts: dict[str, int], text: str) -> None:
    """Conta tags SVG geométricas completas em ``text``."""
    if not text:
        return
    for match in _SVG_OPEN_TAG.finditer(text):
        tag_name = match.group(1).lower()
        field = _SVG_TAG_FIELD.get(tag_name)
        if field is not None:
            counts[field] += 1


def _closed_markup_prefix_length(text: str) -> int:
    """Comprimento do prefixo sem tag/aspas abertas (retém o restante)."""
    in_tag = False
    quote: str | None = None
    tag_start = 0
    index = 0
    length = len(text)
    while index < length:
        char = text[index]
        if in_tag:
            if quote is not None:
                if char == quote:
                    quote = None
            elif char in "\"'":
                quote = char
            elif char == ">":
                in_tag = False
            index += 1
            continue
        if char == "<":
            in_tag = True
            tag_start = index
        index += 1
    if in_tag:
        return tag_start
    return length


def _update_svg_document_bounds(text: str, state: dict[str, bool]) -> None:
    _reject_svg_trailing_garbage(text, state)


def _kill_process(proc: subprocess.Popen[bytes]) -> None:
    if proc.poll() is not None:
        return
    try:
        proc.kill()
    except OSError:
        pass
    try:
        proc.wait(timeout=5)
    except Exception:
        try:
            proc.poll()
        except Exception:
            pass


def _stream_rendered_svg_counts(
    args: Sequence[str],
    *,
    timeout_seconds: int,
    max_stream_bytes: int,
    max_stderr_bytes: int = DEFAULT_MAX_STDERR_BYTES,
    cwd: Path | None = None,
) -> RenderedSvgSignals:
    """Conta elementos SVG via stdout com timeout, UTF-8 estrito e sem overlap."""
    counts = {name: 0 for _tag, name in _SVG_TAGS}
    text_carry = ""
    byte_carry = b""
    total_read = 0
    svg_bounds = {"open": False, "close": False}
    deadline = time.monotonic() + timeout_seconds
    try:
        proc = subprocess.Popen(
            list(args),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=minimal_subprocess_env(),
            cwd=str(cwd) if cwd is not None else None,
            shell=False,
        )
    except FileNotFoundError as exc:
        raise PdfBackendError("comando Poppler ausente") from exc

    try:
        assert proc.stdout is not None
        assert proc.stderr is not None
        os.set_blocking(proc.stdout.fileno(), False)
        os.set_blocking(proc.stderr.fileno(), False)
        stderr_size = 0
        stdout_closed = False
        stderr_closed = False
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                _kill_process(proc)
                raise PdfBackendError("timeout do subprocesso Poppler")
            if stdout_closed and stderr_closed and proc.poll() is not None:
                break
            wait_fds: list[object] = []
            if not stdout_closed:
                wait_fds.append(proc.stdout)
            if not stderr_closed:
                wait_fds.append(proc.stderr)
            if not wait_fds:
                try:
                    proc.wait(timeout=remaining)
                except subprocess.TimeoutExpired as exc:
                    _kill_process(proc)
                    raise PdfBackendError(
                        "timeout do subprocesso Poppler"
                    ) from exc
                break
            ready, _, _ = select.select(wait_fds, [], [], remaining)
            if not ready:
                _kill_process(proc)
                raise PdfBackendError("timeout do subprocesso Poppler")
            if proc.stderr in ready:
                chunk = proc.stderr.read(65536)
                if chunk is None:
                    pass
                elif chunk == b"":
                    stderr_closed = True
                else:
                    stderr_size += len(chunk)
                    if stderr_size > max_stderr_bytes:
                        _kill_process(proc)
                        raise PdfBackendError(
                            "stderr acima do limite configurado"
                        )
            if proc.stdout in ready:
                chunk = proc.stdout.read(65536)
                if chunk is None:
                    pass
                elif chunk == b"":
                    stdout_closed = True
                else:
                    total_read += len(chunk)
                    if total_read > max_stream_bytes:
                        _kill_process(proc)
                        raise PdfBackendError(
                            "stdout acima do limite configurado"
                        )
                    text, byte_carry = _decode_utf8_stream_chunk(
                        byte_carry, chunk
                    )
                    if text:
                        combined = text_carry + text
                        split_at = _closed_markup_prefix_length(combined)
                        prefix = combined[:split_at]
                        text_carry = combined[split_at:]
                        _accumulate_svg_tag_counts(counts, prefix)
                        _reject_svg_trailing_garbage(prefix, svg_bounds)
        if byte_carry:
            _kill_process(proc)
            raise PdfParseError("encoding inválido na saída Poppler")
        if text_carry:
            if _closed_markup_prefix_length(text_carry) < len(text_carry):
                _kill_process(proc)
                raise PdfParseError("SVG renderizado malformado")
            _accumulate_svg_tag_counts(counts, text_carry)
            _reject_svg_trailing_garbage(text_carry, svg_bounds)
        if proc.returncode is None:
            try:
                proc.wait(timeout=max(0.0, deadline - time.monotonic()))
            except subprocess.TimeoutExpired as exc:
                _kill_process(proc)
                raise PdfBackendError("timeout do subprocesso Poppler") from exc
        if proc.returncode != 0:
            raise PdfBackendError("pdftocairo retornou código não zero")
        if total_read == 0 or not svg_bounds["open"] or not svg_bounds["close"]:
            raise PdfParseError("SVG renderizado malformado")
    except BaseException:
        _kill_process(proc)
        raise
    finally:
        if proc.stdout is not None:
            proc.stdout.close()
        if proc.stderr is not None:
            proc.stderr.close()
        if proc.poll() is None:
            _kill_process(proc)
        elif proc.returncode is None:
            try:
                proc.wait(timeout=max(0.0, deadline - time.monotonic()))
            except Exception:
                _kill_process(proc)

    return RenderedSvgSignals(
        path_count=counts["path_count"],
        line_count=counts["line_count"],
        rect_count=counts["rect_count"],
        polyline_count=counts["polyline_count"],
        polygon_count=counts["polygon_count"],
        circle_count=counts["circle_count"],
        ellipse_count=counts["ellipse_count"],
    )


def _resolve_svg_output(output_prefix: Path) -> Path:
    candidates = (
        Path(f"{output_prefix}.svg"),
        Path(str(output_prefix)),
        Path(f"{output_prefix}-1.svg"),
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise PdfBackendError("saída SVG temporária ausente")


def _count_rendered_svg_elements(path: Path) -> RenderedSvgSignals:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PdfBackendError("falha ao ler SVG renderizado") from exc
    except UnicodeDecodeError as exc:
        raise PdfParseError("encoding inválido na saída Poppler") from exc
    if path.stat().st_size > 0:
        _assert_svg_structure(text)
    return _count_tags_without_overlap(text)


def fake_poppler_runner(responses: dict[tuple[str, ...], CommandResult]):
    """Factory de runner fake para testes (mapeia argv → resultado)."""

    def _runner(args: Sequence[str], **kwargs) -> CommandResult:
        key = tuple(args)
        if key not in responses:
            raise PdfBackendError("comando Poppler inesperado em fake runner")
        return responses[key]

    return _runner
