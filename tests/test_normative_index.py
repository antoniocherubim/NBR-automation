"""Testes do índice normativo v1 (stdlib; sem store privado)."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from nbr12721.normative import (
    NormativeDigestMismatchError,
    NormativeReference,
    NormativeValidationError,
    PageLocator,
    PrintedPage,
    assert_matches_source_manifest,
    baseline_index_document,
    baseline_references,
    build_index_dict,
    load_versioned_index,
    parse_index,
    serialize_index,
    validate_index_document,
)
from nbr12721.normative.catalog import baseline_source_and_references
from nbr12721.normative.source import baseline_normative_source
from nbr12721.normative.vocab import EXPECTED_SHA256, SOURCE_ID

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_INDEX_PATH = _PROJECT_ROOT / "registries" / "normative-reference-index.json"
_SCHEMA_PATH = (
    _PROJECT_ROOT / "schemas" / "normative-reference-index-v1.schema.json"
)
_MANIFEST_PATH = _PROJECT_ROOT / "manifests" / "source-manifest.json"

_REQUIRED_SECTIONS = frozenset(
    {
        "Capa / identificação da edição",
        "Prefácio",
        "3.7",
        "3.7.2.1",
        "3.7.2.2",
        "3.7.2.2.1",
        "3.7.2.2.2",
        "3.7.2.2.3",
        "3.7.3",
        "3.7.4",
        "3.14",
        "5.2",
        "5.3",
        "5.4",
        "5.5",
        "5.6",
        "5.7",
        "5.7.1",
        "5.7.2",
        "5.7.3",
        "5.8.1",
        "5.8.2",
        "5.8.3",
        "5.8.3 nota de seleção IV-B / IV-B-1",
        "Anexo A",
        "Anexo A / Quadro I",
        "Anexo A / Quadro II",
        "Anexo A / Quadro IV-B",
        "Anexo A / Quadro IV-B-1",
    }
)


def _versioned() -> dict[str, object]:
    return parse_index(_INDEX_PATH.read_text(encoding="utf-8"))


def _synthetic_valid_entry(
    *,
    entry_id: str = "nbr12721:2006:vc3:synth-a",
    section: str = "synth",
) -> NormativeReference:
    return NormativeReference(
        id=entry_id,
        source_id=SOURCE_ID,
        section=section,
        locator=PageLocator(
            pdf_page=2,
            printed_page=PrintedPage(kind="roman", label="ii"),
        ),
        reference_type="definition_classification",
        formalization_state="indexed",
        description="Entrada sintética apenas para testes públicos.",
        edition_notes="",
        cross_references=(),
        authority_refs=(),
    )


class TestNormativeIndexBaseline(unittest.TestCase):
    def test_edition_identity_and_digest(self) -> None:
        doc = _versioned()
        source = doc["source"]
        assert isinstance(source, dict)
        self.assertEqual(source["year"], 2006)
        self.assertEqual(source["corrected_version"], 3)
        self.assertEqual(source["corrected_version_date"], "2021-01-19")
        self.assertEqual(source["sha256"], EXPECTED_SHA256)
        self.assertNotEqual(source["year"], 2021)
        errata = source["errata"]
        assert isinstance(errata, list)
        labels = {item["label"] for item in errata}
        self.assertEqual(labels, {"Errata 1", "Errata 2", "Errata 3"})

    def test_required_section_coverage(self) -> None:
        sections = {ref.section for ref in baseline_references()}
        self.assertEqual(sections, _REQUIRED_SECTIONS)
        states = {ref.formalization_state for ref in baseline_references()}
        self.assertEqual(states, {"indexed"})

    def test_pdf_and_printed_pages_are_distinct(self) -> None:
        cover = next(
            ref for ref in baseline_references() if ref.id.endswith("cover-identity")
        )
        self.assertEqual(cover.locator.pdf_page, 1)
        self.assertEqual(cover.locator.printed_page.kind, "absent")
        self.assertIsNotNone(cover.locator.printed_page.reason)
        preface = next(
            ref for ref in baseline_references() if ref.id.endswith(":preface")
        )
        self.assertEqual(preface.locator.pdf_page, 6)
        self.assertEqual(preface.locator.printed_page.label, "vi")
        self.assertNotEqual(
            str(preface.locator.pdf_page),
            preface.locator.printed_page.label,
        )

    def test_versioned_matches_reconstruction_byte_identical(self) -> None:
        versioned = _INDEX_PATH.read_text(encoding="utf-8")
        rebuilt = serialize_index(baseline_index_document())
        self.assertEqual(versioned, rebuilt)
        self.assertEqual(
            serialize_index(baseline_index_document()),
            serialize_index(baseline_index_document()),
        )

    def test_round_trip_without_loss(self) -> None:
        original = _versioned()
        text = serialize_index(original)
        parsed = parse_index(text)
        self.assertEqual(parsed, original)

    def test_matches_source_manifest_digest(self) -> None:
        doc = _versioned()
        manifest = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
        assert_matches_source_manifest(doc, manifest)

    def test_digest_mismatch_fails(self) -> None:
        doc = copy.deepcopy(_versioned())
        source = doc["source"]
        assert isinstance(source, dict)
        source["sha256"] = "a" * 64
        with self.assertRaises(NormativeValidationError):
            validate_index_document(doc)
        # Documento estruturalmente válido com digest divergente do manifest.
        good = _versioned()
        bad_manifest = {
            "schema_version": 1,
            "artifacts": [
                {
                    "path": "inputs/normativa/ABNT NBR 12721-2006.pdf",
                    "sha256": "b" * 64,
                    "size_bytes": 1208230,
                    "media_type": "application/pdf",
                }
            ],
        }
        with self.assertRaises(NormativeDigestMismatchError):
            assert_matches_source_manifest(good, bad_manifest)

    def test_no_volatile_fields_or_absolute_paths(self) -> None:
        text = _INDEX_PATH.read_text(encoding="utf-8")
        for forbidden in (
            "timestamp",
            "hostname",
            "mtime",
            "generated_at",
            "/home/",
            "/Users/",
            "/tmp/",
        ):
            self.assertNotIn(forbidden, text)
        self.assertNotIn("inputs/private/", text)

    def test_schema_file_is_draft_2020_12(self) -> None:
        schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertEqual(
            schema["$schema"],
            "https://json-schema.org/draft/2020-12/schema",
        )
        self.assertFalse(schema.get("additionalProperties", True))


class TestNormativeIndexValidation(unittest.TestCase):
    def test_duplicate_id_fails(self) -> None:
        source = baseline_normative_source()
        a = _synthetic_valid_entry()
        b = _synthetic_valid_entry(section="other")
        with self.assertRaises(NormativeValidationError):
            build_index_dict(source=source, references=[a, b])

    def test_unknown_source_id_fails(self) -> None:
        with self.assertRaises(NormativeValidationError):
            NormativeReference(
                id="nbr12721:2006:vc3:synth-b",
                source_id="unknown-source",
                section="x",
                locator=PageLocator(
                    pdf_page=1,
                    printed_page=PrintedPage(
                        kind="absent",
                        reason="fixture sintética",
                    ),
                ),
                reference_type="definition_classification",
                formalization_state="indexed",
                description="sintético",
                edition_notes="",
                cross_references=(),
                authority_refs=(),
            )

    def test_empty_section_fails(self) -> None:
        with self.assertRaises(NormativeValidationError):
            _synthetic_valid_entry(section="   ")

    def test_pdf_page_zero_negative_bool_fail(self) -> None:
        with self.assertRaises(NormativeValidationError):
            PageLocator(
                pdf_page=0,
                printed_page=PrintedPage(kind="arabic", label="1"),
            )
        with self.assertRaises(NormativeValidationError):
            PageLocator(
                pdf_page=-1,
                printed_page=PrintedPage(kind="arabic", label="1"),
            )
        with self.assertRaises(NormativeValidationError):
            PageLocator(
                pdf_page=True,  # type: ignore[arg-type]
                printed_page=PrintedPage(kind="arabic", label="1"),
            )

    def test_printed_absent_requires_reason(self) -> None:
        with self.assertRaises(NormativeValidationError):
            PrintedPage(kind="absent", reason="")
        with self.assertRaises(NormativeValidationError):
            PrintedPage(kind="absent", reason=None)
        ok = PrintedPage(kind="absent", reason="capa sem foliação")
        self.assertEqual(ok.kind, "absent")

    def test_unknown_type_state_and_field_fail(self) -> None:
        doc = copy.deepcopy(_versioned())
        refs = doc["references"]
        assert isinstance(refs, list)
        first = refs[0]
        assert isinstance(first, dict)
        first["reference_type"] = "not-a-type"
        with self.assertRaises(NormativeValidationError):
            validate_index_document(doc)

        doc2 = copy.deepcopy(_versioned())
        refs2 = doc2["references"]
        assert isinstance(refs2, list)
        first2 = refs2[0]
        assert isinstance(first2, dict)
        first2["formalization_state"] = "draft"
        with self.assertRaises(NormativeValidationError):
            validate_index_document(doc2)

        doc3 = copy.deepcopy(_versioned())
        doc3["unexpected"] = True
        with self.assertRaises(NormativeValidationError):
            validate_index_document(doc3)

        doc4 = copy.deepcopy(_versioned())
        refs4 = doc4["references"]
        assert isinstance(refs4, list)
        first4 = refs4[0]
        assert isinstance(first4, dict)
        first4["extra_field"] = "nope"
        with self.assertRaises(NormativeValidationError):
            validate_index_document(doc4)

    def test_formalized_and_implemented_require_links(self) -> None:
        base_kwargs = dict(
            id="nbr12721:2006:vc3:synth-c",
            source_id=SOURCE_ID,
            section="synth",
            locator=PageLocator(
                pdf_page=3,
                printed_page=PrintedPage(kind="roman", label="iii"),
            ),
            reference_type="form_table",
            description="Sintético formalizado/implementado.",
            edition_notes="",
            cross_references=(),
            authority_refs=(),
        )
        with self.assertRaises(NormativeValidationError):
            NormativeReference(
                formalization_state="formalized",
                **base_kwargs,
            )
        with self.assertRaises(NormativeValidationError):
            NormativeReference(
                formalization_state="implemented",
                formal_artifact_ref="schemas/example.json",
                **base_kwargs,
            )
        formalized = NormativeReference(
            formalization_state="formalized",
            formal_artifact_ref="schemas/example.json",
            **base_kwargs,
        )
        self.assertEqual(formalized.formalization_state, "formalized")
        implemented = NormativeReference(
            id="nbr12721:2006:vc3:synth-d",
            source_id=SOURCE_ID,
            section="synth-impl",
            locator=PageLocator(
                pdf_page=4,
                printed_page=PrintedPage(kind="roman", label="iv"),
            ),
            reference_type="form_table",
            formalization_state="implemented",
            description="Sintético implementado.",
            edition_notes="",
            cross_references=(),
            authority_refs=(),
            formal_artifact_ref="schemas/example.json",
            implementation_ref="src/example.py",
        )
        self.assertEqual(implemented.formalization_state, "implemented")

    def test_incompatible_schema_version_fails(self) -> None:
        doc = copy.deepcopy(_versioned())
        doc["schema_version"] = 2
        with self.assertRaises(NormativeValidationError):
            validate_index_document(doc)
        doc["schema_version"] = True
        with self.assertRaises(NormativeValidationError):
            validate_index_document(doc)

    def test_missing_cross_reference_fails(self) -> None:
        source = baseline_normative_source()
        orphan = NormativeReference(
            id="nbr12721:2006:vc3:synth-e",
            source_id=SOURCE_ID,
            section="synth",
            locator=PageLocator(
                pdf_page=5,
                printed_page=PrintedPage(kind="roman", label="v"),
            ),
            reference_type="definition_classification",
            formalization_state="indexed",
            description="Aponta para id inexistente.",
            edition_notes="",
            cross_references=("nbr12721:2006:vc3:does-not-exist",),
            authority_refs=(),
        )
        with self.assertRaises(NormativeValidationError):
            build_index_dict(source=source, references=[orphan])

    def test_reconstruction_does_not_write_under_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inputs = root / "inputs"
            inputs.mkdir()
            before = {p.name for p in inputs.iterdir()}
            _ = baseline_index_document()
            _ = serialize_index(baseline_index_document())
            after = {p.name for p in inputs.iterdir()}
            self.assertEqual(before, after)

    def test_load_versioned_index_from_repo(self) -> None:
        loaded = load_versioned_index(_PROJECT_ROOT)
        self.assertEqual(loaded["schema_version"], 1)
        refs = loaded["references"]
        assert isinstance(refs, list)
        self.assertEqual(len(refs), 29)

    def test_baseline_helper_returns_source_and_refs(self) -> None:
        source, refs = baseline_source_and_references()
        self.assertEqual(source.id, SOURCE_ID)
        self.assertEqual(len(refs), 29)


class TestNormativeIndexHardening(unittest.TestCase):
    def test_json_scalars_are_not_coerced_to_strings(self) -> None:
        cases: list[tuple[list[str], object]] = [
            (["source", "errata", "0", "label"], 1),
            (["references", "0", "section"], 37),
            (["references", "0", "description"], True),
            (["references", "0", "locator", "printed_page", "label"], 65),
        ]
        for path, replacement in cases:
            with self.subTest(path=path):
                doc = copy.deepcopy(_versioned())
                target: object = doc
                for component in path[:-1]:
                    if isinstance(target, dict):
                        target = target[component]
                    else:
                        assert isinstance(target, list)
                        target = target[int(component)]
                assert isinstance(target, dict)
                target[path[-1]] = replacement
                with self.assertRaises(NormativeValidationError):
                    validate_index_document(doc)

    def test_direct_contracts_reject_wrong_nested_types(self) -> None:
        with self.assertRaises(NormativeValidationError):
            PrintedPage(kind=["arabic"], label="1")  # type: ignore[arg-type]
        with self.assertRaises(NormativeValidationError):
            PageLocator(pdf_page=1, printed_page={})  # type: ignore[arg-type]

    def test_duplicate_json_key_fails_closed(self) -> None:
        with self.assertRaises(NormativeValidationError):
            parse_index("{\"schema_version\":1,\"schema_version\":1}")

    def test_link_order_is_canonical(self) -> None:
        left = NormativeReference(
            id="nbr12721:2006:vc3:synth-order",
            source_id=SOURCE_ID,
            section="synth",
            locator=PageLocator(
                pdf_page=2,
                printed_page=PrintedPage(kind="arabic", label="1"),
            ),
            reference_type="definition_classification",
            formalization_state="indexed",
            description="Sintético para ordenação.",
            edition_notes="",
            cross_references=(
                "nbr12721:2006:vc3:z",
                "nbr12721:2006:vc3:a",
            ),
            authority_refs=(),
        )
        right = NormativeReference(
            id=left.id,
            source_id=left.source_id,
            section=left.section,
            locator=left.locator,
            reference_type=left.reference_type,
            formalization_state=left.formalization_state,
            description=left.description,
            edition_notes=left.edition_notes,
            cross_references=tuple(reversed(left.cross_references)),
            authority_refs=(),
        )
        self.assertEqual(left.to_dict(), right.to_dict())

    def test_parking_roles_have_unambiguous_pages(self) -> None:
        by_section = {ref.section: ref for ref in baseline_references()}
        self.assertEqual(by_section["3.7.2.2.1"].locator.pdf_page, 11)
        self.assertEqual(by_section["3.7.2.2.2"].locator.pdf_page, 11)
        self.assertEqual(by_section["3.7.2.2.3"].locator.pdf_page, 12)

    def test_schema_pins_source_identity(self) -> None:
        schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
        source = schema["$defs"]["normative_source"]["properties"]
        self.assertEqual(source["publication_date"]["const"], "2006-08-28")
        self.assertEqual(source["sha256"]["const"], EXPECTED_SHA256)
        self.assertEqual(source["errata"]["minItems"], 3)
        self.assertEqual(source["errata"]["maxItems"], 3)


if __name__ == "__main__":
    unittest.main()
