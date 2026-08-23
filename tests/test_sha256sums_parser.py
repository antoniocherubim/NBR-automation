"""Testes do parser estrito de SHA256SUMS."""

from __future__ import annotations

import unittest

from nbr12721.sources.errors import Sha256SumsParseError
from nbr12721.sources.sha256sums import parse_sha256sums

_VALID_HASH = "a" * 64


class TestSha256SumsParser(unittest.TestCase):
    def test_real_corpus_paths_with_space_and_unicode(self) -> None:
        project_root = __import__("pathlib").Path(__file__).resolve().parents[1]
        text = (project_root / "SHA256SUMS").read_text(encoding="utf-8")
        entries = parse_sha256sums(text)
        self.assertEqual(len(entries), 14)
        paths = [path for path, _digest in entries]
        self.assertIn(
            "inputs/normativa/ABNT NBR 12721-2006.pdf",
            paths,
        )
        self.assertTrue(
            any("IMPLANTAÇÃO" in path for path in paths),
            "path Unicode do corpus deve ser preservado",
        )
        self.assertEqual(paths, sorted(paths))

    def test_malformed_line_and_delimiter(self) -> None:
        with self.assertRaises(Sha256SumsParseError):
            parse_sha256sums(f"{_VALID_HASH} inputs/a.pdf\n")
        with self.assertRaises(Sha256SumsParseError):
            parse_sha256sums(f"{_VALID_HASH}   inputs/a.pdf\n")

    def test_invalid_hash(self) -> None:
        with self.assertRaises(Sha256SumsParseError):
            parse_sha256sums(f"{'A' * 64}  inputs/a.pdf\n")
        with self.assertRaises(Sha256SumsParseError):
            parse_sha256sums(f"{'a' * 63}  inputs/a.pdf\n")
        with self.assertRaises(Sha256SumsParseError):
            parse_sha256sums(f"{'g' * 64}  inputs/a.pdf\n")

    def test_empty_duplicate_absolute_traversal_nul_backslash(self) -> None:
        cases = [
            f"{_VALID_HASH}  \n",
            "\n".join(
                [
                    f"{_VALID_HASH}  inputs/a.pdf",
                    f"{_VALID_HASH}  inputs/a.pdf",
                ]
            ),
            f"{_VALID_HASH}  /etc/passwd\n",
            f"{_VALID_HASH}  inputs/../secret.pdf\n",
            f"{_VALID_HASH}  inputs/a\x00b.pdf\n",
            f"{_VALID_HASH}  inputs\\a.pdf\n",
            f"{_VALID_HASH}  inputs//a.pdf\n",
        ]
        for case in cases:
            with self.subTest(case=repr(case)):
                with self.assertRaises(Sha256SumsParseError):
                    parse_sha256sums(case)

    def test_deterministic_sorting(self) -> None:
        text = "\n".join(
            [
                f"{_VALID_HASH}  inputs/z.pdf",
                f"{_VALID_HASH}  inputs/a.pdf",
                f"{_VALID_HASH}  inputs/m.pdf",
            ]
        )
        entries = parse_sha256sums(text)
        self.assertEqual(
            [path for path, _ in entries],
            ["inputs/a.pdf", "inputs/m.pdf", "inputs/z.pdf"],
        )


if __name__ == "__main__":
    unittest.main()
