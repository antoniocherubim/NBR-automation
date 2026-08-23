"""Testes da policy de destino de outputs."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from nbr12721.sources.errors import OutputPathPolicyError
from nbr12721.sources.output_policy import validate_output_destination

_VALID_HASH = "a" * 64


class TestOutputPathPolicy(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.tempdir.name)
        self.addCleanup(self.tempdir.cleanup)

    def test_valid_destination_under_outputs(self) -> None:
        resolved = validate_output_destination(
            self.repo_root,
            "outputs/run/result.json",
        )
        self.assertTrue(str(resolved).endswith("outputs/run/result.json"))

    def test_rejects_inputs_destination(self) -> None:
        with self.assertRaises(OutputPathPolicyError):
            validate_output_destination(self.repo_root, "inputs/copy.pdf")

    def test_rejects_absolute_empty_root_and_traversal(self) -> None:
        for path in ("/tmp/out", "", ".", "outputs/../secret"):
            with self.subTest(path=path):
                with self.assertRaises(OutputPathPolicyError):
                    validate_output_destination(self.repo_root, path)

    def test_symlink_escape_from_allowlisted_root(self) -> None:
        outputs = self.repo_root / "outputs"
        outputs.mkdir()
        outside = self.repo_root.parent / "outside_output"
        outside.mkdir(exist_ok=True)
        self.addCleanup(outside.rmdir)
        secret = outside / "secret.txt"
        secret.write_text("secret", encoding="utf-8")
        self.addCleanup(secret.unlink)
        (outputs / "link").symlink_to(outside)
        with self.assertRaises(OutputPathPolicyError):
            validate_output_destination(
                self.repo_root,
                "outputs/link/secret.txt",
            )

    def test_validation_has_no_side_effects(self) -> None:
        before = {
            path.relative_to(self.repo_root)
            for path in self.repo_root.rglob("*")
        }
        validate_output_destination(
            self.repo_root,
            "outputs/new/nested/file.json",
        )
        after = {
            path.relative_to(self.repo_root)
            for path in self.repo_root.rglob("*")
        }
        self.assertEqual(before, after)


class TestGitignoreOutputsRoot(unittest.TestCase):
    _PROJECT_ROOT = Path(__file__).resolve().parents[1]

    def _check_ignore(self, relative_path: str) -> bool:
        result = subprocess.run(
            [
                "git",
                "check-ignore",
                "--no-index",
                "-q",
                relative_path,
            ],
            cwd=self._PROJECT_ROOT,
            capture_output=True,
            check=False,
        )
        return result.returncode == 0

    def test_only_root_outputs_directory_is_ignored(self) -> None:
        self.assertTrue(self._check_ignore("outputs/result.json"))
        for visible in (
            "tests/fixtures/outputs/result.json",
            "manifests/outputs/result.json",
            "inputs/outputs/result.json",
        ):
            with self.subTest(path=visible):
                self.assertFalse(self._check_ignore(visible))


if __name__ == "__main__":
    unittest.main()
