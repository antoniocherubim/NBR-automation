#!/usr/bin/env python3
"""Gera manifests/private-fixtures-v1.json a partir do source-manifest."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts" / "private-fixtures"))

from adapter.inventory import (
    INVENTORY_RELATIVE,
    build_inventory_from_source_manifest,
    serialize_inventory,
)
from nbr12721.sources.manifest import parse_manifest


def main() -> int:
    source = parse_manifest(
        (ROOT / "manifests" / "source-manifest.json").read_text(encoding="utf-8")
    )
    inventory = build_inventory_from_source_manifest(source)
    text = serialize_inventory(inventory)
    out = ROOT / INVENTORY_RELATIVE
    out.write_text(text, encoding="utf-8")
    print(f"wrote {INVENTORY_RELATIVE} bytes={len(text.encode('utf-8'))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
