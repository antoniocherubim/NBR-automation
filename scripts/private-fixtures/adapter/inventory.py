"""Inventário público canônico private-fixtures v1."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from adapter.errors import InventoryError
from nbr12721.sources.errors import MediaTypeError
from nbr12721.sources.media_types import SUPPORTED_MEDIA_TYPES, media_type_for_path
from nbr12721.sources.paths import PathSecurityError, validate_relative_posix_path

SCHEMA_VERSION = 1
INVENTORY_RELATIVE = "manifests/private-fixtures-v1.json"
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_ROOT_KEYS = frozenset({"fixtures", "schema_version"})
_FIXTURE_KEYS = frozenset(
    {
        "id",
        "media_type",
        "materialize_path",
        "sha256",
        "size_bytes",
        "store_path",
    }
)
_ALLOWED_MEDIA_TYPES = frozenset(SUPPORTED_MEDIA_TYPES.values())
_MATERIALIZE_PREFIX = "inputs/private/"


@dataclass(frozen=True, slots=True)
class PrivateFixture:
    """Metadata pública de uma fixture privada."""

    id: str
    store_path: str
    materialize_path: str
    sha256: str
    size_bytes: int
    media_type: str

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "media_type": self.media_type,
            "materialize_path": self.materialize_path,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "store_path": self.store_path,
        }


def validate_inventory_document(document: object) -> None:
    """Valida inventário v1 fail-closed."""
    if not isinstance(document, dict):
        raise InventoryError("inventário deve ser objeto JSON")

    extra_root = set(document.keys()) - _ROOT_KEYS
    if extra_root:
        raise InventoryError(
            f"campos desconhecidos no inventário: {sorted(extra_root)!r}"
        )
    missing_root = _ROOT_KEYS - set(document.keys())
    if missing_root:
        raise InventoryError(
            f"campos obrigatórios ausentes: {sorted(missing_root)!r}"
        )

    schema_version = _require_exact_int(
        document["schema_version"], "schema_version"
    )
    if schema_version != SCHEMA_VERSION:
        raise InventoryError(f"schema_version incompatível: {schema_version!r}")

    fixtures = document["fixtures"]
    if not isinstance(fixtures, list):
        raise InventoryError("fixtures deve ser array")
    if len(fixtures) == 0:
        raise InventoryError("fixtures não pode ser vazio")

    seen_ids: set[str] = set()
    seen_store: set[str] = set()
    seen_materialize: set[str] = set()
    previous_store: str | None = None

    for index, item in enumerate(fixtures):
        fixture = _validate_fixture_item(item, index)
        if fixture.id in seen_ids:
            raise InventoryError(f"id duplicado: {fixture.id!r}")
        if fixture.store_path in seen_store:
            raise InventoryError(
                f"store_path duplicado: {fixture.store_path!r}"
            )
        if fixture.materialize_path in seen_materialize:
            raise InventoryError(
                f"materialize_path duplicado: {fixture.materialize_path!r}"
            )
        if previous_store is not None and fixture.store_path <= previous_store:
            raise InventoryError(
                "fixtures deve estar ordenado lexicograficamente por store_path"
            )
        seen_ids.add(fixture.id)
        seen_store.add(fixture.store_path)
        seen_materialize.add(fixture.materialize_path)
        previous_store = fixture.store_path


def _validate_fixture_item(item: object, index: int) -> PrivateFixture:
    if not isinstance(item, dict):
        raise InventoryError(f"fixtures[{index}] deve ser objeto")

    extra = set(item.keys()) - _FIXTURE_KEYS
    if extra:
        raise InventoryError(
            f"fixtures[{index}] contém campos desconhecidos: {sorted(extra)!r}"
        )
    missing = _FIXTURE_KEYS - set(item.keys())
    if missing:
        raise InventoryError(
            f"fixtures[{index}] campos obrigatórios ausentes: {sorted(missing)!r}"
        )

    fixture_id = item["id"]
    store_path = item["store_path"]
    materialize_path = item["materialize_path"]
    digest = item["sha256"]
    media_type = item["media_type"]
    size_bytes = _require_exact_int(
        item["size_bytes"], f"fixtures[{index}].size_bytes"
    )

    if not isinstance(fixture_id, str) or fixture_id == "":
        raise InventoryError(f"fixtures[{index}].id deve ser string não vazia")
    try:
        validate_relative_posix_path(
            fixture_id, context=f"fixtures[{index}].id"
        )
    except PathSecurityError as exc:
        raise InventoryError(str(exc)) from exc

    if not isinstance(store_path, str) or store_path == "":
        raise InventoryError(
            f"fixtures[{index}].store_path deve ser string não vazia"
        )
    try:
        validate_relative_posix_path(
            store_path, context=f"fixtures[{index}].store_path"
        )
    except PathSecurityError as exc:
        raise InventoryError(str(exc)) from exc

    if not isinstance(materialize_path, str) or materialize_path == "":
        raise InventoryError(
            f"fixtures[{index}].materialize_path deve ser string não vazia"
        )
    try:
        validate_relative_posix_path(
            materialize_path, context=f"fixtures[{index}].materialize_path"
        )
    except PathSecurityError as exc:
        raise InventoryError(str(exc)) from exc

    if not materialize_path.startswith(_MATERIALIZE_PREFIX):
        raise InventoryError(
            f"fixtures[{index}].materialize_path deve ficar sob inputs/private/"
        )
    expected_materialize = f"{_MATERIALIZE_PREFIX}{store_path}"
    if materialize_path != expected_materialize:
        raise InventoryError(
            f"fixtures[{index}].materialize_path deve espelhar store_path"
        )

    if size_bytes < 0:
        raise InventoryError(
            f"fixtures[{index}].size_bytes deve ser não negativo"
        )
    if not isinstance(digest, str) or not _SHA256_PATTERN.fullmatch(digest):
        raise InventoryError(f"fixtures[{index}].sha256 inválido")
    if not isinstance(media_type, str) or media_type not in _ALLOWED_MEDIA_TYPES:
        raise InventoryError(f"fixtures[{index}].media_type inválido")

    try:
        expected_media = media_type_for_path(store_path)
        materialize_media = media_type_for_path(materialize_path)
    except MediaTypeError as exc:
        raise InventoryError(str(exc)) from exc
    if media_type != expected_media:
        raise InventoryError(
            f"fixtures[{index}].media_type não corresponde à extensão"
        )
    if materialize_media != media_type:
        raise InventoryError(
            f"fixtures[{index}].materialize_path extensão inconsistente"
        )

    return PrivateFixture(
        id=fixture_id,
        store_path=store_path,
        materialize_path=materialize_path,
        sha256=digest,
        size_bytes=size_bytes,
        media_type=media_type,
    )


def serialize_inventory(document: dict[str, object]) -> str:
    """Serializa inventário v1 com forma canônica byte-estável."""
    validate_inventory_document(document)
    return (
        json.dumps(
            document,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    )


def parse_inventory(text: str) -> dict[str, object]:
    document = json.loads(text)
    validate_inventory_document(document)
    return document


def load_inventory(repo_root: Path) -> list[PrivateFixture]:
    path = repo_root / INVENTORY_RELATIVE
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise InventoryError(f"inventário ausente: {INVENTORY_RELATIVE}") from exc
    document = parse_inventory(text)
    return fixtures_from_document(document)


def fixtures_from_document(document: dict[str, object]) -> list[PrivateFixture]:
    validate_inventory_document(document)
    raw_items = document["fixtures"]
    assert isinstance(raw_items, list)
    return [
        PrivateFixture(
            id=str(item["id"]),
            store_path=str(item["store_path"]),
            materialize_path=str(item["materialize_path"]),
            sha256=str(item["sha256"]),
            size_bytes=int(item["size_bytes"]),
            media_type=str(item["media_type"]),
        )
        for item in raw_items
    ]


def build_inventory_from_source_manifest(
    source_manifest: dict[str, object],
) -> dict[str, object]:
    """Deriva inventário privado do source-manifest (metadata apenas)."""
    artifacts = source_manifest.get("artifacts")
    if not isinstance(artifacts, list):
        raise InventoryError("source-manifest sem artifacts")

    fixtures: list[PrivateFixture] = []
    for item in artifacts:
        if not isinstance(item, dict):
            raise InventoryError("artifact inválido no source-manifest")
        tracked_path = str(item["path"])
        if not tracked_path.startswith("inputs/"):
            raise InventoryError(
                f"path rastreado fora de inputs/: {tracked_path!r}"
            )
        store_path = tracked_path[len("inputs/") :]
        fixture = PrivateFixture(
            id=tracked_path,
            store_path=store_path,
            materialize_path=f"{_MATERIALIZE_PREFIX}{store_path}",
            sha256=str(item["sha256"]),
            size_bytes=int(item["size_bytes"]),
            media_type=str(item["media_type"]),
        )
        fixtures.append(fixture)

    fixtures.sort(key=lambda item: item.store_path)
    document: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "fixtures": [item.to_dict() for item in fixtures],
    }
    validate_inventory_document(document)
    return document


def _require_exact_int(value: object, context: str) -> int:
    if type(value) is not int:
        raise InventoryError(f"{context} deve ser inteiro")
    return value
