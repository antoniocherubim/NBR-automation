#!/usr/bin/env python3
"""Gate offline da árvore pública (commit ou snapshot candidato)."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts" / "ci"))

from candidate_snapshot import (
    PublicTreeError,
    candidate_file_map,
    git_ls_tree_paths,
    load_private_fixture_policy,
    scan_public_tree,
)

_COMMIT_TEMPS: list[tempfile.TemporaryDirectory[str]] = []


def _commit_file_map(repo_root: Path, commit: str) -> dict[str, Path]:
    """Extrai blobs do commit para arquivos temporários regulares."""
    files: dict[str, Path] = {}
    tmp = tempfile.TemporaryDirectory(prefix="public-tree-")
    _COMMIT_TEMPS.append(tmp)
    tmp_root = Path(tmp.name)

    for relative in sorted(git_ls_tree_paths(repo_root, commit)):
        destination = tmp_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            ["git", "cat-file", "-p", f"{commit}:{relative}"],
            cwd=repo_root,
            capture_output=True,
            check=True,
        )
        destination.write_bytes(result.stdout)
        os.chmod(destination, 0o444)
        files[relative] = destination
    return files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--candidate",
        action="store_true",
        help="examina o snapshot candidato (working tree sem staging)",
    )
    group.add_argument(
        "--commit",
        default=None,
        help="examina o tree de um commit/tree-ish Git",
    )
    parser.add_argument(
        "--repo-root",
        default=str(ROOT),
        help="raiz do repositório (default: raiz do checkout)",
    )
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    try:
        historical_paths, private_digests = load_private_fixture_policy(repo_root)
        if args.commit:
            files = _commit_file_map(repo_root, args.commit)
            mode = f"commit={args.commit}"
        else:
            files = candidate_file_map(repo_root, base="HEAD")
            mode = "candidate"
        summary = scan_public_tree(
            files,
            historical_paths=historical_paths,
            private_digests=private_digests,
        )
    except (PublicTreeError, OSError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(
        f"[public-tree] mode={mode} files={summary['file_count']} "
        f"private_path_hits={summary['private_path_hits']} "
        f"historical_hits={summary['historical_hits']} "
        f"digest_hits={summary['digest_hits']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
