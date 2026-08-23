#!/usr/bin/env python3
"""CLI: materializa fixtures privadas conforme inventário rastreado."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts" / "private-fixtures"))

from adapter.config import read_private_root, validate_private_root
from adapter.errors import PrivateFixturesError
from adapter.inventory import load_inventory
from adapter.materialize import materialize_fixtures


def main() -> int:
    repo_root = Path(os.environ.get("AGENT_LOOP_WORKTREE") or ROOT).resolve()
    if (repo_root / ".git").exists() or (repo_root / ".git").is_file():
        pass
    try:
        private_root = read_private_root()
        private_root = validate_private_root(private_root, repo_root=repo_root)
        fixtures = load_inventory(repo_root)
        result = materialize_fixtures(
            repo_root=repo_root,
            private_root=private_root,
            fixtures=fixtures,
        )
    except PrivateFixturesError as exc:
        # Mensagens tipadas já omitem o root absoluto; não vazar via traceback.
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except OSError:
        print("ERROR: falha de I/O no store ou materialização", file=sys.stderr)
        return 1
    print(
        f"[private-fixtures] materializados={result['copied']} "
        f"verificados={result['verified']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
