"""Adapter interno de fixtures privadas (fora da superfície pública de nbr12721)."""

from __future__ import annotations

from adapter.config import (
    config_file_path,
    read_private_root,
    validate_private_root,
)
from adapter.errors import (
    ConfigError,
    InventoryError,
    MaterializeError,
    PrivateFixturesError,
    TaskMarkerError,
)
from adapter.inventory import (
    INVENTORY_RELATIVE,
    PrivateFixture,
    build_inventory_from_source_manifest,
    fixtures_from_document,
    load_inventory,
    parse_inventory,
    serialize_inventory,
    validate_inventory_document,
)
from adapter.materialize import (
    materialize_fixtures,
    verify_materialized,
)
from adapter.task_marker import parse_task_marker, read_task_marker

__all__ = [
    "INVENTORY_RELATIVE",
    "ConfigError",
    "InventoryError",
    "MaterializeError",
    "PrivateFixture",
    "PrivateFixturesError",
    "TaskMarkerError",
    "build_inventory_from_source_manifest",
    "config_file_path",
    "fixtures_from_document",
    "load_inventory",
    "materialize_fixtures",
    "parse_inventory",
    "parse_task_marker",
    "read_private_root",
    "read_task_marker",
    "serialize_inventory",
    "validate_inventory_document",
    "validate_private_root",
    "verify_materialized",
]
