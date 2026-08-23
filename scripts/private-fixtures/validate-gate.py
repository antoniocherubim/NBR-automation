#!/usr/bin/env python3
"""Gate task-aware de validação de fixtures privadas (adapter N+1)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts" / "private-fixtures"))

from adapter.errors import PrivateFixturesError
from adapter.inventory import (
    build_inventory_from_source_manifest,
    load_inventory,
    serialize_inventory,
)
from adapter.materialize import verify_materialized
from adapter.task_marker import read_task_marker
from nbr12721.sources.manifest import parse_manifest
from nbr12721.sources.sha256sums import parse_sha256sums


def main() -> int:
    repo_root = Path(os.environ.get("AGENT_LOOP_WORKTREE") or ROOT).resolve()
    task_file = os.environ.get("AGENT_LOOP_TASK_FILE")

    try:
        marker = _resolve_marker(task_file, repo_root)
        _check_inventory_consistency(repo_root)
        if marker == "none":
            private_dir = repo_root / "inputs" / "private"
            if private_dir.exists():
                # Tasks públicas não devem depender do corpus materializado.
                print(
                    "[private-fixtures] marker=none; inventário público OK; "
                    "corpus privado não exigido"
                )
            else:
                print(
                    "[private-fixtures] marker=none; inventário público OK; "
                    "sem inputs/private/"
                )
            return 0

        fixtures = load_inventory(repo_root)
        result = verify_materialized(repo_root=repo_root, fixtures=fixtures)
        print(
            f"[private-fixtures] marker=required; "
            f"verificados={result['verified']}"
        )
        return 0
    except PrivateFixturesError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


def _resolve_marker(task_file: str | None, repo_root: Path) -> str:
    if not task_file:
        # Sem contexto de task (execução local/manual): trata como none.
        return "none"
    path = Path(task_file)
    if not path.is_absolute():
        path = repo_root / path
    return read_task_marker(path)


def _check_inventory_consistency(repo_root: Path) -> None:
    """Confere inventário público contra SHA256SUMS e source-manifest (metadata)."""
    inventory_path = repo_root / "manifests" / "private-fixtures-v1.json"
    source_path = repo_root / "manifests" / "source-manifest.json"
    sums_path = repo_root / "SHA256SUMS"

    inventory_text = inventory_path.read_text(encoding="utf-8")
    source_text = source_path.read_text(encoding="utf-8")
    source_manifest = parse_manifest(source_text)
    expected = build_inventory_from_source_manifest(source_manifest)
    expected_text = serialize_inventory(expected)
    if inventory_text != expected_text:
        raise PrivateFixturesError(
            "inventário privado diverge do source-manifest canônico"
        )

    sums = dict(parse_sha256sums(sums_path.read_text(encoding="utf-8")))
    fixtures = json.loads(inventory_text)["fixtures"]
    if len(fixtures) != len(sums):
        raise PrivateFixturesError(
            "contagem do inventário privado diverge de SHA256SUMS"
        )
    for item in fixtures:
        tracked = item["id"]
        if tracked not in sums:
            raise PrivateFixturesError(
                f"id ausente em SHA256SUMS: {tracked!r}"
            )
        if sums[tracked] != item["sha256"]:
            raise PrivateFixturesError(
                f"sha256 diverge de SHA256SUMS para {tracked!r}"
            )


if __name__ == "__main__":
    raise SystemExit(main())
