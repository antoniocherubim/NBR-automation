"""Erros tipados do contrato comum de envelopes v1."""

from __future__ import annotations


class ArtifactError(ValueError):
    """Erro base dos contratos de artefato."""


class ArtifactValidationError(ArtifactError):
    """Documento ou value object viola o contrato fail-closed."""


class ArtifactSchemaVersionError(ArtifactValidationError):
    """schema_version ausente ou incompatível com o leitor v1."""

    def __init__(
        self,
        *,
        received: object,
        supported: tuple[int, ...] = (1,),
    ) -> None:
        self.received = received
        self.supported = supported
        supported_text = ", ".join(str(item) for item in supported)
        super().__init__(
            "schema_version incompatível: "
            f"recebido={received!r}; suportado=[{supported_text}]"
        )


class ArtifactCanonicalJsonError(ArtifactValidationError):
    """Falha de serialização/parsing JSON canônico."""


class ArtifactDecimalError(ArtifactValidationError):
    """Valor Decimal não representável como decimal-string canônica."""
