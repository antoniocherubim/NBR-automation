"""Registro determinístico e somente leitura das fontes originais."""

from __future__ import annotations

from nbr12721.sources.artifact import SourceArtifact
from nbr12721.sources.errors import (
    ManifestValidationError,
    MediaTypeError,
    OutputPathPolicyError,
    PathMappingError,
    PathSecurityError,
    Sha256SumsParseError,
    SourceRegistryError,
    SourceVerificationError,
)
from nbr12721.sources.manifest import (
    artifacts_from_manifest,
    build_manifest_dict,
    load_verified_manifest,
    parse_manifest,
    serialize_manifest,
)
from nbr12721.sources.mapping import validate_path_mapping
from nbr12721.sources.output_policy import (
    DEFAULT_OUTPUT_ROOTS,
    validate_output_destination,
)
from nbr12721.sources.sha256sums import parse_sha256sums
from nbr12721.sources.verify import verify_all_sources, verify_source

__all__ = [
    "DEFAULT_OUTPUT_ROOTS",
    "ManifestValidationError",
    "MediaTypeError",
    "OutputPathPolicyError",
    "PathMappingError",
    "PathSecurityError",
    "Sha256SumsParseError",
    "SourceArtifact",
    "SourceRegistryError",
    "SourceVerificationError",
    "artifacts_from_manifest",
    "build_manifest_dict",
    "load_verified_manifest",
    "parse_manifest",
    "parse_sha256sums",
    "serialize_manifest",
    "validate_output_destination",
    "validate_path_mapping",
    "verify_all_sources",
    "verify_source",
]
