"""Boundary PDF: profiler determinístico de páginas (Poppler, page-profiles v1)."""

from __future__ import annotations

from nbr12721.pdf.backend import PdfBackend, PopplerBackend
from nbr12721.pdf.config import (
    DEFAULT_THRESHOLDS,
    PAYLOAD_VERSION,
    PROFILER_NAME,
    PROFILER_VERSION,
    PROJECT_ID_AY0410,
    ProfilerThresholdsV1,
)
from nbr12721.pdf.errors import (
    PdfBackendError,
    PdfError,
    PdfParseError,
    PdfProfilerError,
    PdfSchemaError,
)
from nbr12721.pdf.profiler import (
    build_page_profiles_envelope,
    profile_verified_sources,
    select_ay0410_pdf_sources,
    serialize_page_profiles,
)
from nbr12721.pdf.schema import validate_page_profiles_payload

__all__ = [
    "DEFAULT_THRESHOLDS",
    "PAYLOAD_VERSION",
    "PROFILER_NAME",
    "PROFILER_VERSION",
    "PROJECT_ID_AY0410",
    "PdfBackend",
    "PdfBackendError",
    "PdfError",
    "PdfParseError",
    "PdfProfilerError",
    "PdfSchemaError",
    "PopplerBackend",
    "ProfilerThresholdsV1",
    "build_page_profiles_envelope",
    "profile_verified_sources",
    "select_ay0410_pdf_sources",
    "serialize_page_profiles",
    "validate_page_profiles_payload",
]
