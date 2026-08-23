"""Testes do mapeamento lógico → físico e verificação com path distinto."""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from nbr12721.sources.errors import PathMappingError, SourceVerificationError
from nbr12721.sources.mapping import validate_path_mapping
from nbr12721.sources.verify import verify_all_sources, verify_source


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class TestPathMapping(unittest.TestCase):
    def test_total_bijective_mapping(self) -> None:
        mapping = {
            "inputs/a.pdf": "inputs/private/a.pdf",
            "inputs/b.pdf": "inputs/private/b.pdf",
        }
        result = validate_path_mapping(list(mapping), mapping)
        self.assertEqual(result, mapping)

    def test_missing_key(self) -> None:
        with self.assertRaises(PathMappingError):
            validate_path_mapping(
                ["inputs/a.pdf", "inputs/b.pdf"],
                {"inputs/a.pdf": "inputs/private/a.pdf"},
            )

    def test_extra_key(self) -> None:
        with self.assertRaises(PathMappingError):
            validate_path_mapping(
                ["inputs/a.pdf"],
                {
                    "inputs/a.pdf": "inputs/private/a.pdf",
                    "inputs/b.pdf": "inputs/private/b.pdf",
                },
            )

    def test_duplicate_physical(self) -> None:
        with self.assertRaises(PathMappingError):
            validate_path_mapping(
                ["inputs/a.pdf", "inputs/b.pdf"],
                {
                    "inputs/a.pdf": "inputs/private/same.pdf",
                    "inputs/b.pdf": "inputs/private/same.pdf",
                },
            )

    def test_outside_private_prefix(self) -> None:
        with self.assertRaises(PathMappingError):
            validate_path_mapping(
                ["inputs/a.pdf"],
                {"inputs/a.pdf": "inputs/other/a.pdf"},
            )

    def test_unsafe_physical_path(self) -> None:
        with self.assertRaises(PathMappingError):
            validate_path_mapping(
                ["inputs/a.pdf"],
                {"inputs/a.pdf": "inputs/private/../escape.pdf"},
            )

    def test_rejects_non_string_mapping_key(self) -> None:
        with self.assertRaises(PathMappingError):
            validate_path_mapping(
                ["inputs/a.pdf"],
                {"inputs/a.pdf": "inputs/private/a.pdf", 7: "inputs/private/x"},  # type: ignore[dict-item]
            )

    def test_rejects_non_string_or_unsafe_logical_id(self) -> None:
        with self.assertRaises(PathMappingError):
            validate_path_mapping([7], {})  # type: ignore[list-item]
        with self.assertRaises(PathMappingError):
            validate_path_mapping(
                ["../a.pdf"],
                {"../a.pdf": "inputs/private/a.pdf"},
            )


class TestMappedVerification(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.tempdir.name)
        self.addCleanup(self.tempdir.cleanup)

    def test_preserves_logical_id(self) -> None:
        payload = b"%PDF-synthetic-mapped\n"
        physical = "inputs/private/demo/sample.pdf"
        target = self.repo_root / physical
        target.parent.mkdir(parents=True)
        target.write_bytes(payload)
        digest = _digest(payload)
        logical = "inputs/demo/sample.pdf"
        artifact = verify_source(
            self.repo_root,
            logical,
            digest,
            physical_relative_path=physical,
        )
        self.assertEqual(artifact.path, logical)
        self.assertEqual(artifact.sha256, digest)
        self.assertEqual(artifact.size_bytes, len(payload))

    def test_verify_all_with_mapping(self) -> None:
        payload = b"%PDF-batch\n"
        physical = "inputs/private/demo/batch.pdf"
        target = self.repo_root / physical
        target.parent.mkdir(parents=True)
        target.write_bytes(payload)
        digest = _digest(payload)
        logical = "inputs/demo/batch.pdf"
        artifacts = verify_all_sources(
            self.repo_root,
            [(digest, logical)],
            path_mapping={logical: physical},
        )
        self.assertEqual(len(artifacts), 1)
        self.assertEqual(artifacts[0].path, logical)

    def test_symlink_physical_rejected(self) -> None:
        real = self.repo_root / "inputs/private/demo/real.pdf"
        real.parent.mkdir(parents=True)
        real.write_bytes(b"real")
        link = self.repo_root / "inputs/private/demo/link.pdf"
        link.symlink_to(real)
        digest = _digest(b"real")
        with self.assertRaises(SourceVerificationError):
            verify_source(
                self.repo_root,
                "inputs/demo/link.pdf",
                digest,
                physical_relative_path="inputs/private/demo/link.pdf",
            )


if __name__ == "__main__":
    unittest.main()
