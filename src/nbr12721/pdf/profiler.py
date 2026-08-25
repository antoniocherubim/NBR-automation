"""Profiler: sinais brutos → payload page-profiles v1 dentro do envelope ARCH."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from nbr12721.artifacts.envelope import serialize_envelope
from nbr12721.artifacts.models import ArtifactEnvelope, ProducerRef, SourceRef
from nbr12721.pdf.backend import PdfBackend, PopplerBackend
from nbr12721.pdf.config import (
    COORDINATE_SYSTEM,
    PAYLOAD_VERSION,
    PROFILER_NAME,
    PROFILER_VERSION,
    PROJECT_ID_AY0410,
    ProfilerThresholdsV1,
    producer_configuration,
)
from nbr12721.pdf.errors import PdfProfilerError
from nbr12721.pdf.models import (
    DocumentRawSignals,
    derive_flags,
    page_to_payload_dict,
)
from nbr12721.pdf.schema import validate_page_profiles_payload
from nbr12721.sources.artifact import SourceArtifact
from nbr12721.sources.errors import SourceVerificationError
from nbr12721.sources.verify import verify_source

AY0410_LOGICAL_PREFIX = "inputs/projetos_modelo/AY0410/"


def select_ay0410_pdf_sources(
    artifacts: Sequence[SourceArtifact],
) -> tuple[SourceArtifact, ...]:
    """Seleciona exatamente os 12 PDFs AY0410 do manifest verificado."""
    selected = [
        item
        for item in artifacts
        if item.path.startswith(AY0410_LOGICAL_PREFIX)
        and item.media_type == "application/pdf"
    ]
    ordered = tuple(sorted(selected, key=lambda item: item.path))
    if len(ordered) != 12:
        raise PdfProfilerError(
            f"esperados 12 PDFs AY0410, encontrados {len(ordered)}"
        )
    return ordered


def build_page_profiles_envelope(
    documents: Sequence[DocumentRawSignals],
    *,
    sources: Sequence[SourceRef],
    project_id: str = PROJECT_ID_AY0410,
    backend: PdfBackend,
    thresholds: ProfilerThresholdsV1 | None = None,
) -> ArtifactEnvelope:
    """Monta envelope ARCH-001 com artifact_type page-profiles."""
    active_thresholds = thresholds or ProfilerThresholdsV1.baseline()
    source_paths = {item.path for item in sources}
    document_paths = {doc.source_path for doc in documents}
    if source_paths != document_paths:
        missing = sorted(source_paths - document_paths)
        extra = sorted(document_paths - source_paths)
        raise PdfProfilerError(
            f"cobertura incompleta: missing={missing!r} extra={extra!r}"
        )

    ordered_documents = sorted(documents, key=lambda item: item.source_path)
    payload_documents: list[dict[str, object]] = []
    for document in ordered_documents:
        pages = []
        for page in sorted(document.pages, key=lambda item: item.page_number):
            flags = derive_flags(
                page,
                low_native_text_word_count=active_thresholds.low_native_text_word_count,
                high_rendered_svg_path_count=active_thresholds.high_rendered_svg_path_count,
            )
            pages.append(page_to_payload_dict(page, flags=flags))
        payload_documents.append(
            {
                "pages": pages,
                "source_path": document.source_path,
            }
        )

    payload: dict[str, object] = {
        "coordinate_system": dict(COORDINATE_SYSTEM),
        "documents": payload_documents,
        "payload_version": PAYLOAD_VERSION,
        "thresholds": active_thresholds.to_dict(),
    }
    validate_page_profiles_payload(payload, sources=source_paths)

    producer = ProducerRef(
        name=PROFILER_NAME,
        version=PROFILER_VERSION,
        configuration=producer_configuration(
            backend_name=backend.name,
            backend_version=backend.version,
            thresholds=active_thresholds,
        ),
    )
    return ArtifactEnvelope(
        schema_version=1,
        artifact_type="page-profiles",
        project_id=project_id,
        sources=tuple(sorted(sources, key=lambda item: item.sort_key())),
        producer=producer,
        inputs=(),
        payload=payload,
    )


def profile_verified_sources(
    repo_root: Path,
    *,
    sources: Sequence[SourceArtifact],
    path_mapping: Mapping[str, str],
    backend: PdfBackend | None = None,
    thresholds: ProfilerThresholdsV1 | None = None,
) -> ArtifactEnvelope:
    """Perfil determinístico de fontes já verificadas com mapping explícito."""
    active_backend = backend or PopplerBackend()
    selected = select_ay0410_pdf_sources(sources)
    documents: list[DocumentRawSignals] = []
    source_refs: list[SourceRef] = []
    for artifact in selected:
        physical = path_mapping.get(artifact.path)
        if physical is None:
            raise PdfProfilerError(
                f"mapeamento ausente para fonte lógica: {artifact.path!r}"
            )
        try:
            verified = verify_source(
                repo_root,
                artifact.path,
                artifact.sha256,
                physical_relative_path=physical,
            )
        except SourceVerificationError:
            # Mensagem sanitizada: só ID lógico público; nunca path físico/absoluto.
            raise PdfProfilerError(
                f"verificação de fonte falhou para {artifact.path!r}"
            ) from None
        source_refs.append(
            SourceRef(path=verified.path, sha256=verified.sha256)
        )
        pdf_path = repo_root / physical
        documents.append(
            active_backend.profile_document(
                pdf_path,
                source_path=verified.path,
            )
        )
    return build_page_profiles_envelope(
        documents,
        sources=source_refs,
        backend=active_backend,
        thresholds=thresholds,
    )


def serialize_page_profiles(envelope: ArtifactEnvelope) -> str:
    return serialize_envelope(envelope)
