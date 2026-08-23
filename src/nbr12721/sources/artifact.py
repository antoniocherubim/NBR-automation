"""Value object SourceArtifact."""

from __future__ import annotations

from dataclasses import dataclass
import re

from nbr12721.sources.errors import ManifestValidationError, MediaTypeError
from nbr12721.sources.media_types import media_type_for_path
from nbr12721.sources.paths import validate_relative_posix_path

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class SourceArtifact:
    """Representação imutável de uma fonte verificada."""

    path: str
    sha256: str
    size_bytes: int
    media_type: str

    def __post_init__(self) -> None:
        validate_relative_posix_path(self.path, context="SourceArtifact.path")
        try:
            expected_media_type = media_type_for_path(self.path)
        except MediaTypeError:
            raise
        if self.media_type != expected_media_type:
            raise ManifestValidationError(
                "media_type não corresponde à extensão do path"
            )
        if type(self.size_bytes) is not int:
            raise ManifestValidationError("size_bytes deve ser inteiro")
        if self.size_bytes < 0:
            raise ManifestValidationError("size_bytes deve ser não negativo")
        if not _SHA256_PATTERN.fullmatch(self.sha256):
            raise ManifestValidationError(
                "sha256 deve ser hexadecimal lowercase com 64 caracteres"
            )

    def to_manifest_item(self) -> dict[str, object]:
        return {
            "media_type": self.media_type,
            "path": self.path,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
        }
