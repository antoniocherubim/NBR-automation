"""Validação mínima de artifact contra source-manifest-v1.schema.json (stdlib).

Patterns do Draft 2020-12 são tratados como ECMA-262: grupos Python-only
(como `(?i)`) são rejeitados antes de qualquer `re.compile`. A prova de
dialeto usa somente a stdlib; não invoca Node nem outras ferramentas.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SCHEMA_PATH = _PROJECT_ROOT / "schemas" / "source-manifest-v1.schema.json"
_SCHEMA = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
_ARTIFACT_DEF = _SCHEMA["$defs"]["source_artifact"]
_ARTIFACTS_ARRAY = _SCHEMA["properties"]["artifacts"]
_UNIQUE_ITEMS = _ARTIFACTS_ARRAY.get("uniqueItems") is True

_ECMA262_GROUP_PREFIXES = (
    ":",
    "=",
    "!",
    "<=",
    "<!",
)


class JsonSchemaArtifactError(ValueError):
    """Artifact não satisfaz restrições estruturais do JSON Schema v1."""


class JsonSchemaManifestError(ValueError):
    """Documento de manifest não satisfaz restrições do JSON Schema v1."""


class Ecma262PatternError(ValueError):
    """Pattern do JSON Schema não é um ECMA-262 Regular Expression válido."""


def collect_schema_patterns(node: object | None = None) -> list[str]:
    """Coleta todos os `pattern` do schema Draft 2020-12 versionado."""
    if node is None:
        node = _SCHEMA
    found: list[str] = []
    if isinstance(node, dict):
        pattern = node.get("pattern")
        if isinstance(pattern, str):
            found.append(pattern)
        for value in node.values():
            found.extend(collect_schema_patterns(value))
    elif isinstance(node, list):
        for item in node:
            found.extend(collect_schema_patterns(item))
    return found


def compile_ecma262_pattern(pattern: str) -> re.Pattern[str]:
    """Compila um pattern JSON Schema no dialeto ECMA-262 (não flags Python)."""
    assert_ecma262_pattern(pattern)
    return re.compile(pattern)


def assert_ecma262_pattern(pattern: str) -> None:
    """Rejeita constructs inválidos em ECMA-262 usando somente a stdlib."""
    _assert_ecma262_group_syntax(pattern)


def _assert_ecma262_group_syntax(pattern: str) -> None:
    index = 0
    in_class = False
    length = len(pattern)
    while index < length:
        char = pattern[index]
        if char == "\\" and index + 1 < length:
            index += 2
            continue
        if in_class:
            if char == "]":
                in_class = False
            index += 1
            continue
        if char == "[":
            in_class = True
            index += 1
            continue
        if char == "(" and index + 1 < length and pattern[index + 1] == "?":
            rest = pattern[index + 2 :]
            if rest.startswith("<") and not rest.startswith(("<!", "<=")):
                # Named capture ECMA-262: (?<name>
                named = re.match(r"^<[A-Za-z_][A-Za-z0-9_]*>", rest)
                if named is None:
                    raise Ecma262PatternError(
                        f"Invalid group in ECMA-262 pattern: {pattern!r}"
                    )
            elif not rest.startswith(_ECMA262_GROUP_PREFIXES):
                raise Ecma262PatternError(
                    f"Invalid group in ECMA-262 pattern: {pattern!r}"
                )
        index += 1


_PATH_PATTERN = compile_ecma262_pattern(
    _ARTIFACT_DEF["properties"]["path"]["pattern"]
)
_SHA256_PATTERN = compile_ecma262_pattern(
    _ARTIFACT_DEF["properties"]["sha256"]["pattern"]
)
_ALLOWED_MEDIA_TYPES = frozenset(
    _ARTIFACT_DEF["properties"]["media_type"]["enum"]
)
# oneOf exige stem no último componente (`(?:^|/)[^/]+\\.ext$`): `.pdf`/`.xlsx`
# são rejeitados; `.well-known/source.pdf` continua aceito.
_ONE_OF_BRANCHES = [
    (
        compile_ecma262_pattern(branch["properties"]["path"]["pattern"]),
        branch["properties"]["media_type"]["const"],
    )
    for branch in _ARTIFACT_DEF["oneOf"]
]
_ARTIFACT_KEYS = frozenset(_ARTIFACT_DEF["required"])


def validate_artifact_against_json_schema(artifact: object) -> None:
    """Valida um artifact contra patterns e oneOf do schema versionado."""
    if not isinstance(artifact, dict):
        raise JsonSchemaArtifactError("artifact deve ser objeto")

    extra = set(artifact.keys()) - _ARTIFACT_KEYS
    if extra:
        raise JsonSchemaArtifactError(
            f"campos desconhecidos: {sorted(extra)!r}"
        )
    missing = _ARTIFACT_KEYS - set(artifact.keys())
    if missing:
        raise JsonSchemaArtifactError(
            f"campos obrigatórios ausentes: {sorted(missing)!r}"
        )

    path = artifact["path"]
    if not isinstance(path, str) or path == "":
        raise JsonSchemaArtifactError("path inválido")
    if _PATH_PATTERN.search(path) is None:
        raise JsonSchemaArtifactError("path falha pattern do schema")

    digest = artifact["sha256"]
    if not isinstance(digest, str) or _SHA256_PATTERN.search(digest) is None:
        raise JsonSchemaArtifactError("sha256 inválido")

    size_bytes = artifact["size_bytes"]
    if type(size_bytes) is not int or size_bytes < 0:
        raise JsonSchemaArtifactError("size_bytes inválido")

    media_type = artifact["media_type"]
    if not isinstance(media_type, str) or media_type not in _ALLOWED_MEDIA_TYPES:
        raise JsonSchemaArtifactError("media_type inválido")

    matches = sum(
        1
        for path_pattern, expected_media in _ONE_OF_BRANCHES
        if path_pattern.search(path) is not None
        and media_type == expected_media
    )
    if matches != 1:
        raise JsonSchemaArtifactError(
            "extensão e media_type não satisfazem oneOf do schema"
        )


def _canonical_json_item(item: object) -> str:
    return json.dumps(
        item,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def validate_manifest_against_json_schema(document: object) -> None:
    """Valida o documento contra restrições de array do schema versionado."""
    if not isinstance(document, dict):
        raise JsonSchemaManifestError("manifest deve ser objeto")

    artifacts = document.get("artifacts")
    if not isinstance(artifacts, list):
        raise JsonSchemaManifestError("artifacts deve ser array")

    if not _UNIQUE_ITEMS:
        raise JsonSchemaManifestError(
            "schema v1 deve declarar artifacts.uniqueItems = true"
        )

    for artifact in artifacts:
        try:
            validate_artifact_against_json_schema(artifact)
        except JsonSchemaArtifactError as exc:
            raise JsonSchemaManifestError(str(exc)) from exc

    seen: set[str] = set()
    for item in artifacts:
        identity = _canonical_json_item(item)
        if identity in seen:
            raise JsonSchemaManifestError(
                "artifacts viola uniqueItems do schema"
            )
        seen.add(identity)
