"""Testes da verificação fail-closed de fontes."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import tempfile
import unittest

from nbr12721.sources.errors import SourceVerificationError
from nbr12721.sources.verify import verify_all_sources, verify_source

_VALID_HASH = "a" * 64


class TestSourceVerifier(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.tempdir.name)
        self.addCleanup(self.tempdir.cleanup)

    def _write_regular(self, relative_path: str, content: bytes) -> str:
        target = self.repo_root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return hashlib.sha256(content).hexdigest()

    def test_regular_file_success(self) -> None:
        digest = self._write_regular("inputs/sample.pdf", b"%PDF-sample")
        artifact = verify_source(self.repo_root, "inputs/sample.pdf", digest)
        self.assertEqual(artifact.path, "inputs/sample.pdf")
        self.assertEqual(artifact.sha256, digest)
        self.assertEqual(artifact.size_bytes, len(b"%PDF-sample"))
        self.assertEqual(artifact.media_type, "application/pdf")

    def test_divergent_digest(self) -> None:
        self._write_regular("inputs/sample.pdf", b"content")
        with self.assertRaises(SourceVerificationError):
            verify_source(self.repo_root, "inputs/sample.pdf", _VALID_HASH)

    def test_missing_file(self) -> None:
        with self.assertRaises(Exception):
            verify_source(self.repo_root, "inputs/missing.pdf", _VALID_HASH)

    def test_directory_target(self) -> None:
        (self.repo_root / "inputs/dir.pdf").mkdir(parents=True)
        with self.assertRaises(SourceVerificationError):
            verify_source(self.repo_root, "inputs/dir.pdf", _VALID_HASH)

    def test_fifo_target(self) -> None:
        target = self.repo_root / "inputs/pipe.pdf"
        target.parent.mkdir(parents=True)
        os.mkfifo(target)
        with self.assertRaises(SourceVerificationError):
            verify_source(self.repo_root, "inputs/pipe.pdf", _VALID_HASH)

    def test_symlink_file_target(self) -> None:
        digest = self._write_regular("inputs/real.pdf", b"real")
        link = self.repo_root / "inputs/link.pdf"
        link.symlink_to(self.repo_root / "inputs/real.pdf")
        with self.assertRaises(SourceVerificationError):
            verify_source(self.repo_root, "inputs/link.pdf", digest)

    def test_symlink_directory_escape(self) -> None:
        outside = self.repo_root.parent / "outside_escape"
        outside.mkdir(exist_ok=True)
        self.addCleanup(outside.rmdir)
        secret = outside / "secret.pdf"
        secret.write_bytes(b"secret")
        self.addCleanup(secret.unlink)
        trap = self.repo_root / "inputs" / "trap"
        trap.mkdir(parents=True)
        (trap / "link").symlink_to(outside)
        digest = hashlib.sha256(b"secret").hexdigest()
        with self.assertRaises(Exception):
            verify_source(self.repo_root, "inputs/trap/link/secret.pdf", digest)

    def test_streaming_chunk_size_and_size_bytes(self) -> None:
        payload = b"x" * (128 * 1024 + 17)
        digest = self._write_regular("inputs/large.pdf", payload)
        artifact = verify_source(self.repo_root, "inputs/large.pdf", digest)
        self.assertEqual(artifact.size_bytes, len(payload))

    def test_no_partial_manifest_on_failure(self) -> None:
        good_digest = self._write_regular("inputs/good.pdf", b"good")
        entries = [
            (good_digest, "inputs/good.pdf"),
            (_VALID_HASH, "inputs/bad.pdf"),
        ]
        with self.assertRaises(SourceVerificationError):
            verify_all_sources(self.repo_root, entries)


if __name__ == "__main__":
    unittest.main()
