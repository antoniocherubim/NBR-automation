#!/usr/bin/env python3
"""Gera ou verifica o artefato page-profiles v1 do corpus AY0410."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

from nbr12721.artifacts.envelope import content_id, content_sha256_hex
from nbr12721.pdf.config import DEFAULT_THRESHOLDS
from nbr12721.pdf.errors import PdfError, PdfProfilerError
from nbr12721.pdf.profiler import (
    AY0410_LOGICAL_PREFIX,
    profile_verified_sources,
    select_ay0410_pdf_sources,
    serialize_page_profiles,
)
from nbr12721.sources.manifest import artifacts_from_manifest, parse_manifest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_OUTPUT = _REPO_ROOT / "profiles" / "page-profiles.json"
_PRIVATE_MANIFEST = _REPO_ROOT / "manifests" / "private-fixtures-v1.json"
_SHEET_ID = re.compile(r"PL-\d{4}")
_HIGH_SVG = DEFAULT_THRESHOLDS.high_rendered_svg_path_count
_LOW_TEXT = DEFAULT_THRESHOLDS.low_native_text_word_count

# Sinais mínimos observados no corpus AY0410 (ROADMAP §3.3 + artefato versionado).
_SHEET_EXPECTATIONS: dict[str, dict[str, object]] = {
    "PL-0001": {"words_min": 90, "words_max": 110, "images_min": 1, "svg_min": _HIGH_SVG},
    "PL-0002": {
        "words_min": 90,
        "words_max": 110,
        "images_max": 0,
        "svg_min": _HIGH_SVG,
        "require_low_text_flag": True,
    },
    "PL-0003": {
        "words_min": 90,
        "words_max": 110,
        "images_max": 0,
        "svg_min": _HIGH_SVG,
        "require_low_text_flag": True,
    },
    "PL-0004": {
        "words_min": 90,
        "words_max": 110,
        "images_max": 0,
        "svg_max": _HIGH_SVG - 1,
        "require_low_text_flag": True,
    },
    "PL-0005": {
        "words_min": 90,
        "words_max": 110,
        "images_min": 1,
        "svg_min": _HIGH_SVG,
        "require_low_text_flag": True,
    },
    "PL-0006": {
        "words_min": 90,
        "words_max": 110,
        "images_min": 1,
        "svg_min": _HIGH_SVG,
        "require_low_text_flag": True,
    },
    "PL-0007": {"words_min": 700, "images_max": 0, "svg_min": _HIGH_SVG},
    "PL-0008": {"words_min": 700, "images_max": 0, "svg_min": _HIGH_SVG},
    "PL-0009": {"words_min": 700, "images_max": 0, "svg_min": _HIGH_SVG},
    "PL-0010": {"words_min": 700, "images_max": 0, "svg_min": _HIGH_SVG},
    "PL-0011": {"words_min": 700, "images_min": 100, "svg_min": _HIGH_SVG},
    "PL-0012": {"words_min": 700, "images_max": 0, "svg_min": _HIGH_SVG},
}


def _load_ay0410_mapping() -> dict[str, str]:
    document = json.loads(_PRIVATE_MANIFEST.read_text(encoding="utf-8"))
    mapping: dict[str, str] = {}
    for fixture in document["fixtures"]:
        logical_id = fixture["id"]
        if logical_id.startswith(AY0410_LOGICAL_PREFIX):
            mapping[logical_id] = fixture["materialize_path"]
    if len(mapping) != 12:
        raise PdfProfilerError(
            f"esperados 12 mapeamentos AY0410, encontrados {len(mapping)}"
        )
    return mapping


def build_envelope(repo_root: Path):
    mapping = _load_ay0410_mapping()
    manifest_path = repo_root / "manifests" / "source-manifest.json"
    manifest = parse_manifest(manifest_path.read_text(encoding="utf-8"))
    all_artifacts = artifacts_from_manifest(manifest)
    selected = select_ay0410_pdf_sources(all_artifacts)
    return profile_verified_sources(
        repo_root,
        sources=selected,
        path_mapping=mapping,
    )


def _sheet_id(source_path: str) -> str:
    match = _SHEET_ID.search(source_path)
    if match is None:
        raise PdfProfilerError(f"ID lógico PL-XXXX ausente em {source_path!r}")
    return match.group(0)


def _conformance_checks(envelope) -> None:
    payload = envelope.payload
    documents = payload["documents"]
    if len(documents) != 12:
        raise PdfProfilerError(f"esperados 12 documentos, encontrados {len(documents)}")
    page_total = sum(len(doc["pages"]) for doc in documents)
    if page_total != 12:
        raise PdfProfilerError(f"esperadas 12 páginas, encontradas {page_total}")

    origin_counts: dict[str, int] = {}
    seen_sheets: set[str] = set()
    for doc in documents:
        sheet = _sheet_id(doc["source_path"])
        if sheet in seen_sheets:
            raise PdfProfilerError(f"documento duplicado para {sheet}")
        seen_sheets.add(sheet)
        page = doc["pages"][0]
        origin = page["probable_origin"]
        origin_counts[origin] = origin_counts.get(origin, 0) + 1
        forbidden = {"is_scan", "needs_ocr", "text_page", "vector_page"}
        for flag in page["flags"]:
            if flag in forbidden:
                raise PdfProfilerError(f"flag proibida encontrada: {flag!r}")

        words = page["native_word_count"]
        images = page["image_count"]
        svg_paths = page["rendered_svg_path_count"]
        codepoints = page["native_codepoint_count"]
        if (
            words == 0
            and codepoints == 0
            and images == 0
            and svg_paths == 0
            and page["font_count"] == 0
        ):
            raise PdfProfilerError(
                f"sinais zerados materialmente divergentes para {sheet}"
            )

        expectations = _SHEET_EXPECTATIONS.get(sheet)
        if expectations is None:
            raise PdfProfilerError(f"expectativa de corpus ausente para {sheet}")

        words_min = expectations.get("words_min")
        words_max = expectations.get("words_max")
        if words_min is not None and words < int(words_min):
            raise PdfProfilerError(
                f"{sheet}: palavras abaixo do mínimo esperado ({words} < {words_min})"
            )
        if words_max is not None and words > int(words_max):
            raise PdfProfilerError(
                f"{sheet}: palavras acima do máximo esperado ({words} > {words_max})"
            )
        images_min = expectations.get("images_min")
        images_max = expectations.get("images_max")
        if images_min is not None and images < int(images_min):
            raise PdfProfilerError(
                f"{sheet}: imagens abaixo do mínimo esperado ({images} < {images_min})"
            )
        if images_max is not None and images > int(images_max):
            raise PdfProfilerError(
                f"{sheet}: imagens acima do máximo esperado ({images} > {images_max})"
            )
        svg_min = expectations.get("svg_min")
        svg_max = expectations.get("svg_max")
        if svg_min is not None and svg_paths < int(svg_min):
            raise PdfProfilerError(
                f"{sheet}: paths SVG abaixo do mínimo ({svg_paths} < {svg_min})"
            )
        if svg_max is not None and svg_paths > int(svg_max):
            raise PdfProfilerError(
                f"{sheet}: paths SVG acima do máximo ({svg_paths} > {svg_max})"
            )
        if expectations.get("require_low_text_flag"):
            if "low_native_text" not in page["flags"]:
                raise PdfProfilerError(
                    f"{sheet}: flag low_native_text esperada para estacionamento/memorial"
                )
        if words <= _LOW_TEXT and svg_paths >= _HIGH_SVG:
            overlap = {"low_native_text", "high_rendered_svg_complexity"}
            if not overlap.issubset(set(page["flags"])):
                raise PdfProfilerError(
                    f"{sheet}: flags vetoriais/texto baixo sobrepostas ausentes"
                )

    if origin_counts.get("autocad_pdfplot", 0) != 10:
        raise PdfProfilerError(
            "esperadas 10 origens autocad_pdfplot, "
            f"encontradas {origin_counts.get('autocad_pdfplot', 0)}"
        )
    if origin_counts.get("pdfium", 0) != 2:
        raise PdfProfilerError(
            "esperadas 2 origens pdfium, "
            f"encontradas {origin_counts.get('pdfium', 0)}"
        )
    if seen_sheets != set(_SHEET_EXPECTATIONS):
        missing = sorted(set(_SHEET_EXPECTATIONS) - seen_sheets)
        raise PdfProfilerError(f"planilhas AY0410 ausentes na conformidade: {missing}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="reconstrói em temporário e compara com artefato versionado",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="grava profiles/page-profiles.json (uso operacional; não usado em CI)",
    )
    args = parser.parse_args(argv)

    try:
        envelope = build_envelope(_REPO_ROOT)
        _conformance_checks(envelope)
        canonical = serialize_page_profiles(envelope)
        digest = content_sha256_hex(canonical)
        identity = content_id(canonical)

        if args.check:
            versioned = _DEFAULT_OUTPUT
            if not versioned.is_file():
                raise PdfProfilerError("artefato versionado ausente")
            expected = versioned.read_text(encoding="utf-8")
            if expected != canonical:
                raise PdfProfilerError(
                    "bytes do artefato versionado divergem da reconstrução"
                )
            expected_digest = content_sha256_hex(expected)
            if expected_digest != digest:
                raise PdfProfilerError("content ID diverge da reconstrução")
            print(
                f"[profile-ay0410] check ok documents=12 pages=12 "
                f"content_id={identity}"
            )
            return 0

        if args.write:
            _DEFAULT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
            _DEFAULT_OUTPUT.write_text(canonical, encoding="utf-8")
            print(f"[profile-ay0410] gravado {_DEFAULT_OUTPUT.name} id={identity}")
            return 0

        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix="page-profiles-",
            suffix=".json",
            delete=True,
        ) as handle:
            handle.write(canonical)
            handle.flush()
            print(
                f"[profile-ay0410] gerado em temporário documents=12 pages=12 "
                f"content_id={identity}"
            )
        return 0
    except PdfError as exc:
        print(f"[profile-ay0410] erro: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
