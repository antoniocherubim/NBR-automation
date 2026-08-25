"""Testes do profiler PDF page-profiles v1 (sintéticos e fake backend)."""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from decimal import Decimal
from pathlib import Path
from unittest import mock

from nbr12721.artifacts.envelope import content_sha256_hex, parse_envelope
from nbr12721.artifacts.models import SourceRef
from nbr12721.pdf.backend import (
    PopplerBackend,
    _count_rendered_svg_from_text,
    _parse_page_boxes_and_rotations,
    _parse_page_count,
    _parse_pdffonts_output,
    _parse_pdfimages_output,
    _parse_pdftotext_bbox_output,
    _parse_producer,
    _stream_rendered_svg_counts,
    fake_poppler_runner,
)
from nbr12721.pdf.config import (
    DEFAULT_THRESHOLDS,
    ProfilerThresholdsV1,
)
from nbr12721.pdf.errors import (
    PdfBackendError,
    PdfParseError,
    PdfProfilerError,
    PdfSchemaError,
)
from nbr12721.pdf.models import (
    DocumentRawSignals,
    PageBox,
    PageRawSignals,
    RenderedSvgSignals,
    derive_flags,
)
from nbr12721.pdf.origin import classify_probable_origin
from nbr12721.pdf.profiler import (
    build_page_profiles_envelope,
    profile_verified_sources,
    select_ay0410_pdf_sources,
    serialize_page_profiles,
)
from nbr12721.pdf.schema import validate_page_profiles_payload
from nbr12721.pdf.subprocess_runner import (
    CommandResult,
    RestrictedTempDirectory,
    require_success,
    run_command,
)
from nbr12721.sources.artifact import SourceArtifact
from tests.page_profiles_schema_support import (
    PageProfilesSchemaError,
    validate_page_profiles_against_json_schema,
)
from tests.pdf_synthetic import (
    write_minimal_hybrid_pdf,
    write_minimal_raster_pdf,
    write_minimal_text_pdf,
    write_minimal_vector_pdf,
    write_multipage_mixed_pdf,
)

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_VERSIONED_ARTIFACT = _PROJECT_ROOT / "profiles" / "page-profiles.json"
_CLI = _PROJECT_ROOT / "scripts" / "pdf" / "profile-ay0410.py"

_SAMPLE_INFO = """\
Title:           Demo
Producer:        pdfplot11.hdi 11.1.18.0
Pages:           1
"""

_SAMPLE_INFO_BOXES = """\
Page    1 MediaBox:            0.00     0.00   200.00   100.00
Page    1 CropBox:             0.00     0.00   200.00   100.00
Page    1 rot:                 0
"""

_SAMPLE_BBOX = """\
<!DOCTYPE html><html><body><doc><page width="200" height="100">
<word xMin="1.0" yMin="2.0" xMax="3.0" yMax="4.0">Hello</word>
<word xMin="5.0" yMin="2.0" xMax="9.0" yMax="4.0">-03&apos;00&apos;</word>
</page></doc></body></html>
"""

_SAMPLE_FONTS = """\
name                                 type              encoding         emb sub uni object ID
------------------------------------ ----------------- ---------------- --- --- --- ---------
Helvetica                            Type 1            Custom           yes no  no       6  0
ArialMT                              CID TrueType      Identity-H       yes no  no     232  0
Swiss721BT-BlackExtended             TrueType          WinAnsi          no  no  no     235  0
"""

_SAMPLE_IMAGES_PAGE_ZERO = """\
page   num  type   width height color comp bpc  enc interp  object ID x-ppi y-ppi size ratio
--------------------------------------------------------------------------------------------
   0     0 image     100   100  rgb     3   8  jpeg   no         1  0   100   100 1000B 1.0%
"""

_SAMPLE_SVG = (
    '<?xml version="1.0"?><svg><path d="M0 0"/><path d="M1 1"/>'
    '<rect x="0" y="0" width="1" height="1"/></svg>'
)

_EMPTY_IMAGES = """\
page   num  type   width height color comp bpc  enc interp  object ID x-ppi y-ppi size ratio
--------------------------------------------------------------------------------------------
"""


def _expected_sources(payload: dict) -> set[str]:
    return {doc["source_path"] for doc in payload["documents"]}


def _fake_backend(responses: dict[tuple[str, ...], CommandResult]) -> PopplerBackend:
    version_result = CommandResult(
        returncode=0,
        stdout=b"",
        stderr=b"pdfinfo version 24.02.0\n",
    )
    merged = dict(responses)
    merged.setdefault(("pdfinfo", "-v"), version_result)
    return PopplerBackend(runner=fake_poppler_runner(merged))


def _minimal_valid_payload(**overrides: object) -> dict:
    box = {
        "x0": "0",
        "y0": "0",
        "x1": "200",
        "y1": "100",
        "width": "200",
        "height": "100",
    }
    page = {
        "page_number": 1,
        "media_box": dict(box),
        "crop_box": dict(box),
        "rotation": 0,
        "native_word_count": 1,
        "native_codepoint_count": 5,
        "native_word_with_bbox_count": 1,
        "font_count": 1,
        "embedded_font_count": 0,
        "subset_font_count": 0,
        "image_count": 0,
        "image_width_sum": 0,
        "image_height_sum": 0,
        "image_pixel_sum": 0,
        "rendered_svg_path_count": 0,
        "rendered_svg_line_count": 0,
        "rendered_svg_rect_count": 0,
        "rendered_svg_polyline_count": 0,
        "rendered_svg_polygon_count": 0,
        "rendered_svg_circle_count": 0,
        "rendered_svg_ellipse_count": 0,
        "probable_origin": "pdfium",
        "flags": ["low_native_text"],
    }
    payload: dict[str, object] = {
        "payload_version": "1.0.0",
        "coordinate_system": {
            "unit": "pt",
            "origin": "bottom-left",
            "x_axis": "right",
            "y_axis": "up",
        },
        "thresholds": DEFAULT_THRESHOLDS.to_dict(),
        "documents": [
            {
                "source_path": "inputs/projetos_modelo/AY0410/demo.pdf",
                "pages": [page],
            }
        ],
    }
    payload.update(overrides)
    return payload


class OriginTests(unittest.TestCase):
    def test_origin_vocabulary(self) -> None:
        self.assertEqual(classify_probable_origin("pdfplot11.hdi"), "autocad_pdfplot")
        self.assertEqual(classify_probable_origin("AutoCAD 2014"), "autocad_pdfplot")
        self.assertEqual(classify_probable_origin("PDFium"), "pdfium")
        self.assertEqual(classify_probable_origin("LibreOffice 7"), "other")
        self.assertEqual(classify_probable_origin(None), "absent")
        self.assertEqual(classify_probable_origin(""), "unknown")
        self.assertEqual(classify_probable_origin("   "), "unknown")
        self.assertEqual(classify_probable_origin("\x00bad"), "unknown")
        self.assertIsNone(_parse_producer("Pages:           1\n"))
        self.assertEqual(_parse_producer("Producer:\nPages: 1\n"), "")
        self.assertEqual(_parse_producer("Producer:        \nPages: 1\n").strip(), "")
        self.assertEqual(
            classify_probable_origin(_parse_producer("Producer:\n")),
            "unknown",
        )


class FlagThresholdTests(unittest.TestCase):
    def _page(self, *, words: int, paths: int, images: int) -> PageRawSignals:
        box = PageBox.from_coords(
            Decimal("0"), Decimal("0"), Decimal("100"), Decimal("100")
        )
        return PageRawSignals(
            page_number=1,
            media_box=box,
            crop_box=box,
            rotation=0,
            native_word_count=words,
            native_codepoint_count=words,
            native_word_with_bbox_count=words,
            font_count=1,
            embedded_font_count=0,
            subset_font_count=0,
            image_count=images,
            image_width_sum=images,
            image_height_sum=images,
            image_pixel_sum=images,
            rendered_svg=RenderedSvgSignals(
                path_count=paths,
                line_count=0,
                rect_count=0,
                polyline_count=0,
                polygon_count=0,
                circle_count=0,
                ellipse_count=0,
            ),
            probable_origin="autocad_pdfplot",
        )

    def test_threshold_boundaries(self) -> None:
        thresholds = ProfilerThresholdsV1(
            low_native_text_word_count=150,
            high_rendered_svg_path_count=10000,
        )
        below = self._page(words=149, paths=9999, images=0)
        at_low = self._page(words=150, paths=9999, images=0)
        above_low = self._page(words=151, paths=9999, images=0)
        below_high = self._page(words=200, paths=9999, images=0)
        at_high = self._page(words=200, paths=10000, images=0)
        above_high = self._page(words=200, paths=10001, images=0)
        self.assertIn(
            "low_native_text",
            derive_flags(
                below,
                low_native_text_word_count=thresholds.low_native_text_word_count,
                high_rendered_svg_path_count=thresholds.high_rendered_svg_path_count,
            ),
        )
        self.assertIn(
            "low_native_text",
            derive_flags(
                at_low,
                low_native_text_word_count=thresholds.low_native_text_word_count,
                high_rendered_svg_path_count=thresholds.high_rendered_svg_path_count,
            ),
        )
        self.assertNotIn(
            "low_native_text",
            derive_flags(
                above_low,
                low_native_text_word_count=thresholds.low_native_text_word_count,
                high_rendered_svg_path_count=thresholds.high_rendered_svg_path_count,
            ),
        )
        self.assertNotIn(
            "high_rendered_svg_complexity",
            derive_flags(
                below_high,
                low_native_text_word_count=thresholds.low_native_text_word_count,
                high_rendered_svg_path_count=thresholds.high_rendered_svg_path_count,
            ),
        )
        self.assertIn(
            "high_rendered_svg_complexity",
            derive_flags(
                at_high,
                low_native_text_word_count=thresholds.low_native_text_word_count,
                high_rendered_svg_path_count=thresholds.high_rendered_svg_path_count,
            ),
        )
        self.assertIn(
            "high_rendered_svg_complexity",
            derive_flags(
                above_high,
                low_native_text_word_count=thresholds.low_native_text_word_count,
                high_rendered_svg_path_count=thresholds.high_rendered_svg_path_count,
            ),
        )

    def test_overlapping_flags_for_parking_like_page(self) -> None:
        page = self._page(words=100, paths=20000, images=0)
        flags = derive_flags(
            page,
            low_native_text_word_count=DEFAULT_THRESHOLDS.low_native_text_word_count,
            high_rendered_svg_path_count=DEFAULT_THRESHOLDS.high_rendered_svg_path_count,
        )
        self.assertEqual(
            set(flags),
            {"low_native_text", "high_rendered_svg_complexity"},
        )
        self.assertNotIn("is_scan", flags)


class ParserUnitTests(unittest.TestCase):
    def test_pdffonts_spaced_type_and_separator(self) -> None:
        stats = _parse_pdffonts_output(_SAMPLE_FONTS)
        self.assertEqual(stats.font_count, 3)
        self.assertEqual(stats.embedded_font_count, 2)
        self.assertEqual(stats.subset_font_count, 0)

    def test_pdffonts_malformed_fails_closed(self) -> None:
        with self.assertRaises(PdfParseError):
            _parse_pdffonts_output("not a pdffonts header\ngarbage\n")

    def test_pdffonts_header_only_fails_closed(self) -> None:
        header_only = (
            "name                                 type              encoding         "
            "emb sub uni object ID\n"
        )
        with self.assertRaises(PdfParseError):
            _parse_pdffonts_output(header_only)

    def test_pdffonts_truncated_row_fails_closed(self) -> None:
        truncated = (
            "name                                 type              encoding         "
            "emb sub uni object ID\n"
            "------------------------------------ ----------------- ---------------- "
            "--- --- --- ---------\n"
            "Helvetica                            Type 1\n"
        )
        with self.assertRaises(PdfParseError):
            _parse_pdffonts_output(truncated)

    def test_pdftotext_decodes_xml_entities(self) -> None:
        stats = _parse_pdftotext_bbox_output(_SAMPLE_BBOX)
        self.assertEqual(stats.word_count, 2)
        # Hello (5) + -03'00' (7) após unescape de &apos;
        self.assertEqual(stats.codepoint_count, 12)
        self.assertEqual(stats.word_with_bbox_count, 2)

    def test_pdftotext_arbitrary_output_fails_closed(self) -> None:
        with self.assertRaises(PdfParseError):
            _parse_pdftotext_bbox_output("garbage without bbox layout")

    def test_pdftotext_truncated_word_fails_closed(self) -> None:
        truncated = (
            '<!DOCTYPE html><html><body><doc><page width="200" height="100">'
            '<word xMin="1.0" yMin="2.0" xMax="3.0" yMax="4.0">Hello</word>'
            '<word xMin="5.0" yMin="2.0" xMax="9.0" yMax="4.0">Wor'
        )
        with self.assertRaises(PdfParseError):
            _parse_pdftotext_bbox_output(truncated)

    def test_pdftotext_truncated_after_complete_word_fails_closed(self) -> None:
        truncated = (
            '<!DOCTYPE html><html><body><doc><page width="200" height="100">'
            '<word xMin="1.0" yMin="2.0" xMax="3.0" yMax="4.0">Hello</word>'
        )
        with self.assertRaises(PdfParseError):
            _parse_pdftotext_bbox_output(truncated)

    def test_pdftotext_truncated_ending_at_page_close_fails_closed(self) -> None:
        # Completo até </page>, mas sem </doc> — aceito incorretamente antes.
        truncated = (
            '<!DOCTYPE html><html><body><doc><page width="200" height="100">'
            '<word xMin="1.0" yMin="2.0" xMax="3.0" yMax="4.0">Hello</word>'
            "</page>"
        )
        with self.assertRaises(PdfParseError):
            _parse_pdftotext_bbox_output(truncated)

    def test_pdftotext_truncated_immediately_after_doc_close_fails_closed(self) -> None:
        # Envelope HTML incompleto: truncado logo após </doc>.
        truncated = (
            '<!DOCTYPE html><html><body><doc><page width="200" height="100">'
            '<word xMin="1.0" yMin="2.0" xMax="3.0" yMax="4.0">Hello</word>'
            "</page></doc>"
        )
        with self.assertRaises(PdfParseError):
            _parse_pdftotext_bbox_output(truncated)

    def test_pdftotext_multiple_pages_in_single_page_response_fails_closed(self) -> None:
        multi_page = (
            '<!DOCTYPE html><html><body><doc>'
            '<page width="200" height="100">'
            '<word xMin="1.0" yMin="2.0" xMax="3.0" yMax="4.0">A</word>'
            "</page>"
            '<page width="200" height="100">'
            '<word xMin="1.0" yMin="2.0" xMax="3.0" yMax="4.0">B</word>'
            "</page>"
            "</doc></body></html>"
        )
        with self.assertRaises(PdfParseError):
            _parse_pdftotext_bbox_output(multi_page)

    def test_pdffonts_row_missing_name_type_encoding_fails_closed(self) -> None:
        truncated = (
            "name                                 type              encoding         "
            "emb sub uni object ID\n"
            "------------------------------------ ----------------- ---------------- "
            "--- --- --- ---------\n"
            "yes no no  10  0\n"
        )
        with self.assertRaises(PdfParseError):
            _parse_pdffonts_output(truncated)

    def test_pdfimages_page_zero_fails_closed(self) -> None:
        with self.assertRaises(PdfParseError):
            _parse_pdfimages_output(_SAMPLE_IMAGES_PAGE_ZERO)

    def test_pdfimages_header_only_fails_closed(self) -> None:
        header_only = (
            "page   num  type   width height color comp bpc  enc interp  "
            "object ID x-ppi y-ppi size ratio\n"
        )
        with self.assertRaises(PdfParseError):
            _parse_pdfimages_output(header_only)

    def test_pdfimages_truncated_row_fails_closed(self) -> None:
        truncated = (
            "page   num  type   width height color comp bpc  enc interp  "
            "object ID x-ppi y-ppi size ratio\n"
            "--------------------------------------------------------------------------------------------\n"
            "   1     0 image\n"
        )
        with self.assertRaises(PdfParseError):
            _parse_pdfimages_output(truncated, page_count=1)

    def test_pdfimages_truncated_after_width_height_fails_closed(self) -> None:
        truncated = (
            "page   num  type   width height color comp bpc  enc interp  "
            "object ID x-ppi y-ppi size ratio\n"
            "--------------------------------------------------------------------------------------------\n"
            "   1     0 image     100    50\n"
        )
        with self.assertRaises(PdfParseError):
            _parse_pdfimages_output(truncated, page_count=1)

    def test_pdfimages_truncated_after_bpc_fails_closed(self) -> None:
        truncated = (
            "page   num  type   width height color comp bpc  enc interp  "
            "object ID x-ppi y-ppi size ratio\n"
            "--------------------------------------------------------------------------------------------\n"
            "   1     0 image     100   200  rgb     3   8\n"
        )
        with self.assertRaises(PdfParseError):
            _parse_pdfimages_output(truncated, page_count=1)

    def test_pdfinfo_duplicate_pages_summary_fails_closed(self) -> None:
        with self.assertRaises(PdfParseError):
            _parse_page_count("Pages:           1\nPages:           2\n")
        with self.assertRaises(PdfParseError):
            _parse_page_count("Pages:           1\nPages:           1\n")
        self.assertEqual(_parse_page_count("Pages:           1\n"), 1)

    def test_pdfimages_page_outside_document_range_fails_closed(self) -> None:
        listing = (
            "page   num  type   width height color comp bpc  enc interp  "
            "object ID x-ppi y-ppi size ratio\n"
            "--------------------------------------------------------------------------------------------\n"
            "   2     0 image     100   100  rgb     3   8  jpeg   no         "
            "1  0   100   100 1000B 1.0%\n"
        )
        with self.assertRaises(PdfParseError):
            _parse_pdfimages_output(listing, page_count=1)

    def test_svg_unclosed_path_not_counted(self) -> None:
        with self.assertRaises(PdfParseError):
            _count_rendered_svg_from_text('<?xml?><svg><path d="M0 0"')

    def test_svg_trailing_garbage_after_close_fails_closed(self) -> None:
        with self.assertRaises(PdfParseError):
            _count_rendered_svg_from_text(
                '<?xml?><svg><path d="M0 0"/></svg>GARBAGE'
            )

    def test_pdfinfo_duplicate_page_records_fail_closed(self) -> None:
        duplicated = (
            "Page 1 MediaBox: 0 0 612 792\n"
            "Page 1 CropBox: 0 0 612 792\n"
            "Page 1 rot: 0\n"
            "Page 1 MediaBox: 0 0 100 200\n"
            "Page 1 CropBox: 0 0 100 200\n"
            "Page 1 rot: 90\n"
        )
        with self.assertRaises(PdfParseError):
            _parse_page_boxes_and_rotations(duplicated, 1)

    def test_pdfinfo_out_of_range_page_fails_closed(self) -> None:
        out_of_range = (
            "Page 1 MediaBox: 0 0 612 792\n"
            "Page 1 CropBox: 0 0 612 792\n"
            "Page 1 rot: 0\n"
            "Page 2 MediaBox: 0 0 100 200\n"
            "Page 2 CropBox: 0 0 100 200\n"
            "Page 2 rot: 0\n"
        )
        with self.assertRaises(PdfParseError):
            _parse_page_boxes_and_rotations(out_of_range, 1)


class PopplerParserTests(unittest.TestCase):
    def test_fake_backend_profiles_document(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = Path(tmp) / "demo.pdf"
            write_minimal_text_pdf(pdf_path)
            responses = {
                ("pdfinfo", "-v"): CommandResult(
                    0, b"", b"pdfinfo version 24.02.0\n"
                ),
                ("pdfinfo", str(pdf_path)): CommandResult(
                    0, _SAMPLE_INFO.encode(), b""
                ),
                (
                    "pdfinfo",
                    "-box",
                    "-f",
                    "1",
                    "-l",
                    "1",
                    str(pdf_path),
                ): CommandResult(0, _SAMPLE_INFO_BOXES.encode(), b""),
                (
                    "pdffonts",
                    "-f",
                    "1",
                    "-l",
                    "1",
                    str(pdf_path),
                ): CommandResult(0, _SAMPLE_FONTS.encode(), b""),
                ("pdfimages", "-list", str(pdf_path)): CommandResult(
                    0, _EMPTY_IMAGES.encode(), b""
                ),
                (
                    "pdftotext",
                    "-bbox-layout",
                    "-f",
                    "1",
                    "-l",
                    "1",
                    str(pdf_path),
                    "-",
                ): CommandResult(0, _SAMPLE_BBOX.encode(), b""),
                (
                    "pdftocairo",
                    "-svg",
                    "-f",
                    "1",
                    "-l",
                    "1",
                    str(pdf_path),
                    "-",
                ): CommandResult(0, _SAMPLE_SVG.encode(), b""),
            }
            backend = PopplerBackend(runner=fake_poppler_runner(responses))
            doc = backend.profile_document(pdf_path, source_path="inputs/demo.pdf")
            page = doc.pages[0]
            self.assertEqual(page.native_word_count, 2)
            self.assertEqual(page.native_codepoint_count, 12)
            self.assertEqual(page.font_count, 3)
            self.assertEqual(page.embedded_font_count, 2)
            self.assertEqual(page.rendered_svg.path_count, 2)
            self.assertEqual(page.probable_origin, "autocad_pdfplot")

    def test_missing_command_fail_closed(self) -> None:
        def failing_runner(args, **kwargs):
            if args[-1:] == ("-v",) or (len(args) >= 2 and args[1] == "-v"):
                return CommandResult(
                    returncode=0,
                    stdout=b"",
                    stderr=b"pdfinfo version 24.02.0\n",
                )
            raise PdfBackendError("comando Poppler ausente")

        backend = PopplerBackend(runner=failing_runner)
        with tempfile.NamedTemporaryFile(suffix=".pdf") as handle:
            with self.assertRaises(PdfBackendError):
                backend.profile_document(
                    Path(handle.name), source_path="inputs/demo.pdf"
                )

    def test_rejects_symlink_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            real = Path(tmp) / "real.pdf"
            write_minimal_text_pdf(real)
            link = Path(tmp) / "link.pdf"
            link.symlink_to(real)
            backend = PopplerBackend.__new__(PopplerBackend)
            backend._commands = {
                "pdfinfo": "pdfinfo",
                "pdftotext": "pdftotext",
                "pdffonts": "pdffonts",
                "pdfimages": "pdfimages",
                "pdftocairo": "pdftocairo",
            }
            backend._runner = lambda *a, **k: (_ for _ in ()).throw(
                AssertionError("runner não deve executar para symlink")
            )
            backend._version = "0.0.0"
            with self.assertRaises(PdfBackendError) as ctx:
                backend.profile_document(link, source_path="inputs/demo.pdf")
            self.assertIn("symlink", str(ctx.exception).lower())


class SvgStreamTests(unittest.TestCase):
    def _run_stream(
        self,
        stdout_bytes: bytes,
        *,
        timeout: int = 2,
        limit: int = 1024 * 1024,
        max_read: int | None = None,
        cwd: Path | None = None,
    ):
        class Stream:
            def __init__(self, data: bytes) -> None:
                self._buf = io.BytesIO(data)
                self._closed = False

            def fileno(self):
                return 1

            def read(self, size: int = -1) -> bytes:
                if self._closed:
                    return b""
                if max_read is not None:
                    size = max_read if size < 0 else min(size, max_read)
                chunk = self._buf.read(size)
                if chunk == b"":
                    self._closed = True
                return chunk

            def close(self) -> None:
                self._closed = True

        class FakeProc:
            def __init__(self) -> None:
                self.stdout = Stream(stdout_bytes)
                self.stderr = Stream(b"")
                self.returncode: int | None = None
                self.killed = False

            def poll(self):
                if self.stdout._closed and self.stderr._closed:
                    self.returncode = 0
                    return 0
                return None

            def wait(self, timeout=None):
                self.returncode = 0
                return 0

            def kill(self) -> None:
                self.killed = True
                self.returncode = -9

        def fake_popen(args, **kwargs):
            return FakeProc()

        with mock.patch("subprocess.Popen", side_effect=fake_popen):
            with mock.patch("os.set_blocking"):
                with mock.patch(
                    "select.select",
                    side_effect=lambda r, w, x, t: (list(r), [], []),
                ):
                    return _stream_rendered_svg_counts(
                        ["pdftocairo", "-svg", "-", "-"],
                        timeout_seconds=timeout,
                        max_stream_bytes=limit,
                        cwd=cwd,
                    )

    def test_file_svg_counts_complete_path_once(self) -> None:
        from nbr12721.pdf.backend import _count_rendered_svg_elements

        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as handle:
            handle.write(b'<?xml?><svg><path d="M0 0"/></svg>')
            handle.flush()
            path = Path(handle.name)
        try:
            signals = _count_rendered_svg_elements(path)
        finally:
            path.unlink(missing_ok=True)
        self.assertEqual(signals.path_count, 1)

    def test_invalid_utf8_fails_closed(self) -> None:
        with self.assertRaises(PdfParseError):
            self._run_stream(b"<svg>\xff\xff\xff\xff\xff</svg>")

    def test_malformed_svg_fails_closed(self) -> None:
        with self.assertRaises(PdfParseError):
            self._run_stream(b"not-svg-at-all")

    def test_missing_svg_close_fails_closed(self) -> None:
        with self.assertRaises(PdfParseError):
            self._run_stream(b'<svg><path d="M0 0"/>')

    def test_trailing_garbage_in_stream_fails_closed(self) -> None:
        with self.assertRaises(PdfParseError):
            self._run_stream(b'<svg><path d="M0 0"/></svg>EXTRA')

    def test_complete_svg_tags_split_at_multiple_boundaries(self) -> None:
        payload = (
            b'<?xml version="1.0"?><svg><path d="M0 0"/>'
            b'<path d="M1 1"/></svg>'
        )
        for chunk_size in (1, 7, 8, 9, 17, 64, 65536):
            with self.subTest(chunk_size=chunk_size):
                signals = self._run_stream(payload, max_read=chunk_size)
                self.assertEqual(signals.path_count, 2)

    def test_path_tag_split_at_64kib_read_boundary(self) -> None:
        head = b'<?xml version="1.0"?><svg>'
        pad = b" " * (65536 - len(head) - len(b"<path"))
        payload = head + pad + b'<path d="M0 0"/></svg>'
        self.assertGreater(len(payload), 65536)
        signals = self._run_stream(payload)
        self.assertEqual(signals.path_count, 1)

    def test_long_path_attribute_split_at_64kib_boundary(self) -> None:
        opening = b'<svg><path d="'
        attribute = b"M0 0 " + (b"L1 1 " * 20000)
        payload = opening + attribute + b'"/></svg>'
        self.assertGreater(len(payload), 65536)
        signals = self._run_stream(payload)
        self.assertEqual(signals.path_count, 1)

    def test_long_attribute_split_at_small_chunks(self) -> None:
        payload = b'<svg><path d="' + (b"M" * 200) + b'"/></svg>'
        signals = self._run_stream(payload, max_read=8)
        self.assertEqual(signals.path_count, 1)

    def test_timeout_enforced_during_stdout_read(self) -> None:
        class FD:
            def __init__(self, buf):
                self._buf = buf

            def fileno(self):
                return 1

            def read(self, size=-1):
                return self._buf.read(size)

            def close(self) -> None:
                pass

        class FakeProc:
            def __init__(self) -> None:
                self.stdout = FD(io.BytesIO(b"x" * 100))
                self.stderr = FD(io.BytesIO(b""))
                self.returncode = None
                self.killed = False

            def poll(self):
                return None

            def wait(self, timeout=None):
                raise subprocess.TimeoutExpired(cmd="x", timeout=timeout)

            def kill(self) -> None:
                self.killed = True
                self.returncode = -9

        with mock.patch("subprocess.Popen", return_value=FakeProc()):
            with mock.patch("os.set_blocking"):
                with mock.patch(
                    "select.select",
                    side_effect=lambda r, w, x, t: ([], [], []),
                ):
                    started = time.monotonic()
                    with self.assertRaises(PdfBackendError) as ctx:
                        _stream_rendered_svg_counts(
                            ["pdftocairo", "-svg", "-", "-"],
                            timeout_seconds=1,
                            max_stream_bytes=1024 * 1024,
                        )
                    elapsed = time.monotonic() - started
        self.assertIn("timeout", str(ctx.exception))
        self.assertLess(elapsed, 2.5)

    def test_parse_error_kills_child_within_timeout(self) -> None:
        script = (
            "import sys, time\n"
            "sys.stdout.buffer.write(b'<svg>\\xff\\xff\\xff\\xff\\xff</svg>')\n"
            "sys.stdout.buffer.flush()\n"
            "time.sleep(3)\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad_utf8_then_sleep.py"
            path.write_text(script, encoding="utf-8")
            started = time.monotonic()
            with self.assertRaises(PdfParseError):
                _stream_rendered_svg_counts(
                    ["python3", str(path)],
                    timeout_seconds=1,
                    max_stream_bytes=1024 * 1024,
                    cwd=Path(tmp),
                )
            elapsed = time.monotonic() - started
        self.assertLess(elapsed, 1.0)

    def test_stdout_limit_fails_closed(self) -> None:
        with self.assertRaises(PdfBackendError) as ctx:
            self._run_stream(b"<svg>" + b"<path/>" * 100, limit=32)
        self.assertIn("stdout", str(ctx.exception))


class SchemaParityTests(unittest.TestCase):
    def test_rejects_empty_documents_pages_and_source_path(self) -> None:
        payload = _minimal_valid_payload(documents=[])
        with self.assertRaises(PdfSchemaError):
            validate_page_profiles_payload(payload, sources=set())
        payload = _minimal_valid_payload()
        payload["documents"][0]["pages"] = []  # type: ignore[index]
        with self.assertRaises(PdfSchemaError):
            validate_page_profiles_payload(
                payload, sources=_expected_sources(payload)
            )
        payload = _minimal_valid_payload()
        payload["documents"][0]["source_path"] = ""  # type: ignore[index]
        with self.assertRaises(PdfSchemaError):
            validate_page_profiles_payload(
                payload, sources=_expected_sources(payload)
            )

    def test_rejects_duplicates_float_bool_negative_unknown(self) -> None:
        payload = _minimal_valid_payload()
        payload["documents"][0]["pages"][0]["flags"] = [  # type: ignore[index]
            "low_native_text",
            "low_native_text",
        ]
        with self.assertRaises(PdfSchemaError):
            validate_page_profiles_payload(
                payload, sources=_expected_sources(payload)
            )

        payload = _minimal_valid_payload()
        page = dict(payload["documents"][0]["pages"][0])  # type: ignore[index]
        payload["documents"][0]["pages"] = [page, dict(page)]  # type: ignore[index]
        with self.assertRaises(PdfSchemaError):
            validate_page_profiles_payload(
                payload, sources=_expected_sources(payload)
            )

        payload = _minimal_valid_payload()
        doc = dict(payload["documents"][0])  # type: ignore[index]
        doc["source_path"] = "inputs/projetos_modelo/AY0410/other.pdf"
        payload["documents"] = [  # type: ignore[index]
            payload["documents"][0],
            doc,
        ]
        with self.assertRaises(PdfSchemaError):
            validate_page_profiles_payload(
                payload, sources=_expected_sources(_minimal_valid_payload())
            )

        payload = _minimal_valid_payload()
        payload["documents"][0]["pages"][0]["native_word_count"] = 1.5  # type: ignore[index]
        with self.assertRaises(PdfSchemaError):
            validate_page_profiles_payload(
                payload, sources=_expected_sources(payload)
            )

        payload = _minimal_valid_payload()
        payload["documents"][0]["pages"][0]["native_word_count"] = True  # type: ignore[index]
        with self.assertRaises(PdfSchemaError):
            validate_page_profiles_payload(
                payload, sources=_expected_sources(payload)
            )

        payload = _minimal_valid_payload()
        payload["documents"][0]["pages"][0]["image_count"] = -1  # type: ignore[index]
        with self.assertRaises(PdfSchemaError):
            validate_page_profiles_payload(
                payload, sources=_expected_sources(payload)
            )

        payload = _minimal_valid_payload(extra_field="nope")
        with self.assertRaises(PdfSchemaError):
            validate_page_profiles_payload(
                payload, sources=_expected_sources(payload)
            )

    def test_rejects_same_key_different_body_duplicates(self) -> None:
        payload = _minimal_valid_payload()
        page_a = dict(payload["documents"][0]["pages"][0])  # type: ignore[index]
        page_b = dict(page_a)
        page_b["native_word_count"] = page_a["native_word_count"] + 7
        page_b["page_number"] = page_a["page_number"]
        payload["documents"][0]["pages"] = [page_a, page_b]  # type: ignore[index]
        with self.assertRaises(PdfSchemaError) as ctx:
            validate_page_profiles_payload(
                payload, sources=_expected_sources(payload)
            )
        self.assertIn("page_number", str(ctx.exception))
        with self.assertRaises(PageProfilesSchemaError):
            validate_page_profiles_against_json_schema(
                payload, sources=_expected_sources(_minimal_valid_payload())
            )

        payload = _minimal_valid_payload()
        doc_a = dict(payload["documents"][0])  # type: ignore[index]
        doc_b = dict(doc_a)
        doc_b["pages"] = [dict(doc_a["pages"][0])]
        doc_b["pages"][0]["native_word_count"] = (
            doc_a["pages"][0]["native_word_count"] + 3
        )
        # Mesmo source_path, corpo diferente.
        payload["documents"] = [doc_a, doc_b]  # type: ignore[index]
        with self.assertRaises(PdfSchemaError) as ctx:
            validate_page_profiles_payload(
                payload, sources=_expected_sources(_minimal_valid_payload())
            )
        self.assertIn("source_path", str(ctx.exception))
        with self.assertRaises(PageProfilesSchemaError):
            validate_page_profiles_against_json_schema(
                payload, sources=_expected_sources(_minimal_valid_payload())
            )

    def test_draft_schema_parity_and_coverage(self) -> None:
        payload = _minimal_valid_payload()
        sources = _expected_sources(payload)
        validate_page_profiles_payload(payload, sources=sources)
        validate_page_profiles_against_json_schema(payload, sources=sources)

        outside = _minimal_valid_payload()
        outside["documents"][0]["source_path"] = (  # type: ignore[index]
            "inputs/projetos_modelo/AY0410/outside.pdf"
        )
        with self.assertRaises(PdfSchemaError):
            validate_page_profiles_payload(outside, sources=sources)
        with self.assertRaises(PageProfilesSchemaError):
            validate_page_profiles_against_json_schema(outside, sources=sources)

        incomplete = _minimal_valid_payload()
        with self.assertRaises(PdfSchemaError):
            validate_page_profiles_payload(incomplete, sources=sources | {"extra.pdf"})
        with self.assertRaises(PageProfilesSchemaError):
            validate_page_profiles_against_json_schema(
                incomplete, sources=sources | {"extra.pdf"}
            )


class EnvelopeTests(unittest.TestCase):
    def _sample_document(self, source_path: str) -> DocumentRawSignals:
        box = PageBox.from_coords(
            Decimal("0"), Decimal("0"), Decimal("200"), Decimal("100")
        )
        page = PageRawSignals(
            page_number=1,
            media_box=box,
            crop_box=box,
            rotation=0,
            native_word_count=5,
            native_codepoint_count=20,
            native_word_with_bbox_count=5,
            font_count=1,
            embedded_font_count=1,
            subset_font_count=0,
            image_count=0,
            image_width_sum=0,
            image_height_sum=0,
            image_pixel_sum=0,
            rendered_svg=RenderedSvgSignals(0, 0, 0, 0, 0, 0, 0),
            probable_origin="pdfium",
        )
        return DocumentRawSignals(source_path=source_path, pages=(page,))

    def test_deterministic_source_order(self) -> None:
        class FakeBackend:
            name = "fake"
            version = "0.0.0"

        docs = [
            self._sample_document("inputs/projetos_modelo/AY0410/z.pdf"),
            self._sample_document("inputs/projetos_modelo/AY0410/a.pdf"),
        ]
        sources = (
            SourceRef(path="inputs/projetos_modelo/AY0410/z.pdf", sha256="b" * 64),
            SourceRef(path="inputs/projetos_modelo/AY0410/a.pdf", sha256="a" * 64),
        )
        env_a = build_page_profiles_envelope(
            docs, sources=sources, backend=FakeBackend()
        )
        env_b = build_page_profiles_envelope(
            list(reversed(docs)), sources=list(reversed(sources)), backend=FakeBackend()
        )
        self.assertEqual(
            serialize_page_profiles(env_a),
            serialize_page_profiles(env_b),
        )

    def test_equivalent_page_order_same_canonical_bytes(self) -> None:
        class FakeBackend:
            name = "fake"
            version = "0.0.0"

        box = PageBox.from_coords(
            Decimal("0"), Decimal("0"), Decimal("200"), Decimal("100")
        )

        def make_page(page_number: int, words: int) -> PageRawSignals:
            return PageRawSignals(
                page_number=page_number,
                media_box=box,
                crop_box=box,
                rotation=0,
                native_word_count=words,
                native_codepoint_count=words * 2,
                native_word_with_bbox_count=words,
                font_count=1,
                embedded_font_count=1,
                subset_font_count=0,
                image_count=0,
                image_width_sum=0,
                image_height_sum=0,
                image_pixel_sum=0,
                rendered_svg=RenderedSvgSignals(0, 0, 0, 0, 0, 0, 0),
                probable_origin="pdfium",
            )

        source_path = "inputs/projetos_modelo/AY0410/multi.pdf"
        sources = (SourceRef(path=source_path, sha256="c" * 64),)
        forward = DocumentRawSignals(
            source_path=source_path,
            pages=(make_page(1, 1), make_page(2, 9)),
        )
        reversed_pages = DocumentRawSignals(
            source_path=source_path,
            pages=(make_page(2, 9), make_page(1, 1)),
        )
        self.assertEqual(
            tuple(page.page_number for page in reversed_pages.pages),
            (1, 2),
        )
        env_a = build_page_profiles_envelope(
            [forward], sources=sources, backend=FakeBackend()
        )
        env_b = build_page_profiles_envelope(
            [reversed_pages], sources=sources, backend=FakeBackend()
        )
        self.assertEqual(
            serialize_page_profiles(env_a),
            serialize_page_profiles(env_b),
        )
        self.assertEqual(
            env_a.payload["documents"][0]["pages"][0]["native_word_count"],
            1,
        )
        self.assertEqual(
            env_a.payload["documents"][0]["pages"][1]["native_word_count"],
            9,
        )

    def test_versioned_artifact_reconstruction(self) -> None:
        self.assertTrue(
            _VERSIONED_ARTIFACT.is_file(),
            "artefato versionado profiles/page-profiles.json ausente",
        )
        versioned = _VERSIONED_ARTIFACT.read_text(encoding="utf-8")
        reparsed = serialize_page_profiles(parse_envelope(versioned))
        self.assertEqual(versioned, reparsed)
        self.assertEqual(
            content_sha256_hex(versioned),
            content_sha256_hex(reparsed),
        )

    def test_schema_rejects_float_and_extra_fields(self) -> None:
        payload = {
            "payload_version": "1.0.0",
            "coordinate_system": {
                "unit": "pt",
                "origin": "bottom-left",
                "x_axis": "right",
                "y_axis": "up",
            },
            "thresholds": DEFAULT_THRESHOLDS.to_dict(),
            "documents": [],
            "extra": True,
        }
        with self.assertRaises(PdfSchemaError):
            validate_page_profiles_payload(payload, sources=set())


class SelectionTests(unittest.TestCase):
    def test_select_ay0410_from_manifest(self) -> None:
        artifacts = [
            SourceArtifact(
                path="inputs/projetos_modelo/AY0410/a.pdf",
                sha256="a" * 64,
                size_bytes=1,
                media_type="application/pdf",
            ),
            SourceArtifact(
                path="inputs/normativa/n.pdf",
                sha256="b" * 64,
                size_bytes=1,
                media_type="application/pdf",
            ),
        ]
        with self.assertRaises(Exception):
            select_ay0410_pdf_sources(artifacts)


class SubprocessRunnerTests(unittest.TestCase):
    def test_temp_directory_cleanup(self) -> None:
        path_holder: list[Path] = []
        try:
            with RestrictedTempDirectory(prefix="test-pdf-") as temp:
                path_holder.append(temp.path)
                temp.path.mkdir(exist_ok=True)
                raise ValueError("force failure")
        except ValueError:
            pass
        self.assertTrue(all(not path.exists() for path in path_holder))

    def test_assert_artifact_size_limit(self) -> None:
        with RestrictedTempDirectory(prefix="test-pdf-art-") as temp:
            artifact = temp.path / "blob.bin"
            artifact.write_bytes(b"12345")
            temp.assert_artifact_size(artifact, limit=5)
            with self.assertRaises(PdfBackendError) as ctx:
                temp.assert_artifact_size(artifact, limit=4)
            self.assertIn("artefato temporário", str(ctx.exception))

    def test_run_command_nonzero_exit(self) -> None:
        result = run_command(["python3", "-c", "import sys; sys.exit(3)"])
        self.assertEqual(result.returncode, 3)
        with self.assertRaises(PdfBackendError) as ctx:
            require_success(result, tool="python3")
        self.assertIn("não zero", str(ctx.exception))

    def test_run_command_timeout(self) -> None:
        with mock.patch(
            "nbr12721.pdf.subprocess_runner.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd=["sleep"], timeout=1),
        ):
            with self.assertRaises(PdfBackendError) as ctx:
                run_command(["sleep", "2"], timeout_seconds=1)
        self.assertIn("timeout", str(ctx.exception))

    def test_run_command_timeout_kill_permission_fails_closed(self) -> None:
        with mock.patch(
            "nbr12721.pdf.subprocess_runner.subprocess.run",
            side_effect=PermissionError("kill denied"),
        ):
            with self.assertRaises(PdfBackendError) as ctx:
                run_command(["sleep", "2"], timeout_seconds=1)
        self.assertIn("subprocesso", str(ctx.exception).lower())

    def test_run_command_stdout_limit(self) -> None:
        with self.assertRaises(PdfBackendError) as ctx:
            run_command(
                ["python3", "-c", "import sys; sys.stdout.buffer.write(b'x' * 64)"],
                max_stdout_bytes=16,
            )
        self.assertIn("stdout", str(ctx.exception))

    def test_run_command_stderr_limit(self) -> None:
        with self.assertRaises(PdfBackendError) as ctx:
            run_command(
                ["python3", "-c", "import sys; sys.stderr.buffer.write(b'y' * 64)"],
                max_stderr_bytes=16,
            )
        self.assertIn("stderr", str(ctx.exception))

    def test_poppler_subprocess_uses_restricted_cwd(self) -> None:
        seen: list[tuple[tuple[str, ...], Path | None]] = []

        def tracking_runner(args, **kwargs):
            cwd = kwargs.get("cwd")
            seen.append(
                (
                    tuple(args),
                    Path(cwd) if cwd is not None else None,
                )
            )
            if args[-1:] == ("-v",) or (len(args) >= 2 and args[1] == "-v"):
                return CommandResult(
                    returncode=0,
                    stdout=b"",
                    stderr=b"pdfinfo version 24.02.0\n",
                )
            raise PdfBackendError("unexpected in tracking runner")

        backend = PopplerBackend(runner=tracking_runner)
        version_calls = [
            item
            for item in seen
            if item[0][-1:] == ("-v",) or (len(item[0]) >= 2 and item[0][1] == "-v")
        ]
        self.assertEqual(len(version_calls), 1)
        self.assertIsNotNone(version_calls[0][1])
        version_cwd = version_calls[0][1]
        assert version_cwd is not None
        self.assertTrue(version_cwd.name.startswith("nbr12721-pdf-"))
        self.assertFalse(version_cwd.exists())

        with tempfile.NamedTemporaryFile(suffix=".pdf") as handle:
            with self.assertRaises(PdfBackendError):
                backend.profile_document(
                    Path(handle.name), source_path="inputs/demo.pdf"
                )
        self.assertGreaterEqual(len(seen), 2)
        self.assertTrue(all(cwd is not None for _args, cwd in seen))
        profile_cwds = [cwd for _args, cwd in seen[1:] if cwd is not None]
        self.assertEqual(len(profile_cwds), 1)
        self.assertTrue(profile_cwds[0].name.startswith("nbr12721-pdf-"))
        self.assertFalse(profile_cwds[0].exists())


class SanitizedVerificationTests(unittest.TestCase):
    def test_missing_source_sanitizes_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sources = tuple(
                SourceArtifact(
                    path=f"inputs/projetos_modelo/AY0410/{index:02d}.pdf",
                    sha256=f"{index:064x}",
                    size_bytes=1,
                    media_type="application/pdf",
                )
                for index in range(12)
            )
            mapping = {
                item.path: f"inputs/private/projetos_modelo/AY0410/{index:02d}.pdf"
                for index, item in enumerate(sources)
            }
            with self.assertRaises(PdfProfilerError) as ctx:
                profile_verified_sources(
                    root,
                    sources=sources,
                    path_mapping=mapping,
                )
            message = str(ctx.exception)
            self.assertNotIn("inputs/private/", message)
            self.assertNotIn(str(root), message)
            self.assertTrue(message.startswith("verificação de fonte falhou"))
            self.assertIn("inputs/projetos_modelo/AY0410/", message)


class SyntheticPdfIntegrationTests(unittest.TestCase):
    def test_poppler_on_synthetic_text_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = Path(tmp) / "text.pdf"
            write_minimal_text_pdf(pdf_path, producer="PDFium")
            backend = PopplerBackend()
            doc = backend.profile_document(pdf_path, source_path="inputs/demo/text.pdf")
            self.assertEqual(len(doc.pages), 1)
            self.assertGreaterEqual(doc.pages[0].native_word_count, 0)
            self.assertIn(
                doc.pages[0].probable_origin,
                {"autocad_pdfplot", "pdfium", "other", "absent", "unknown"},
            )

    def test_poppler_on_synthetic_vector_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = Path(tmp) / "vector.pdf"
            write_minimal_vector_pdf(pdf_path)
            backend = PopplerBackend()
            doc = backend.profile_document(
                pdf_path, source_path="inputs/demo/vector.pdf"
            )
            self.assertEqual(len(doc.pages), 1)
            self.assertEqual(doc.pages[0].native_word_count, 0)

    def test_poppler_on_synthetic_raster_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = Path(tmp) / "raster.pdf"
            write_minimal_raster_pdf(pdf_path)
            backend = PopplerBackend()
            doc = backend.profile_document(
                pdf_path, source_path="inputs/demo/raster.pdf"
            )
            self.assertEqual(len(doc.pages), 1)
            self.assertGreaterEqual(doc.pages[0].image_count, 1)

    def test_poppler_on_synthetic_hybrid_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = Path(tmp) / "hybrid.pdf"
            write_minimal_hybrid_pdf(pdf_path)
            backend = PopplerBackend()
            doc = backend.profile_document(
                pdf_path, source_path="inputs/demo/hybrid.pdf"
            )
            page = doc.pages[0]
            self.assertEqual(page.rotation, 90)
            self.assertNotEqual(
                (
                    page.media_box.x0,
                    page.media_box.y0,
                    page.media_box.x1,
                    page.media_box.y1,
                ),
                (
                    page.crop_box.x0,
                    page.crop_box.y0,
                    page.crop_box.x1,
                    page.crop_box.y1,
                ),
            )
            self.assertGreaterEqual(page.native_word_count, 1)
            self.assertGreaterEqual(page.image_count, 1)

    def test_poppler_on_multipage_mixed_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = Path(tmp) / "multi.pdf"
            write_multipage_mixed_pdf(pdf_path)
            backend = PopplerBackend()
            doc = backend.profile_document(
                pdf_path, source_path="inputs/demo/multi.pdf"
            )
            self.assertEqual(len(doc.pages), 2)
            page1, page2 = doc.pages
            self.assertEqual(page1.page_number, 1)
            self.assertEqual(page2.page_number, 2)
            self.assertEqual(page1.rotation, 0)
            self.assertEqual(page2.rotation, 90)
            self.assertNotEqual(page1.media_box.width, page2.media_box.width)
            self.assertNotEqual(page1.crop_box.width, page2.crop_box.width)
            self.assertGreaterEqual(page1.native_word_count, 1)
            self.assertEqual(page2.native_word_count, 0)
            self.assertGreaterEqual(page1.font_count, 1)
            self.assertGreaterEqual(page2.font_count, 2)
            self.assertNotEqual(page1.font_count, page2.font_count)

    def test_rotations(self) -> None:
        backend = PopplerBackend()
        with tempfile.TemporaryDirectory() as tmp:
            for rotation in (0, 90, 180, 270):
                pdf_path = Path(tmp) / f"rot-{rotation}.pdf"
                write_minimal_text_pdf(pdf_path, rotate=rotation)
                doc = backend.profile_document(
                    pdf_path, source_path=f"inputs/demo/rot-{rotation}.pdf"
                )
                self.assertEqual(doc.pages[0].rotation, rotation)

    def test_unicode_filename(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = Path(tmp) / "ação plano.pdf"
            write_minimal_vector_pdf(pdf_path)
            backend = PopplerBackend()
            doc = backend.profile_document(pdf_path, source_path="inputs/demo/x.pdf")
            self.assertEqual(len(doc.pages), 1)


class CliSanitizationTests(unittest.TestCase):
    def test_cli_catches_pdf_error_without_private_path(self) -> None:
        sys_path = list(sys.path)
        try:
            sys.path.insert(0, str(_PROJECT_ROOT / "src"))
            import importlib.util

            spec = importlib.util.spec_from_file_location(
                "profile_ay0410_under_test", _CLI
            )
            assert spec and spec.loader
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            def boom(repo_root):
                raise PdfProfilerError(
                    "verificação de fonte falhou para "
                    "'inputs/projetos_modelo/AY0410/demo.pdf'"
                )

            module.build_envelope = boom  # type: ignore[method-assign]
            stderr = io.StringIO()
            with mock.patch.object(sys, "stderr", stderr):
                rc = module.main(["--check"])
            self.assertEqual(rc, 1)
            err = stderr.getvalue()
            self.assertIn("verificação de fonte falhou", err)
            self.assertNotIn("inputs/private/", err)
            self.assertNotIn("/home/", err)
        finally:
            sys.path[:] = sys_path


class ConformanceNegativeTests(unittest.TestCase):
    def _load_conformance(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "profile_ay0410_conformance", _CLI
        )
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _mutable_payload(self) -> dict:
        return json.loads(_VERSIONED_ARTIFACT.read_text(encoding="utf-8"))["payload"]

    def test_zeroed_signals_fail_conformance(self) -> None:
        module = self._load_conformance()
        payload = self._mutable_payload()
        payload["documents"][0]["pages"][0]["native_word_count"] = 0
        payload["documents"][0]["pages"][0]["native_codepoint_count"] = 0
        payload["documents"][0]["pages"][0]["rendered_svg_path_count"] = 0
        payload["documents"][0]["pages"][0]["image_count"] = 0
        payload["documents"][0]["pages"][0]["font_count"] = 0
        with self.assertRaises(PdfProfilerError) as ctx:
            module._conformance_checks(type("Env", (), {"payload": payload})())
        self.assertIn("sinais zerados", str(ctx.exception))

    def test_parking_vector_divergence_fails_conformance(self) -> None:
        module = self._load_conformance()
        payload = self._mutable_payload()
        for doc in payload["documents"]:
            if "PL-0002" in doc["source_path"]:
                doc["pages"][0]["image_count"] = 5
                doc["pages"][0]["rendered_svg_path_count"] = 0
                break
        with self.assertRaises(PdfProfilerError) as ctx:
            module._conformance_checks(type("Env", (), {"payload": payload})())
        message = str(ctx.exception)
        self.assertTrue(
            "imagens acima do máximo" in message or "paths SVG abaixo" in message
        )


if __name__ == "__main__":
    unittest.main()
