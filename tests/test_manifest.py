"""Testes do manifest canônico source-manifest v1."""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path
import tempfile
import unittest

from nbr12721.sources.artifact import SourceArtifact
from nbr12721.sources.errors import (
    ManifestValidationError,
    MediaTypeError,
    PathSecurityError,
)
from nbr12721.sources.manifest import (
    artifacts_from_manifest,
    build_manifest_dict,
    load_verified_manifest,
    parse_manifest,
    serialize_manifest,
)
from nbr12721.sources.paths import validate_relative_posix_path
from nbr12721.sources.schema import validate_manifest_document

from json_schema_support import (
    Ecma262PatternError,
    JsonSchemaArtifactError,
    JsonSchemaManifestError,
    assert_ecma262_pattern,
    collect_schema_patterns,
    validate_artifact_against_json_schema,
    validate_manifest_against_json_schema,
)

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_VALID_DIGEST = "a" * 64


def _versioned_manifest() -> dict[str, object]:
    text = (_PROJECT_ROOT / "manifests" / "source-manifest.json").read_text(
        encoding="utf-8"
    )
    return parse_manifest(text)


def _write_sha256sums(root: Path, entries: list[tuple[str, bytes]]) -> dict[str, str]:
    lines: list[str] = []
    mapping: dict[str, str] = {}
    for logical, payload in entries:
        digest = hashlib.sha256(payload).hexdigest()
        physical = f"inputs/private/{logical.removeprefix('inputs/')}"
        target = root / physical
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        lines.append(f"{digest}  {logical}")
        mapping[logical] = physical
    (root / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return mapping


class TestSourceManifest(unittest.TestCase):
    def test_real_corpus_has_fourteen_artifacts(self) -> None:
        manifest = _versioned_manifest()
        artifacts = artifacts_from_manifest(manifest)
        self.assertEqual(len(artifacts), 14)
        self.assertEqual(len(manifest["artifacts"]), 14)

    def test_round_trip_without_loss(self) -> None:
        manifest = _versioned_manifest()
        text = serialize_manifest(manifest)
        parsed = parse_manifest(text)
        rebuilt = artifacts_from_manifest(parsed)
        self.assertEqual(
            [item.to_manifest_item() for item in rebuilt],
            manifest["artifacts"],
        )

    def test_two_serializations_are_byte_identical(self) -> None:
        manifest = _versioned_manifest()
        first = serialize_manifest(manifest)
        second = serialize_manifest(manifest)
        self.assertEqual(first, second)

    def test_versioned_manifest_is_canonical(self) -> None:
        versioned = (_PROJECT_ROOT / "manifests" / "source-manifest.json").read_text(
            encoding="utf-8"
        )
        manifest = parse_manifest(versioned)
        self.assertEqual(versioned, serialize_manifest(manifest))

    def test_load_verified_manifest_with_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mapping = _write_sha256sums(
                root,
                [
                    ("inputs/demo/a.pdf", b"%PDF-a\n"),
                    ("inputs/demo/b.pdf", b"%PDF-b\n"),
                ],
            )
            artifacts, manifest = load_verified_manifest(
                root, path_mapping=mapping
            )
            self.assertEqual(len(artifacts), 2)
            self.assertEqual(
                [item.path for item in artifacts],
                ["inputs/demo/a.pdf", "inputs/demo/b.pdf"],
            )
            self.assertEqual(manifest["schema_version"], 1)

    def test_no_absolute_paths_or_volatile_fields(self) -> None:
        text = (_PROJECT_ROOT / "manifests" / "source-manifest.json").read_text(
            encoding="utf-8"
        )
        self.assertNotIn(":/", text)
        for forbidden in ("timestamp", "hostname", "mtime", "inode", "cwd"):
            self.assertNotIn(forbidden, text)

    def test_schema_rejects_incompatible_and_extra_fields(self) -> None:
        base = artifacts_from_manifest(_versioned_manifest())
        manifest = build_manifest_dict(base)
        bad_version = dict(manifest)
        bad_version["schema_version"] = 2
        with self.assertRaises(ManifestValidationError):
            validate_manifest_document(bad_version)

        extra_root = dict(manifest)
        extra_root["generated_at"] = "2026-01-01"
        with self.assertRaises(ManifestValidationError):
            validate_manifest_document(extra_root)

        extra_item = json.loads(serialize_manifest(manifest))
        extra_item["artifacts"][0]["note"] = "extra"
        with self.assertRaises(ManifestValidationError):
            validate_manifest_document(extra_item)

        wrong_type = json.loads(serialize_manifest(manifest))
        wrong_type["artifacts"][0]["size_bytes"] = 1.5
        with self.assertRaises(ManifestValidationError):
            validate_manifest_document(wrong_type)

        bool_size = json.loads(serialize_manifest(manifest))
        bool_size["artifacts"][0]["size_bytes"] = True
        with self.assertRaises(ManifestValidationError):
            validate_manifest_document(bool_size)

        decimal_size = json.loads(serialize_manifest(manifest))
        decimal_size["artifacts"][0]["size_bytes"] = Decimal("10")
        with self.assertRaises(ManifestValidationError):
            validate_manifest_document(decimal_size)

        bool_version = json.loads(serialize_manifest(manifest))
        bool_version["schema_version"] = True
        with self.assertRaises(ManifestValidationError):
            validate_manifest_document(bool_version)

    def test_source_artifact_rejects_invalid_contract_values(self) -> None:
        digest = "a" * 64
        with self.assertRaises(PathSecurityError):
            SourceArtifact(
                path="/etc/passwd",
                sha256=digest,
                size_bytes=10,
                media_type="application/pdf",
            )
        with self.assertRaises(ManifestValidationError):
            SourceArtifact(
                path="inputs/sample.xlsx",
                sha256=digest,
                size_bytes=10,
                media_type="application/pdf",
            )

    def test_schema_rejects_unsafe_paths_and_media_mismatch(self) -> None:
        base = artifacts_from_manifest(_versioned_manifest())
        manifest = build_manifest_dict(base)
        document = json.loads(serialize_manifest(manifest))

        absolute_path = json.loads(json.dumps(document))
        absolute_path["artifacts"][0]["path"] = "/inputs/sample.pdf"
        with self.assertRaises(ManifestValidationError):
            validate_manifest_document(absolute_path)

        traversal_path = json.loads(json.dumps(document))
        traversal_path["artifacts"][0]["path"] = "../inputs/sample.pdf"
        with self.assertRaises(ManifestValidationError):
            validate_manifest_document(traversal_path)

        mismatched_media = json.loads(json.dumps(document))
        mismatched_media["artifacts"][0]["media_type"] = "application/pdf"
        mismatched_media["artifacts"][0]["path"] = "inputs/sample.xlsx"
        with self.assertRaises(ManifestValidationError):
            validate_manifest_document(mismatched_media)

    def test_build_from_single_artifact(self) -> None:
        artifact = SourceArtifact(
            path="inputs/sample.pdf",
            sha256="a" * 64,
            size_bytes=10,
            media_type="application/pdf",
        )
        manifest = build_manifest_dict([artifact])
        self.assertEqual(manifest["schema_version"], 1)

    def test_every_schema_pattern_compiles_as_ecma262(self) -> None:
        patterns = collect_schema_patterns()
        self.assertGreaterEqual(len(patterns), 4)
        for pattern in patterns:
            with self.subTest(pattern=pattern):
                assert_ecma262_pattern(pattern)
        self.assertTrue(any(r"[Pp][Dd][Ff]" in pattern for pattern in patterns))
        self.assertTrue(any(r"[Xx][Ll][Ss][Xx]" in pattern for pattern in patterns))
        self.assertFalse(any("(?i)" in pattern for pattern in patterns))

    def test_ecma262_stdlib_rejects_python_inline_flags(self) -> None:
        with self.assertRaises(Ecma262PatternError):
            assert_ecma262_pattern(r"(?i)\.pdf$")
        with self.assertRaises(Ecma262PatternError):
            assert_ecma262_pattern(r"(?i)\.xlsx$")

    def test_json_schema_rejects_dot_component_unknown_extension_and_mismatch(
        self,
    ) -> None:
        valid_pdf = {
            "path": "inputs/sample.pdf",
            "sha256": _VALID_DIGEST,
            "size_bytes": 10,
            "media_type": "application/pdf",
        }
        validate_artifact_against_json_schema(valid_pdf)

        dot_only = dict(valid_pdf, path=".")
        with self.assertRaises(JsonSchemaArtifactError):
            validate_artifact_against_json_schema(dot_only)

        leading_dot_slash = dict(valid_pdf, path="./a.pdf")
        with self.assertRaises(JsonSchemaArtifactError):
            validate_artifact_against_json_schema(leading_dot_slash)

        dot_component = dict(valid_pdf, path="inputs/./a.pdf")
        with self.assertRaises(JsonSchemaArtifactError):
            validate_artifact_against_json_schema(dot_component)

        unknown_ext = dict(valid_pdf, path="inputs/sample.txt")
        with self.assertRaises(JsonSchemaArtifactError):
            validate_artifact_against_json_schema(unknown_ext)

        mismatched = dict(valid_pdf, path="inputs/sample.xlsx")
        with self.assertRaises(JsonSchemaArtifactError):
            validate_artifact_against_json_schema(mismatched)

    def test_json_schema_extension_case_and_media_type_mismatch(self) -> None:
        pdf_media = "application/pdf"
        xlsx_media = (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        cases = (
            ("inputs/sample.pdf", pdf_media, True),
            ("inputs/sample.PDF", pdf_media, True),
            ("inputs/sample.Pdf", pdf_media, True),
            ("inputs/sample.xlsx", xlsx_media, True),
            ("inputs/sample.XLSX", xlsx_media, True),
            ("inputs/sample.Xlsx", xlsx_media, True),
            ("inputs/sample.pdf", xlsx_media, False),
            ("inputs/sample.PDF", xlsx_media, False),
            ("inputs/sample.xlsx", pdf_media, False),
            ("inputs/sample.XLSX", pdf_media, False),
        )
        for path, media_type, accepted in cases:
            artifact = {
                "path": path,
                "sha256": _VALID_DIGEST,
                "size_bytes": 10,
                "media_type": media_type,
            }
            with self.subTest(path=path, media_type=media_type):
                if accepted:
                    validate_artifact_against_json_schema(artifact)
                else:
                    with self.assertRaises(JsonSchemaArtifactError):
                        validate_artifact_against_json_schema(artifact)

    def test_extension_only_paths_rejected_by_contract_and_schema(self) -> None:
        pdf_media = "application/pdf"
        xlsx_media = (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        cases = (
            (".pdf", pdf_media),
            (".xlsx", xlsx_media),
        )
        for path, media_type in cases:
            artifact = {
                "path": path,
                "sha256": _VALID_DIGEST,
                "size_bytes": 10,
                "media_type": media_type,
            }
            with self.subTest(path=path):
                with self.assertRaises(MediaTypeError):
                    SourceArtifact(
                        path=path,
                        sha256=_VALID_DIGEST,
                        size_bytes=10,
                        media_type=media_type,
                    )
                with self.assertRaises(ManifestValidationError):
                    validate_manifest_document(
                        {
                            "schema_version": 1,
                            "artifacts": [artifact],
                        }
                    )
                with self.assertRaises(JsonSchemaArtifactError):
                    validate_artifact_against_json_schema(artifact)

    def test_dotfile_relative_path_is_accepted_by_contract_and_schema(self) -> None:
        path = ".well-known/source.pdf"
        validate_relative_posix_path(path, context="dotfile")
        artifact = SourceArtifact(
            path=path,
            sha256=_VALID_DIGEST,
            size_bytes=10,
            media_type="application/pdf",
        )
        validate_artifact_against_json_schema(artifact.to_manifest_item())
        validate_manifest_document(build_manifest_dict([artifact]))

        for rejected in (".", "./a.pdf", "inputs/./a.pdf"):
            with self.subTest(path=rejected):
                with self.assertRaises(PathSecurityError):
                    validate_relative_posix_path(rejected, context="dot-component")
                with self.assertRaises(PathSecurityError):
                    SourceArtifact(
                        path=rejected,
                        sha256=_VALID_DIGEST,
                        size_bytes=10,
                        media_type="application/pdf",
                    )
                with self.assertRaises(JsonSchemaArtifactError):
                    validate_artifact_against_json_schema(
                        {
                            "path": rejected,
                            "sha256": _VALID_DIGEST,
                            "size_bytes": 10,
                            "media_type": "application/pdf",
                        }
                    )

    def test_real_manifest_artifacts_satisfy_json_schema(self) -> None:
        manifest = json.loads(
            (_PROJECT_ROOT / "manifests" / "source-manifest.json").read_text(
                encoding="utf-8"
            )
        )
        for artifact in manifest["artifacts"]:
            with self.subTest(path=artifact["path"]):
                validate_artifact_against_json_schema(artifact)

    def test_json_schema_rejects_identical_artifacts_and_accepts_canonical(
        self,
    ) -> None:
        schema = json.loads(
            (
                _PROJECT_ROOT / "schemas" / "source-manifest-v1.schema.json"
            ).read_text(encoding="utf-8")
        )
        self.assertIs(
            schema["properties"]["artifacts"]["uniqueItems"],
            True,
        )

        canonical = json.loads(
            (_PROJECT_ROOT / "manifests" / "source-manifest.json").read_text(
                encoding="utf-8"
            )
        )
        validate_manifest_against_json_schema(canonical)

        clone = dict(canonical["artifacts"][0])
        duplicates = {
            "schema_version": 1,
            "artifacts": [clone, dict(clone)],
        }
        with self.assertRaises(JsonSchemaManifestError):
            validate_manifest_against_json_schema(duplicates)
        with self.assertRaises(ManifestValidationError):
            validate_manifest_document(duplicates)


if __name__ == "__main__":
    unittest.main()
