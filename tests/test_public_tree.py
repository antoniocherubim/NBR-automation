"""Testes do gate da árvore pública e ensaio de artifact sanitizado."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATE_PUBLIC = REPO_ROOT / "scripts" / "ci" / "validate-public-tree.py"
VALIDATE_ZIP = REPO_ROOT / "scripts" / "ci" / "validate-artifact-zip.py"
PUBLIC_TREE_HELPER = REPO_ROOT / "scripts" / "ci"


def _run(cmd: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd or REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load_candidate_modules() -> tuple[object, object]:
    import sys

    src = str(REPO_ROOT / "src")
    helper = str(PUBLIC_TREE_HELPER)
    if src not in sys.path:
        sys.path.insert(0, src)
    if helper not in sys.path:
        sys.path.insert(0, helper)
    import candidate_snapshot  # noqa: E402

    spec = importlib.util.spec_from_file_location(
        "validate_artifact_zip_mod", VALIDATE_ZIP
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return candidate_snapshot, mod


class PublicTreeCandidateTests(unittest.TestCase):
    def test_candidate_gate_passes_after_removals(self) -> None:
        result = _run(["python3", str(VALIDATE_PUBLIC), "--candidate"])
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("private_path_hits=0", result.stdout)
        self.assertIn("historical_hits=0", result.stdout)
        self.assertIn("digest_hits=0", result.stdout)

    def test_head_commit_fails_while_originais_ainda_no_head(self) -> None:
        status = _run(
            [
                "git",
                "-c",
                "core.quotePath=false",
                "ls-tree",
                "-r",
                "--name-only",
                "HEAD",
            ]
        )
        historical = any(
            line.startswith("inputs/normativa/")
            or line.startswith("inputs/template/")
            or line.startswith("inputs/projetos_modelo/")
            for line in status.stdout.splitlines()
        )
        result = _run(["python3", str(VALIDATE_PUBLIC), "--commit", "HEAD"])
        if historical:
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("histórico privado", result.stderr.lower())
        else:
            self.assertEqual(result.returncode, 0, result.stderr)


class PublicTreeNegativeSyntheticTests(unittest.TestCase):
    def test_candidate_snapshot_includes_staged_new_file(self) -> None:
        candidate_snapshot, _mod = _load_candidate_modules()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _run(["git", "init", "-q"], cwd=root)
            _run(["git", "config", "user.name", "Test"], cwd=root)
            _run(["git", "config", "user.email", "test@example.invalid"], cwd=root)
            (root / "base.txt").write_text("base\n", encoding="utf-8")
            _run(["git", "add", "base.txt"], cwd=root)
            _run(["git", "commit", "-qm", "base"], cwd=root)
            (root / "staged.txt").write_text("staged\n", encoding="utf-8")
            _run(["git", "add", "staged.txt"], cwd=root)
            files = candidate_snapshot.candidate_file_map(root)
            self.assertIn("staged.txt", files)

    def test_candidate_snapshot_rejects_untracked_symlink(self) -> None:
        candidate_snapshot, _mod = _load_candidate_modules()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _run(["git", "init", "-q"], cwd=root)
            _run(["git", "config", "user.name", "Test"], cwd=root)
            _run(["git", "config", "user.email", "test@example.invalid"], cwd=root)
            target = root / "target.txt"
            target.write_text("public synthetic\n", encoding="utf-8")
            _run(["git", "add", "target.txt"], cwd=root)
            committed = _run(["git", "commit", "-qm", "base"], cwd=root)
            self.assertEqual(committed.returncode, 0, committed.stderr)
            (root / "link.txt").symlink_to(target)
            with self.assertRaises(candidate_snapshot.PublicTreeError) as ctx:
                candidate_snapshot.candidate_file_map(root)
            self.assertIn("symlink", str(ctx.exception).lower())

    def test_rejects_historical_path_private_prefix_and_digest(self) -> None:
        candidate_snapshot, _mod = _load_candidate_modules()
        historical, digests = candidate_snapshot.load_private_fixture_policy(
            REPO_ROOT
        )
        sample_path = sorted(historical)[0]

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            hist_file = root / "clone.pdf"
            hist_file.write_bytes(b"%PDF-not-real-content\n")
            with self.assertRaises(candidate_snapshot.PublicTreeError):
                candidate_snapshot.scan_public_tree(
                    {sample_path: hist_file},
                    historical_paths=historical,
                    private_digests=digests,
                )

            renamed = root / "docs" / "leaked.bin"
            renamed.parent.mkdir(parents=True)
            renamed.write_bytes(b"synthetic-public-bytes")
            public_digest = _sha256(b"synthetic-public-bytes")
            poisoned = set(digests) | {public_digest}
            with self.assertRaises(candidate_snapshot.PublicTreeError) as ctx:
                candidate_snapshot.scan_public_tree(
                    {"docs/leaked.bin": renamed},
                    historical_paths=historical,
                    private_digests=poisoned,
                )
            self.assertIn("digest", str(ctx.exception).lower())

            private_tracked = root / "inputs" / "private" / "x.pdf"
            private_tracked.parent.mkdir(parents=True)
            private_tracked.write_bytes(b"x")
            with self.assertRaises(candidate_snapshot.PublicTreeError):
                candidate_snapshot.scan_public_tree(
                    {"inputs/private/x.pdf": private_tracked},
                    historical_paths=historical,
                    private_digests=digests,
                )


class ArtifactCandidateZipTests(unittest.TestCase):
    def test_git_tracked_paths_uses_explicit_repo_root(self) -> None:
        _candidate_snapshot, mod = _load_candidate_modules()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _run(["git", "init", "-q"], cwd=root)
            _run(["git", "config", "user.name", "Test"], cwd=root)
            _run(["git", "config", "user.email", "test@example.invalid"], cwd=root)
            (root / "only-here.txt").write_text("synthetic\n", encoding="utf-8")
            _run(["git", "add", "only-here.txt"], cwd=root)
            committed = _run(["git", "commit", "-qm", "test"], cwd=root)
            self.assertEqual(committed.returncode, 0, committed.stderr)
            self.assertEqual(mod.git_tracked_paths(root, "HEAD"), {"only-here.txt"})

    def test_candidate_zip_round_trip(self) -> None:
        candidate_snapshot, _mod = _load_candidate_modules()
        files = candidate_snapshot.candidate_file_map(REPO_ROOT, base="HEAD")
        self.assertGreater(len(files), 0)
        self.assertFalse(any(p.startswith("inputs/private/") for p in files))
        self.assertFalse(
            any(
                p.startswith("inputs/normativa/")
                or p.startswith("inputs/template/")
                or p.startswith("inputs/projetos_modelo/")
                for p in files
            )
        )

        with tempfile.TemporaryDirectory() as tmp:
            zip_path = Path(tmp) / "artifact.zip"
            count = candidate_snapshot.write_candidate_zip(
                REPO_ROOT, zip_path, files
            )
            self.assertEqual(count, len(files))
            result = _run(
                ["python3", str(VALIDATE_ZIP), str(zip_path), "CANDIDATE"]
            )
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            self.assertIn(f"{count} entradas", result.stdout)

            with zipfile.ZipFile(zip_path, "r") as zf:
                names = {i.filename for i in zf.infolist() if not i.is_dir()}
                self.assertEqual(len(names), count)

    def test_rejects_zip_with_historical_path(self) -> None:
        candidate_snapshot, _mod = _load_candidate_modules()
        files = candidate_snapshot.candidate_file_map(REPO_ROOT, base="HEAD")
        inventory = json.loads(
            (REPO_ROOT / "manifests" / "private-fixtures-v1.json").read_text(
                encoding="utf-8"
            )
        )
        historical = inventory["fixtures"][0]["id"]
        with tempfile.TemporaryDirectory() as tmp:
            zip_path = Path(tmp) / "artifact.zip"
            candidate_snapshot.write_candidate_zip(REPO_ROOT, zip_path, files)
            with zipfile.ZipFile(zip_path, "a") as zf:
                zf.writestr(historical, b"%PDF-synthetic-not-private-bytes\n")
            result = _run(
                ["python3", str(VALIDATE_ZIP), str(zip_path), "CANDIDATE"]
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("histórico privado", result.stderr.lower())

    def test_rejects_zip_with_marked_private_digest(self) -> None:
        candidate_snapshot, mod = _load_candidate_modules()
        files = candidate_snapshot.candidate_file_map(REPO_ROOT, base="HEAD")
        historical, real_digests = candidate_snapshot.load_private_fixture_policy(
            REPO_ROOT
        )
        with tempfile.TemporaryDirectory() as tmp:
            zip_path = Path(tmp) / "artifact.zip"
            candidate_snapshot.write_candidate_zip(REPO_ROOT, zip_path, files)
            payload = b"synthetic-digest-canary\n"
            canary_digest = _sha256(payload)
            with zipfile.ZipFile(zip_path, "a") as zf:
                zf.writestr("docs/canary.bin", payload)
            poisoned = set(real_digests) | {canary_digest}
            expected = set(files.keys()) | {"docs/canary.bin"}
            with self.assertRaises(mod.ArtifactZipValidationError) as ctx:
                mod.validate_artifact_zip(
                    str(zip_path),
                    expected_paths=expected,
                    historical_paths=historical,
                    private_digests=poisoned,
                    label="CANDIDATE",
                )
            self.assertIn("digest", str(ctx.exception).lower())

    def test_rejects_zip_under_inputs_private(self) -> None:
        candidate_snapshot, _mod = _load_candidate_modules()
        files = candidate_snapshot.candidate_file_map(REPO_ROOT, base="HEAD")
        with tempfile.TemporaryDirectory() as tmp:
            zip_path = Path(tmp) / "artifact.zip"
            candidate_snapshot.write_candidate_zip(REPO_ROOT, zip_path, files)
            with zipfile.ZipFile(zip_path, "a") as zf:
                zf.writestr("inputs/private/leak.pdf", b"%PDF-synth\n")
            result = _run(
                ["python3", str(VALIDATE_ZIP), str(zip_path), "CANDIDATE"]
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("inputs/private", result.stderr.lower())


if __name__ == "__main__":
    unittest.main()
