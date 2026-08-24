"""Testes do envelope de artefato v1 (stdlib; dados sintéticos)."""

from __future__ import annotations

import copy
import hashlib
import json
import random
import unittest
from decimal import Decimal, localcontext
from pathlib import Path

from nbr12721.artifacts import (
    ARTIFACT_TYPES,
    ArtifactCanonicalJsonError,
    ArtifactDecimalError,
    ArtifactEnvelope,
    ArtifactSchemaVersionError,
    ArtifactValidationError,
    InputRef,
    ProducerRef,
    SourceRef,
    content_id,
    content_sha256_hex,
    decimal_to_canonical_string,
    dumps_canonical,
    is_canonical_decimal_string,
    loads_canonical,
    parse_canonical_decimal_string,
    parse_envelope,
    serialize_envelope,
    validate_envelope_document,
)
from nbr12721.sources.manifest import parse_manifest, serialize_manifest
from nbr12721.normative import load_versioned_index, serialize_index, baseline_index_document

from json_schema_support import (
    Ecma262PatternError,
    assert_ecma262_pattern,
    collect_schema_patterns,
    compile_ecma262_pattern,
)

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SCHEMA_PATH = _PROJECT_ROOT / "schemas" / "artifact-envelope-v1.schema.json"
_GOLDEN_DIR = _PROJECT_ROOT / "tests" / "fixtures" / "envelopes" / "v1"
_MANIFEST_PATH = _PROJECT_ROOT / "manifests" / "source-manifest.json"
_NORMATIVE_PATH = _PROJECT_ROOT / "registries" / "normative-reference-index.json"
_SOURCE_SCHEMA = _PROJECT_ROOT / "schemas" / "source-manifest-v1.schema.json"
_NORMATIVE_SCHEMA = (
    _PROJECT_ROOT / "schemas" / "normative-reference-index-v1.schema.json"
)
_PRIVATE_SCHEMA = _PROJECT_ROOT / "schemas" / "private-fixtures-v1.schema.json"

_DIGEST_A = "a" * 64
_DIGEST_B = "b" * 64
_DIGEST_C = "c" * 64
_DIGEST_D = "d" * 64

_SCHEMA = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


def _producer(**overrides: object) -> ProducerRef:
    base = {
        "name": "synthetic-producer",
        "version": "1.0.0",
        "configuration": {},
    }
    base.update(overrides)
    return ProducerRef(
        name=base["name"],  # type: ignore[arg-type]
        version=base["version"],  # type: ignore[arg-type]
        configuration=base["configuration"],  # type: ignore[arg-type]
    )


def _minimal_envelope(
    *,
    artifact_type: str = "extraction",
    sources: list[SourceRef] | None = None,
    inputs: list[InputRef] | None = None,
    payload: dict[str, object] | None = None,
    project_id: str = "project:synthetic-demo",
    producer: ProducerRef | None = None,
) -> ArtifactEnvelope:
    if sources is None:
        sources = [
            SourceRef(path="inputs/synthetic/demo.pdf", sha256=_DIGEST_A),
        ]
    if inputs is None:
        inputs = []
    if payload is None:
        payload = {}
    if producer is None:
        producer = _producer()
    return ArtifactEnvelope(
        schema_version=1,
        artifact_type=artifact_type,
        project_id=project_id,
        sources=tuple(sources),
        producer=producer,
        inputs=tuple(inputs),
        payload=payload,
    )


def _validate_against_schema(document: object) -> None:
    """Subset Draft 2020-12 alinhado ao schema versionado (stdlib)."""
    if type(document) is not dict:
        raise AssertionError("documento deve ser objeto")
    required = set(_SCHEMA["required"])
    props = _SCHEMA["properties"]
    if set(document.keys()) - set(props.keys()):
        raise AssertionError("campos desconhecidos")
    if required - set(document.keys()):
        raise AssertionError("campos ausentes")
    if document.get("schema_version") != 1:
        raise AssertionError("schema_version")
    artifact_type = document.get("artifact_type")
    if artifact_type not in _SCHEMA["$defs"]["artifact_type"]["enum"]:
        raise AssertionError("artifact_type")
    project_id = document.get("project_id")
    if type(project_id) is not str:
        raise AssertionError("project_id type")
    project_re = compile_ecma262_pattern(props["project_id"]["pattern"])
    if project_re.search(project_id) is None:
        raise AssertionError("project_id pattern")
    path_re = compile_ecma262_pattern(_SCHEMA["$defs"]["logical_path"]["pattern"])
    sha_re = compile_ecma262_pattern(_SCHEMA["$defs"]["sha256"]["pattern"])
    sources = document.get("sources")
    if type(sources) is not list:
        raise AssertionError("sources")
    seen_sources: set[str] = set()
    for item in sources:
        if type(item) is not dict or set(item) != {"path", "sha256"}:
            raise AssertionError("source shape")
        if path_re.search(item["path"]) is None:
            raise AssertionError("path")
        if sha_re.search(item["sha256"]) is None:
            raise AssertionError("sha")
        identity = json.dumps(item, sort_keys=True, separators=(",", ":"))
        if identity in seen_sources:
            raise AssertionError("source uniqueItems")
        seen_sources.add(identity)
    producer = document.get("producer")
    if type(producer) is not dict or set(producer) != {
        "name",
        "version",
        "configuration",
    }:
        raise AssertionError("producer")
    trimmed_re = compile_ecma262_pattern(
        _SCHEMA["$defs"]["producer_ref"]["properties"]["name"]["pattern"]
    )
    for field in ("name", "version"):
        if (
            type(producer[field]) is not str
            or trimmed_re.search(producer[field]) is None
        ):
            raise AssertionError(f"producer {field}")
    _validate_json_object(producer["configuration"])
    inputs = document.get("inputs")
    if type(inputs) is not list:
        raise AssertionError("inputs")
    seen_inputs: set[str] = set()
    for item in inputs:
        if type(item) is not dict or set(item) != {
            "artifact_type",
            "content_sha256",
        }:
            raise AssertionError("input shape")
        if item["artifact_type"] not in ARTIFACT_TYPES:
            raise AssertionError("input type")
        if sha_re.search(item["content_sha256"]) is None:
            raise AssertionError("input sha")
        identity = json.dumps(item, sort_keys=True, separators=(",", ":"))
        if identity in seen_inputs:
            raise AssertionError("input uniqueItems")
        seen_inputs.add(identity)
    _validate_json_object(document.get("payload"))


def _validate_json_object(value: object) -> None:
    if type(value) is not dict:
        raise AssertionError("JSON object")
    for key, item in value.items():
        if type(key) is not str:
            raise AssertionError("JSON key")
        _validate_json_value(item)


def _validate_json_value(value: object) -> None:
    if type(value) in (str, int, bool, type(None)):
        return
    if type(value) is list:
        for item in value:
            _validate_json_value(item)
        return
    if type(value) is dict:
        _validate_json_object(value)
        return
    raise AssertionError("JSON value")


class TestEnvelopeConstruction(unittest.TestCase):
    def test_each_artifact_type_minimal(self) -> None:
        for artifact_type in sorted(ARTIFACT_TYPES):
            env = _minimal_envelope(artifact_type=artifact_type)
            text = serialize_envelope(env)
            again = parse_envelope(text)
            self.assertEqual(serialize_envelope(again), text)
            self.assertTrue(text.endswith("\n"))
            self.assertFalse(text.endswith("\n\n"))

    def test_value_objects_immutable(self) -> None:
        source_payload = {"nested": {"items": [1, 2]}}
        source_config = {"options": {"enabled": True}}
        env = _minimal_envelope(
            payload=source_payload,
            producer=_producer(configuration=source_config),
        )
        original_id = content_id(env)
        with self.assertRaises(Exception):
            env.project_id = "x"  # type: ignore[misc]
        with self.assertRaises(Exception):
            env.sources[0].path = "y"  # type: ignore[misc]
        with self.assertRaises(TypeError):
            env.payload["new"] = 1  # type: ignore[index]
        with self.assertRaises(TypeError):
            env.payload["nested"]["items"][0] = 9  # type: ignore[index]
        with self.assertRaises(TypeError):
            env.producer.configuration["new"] = 1  # type: ignore[index]

        source_payload["nested"]["items"][0] = 9
        source_config["options"]["enabled"] = False
        self.assertEqual(content_id(env), original_id)
        self.assertEqual(env.to_dict()["payload"]["nested"]["items"], [1, 2])

    def test_schema_version_diagnostics(self) -> None:
        base = _minimal_envelope().to_dict()
        for bad in (None, True, False, 1.0, 0, -1, 2, "1"):
            doc = copy.deepcopy(base)
            doc["schema_version"] = bad
            with self.assertRaises(ArtifactSchemaVersionError) as ctx:
                validate_envelope_document(doc)
            message = str(ctx.exception)
            self.assertIn("recebido=", message)
            self.assertIn("suportado=", message)

        missing = copy.deepcopy(base)
        del missing["schema_version"]
        with self.assertRaises(ArtifactValidationError):
            validate_envelope_document(missing)

    def test_unknown_artifact_type(self) -> None:
        with self.assertRaises(ArtifactValidationError):
            _minimal_envelope(artifact_type="not-a-stage")

    def test_unknown_and_missing_fields(self) -> None:
        base = _minimal_envelope().to_dict()
        extra = copy.deepcopy(base)
        extra["hostname"] = "box"
        with self.assertRaises(ArtifactValidationError):
            validate_envelope_document(extra)
        producer_extra = copy.deepcopy(base)
        producer_extra["producer"]["pid"] = 1
        with self.assertRaises(ArtifactValidationError):
            validate_envelope_document(producer_extra)
        source_extra = copy.deepcopy(base)
        source_extra["sources"][0]["note"] = "x"
        with self.assertRaises(ArtifactValidationError):
            validate_envelope_document(source_extra)
        for key in list(base):
            broken = copy.deepcopy(base)
            del broken[key]
            with self.assertRaises(ArtifactValidationError):
                validate_envelope_document(broken)

    def test_empty_whitespace_and_coercion(self) -> None:
        with self.assertRaises(ArtifactValidationError):
            _minimal_envelope(project_id="")
        with self.assertRaises(ArtifactValidationError):
            _minimal_envelope(project_id="  ")
        with self.assertRaises(ArtifactValidationError):
            _minimal_envelope(project_id=" project:x ")
        with self.assertRaises(ArtifactValidationError):
            ProducerRef(name="", version="1", configuration={})
        with self.assertRaises(ArtifactValidationError):
            SourceRef(path="inputs/synthetic/demo.pdf", sha256=True)  # type: ignore[arg-type]

    def test_path_and_digest_validation(self) -> None:
        bad_paths = [
            "/abs/file.pdf",
            "../escape.pdf",
            "inputs\\win.pdf",
            "inputs/with\x00nul.pdf",
            "./relative.pdf",
            "inputs/./a.pdf",
        ]
        for path in bad_paths:
            with self.assertRaises(ArtifactValidationError):
                SourceRef(path=path, sha256=_DIGEST_A)
        with self.assertRaises(ArtifactValidationError):
            SourceRef(path="inputs/synthetic/demo.pdf", sha256="zz")
        with self.assertRaises(ArtifactValidationError):
            SourceRef(path="inputs/synthetic/demo.pdf", sha256="A" * 64)

    def test_duplicate_sources_and_inputs(self) -> None:
        with self.assertRaises(ArtifactValidationError):
            _minimal_envelope(
                sources=[
                    SourceRef(path="inputs/synthetic/a.pdf", sha256=_DIGEST_A),
                    SourceRef(path="inputs/synthetic/a.pdf", sha256=_DIGEST_B),
                ]
            )
        with self.assertRaises(ArtifactValidationError):
            _minimal_envelope(
                inputs=[
                    InputRef(artifact_type="page-profiles", content_sha256=_DIGEST_C),
                    InputRef(artifact_type="page-profiles", content_sha256=_DIGEST_C),
                ]
            )

    def test_payload_must_be_object(self) -> None:
        with self.assertRaises(ArtifactValidationError):
            ArtifactEnvelope(
                schema_version=1,
                artifact_type="extraction",
                project_id="project:x",
                sources=(SourceRef(path="inputs/synthetic/a.pdf", sha256=_DIGEST_A),),
                producer=_producer(),
                inputs=(),
                payload=[],  # type: ignore[arg-type]
            )


class TestCanonicalizationAndIdentity(unittest.TestCase):
    def test_key_order_independent(self) -> None:
        env = _minimal_envelope(
            payload={"z": 1, "a": {"y": 2, "b": 3}},
            producer=_producer(configuration={"z": True, "a": False}),
        )
        text = serialize_envelope(env)
        envelope_dict = env.to_dict()
        shuffled = {
            "payload": envelope_dict["payload"],
            "sources": [item.to_dict() for item in env.sources],
            "schema_version": 1,
            "producer": env.producer.to_dict(),
            "project_id": env.project_id,
            "inputs": [],
            "artifact_type": env.artifact_type,
        }
        self.assertEqual(serialize_envelope(shuffled), text)

    def test_sources_inputs_order_normalized(self) -> None:
        env_a = _minimal_envelope(
            sources=[
                SourceRef(path="inputs/synthetic/z.pdf", sha256=_DIGEST_A),
                SourceRef(path="inputs/synthetic/a.pdf", sha256=_DIGEST_B),
            ],
            inputs=[
                InputRef(artifact_type="project", content_sha256=_DIGEST_D),
                InputRef(artifact_type="page-profiles", content_sha256=_DIGEST_C),
            ],
        )
        env_b = _minimal_envelope(
            sources=[
                SourceRef(path="inputs/synthetic/a.pdf", sha256=_DIGEST_B),
                SourceRef(path="inputs/synthetic/z.pdf", sha256=_DIGEST_A),
            ],
            inputs=[
                InputRef(artifact_type="page-profiles", content_sha256=_DIGEST_C),
                InputRef(artifact_type="project", content_sha256=_DIGEST_D),
            ],
        )
        self.assertEqual(serialize_envelope(env_a), serialize_envelope(env_b))
        self.assertEqual(
            [item.path for item in env_a.sources],
            ["inputs/synthetic/a.pdf", "inputs/synthetic/z.pdf"],
        )

    def test_payload_array_order_significant(self) -> None:
        left = _minimal_envelope(payload={"items": [1, 2, 3]})
        right = _minimal_envelope(payload={"items": [3, 2, 1]})
        self.assertNotEqual(serialize_envelope(left), serialize_envelope(right))

    def test_round_trip_byte_stable(self) -> None:
        env = _minimal_envelope(payload={"list": [1, 2], "nested": {"k": "v"}})
        first = serialize_envelope(env)
        second = serialize_envelope(parse_envelope(first))
        third = serialize_envelope(parse_envelope(second))
        self.assertEqual(first, second)
        self.assertEqual(second, third)
        self.assertTrue(first.endswith("\n"))
        self.assertFalse(first.startswith("\ufeff"))

    def test_duplicate_key_and_bad_utf8(self) -> None:
        with self.assertRaises(ArtifactCanonicalJsonError):
            loads_canonical('{"a":1,"a":2}')
        with self.assertRaises(ArtifactCanonicalJsonError):
            loads_canonical(b"\xef\xbb\xbf{}")
        with self.assertRaises(ArtifactCanonicalJsonError):
            loads_canonical(b"\xff\xfe{}")
        with self.assertRaises(ArtifactCanonicalJsonError):
            loads_canonical('{"x":"\\ud800"}')

    def test_float_nan_inf_and_unsupported_types(self) -> None:
        with self.assertRaises(ArtifactCanonicalJsonError):
            dumps_canonical({"x": 1.5})
        with self.assertRaises(ArtifactCanonicalJsonError):
            loads_canonical('{"x":1.5}')
        with self.assertRaises(ArtifactCanonicalJsonError):
            loads_canonical('{"x":NaN}')
        with self.assertRaises(ArtifactCanonicalJsonError):
            dumps_canonical({"x": {1, 2}})
        with self.assertRaises(ArtifactCanonicalJsonError):
            dumps_canonical({"x": b"abc"})
        with self.assertRaises(ArtifactCanonicalJsonError):
            dumps_canonical({"x": "\ud800"})
        with self.assertRaises(ArtifactValidationError):
            _minimal_envelope(payload={"x": 1.25})

    def test_content_id_changes_with_stable_fields(self) -> None:
        base = _minimal_envelope()
        base_id = content_id(base)
        self.assertRegex(base_id, r"^sha256:[0-9a-f]{64}$")
        independent = hashlib.sha256(
            serialize_envelope(base).encode("utf-8")
        ).hexdigest()
        self.assertEqual(content_sha256_hex(base), independent)
        self.assertEqual(base_id, f"sha256:{independent}")

        variants = [
            _minimal_envelope(artifact_type="project"),
            _minimal_envelope(project_id="project:other"),
            _minimal_envelope(
                sources=[SourceRef(path="inputs/synthetic/other.pdf", sha256=_DIGEST_B)]
            ),
            _minimal_envelope(producer=_producer(version="1.0.1")),
            _minimal_envelope(producer=_producer(configuration={"mode": "x"})),
            _minimal_envelope(
                inputs=[InputRef(artifact_type="page-profiles", content_sha256=_DIGEST_C)]
            ),
            _minimal_envelope(payload={"k": 1}),
        ]
        for variant in variants:
            self.assertNotEqual(content_id(variant), base_id)


class TestDecimalString(unittest.TestCase):
    def test_table_cases(self) -> None:
        cases = [
            (Decimal("0"), "0"),
            (Decimal("-0.000"), "0"),
            (Decimal("12.3400"), "12.34"),
            (Decimal("1E+3"), "1000"),
            (Decimal("0.00100"), "0.001"),
        ]
        for value, expected in cases:
            self.assertEqual(decimal_to_canonical_string(value), expected)
            self.assertTrue(is_canonical_decimal_string(expected))
            self.assertEqual(parse_canonical_decimal_string(expected), Decimal(expected))

    def test_signs_integers_fractions_exponents(self) -> None:
        self.assertEqual(decimal_to_canonical_string(Decimal("-12.3400")), "-12.34")
        self.assertEqual(decimal_to_canonical_string(Decimal("42")), "42")
        self.assertEqual(decimal_to_canonical_string(Decimal("-0.5")), "-0.5")
        self.assertEqual(decimal_to_canonical_string(Decimal("1E-3")), "0.001")
        huge = decimal_to_canonical_string(Decimal("1E+40"))
        self.assertEqual(huge, "1" + "0" * 40)
        self.assertNotIn("E", huge.upper())
        tiny = decimal_to_canonical_string(Decimal("1E-12"))
        self.assertEqual(tiny, "0.000000000001")
        self.assertNotIn("E", tiny.upper())

    def test_conversion_preserves_value_independent_of_decimal_context(self) -> None:
        value = Decimal("12345678901234567890.123456789")
        with localcontext() as context:
            context.prec = 6
            text = decimal_to_canonical_string(value)
        self.assertEqual(text, "12345678901234567890.123456789")
        self.assertEqual(Decimal(text), value)

    def test_reject_non_finite_and_non_decimal(self) -> None:
        with self.assertRaises(ArtifactDecimalError):
            decimal_to_canonical_string(Decimal("NaN"))
        with self.assertRaises(ArtifactDecimalError):
            decimal_to_canonical_string(Decimal("Infinity"))
        with self.assertRaises(ArtifactDecimalError):
            decimal_to_canonical_string(Decimal("-Infinity"))
        with self.assertRaises(ArtifactDecimalError):
            decimal_to_canonical_string(1.5)  # type: ignore[arg-type]
        with self.assertRaises(ArtifactDecimalError):
            parse_canonical_decimal_string("1e3")
        with self.assertRaises(ArtifactDecimalError):
            parse_canonical_decimal_string("01")
        with self.assertRaises(ArtifactDecimalError):
            parse_canonical_decimal_string("1.10")

    def test_no_float_conversion_path(self) -> None:
        source = Path(
            _PROJECT_ROOT / "src" / "nbr12721" / "artifacts" / "decimal_string.py"
        ).read_text(encoding="utf-8")
        self.assertNotRegex(source, r"\bfloat\s*\(")
        self.assertNotIn("float(", decimal_to_canonical_string.__code__.co_names)
        value = Decimal("12345678901234567890.123456789")
        text = decimal_to_canonical_string(value)
        self.assertEqual(parse_canonical_decimal_string(text), Decimal(text))
        # float perderia precisão; a string canônica preserva dígitos.
        self.assertNotEqual(text, str(float(value)))


class TestSchemaGoldensAndRegression(unittest.TestCase):
    def test_all_goldens_validate_and_round_trip(self) -> None:
        files = sorted(_GOLDEN_DIR.glob("*.json"))
        self.assertEqual(len(files), 8)
        seen_types: set[str] = set()
        for path in files:
            raw = path.read_text(encoding="utf-8")
            env = parse_envelope(raw)
            seen_types.add(env.artifact_type)
            rebuilt = serialize_envelope(env)
            self.assertEqual(rebuilt, raw)
            document = env.to_dict()
            _validate_against_schema(document)
            validate_envelope_document(document)
        self.assertEqual(seen_types, set(ARTIFACT_TYPES))

    def test_schema_patterns_are_ecma262(self) -> None:
        patterns = collect_schema_patterns(_SCHEMA)
        self.assertGreaterEqual(len(patterns), 3)
        for pattern in patterns:
            assert_ecma262_pattern(pattern)
        with self.assertRaises(Ecma262PatternError):
            assert_ecma262_pattern("(?i)abc")

    def test_schema_and_python_agree_on_cases(self) -> None:
        good = _minimal_envelope().to_dict()
        validate_envelope_document(good)
        _validate_against_schema(good)

        bad_cases = [
            {**good, "schema_version": 2},
            {**good, "artifact_type": "nope"},
            {**good, "extra": 1},
            {**good, "sources": [{**good["sources"][0], "note": "x"}]},
            {**good, "payload": []},
            {**good, "payload": {"not_canonical": 1.5}},
            {
                **good,
                "producer": {
                    **good["producer"],
                    "name": " synthetic-producer ",
                },
            },
            {
                **good,
                "sources": [
                    {"path": "/abs.pdf", "sha256": _DIGEST_A},
                ],
            },
        ]
        for case in bad_cases:
            with self.assertRaises((ArtifactValidationError, ArtifactSchemaVersionError)):
                validate_envelope_document(case)
            with self.assertRaises(AssertionError):
                _validate_against_schema(case)

    def test_property_permutations_and_decimals(self) -> None:
        rng = random.Random(20260823)
        base_sources = [
            SourceRef(path="inputs/synthetic/a.pdf", sha256=_DIGEST_A),
            SourceRef(path="inputs/synthetic/b.pdf", sha256=_DIGEST_B),
            SourceRef(path="inputs/synthetic/c.pdf", sha256=_DIGEST_C),
        ]
        base_inputs = [
            InputRef(artifact_type="page-profiles", content_sha256=_DIGEST_D),
            InputRef(artifact_type="extraction", content_sha256=_DIGEST_A),
        ]
        canonical = serialize_envelope(
            _minimal_envelope(sources=base_sources, inputs=base_inputs)
        )
        for _ in range(20):
            sources = list(base_sources)
            inputs = list(base_inputs)
            rng.shuffle(sources)
            rng.shuffle(inputs)
            text = serialize_envelope(
                _minimal_envelope(sources=sources, inputs=inputs)
            )
            self.assertEqual(text, canonical)

        for _ in range(30):
            scale = rng.randint(-12, 12)
            coeff = Decimal(rng.randint(-10_000, 10_000))
            if coeff == 0:
                value = Decimal("0")
            else:
                value = coeff.scaleb(scale)
            text = decimal_to_canonical_string(value)
            self.assertTrue(is_canonical_decimal_string(text))
            self.assertEqual(decimal_to_canonical_string(Decimal(text)), text)
            self.assertNotIn("e", text.lower())
            self.assertNotIn("+", text)

    def test_preexisting_artifacts_byte_identical(self) -> None:
        manifest_text = _MANIFEST_PATH.read_text(encoding="utf-8")
        normative_text = _NORMATIVE_PATH.read_text(encoding="utf-8")
        self.assertEqual(
            serialize_manifest(parse_manifest(manifest_text)),
            manifest_text,
        )
        self.assertEqual(
            serialize_index(load_versioned_index(_PROJECT_ROOT)),
            normative_text,
        )
        self.assertEqual(
            serialize_index(baseline_index_document()),
            normative_text,
        )
        # Schemas e manifests pré-existentes não foram reescritos.
        for path in (
            _MANIFEST_PATH,
            _NORMATIVE_PATH,
            _SOURCE_SCHEMA,
            _NORMATIVE_SCHEMA,
            _PRIVATE_SCHEMA,
        ):
            self.assertTrue(path.is_file())
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(len(digest), 64)

    def test_goldens_are_synthetic_only(self) -> None:
        private_markers = (
            "AY0410",
            "inputs/private/",
            "76b3c72fd5934867305b2440c3af66ef79004c07496c436095516c3afdc05674",
            "6ad3eb9b849e34cc7a419e0954d7ed817a9659d56fb213b36d83b4e78c38d19b",
        )
        for path in _GOLDEN_DIR.glob("*.json"):
            text = path.read_text(encoding="utf-8")
            for marker in private_markers:
                self.assertNotIn(marker, text)


class TestOperationalMetadataBoundary(unittest.TestCase):
    def test_operational_fields_rejected_in_envelope(self) -> None:
        base = _minimal_envelope().to_dict()
        for field, value in (
            ("created_at", "2026-08-23T00:00:00Z"),
            ("hostname", "box"),
            ("duration_ms", 12),
            ("run_id", "abc"),
        ):
            doc = copy.deepcopy(base)
            doc[field] = value
            with self.assertRaises(ArtifactValidationError):
                validate_envelope_document(doc)


if __name__ == "__main__":
    unittest.main()
