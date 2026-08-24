"""Value objects imutáveis do envelope de artefato v1."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import re
from types import MappingProxyType
from typing import Any

from nbr12721.artifacts.canonical_json import assert_json_safe
from nbr12721.artifacts.errors import ArtifactValidationError
from nbr12721.artifacts.vocab import ARTIFACT_TYPES, SCHEMA_VERSION
from nbr12721.sources.paths import PathSecurityError, validate_relative_posix_path

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_PROJECT_ID_PATTERN = re.compile(r"^[^\s]+$")


def _require_nonempty_str(value: object, *, context: str) -> str:
    if type(value) is not str:
        raise ArtifactValidationError(
            f"{context} deve ser string, recebido {type(value).__name__}"
        )
    if value == "" or value.strip() == "":
        raise ArtifactValidationError(f"{context} não pode ser vazio/whitespace")
    if value != value.strip():
        raise ArtifactValidationError(
            f"{context} não pode ter whitespace nas extremidades"
        )
    return value


def _require_sha256(value: object, *, context: str) -> str:
    text = _require_nonempty_str(value, context=context)
    if _SHA256_PATTERN.fullmatch(text) is None:
        raise ArtifactValidationError(
            f"{context} deve ser SHA-256 hexadecimal lowercase com 64 caracteres"
        )
    return text


def _require_artifact_type(value: object, *, context: str) -> str:
    text = _require_nonempty_str(value, context=context)
    if text not in ARTIFACT_TYPES:
        raise ArtifactValidationError(
            f"{context} desconhecido: {text!r}; "
            f"suportados={sorted(ARTIFACT_TYPES)!r}"
        )
    return text


def _require_exact_int(value: object, *, context: str) -> int:
    if type(value) is not int:
        raise ArtifactValidationError(
            f"{context} deve ser inteiro exato, recebido {type(value).__name__}"
        )
    return value


def _freeze_json_object(
    value: object,
    *,
    context: str,
) -> Mapping[str, Any]:
    if type(value) is not dict:
        raise ArtifactValidationError(
            f"{context} deve ser objeto JSON, recebido {type(value).__name__}"
        )
    assert_json_safe(value, path=context)
    return _freeze_json(value)


def _freeze_json(value: object) -> Any:
    if type(value) is dict:
        return MappingProxyType(
            {key: _freeze_json(item) for key, item in value.items()}
        )
    if type(value) is list:
        return tuple(_freeze_json(item) for item in value)
    return value


def _thaw_json(value: object) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_json(item) for key, item in value.items()}
    if type(value) is tuple:
        return [_thaw_json(item) for item in value]
    return value


@dataclass(frozen=True, slots=True)
class SourceRef:
    """Referência a fonte original por path lógico e SHA-256."""

    path: str
    sha256: str

    def __post_init__(self) -> None:
        path = _require_nonempty_str(self.path, context="SourceRef.path")
        try:
            validate_relative_posix_path(path, context="SourceRef.path")
        except PathSecurityError as exc:
            raise ArtifactValidationError(str(exc)) from exc
        object.__setattr__(self, "path", path)
        object.__setattr__(
            self,
            "sha256",
            _require_sha256(self.sha256, context="SourceRef.sha256"),
        )

    def to_dict(self) -> dict[str, str]:
        return {"path": self.path, "sha256": self.sha256}

    @classmethod
    def from_dict(cls, raw: object, *, context: str = "source") -> SourceRef:
        if type(raw) is not dict:
            raise ArtifactValidationError(
                f"{context} deve ser objeto, recebido {type(raw).__name__}"
            )
        allowed = frozenset({"path", "sha256"})
        extra = set(raw.keys()) - allowed
        if extra:
            raise ArtifactValidationError(
                f"{context} contém campos desconhecidos: {sorted(extra)!r}"
            )
        missing = allowed - set(raw.keys())
        if missing:
            raise ArtifactValidationError(
                f"{context} campos obrigatórios ausentes: {sorted(missing)!r}"
            )
        return cls(path=raw["path"], sha256=raw["sha256"])

    def sort_key(self) -> tuple[str, str]:
        return (self.path, self.sha256)


@dataclass(frozen=True, slots=True)
class ProducerRef:
    """Produtor estável: nome, versão e configuração relevante."""

    name: str
    version: str
    configuration: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "name", _require_nonempty_str(self.name, context="ProducerRef.name")
        )
        object.__setattr__(
            self,
            "version",
            _require_nonempty_str(self.version, context="ProducerRef.version"),
        )
        if type(self.configuration) is not dict:
            raise ArtifactValidationError(
                "ProducerRef.configuration deve ser objeto JSON, "
                f"recebido {type(self.configuration).__name__}"
            )
        frozen_config = _freeze_json_object(
            self.configuration, context="ProducerRef.configuration"
        )
        object.__setattr__(self, "configuration", frozen_config)

    def to_dict(self) -> dict[str, object]:
        return {
            "configuration": _thaw_json(self.configuration),
            "name": self.name,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, raw: object, *, context: str = "producer") -> ProducerRef:
        if type(raw) is not dict:
            raise ArtifactValidationError(
                f"{context} deve ser objeto, recebido {type(raw).__name__}"
            )
        allowed = frozenset({"name", "version", "configuration"})
        extra = set(raw.keys()) - allowed
        if extra:
            raise ArtifactValidationError(
                f"{context} contém campos desconhecidos: {sorted(extra)!r}"
            )
        missing = allowed - set(raw.keys())
        if missing:
            raise ArtifactValidationError(
                f"{context} campos obrigatórios ausentes: {sorted(missing)!r}"
            )
        return cls(
            name=raw["name"],
            version=raw["version"],
            configuration=raw["configuration"],
        )


@dataclass(frozen=True, slots=True)
class InputRef:
    """Referência de lineage a artefato intermediário de entrada."""

    artifact_type: str
    content_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "artifact_type",
            _require_artifact_type(
                self.artifact_type, context="InputRef.artifact_type"
            ),
        )
        object.__setattr__(
            self,
            "content_sha256",
            _require_sha256(
                self.content_sha256, context="InputRef.content_sha256"
            ),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "artifact_type": self.artifact_type,
            "content_sha256": self.content_sha256,
        }

    @classmethod
    def from_dict(cls, raw: object, *, context: str = "input") -> InputRef:
        if type(raw) is not dict:
            raise ArtifactValidationError(
                f"{context} deve ser objeto, recebido {type(raw).__name__}"
            )
        allowed = frozenset({"artifact_type", "content_sha256"})
        extra = set(raw.keys()) - allowed
        if extra:
            raise ArtifactValidationError(
                f"{context} contém campos desconhecidos: {sorted(extra)!r}"
            )
        missing = allowed - set(raw.keys())
        if missing:
            raise ArtifactValidationError(
                f"{context} campos obrigatórios ausentes: {sorted(missing)!r}"
            )
        return cls(
            artifact_type=raw["artifact_type"],
            content_sha256=raw["content_sha256"],
        )

    def sort_key(self) -> tuple[str, str]:
        return (self.artifact_type, self.content_sha256)


@dataclass(frozen=True, slots=True)
class ArtifactEnvelope:
    """Envelope persistível v1 (conteúdo canônico sem metadata operacional)."""

    schema_version: int
    artifact_type: str
    project_id: str
    sources: tuple[SourceRef, ...]
    producer: ProducerRef
    inputs: tuple[InputRef, ...]
    payload: Mapping[str, Any]

    def __post_init__(self) -> None:
        version = _require_exact_int(
            self.schema_version, context="ArtifactEnvelope.schema_version"
        )
        if version != SCHEMA_VERSION:
            raise ArtifactValidationError(
                f"ArtifactEnvelope.schema_version deve ser {SCHEMA_VERSION}, "
                f"recebido {version!r}"
            )
        object.__setattr__(
            self,
            "artifact_type",
            _require_artifact_type(
                self.artifact_type, context="ArtifactEnvelope.artifact_type"
            ),
        )
        project_id = _require_nonempty_str(
            self.project_id, context="ArtifactEnvelope.project_id"
        )
        if _PROJECT_ID_PATTERN.fullmatch(project_id) is None:
            raise ArtifactValidationError(
                "ArtifactEnvelope.project_id não pode conter whitespace"
            )
        object.__setattr__(self, "project_id", project_id)

        if not isinstance(self.producer, ProducerRef):
            raise ArtifactValidationError(
                "ArtifactEnvelope.producer deve ser ProducerRef"
            )

        sources = _normalize_sources(self.sources)
        inputs = _normalize_inputs(self.inputs)
        object.__setattr__(self, "sources", sources)
        object.__setattr__(self, "inputs", inputs)

        if type(self.payload) is not dict:
            raise ArtifactValidationError(
                "ArtifactEnvelope.payload deve ser objeto JSON, "
                f"recebido {type(self.payload).__name__}"
            )
        payload = _freeze_json_object(
            self.payload, context="ArtifactEnvelope.payload"
        )
        object.__setattr__(self, "payload", payload)

    def to_dict(self) -> dict[str, object]:
        return {
            "artifact_type": self.artifact_type,
            "inputs": [item.to_dict() for item in self.inputs],
            "payload": _thaw_json(self.payload),
            "producer": self.producer.to_dict(),
            "project_id": self.project_id,
            "schema_version": self.schema_version,
            "sources": [item.to_dict() for item in self.sources],
        }


def _normalize_sources(
    sources: Sequence[SourceRef] | Sequence[object],
) -> tuple[SourceRef, ...]:
    if type(sources) not in (list, tuple):
        raise ArtifactValidationError(
            "ArtifactEnvelope.sources deve ser lista/tupla"
        )
    items: list[SourceRef] = []
    for index, raw in enumerate(sources):
        if isinstance(raw, SourceRef):
            items.append(raw)
        else:
            items.append(SourceRef.from_dict(raw, context=f"sources[{index}]"))
    ordered = sorted(items, key=lambda item: item.sort_key())
    seen_paths: set[str] = set()
    seen_pairs: set[tuple[str, str]] = set()
    for item in ordered:
        if item.path in seen_paths:
            raise ArtifactValidationError(
                f"fonte duplicada por path: {item.path!r}"
            )
        pair = item.sort_key()
        if pair in seen_pairs:
            raise ArtifactValidationError(
                f"fonte duplicada: path={item.path!r} sha256={item.sha256!r}"
            )
        seen_paths.add(item.path)
        seen_pairs.add(pair)
    return tuple(ordered)


def _normalize_inputs(
    inputs: Sequence[InputRef] | Sequence[object],
) -> tuple[InputRef, ...]:
    if type(inputs) not in (list, tuple):
        raise ArtifactValidationError(
            "ArtifactEnvelope.inputs deve ser lista/tupla"
        )
    items: list[InputRef] = []
    for index, raw in enumerate(inputs):
        if isinstance(raw, InputRef):
            items.append(raw)
        else:
            items.append(InputRef.from_dict(raw, context=f"inputs[{index}]"))
    ordered = sorted(items, key=lambda item: item.sort_key())
    seen: set[tuple[str, str]] = set()
    for item in ordered:
        key = item.sort_key()
        if key in seen:
            raise ArtifactValidationError(
                "input duplicado: "
                f"artifact_type={item.artifact_type!r} "
                f"content_sha256={item.content_sha256!r}"
            )
        seen.add(key)
    return tuple(ordered)
