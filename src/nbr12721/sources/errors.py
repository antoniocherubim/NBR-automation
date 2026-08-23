"""Exceções tipadas do registro de fontes."""

from __future__ import annotations


class SourceRegistryError(Exception):
    """Erro base do módulo de fontes."""


class Sha256SumsParseError(SourceRegistryError):
    """Falha ao interpretar uma entrada de SHA256SUMS."""


class PathSecurityError(SourceRegistryError):
    """Path relativo inseguro ou fora da raiz permitida."""


class PathMappingError(SourceRegistryError):
    """Mapeamento lógico → físico incompleto, ambíguo ou inseguro."""


class MediaTypeError(SourceRegistryError):
    """Extensão de arquivo sem mapeamento de media type suportado."""


class SourceVerificationError(SourceRegistryError):
    """Falha na verificação de bytes ou metadata de uma fonte."""


class ManifestValidationError(SourceRegistryError):
    """Documento de manifest incompatível com source-manifest v1."""


class OutputPathPolicyError(SourceRegistryError):
    """Destino de output rejeitado pela policy fail-closed."""
