"""Testes sintéticos do adapter de fixtures privadas (REPO-003A)."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
import zipfile
from pathlib import Path

# Compatível com o gate congelado (`PYTHONPATH=src`) e com o test.sh N+1
# (`PYTHONPATH=src:scripts/private-fixtures`).
REPO_ROOT = Path(__file__).resolve().parents[1]
_ADAPTER_PATH = REPO_ROOT / "scripts" / "private-fixtures"
if str(_ADAPTER_PATH) not in sys.path:
    sys.path.insert(0, str(_ADAPTER_PATH))

from adapter.config import (
    config_file_path,
    read_private_root,
    validate_private_root,
)
from adapter.errors import (
    ConfigError,
    InventoryError,
    MaterializeError,
    TaskMarkerError,
)
from adapter.inventory import (
    PrivateFixture,
    build_inventory_from_source_manifest,
    load_inventory,
    parse_inventory,
    serialize_inventory,
    validate_inventory_document,
)
from adapter.materialize import (
    materialize_fixtures,
    verify_materialized,
)
from adapter.task_marker import parse_task_marker
from nbr12721.sources.manifest import parse_manifest


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write(path: Path, data: bytes, mode: int = 0o644) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    os.chmod(path, mode)


def _synthetic_fixture(
    *,
    name: str = "sample.pdf",
    payload: bytes = b"%PDF-synthetic-1\n",
) -> tuple[PrivateFixture, bytes]:
    digest = _sha256(payload)
    store_path = f"demo/{name}"
    fixture = PrivateFixture(
        id=f"inputs/{store_path}",
        store_path=store_path,
        materialize_path=f"inputs/private/{store_path}",
        sha256=digest,
        size_bytes=len(payload),
        media_type="application/pdf",
    )
    return fixture, payload


def _ephemeral_under_inputs(work: Path) -> list[str]:
    inputs = work / "inputs"
    if not inputs.is_dir():
        return []
    found: list[str] = []
    for child in inputs.iterdir():
        name = child.name
        if name.startswith(".private-staging-") or name.startswith(
            ".private-backup-"
        ):
            found.append(name)
    return found


def _assert_no_private_bytes_in_git_status(work: Path) -> None:
    status = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all"],
        cwd=work,
        capture_output=True,
        text=True,
        check=True,
    )
    for line in status.stdout.splitlines():
        lowered = line.lower()
        assert "inputs/private" not in lowered, status.stdout
        assert ".private-staging-" not in lowered, status.stdout
        assert ".private-backup-" not in lowered, status.stdout


class TaskMarkerTests(unittest.TestCase):
    def test_none_and_required(self) -> None:
        none_text = "---\nid: T\nprivate_fixtures: none\n---\n\nbody\n"
        required_text = "---\nid: T\nprivate_fixtures: required\n---\n\nbody\n"
        self.assertEqual(parse_task_marker(none_text), "none")
        self.assertEqual(parse_task_marker(required_text), "required")

    def test_absent_marker_defaults_to_none(self) -> None:
        text = "---\nid: LEGACY\nstatus: ready\n---\n\nlegacy task\n"
        self.assertEqual(parse_task_marker(text), "none")
        self.assertEqual(parse_task_marker("# sem front matter\n"), "none")

    def test_duplicate_marker_fails(self) -> None:
        text = (
            "---\nid: T\nprivate_fixtures: none\n"
            "private_fixtures: required\n---\n"
        )
        with self.assertRaises(TaskMarkerError):
            parse_task_marker(text)

    def test_unknown_value_fails(self) -> None:
        text = "---\nid: T\nprivate_fixtures: maybe\n---\n"
        with self.assertRaises(TaskMarkerError):
            parse_task_marker(text)

    def test_misplaced_marker_outside_front_matter_fails(self) -> None:
        text = "---\nid: T\n---\n\nprivate_fixtures: required\n"
        with self.assertRaises(TaskMarkerError):
            parse_task_marker(text)

    def test_marker_inside_fence_in_body_is_ignored(self) -> None:
        text = (
            "---\nid: T\nprivate_fixtures: none\n---\n\n"
            "```yaml\nprivate_fixtures: required\n```\n"
        )
        self.assertEqual(parse_task_marker(text), "none")

    def test_quoted_values(self) -> None:
        text = "---\nid: T\nprivate_fixtures: \"required\"\n---\n"
        self.assertEqual(parse_task_marker(text), "required")

    def test_empty_marker_declaration_fails(self) -> None:
        for text in (
            "---\nid: T\nprivate_fixtures:\n---\n\nbody\n",
            "---\nid: T\nprivate_fixtures: \n---\n\nbody\n",
            "---\nid: T\nprivate_fixtures: \"\"\n---\n\nbody\n",
        ):
            with self.subTest(text=text):
                with self.assertRaises(TaskMarkerError):
                    parse_task_marker(text)

    def test_duplicate_including_empty_or_malformed_fails(self) -> None:
        cases = (
            "---\nid: T\nprivate_fixtures: none\nprivate_fixtures:\n---\n",
            "---\nid: T\nprivate_fixtures:\nprivate_fixtures: none\n---\n",
            "---\nid: T\nprivate_fixtures: required\nprivate_fixtures: \n---\n",
            "---\nid: T\nprivate_fixtures: none\nprivate_fixtures: maybe\n---\n",
        )
        for text in cases:
            with self.subTest(text=text):
                with self.assertRaises(TaskMarkerError):
                    parse_task_marker(text)

    def test_indented_marker_in_front_matter_fails(self) -> None:
        cases = (
            "---\nid: T\n private_fixtures: required\n---\n\nbody\n",
            "---\nid: T\n\tprivate_fixtures: none\n---\n\nbody\n",
            "---\nid: T\n  private_fixtures: required\n---\n\nbody\n",
        )
        for text in cases:
            with self.subTest(text=repr(text)):
                with self.assertRaises(TaskMarkerError):
                    parse_task_marker(text)

    def test_indented_marker_in_body_fails(self) -> None:
        text = "---\nid: T\n---\n\n private_fixtures: required\n"
        with self.assertRaises(TaskMarkerError):
            parse_task_marker(text)


class ConfigureHelperTests(unittest.TestCase):
    def test_configure_write_and_check_with_temp_xdg(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            store = tmp_path / "store"
            store.mkdir()
            xdg = tmp_path / "xdg"
            env = {
                **os.environ,
                "HOME": str(tmp_path / "home"),
                "XDG_CONFIG_HOME": str(xdg),
                "NBR12721_PRIVATE_INPUTS": str(store),
            }
            script = REPO_ROOT / "scripts/private-fixtures/configure.sh"
            write = subprocess.run(
                ["bash", str(script)],
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(write.returncode, 0, write.stderr)
            self.assertNotIn(str(store), write.stdout)
            cfg = xdg / "nbr12721" / "private-inputs-root"
            self.assertTrue(cfg.is_file())
            self.assertEqual(cfg.read_text(encoding="utf-8"), f"{store.resolve()}\n")
            self.assertEqual(stat.S_IMODE(cfg.stat().st_mode), 0o600)

            check = subprocess.run(
                ["bash", str(script), "--check"],
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(check.returncode, 0, check.stderr)

    def test_configure_rejects_relative_and_repo_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            xdg = tmp_path / "xdg"
            script = REPO_ROOT / "scripts/private-fixtures/configure.sh"
            env_base = {
                **os.environ,
                "HOME": str(tmp_path / "home"),
                "XDG_CONFIG_HOME": str(xdg),
            }
            relative = subprocess.run(
                ["bash", str(script)],
                cwd=REPO_ROOT,
                env={**env_base, "NBR12721_PRIVATE_INPUTS": "relative/path"},
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(relative.returncode, 0)

            repo = subprocess.run(
                ["bash", str(script)],
                cwd=REPO_ROOT,
                env={**env_base, "NBR12721_PRIVATE_INPUTS": str(REPO_ROOT)},
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(repo.returncode, 0)

            root = subprocess.run(
                ["bash", str(script)],
                cwd=REPO_ROOT,
                env={**env_base, "NBR12721_PRIVATE_INPUTS": "/"},
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(root.returncode, 0)

            missing = subprocess.run(
                ["bash", str(script)],
                cwd=REPO_ROOT,
                env={
                    **env_base,
                    "NBR12721_PRIVATE_INPUTS": str(tmp_path / "missing"),
                },
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(missing.returncode, 0)

    def test_configure_rejects_symlink_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            real = tmp_path / "real"
            real.mkdir()
            link = tmp_path / "link"
            link.symlink_to(real)
            xdg = tmp_path / "xdg"
            script = REPO_ROOT / "scripts/private-fixtures/configure.sh"
            result = subprocess.run(
                ["bash", str(script)],
                cwd=REPO_ROOT,
                env={
                    **os.environ,
                    "HOME": str(tmp_path / "home"),
                    "XDG_CONFIG_HOME": str(xdg),
                    "NBR12721_PRIVATE_INPUTS": str(link),
                },
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)

    def test_configure_rejects_symlink_root_with_trailing_slash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            real = tmp_path / "real"
            real.mkdir()
            link = tmp_path / "link-store"
            link.symlink_to(real)
            xdg = tmp_path / "xdg"
            script = REPO_ROOT / "scripts/private-fixtures/configure.sh"
            env = {
                **os.environ,
                "HOME": str(tmp_path / "home"),
                "XDG_CONFIG_HOME": str(xdg),
                "NBR12721_PRIVATE_INPUTS": str(link) + "/",
            }
            write = subprocess.run(
                ["bash", str(script)],
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(write.returncode, 0, write.stdout + write.stderr)

            cfg = xdg / "nbr12721" / "private-inputs-root"
            cfg.parent.mkdir(parents=True)
            cfg.write_text(f"{link}/\n", encoding="utf-8")
            check = subprocess.run(
                ["bash", str(script), "--check"],
                cwd=REPO_ROOT,
                env={
                    **os.environ,
                    "HOME": str(tmp_path / "home"),
                    "XDG_CONFIG_HOME": str(xdg),
                },
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(check.returncode, 0, check.stdout + check.stderr)

    def test_configure_rejects_carriage_return_in_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            # Directory name containing CR (newline-like / insecure).
            store = tmp_path / ("store\rname")
            store.mkdir()
            xdg = tmp_path / "xdg"
            script = REPO_ROOT / "scripts/private-fixtures/configure.sh"
            env = {
                **os.environ,
                "HOME": str(tmp_path / "home"),
                "XDG_CONFIG_HOME": str(xdg),
                "NBR12721_PRIVATE_INPUTS": str(store),
            }
            write = subprocess.run(
                ["bash", str(script)],
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(write.returncode, 0, write.stdout + write.stderr)

            cfg = xdg / "nbr12721" / "private-inputs-root"
            cfg.parent.mkdir(parents=True)
            cfg.write_text(f"{store.resolve()}\n", encoding="utf-8")
            check = subprocess.run(
                ["bash", str(script), "--check"],
                cwd=REPO_ROOT,
                env={
                    **os.environ,
                    "HOME": str(tmp_path / "home"),
                    "XDG_CONFIG_HOME": str(xdg),
                },
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(check.returncode, 0, check.stdout + check.stderr)

    def test_configure_check_rejects_double_slash_multiline_and_other_git(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            xdg = tmp_path / "xdg"
            cfg = xdg / "nbr12721" / "private-inputs-root"
            cfg.parent.mkdir(parents=True)
            script = REPO_ROOT / "scripts/private-fixtures/configure.sh"
            env = {
                **os.environ,
                "HOME": str(tmp_path / "home"),
                "XDG_CONFIG_HOME": str(xdg),
            }

            cfg.write_text("//\n", encoding="utf-8")
            slash = subprocess.run(
                ["bash", str(script), "--check"],
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(slash.returncode, 0, slash.stdout + slash.stderr)

            cfg.write_text("/tmp/a\n/tmp/b\n", encoding="utf-8")
            multiline = subprocess.run(
                ["bash", str(script), "--check"],
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(
                multiline.returncode, 0, multiline.stdout + multiline.stderr
            )

            other = tmp_path / "other-repo"
            other.mkdir()
            subprocess.run(
                ["git", "init"],
                cwd=other,
                check=True,
                capture_output=True,
            )
            write = subprocess.run(
                ["bash", str(script)],
                cwd=REPO_ROOT,
                env={**env, "NBR12721_PRIVATE_INPUTS": str(other)},
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(write.returncode, 0, write.stdout + write.stderr)

            cfg.write_text(f"{other.resolve()}\n", encoding="utf-8")
            check_other = subprocess.run(
                ["bash", str(script), "--check"],
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(
                check_other.returncode, 0, check_other.stdout + check_other.stderr
            )

    def test_configure_check_rejects_embedded_nul(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            store = tmp_path / "store"
            store.mkdir()
            xdg = tmp_path / "xdg"
            cfg = xdg / "nbr12721" / "private-inputs-root"
            cfg.parent.mkdir(parents=True)
            # Path válido + NUL + sufixo: mapfile/Bash truncariam e aceitariam.
            cfg.write_bytes(str(store.resolve()).encode("utf-8") + b"\x00suffix\n")
            script = REPO_ROOT / "scripts/private-fixtures/configure.sh"
            env = {
                **os.environ,
                "HOME": str(tmp_path / "home"),
                "XDG_CONFIG_HOME": str(xdg),
            }
            result = subprocess.run(
                ["bash", str(script), "--check"],
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            combined = result.stdout + result.stderr
            self.assertNotIn(str(store.resolve()), combined)

    def test_configure_sanitizes_inaccessible_root_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            store = tmp_path / "locked-store"
            store.mkdir()
            xdg = tmp_path / "xdg"
            cfg = xdg / "nbr12721" / "private-inputs-root"
            cfg.parent.mkdir(parents=True)
            resolved = str(store.resolve())
            cfg.write_text(f"{resolved}\n", encoding="utf-8")
            script = REPO_ROOT / "scripts/private-fixtures/configure.sh"
            env = {
                **os.environ,
                "HOME": str(tmp_path / "home"),
                "XDG_CONFIG_HOME": str(xdg),
            }
            os.chmod(store, 0o000)
            try:
                check = subprocess.run(
                    ["bash", str(script), "--check"],
                    cwd=REPO_ROOT,
                    env=env,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                write = subprocess.run(
                    ["bash", str(script)],
                    cwd=REPO_ROOT,
                    env={**env, "NBR12721_PRIVATE_INPUTS": resolved},
                    capture_output=True,
                    text=True,
                    check=False,
                )
            finally:
                os.chmod(store, 0o700)
            self.assertNotEqual(check.returncode, 0, check.stdout + check.stderr)
            self.assertNotEqual(write.returncode, 0, write.stdout + write.stderr)
            for result in (check, write):
                combined = result.stdout + result.stderr
                self.assertNotIn(resolved, combined)
                self.assertIn("ERROR:", combined)

    def test_read_private_root_python_helper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            store = tmp_path / "store"
            store.mkdir()
            xdg = tmp_path / "xdg"
            cfg = config_file_path(xdg_config_home=str(xdg))
            cfg.parent.mkdir(parents=True)
            cfg.write_text(f"{store.resolve()}\n", encoding="utf-8")
            loaded = read_private_root(xdg_config_home=str(xdg))
            self.assertEqual(loaded, store.resolve())
            with self.assertRaises(ConfigError):
                validate_private_root(Path("/"), repo_root=REPO_ROOT)
            with self.assertRaises(ConfigError):
                validate_private_root(Path("//"), repo_root=REPO_ROOT)
            with self.assertRaises(ConfigError):
                validate_private_root(REPO_ROOT, repo_root=REPO_ROOT)

            other = tmp_path / "git-checkout"
            other.mkdir()
            subprocess.run(
                ["git", "init"],
                cwd=other,
                check=True,
                capture_output=True,
            )
            with self.assertRaises(ConfigError):
                validate_private_root(other, repo_root=REPO_ROOT)

            cfg.write_text("/tmp/one\n/tmp/two\n", encoding="utf-8")
            with self.assertRaises(ConfigError):
                read_private_root(xdg_config_home=str(xdg))


class InventoryTests(unittest.TestCase):
    def test_tracked_inventory_matches_source_and_sums(self) -> None:
        inventory = load_inventory(REPO_ROOT)
        self.assertEqual(len(inventory), 14)
        source = parse_manifest(
            (REPO_ROOT / "manifests/source-manifest.json").read_text(
                encoding="utf-8"
            )
        )
        expected = build_inventory_from_source_manifest(source)
        actual_text = (REPO_ROOT / "manifests/private-fixtures-v1.json").read_text(
            encoding="utf-8"
        )
        self.assertEqual(actual_text, serialize_inventory(expected))
        self.assertTrue(actual_text.endswith("\n"))
        self.assertNotIn("/home/", actual_text)
        # IDs lógicos públicos não apontam mais para bytes rastreados.
        for fixture in inventory:
            tracked = REPO_ROOT / fixture.id
            self.assertFalse(
                tracked.exists(),
                f"path histórico ainda presente no working tree: {fixture.id}",
            )
            materialized = REPO_ROOT / fixture.materialize_path
            if materialized.is_file():
                self.assertEqual(materialized.stat().st_size, fixture.size_bytes)

    def test_inventory_rejects_traversal_and_bad_materialize(self) -> None:
        base = {
            "schema_version": 1,
            "fixtures": [
                {
                    "id": "inputs/demo/a.pdf",
                    "store_path": "../escape.pdf",
                    "materialize_path": "inputs/private/../escape.pdf",
                    "sha256": "0" * 64,
                    "size_bytes": 1,
                    "media_type": "application/pdf",
                }
            ],
        }
        with self.assertRaises(InventoryError):
            validate_inventory_document(base)

        base["fixtures"][0]["store_path"] = "demo/a.pdf"
        base["fixtures"][0]["materialize_path"] = "inputs/other/a.pdf"
        with self.assertRaises(InventoryError):
            validate_inventory_document(base)

    def test_inventory_rejects_duplicates(self) -> None:
        fixture, _ = _synthetic_fixture()
        doc = {
            "schema_version": 1,
            "fixtures": [fixture.to_dict(), fixture.to_dict()],
        }
        with self.assertRaises(InventoryError):
            validate_inventory_document(doc)

    def test_serialization_is_byte_stable(self) -> None:
        source = parse_manifest(
            (REPO_ROOT / "manifests/source-manifest.json").read_text(
                encoding="utf-8"
            )
        )
        first = serialize_inventory(build_inventory_from_source_manifest(source))
        second = serialize_inventory(parse_inventory(first))
        self.assertEqual(first, second)


class MaterializeTests(unittest.TestCase):
    def test_public_task_bootstrap_skips_private(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "work"
            self._init_mini_repo(work)
            env = {
                **os.environ,
                "AGENT_LOOP_WORKTREE": str(work),
                "AGENT_LOOP_TASK_FILE": str(work / "task.md"),
                "HOME": str(Path(tmp) / "home"),
                "XDG_CONFIG_HOME": str(Path(tmp) / "xdg"),
            }
            (work / "task.md").write_text(
                "---\nid: PUB\nprivate_fixtures: none\n---\n\npublic\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                ["bash", str(work / "scripts/agent-loop/bootstrap.sh")],
                cwd=work,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertFalse((work / "inputs/private").exists())

    def test_empty_marker_bootstrap_and_validate_gate_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "work"
            self._init_mini_repo(work)
            (work / "task.md").write_text(
                "---\nid: BAD\nprivate_fixtures:\n---\n\nempty marker\n",
                encoding="utf-8",
            )
            env = {
                **os.environ,
                "AGENT_LOOP_WORKTREE": str(work),
                "AGENT_LOOP_TASK_FILE": str(work / "task.md"),
                "HOME": str(Path(tmp) / "home"),
                "XDG_CONFIG_HOME": str(Path(tmp) / "xdg"),
            }
            bootstrap = subprocess.run(
                ["bash", str(work / "scripts/agent-loop/bootstrap.sh")],
                cwd=work,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(bootstrap.returncode, 0, bootstrap.stdout)
            self.assertIn("ERROR:", bootstrap.stderr)
            self.assertFalse((work / "inputs/private").exists())

            gate = subprocess.run(
                [
                    "python3",
                    str(work / "scripts/private-fixtures/validate-gate.py"),
                ],
                cwd=work,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(gate.returncode, 0, gate.stdout)
            self.assertIn("ERROR:", gate.stderr)

    def test_required_fails_without_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "work"
            self._init_mini_repo(work)
            (work / "task.md").write_text(
                "---\nid: PRIV\nprivate_fixtures: required\n---\n\npriv\n",
                encoding="utf-8",
            )
            env = {
                **os.environ,
                "AGENT_LOOP_WORKTREE": str(work),
                "AGENT_LOOP_TASK_FILE": str(work / "task.md"),
                "HOME": str(Path(tmp) / "home"),
                "XDG_CONFIG_HOME": str(Path(tmp) / "xdg"),
            }
            result = subprocess.run(
                ["bash", str(work / "scripts/agent-loop/bootstrap.sh")],
                cwd=work,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)

    def test_materialize_success_idempotent_readonly_no_source_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            store = tmp_path / "store"
            work = tmp_path / "work"
            self._init_mini_repo(work)
            fixture, payload = _synthetic_fixture()
            source = store / fixture.store_path
            _write(source, payload, 0o444)
            source_mtime = source.stat().st_mtime_ns
            source_mode = source.stat().st_mode

            for _ in range(3):
                result = materialize_fixtures(
                    repo_root=work,
                    private_root=store,
                    fixtures=[fixture],
                )
                self.assertEqual(result["copied"], 1)
                self.assertEqual(_ephemeral_under_inputs(work), [])
                _assert_no_private_bytes_in_git_status(work)

            dest = work / fixture.materialize_path
            self.assertTrue(dest.is_file())
            self.assertFalse(dest.is_symlink())
            self.assertEqual(dest.read_bytes(), payload)
            self.assertEqual(stat.S_IMODE(dest.stat().st_mode), 0o444)
            self.assertEqual(source.stat().st_mtime_ns, source_mtime)
            self.assertEqual(source.stat().st_mode, source_mode)
            verify_materialized(repo_root=work, fixtures=[fixture])

    def test_partial_failure_keeps_previous_destination(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            store = tmp_path / "store"
            work = tmp_path / "work"
            self._init_mini_repo(work)
            good, payload = _synthetic_fixture(name="good.pdf")
            _write(store / good.store_path, payload, 0o444)

            materialize_fixtures(
                repo_root=work,
                private_root=store,
                fixtures=[good],
            )
            dest = work / good.materialize_path
            self.assertEqual(dest.read_bytes(), payload)

            bad_payload = payload + b"-corrupt"
            bad = PrivateFixture(
                id=good.id,
                store_path=good.store_path,
                materialize_path=good.materialize_path,
                sha256=good.sha256,
                size_bytes=good.size_bytes,
                media_type=good.media_type,
            )
            os.chmod(store / good.store_path, 0o644)
            _write(store / good.store_path, bad_payload, 0o444)

            with self.assertRaises(MaterializeError):
                materialize_fixtures(
                    repo_root=work,
                    private_root=store,
                    fixtures=[bad],
                )

            self.assertTrue(dest.is_file())
            self.assertEqual(dest.read_bytes(), payload)
            self.assertEqual(_ephemeral_under_inputs(work), [])
            _assert_no_private_bytes_in_git_status(work)
            verify_materialized(repo_root=work, fixtures=[good])

    def test_short_copy_error_verifies_staging_before_promote(self) -> None:
        """Hash em memória não basta: staging é relido antes de promover."""
        import adapter.materialize as materialize_mod

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            store = tmp_path / "store"
            work = tmp_path / "work"
            self._init_mini_repo(work)
            good, payload = _synthetic_fixture(name="good.pdf")
            self.assertGreaterEqual(len(payload), 8)
            _write(store / good.store_path, payload, 0o444)

            materialize_fixtures(
                repo_root=work,
                private_root=store,
                fixtures=[good],
            )
            dest = work / good.materialize_path
            self.assertEqual(dest.read_bytes(), payload)

            real_one = materialize_mod._materialize_one

            def truncate_after_copy(**kwargs):
                real_one(**kwargs)
                staged = kwargs["staging_root"] / kwargs["fixture"].store_path
                data = staged.read_bytes()
                os.chmod(staged, 0o644)
                staged.write_bytes(data[: len(data) // 2])
                os.chmod(staged, 0o444)

            with unittest.mock.patch.object(
                materialize_mod, "_materialize_one", side_effect=truncate_after_copy
            ):
                with self.assertRaises(MaterializeError) as ctx:
                    materialize_fixtures(
                        repo_root=work,
                        private_root=store,
                        fixtures=[good],
                    )
            self.assertIn("staging", str(ctx.exception).lower())
            self.assertTrue(dest.is_file())
            self.assertEqual(dest.read_bytes(), payload)
            self.assertEqual(_ephemeral_under_inputs(work), [])
            verify_materialized(repo_root=work, fixtures=[good])

    def test_first_materialization_post_promote_verify_clears_destination(
        self,
    ) -> None:
        """Falha na verificação pós-promoção sem backup não deixa destino."""
        import adapter.materialize as materialize_mod

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            store = tmp_path / "store"
            work = tmp_path / "work"
            self._init_mini_repo(work)
            fixture, payload = _synthetic_fixture(name="first.pdf")
            _write(store / fixture.store_path, payload, 0o444)

            private_dir = work / "inputs" / "private"
            self.assertFalse(private_dir.exists())

            real_verify = materialize_mod._verify_fixture_tree

            def fail_after_promote(tree_root, fixtures, *, label):
                if label == "destino":
                    # Simula destino já promovido e inválido (ex.: digest).
                    target = tree_root / fixtures[0].store_path
                    os.chmod(target, 0o644)
                    target.write_bytes(b"corrupt")
                    os.chmod(target, 0o444)
                    raise MaterializeError(
                        f"digest divergente no destino: {fixtures[0].store_path!r}"
                    )
                return real_verify(tree_root, fixtures, label=label)

            with unittest.mock.patch.object(
                materialize_mod,
                "_verify_fixture_tree",
                side_effect=fail_after_promote,
            ):
                with self.assertRaises(MaterializeError) as ctx:
                    materialize_fixtures(
                        repo_root=work,
                        private_root=store,
                        fixtures=[fixture],
                    )
            self.assertIn("destino", str(ctx.exception).lower())
            self.assertFalse(private_dir.exists())
            self.assertEqual(_ephemeral_under_inputs(work), [])
            _assert_no_private_bytes_in_git_status(work)

    def test_rejects_symlink_fifo_directory_size_hash_and_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            store = tmp_path / "store"
            work = tmp_path / "work"
            work.mkdir()
            fixture, payload = _synthetic_fixture()

            # Symlink source
            real = store / "real.pdf"
            _write(real, payload)
            link = store / fixture.store_path
            link.parent.mkdir(parents=True, exist_ok=True)
            link.symlink_to(real)
            with self.assertRaises(MaterializeError):
                materialize_fixtures(
                    repo_root=work,
                    private_root=store,
                    fixtures=[fixture],
                )
            self.assertFalse((work / "inputs/private").exists())
            self.assertEqual(_ephemeral_under_inputs(work), [])

            # FIFO source
            if link.exists() or link.is_symlink():
                link.unlink()
            fifo = store / fixture.store_path
            fifo.parent.mkdir(parents=True, exist_ok=True)
            os.mkfifo(fifo)
            with self.assertRaises(MaterializeError):
                materialize_fixtures(
                    repo_root=work,
                    private_root=store,
                    fixtures=[fixture],
                )
            self.assertFalse((work / "inputs/private").exists())
            self.assertEqual(_ephemeral_under_inputs(work), [])
            fifo.unlink()

            # Directory where a regular file is required
            directory = store / fixture.store_path
            directory.mkdir(parents=True)
            with self.assertRaises(MaterializeError):
                materialize_fixtures(
                    repo_root=work,
                    private_root=store,
                    fixtures=[fixture],
                )
            self.assertFalse((work / "inputs/private").exists())
            self.assertEqual(_ephemeral_under_inputs(work), [])
            directory.rmdir()

            # Hash / size mismatch
            _write(store / fixture.store_path, payload + b"x")
            bad = PrivateFixture(
                id=fixture.id,
                store_path=fixture.store_path,
                materialize_path=fixture.materialize_path,
                sha256=fixture.sha256,
                size_bytes=len(payload),
                media_type=fixture.media_type,
            )
            with self.assertRaises(MaterializeError):
                materialize_fixtures(
                    repo_root=work,
                    private_root=store,
                    fixtures=[bad],
                )
            self.assertFalse((work / "inputs/private").exists())
            self.assertEqual(_ephemeral_under_inputs(work), [])

            # Missing entry
            missing = PrivateFixture(
                id="inputs/demo/missing.pdf",
                store_path="demo/missing.pdf",
                materialize_path="inputs/private/demo/missing.pdf",
                sha256=_sha256(b"missing"),
                size_bytes=7,
                media_type="application/pdf",
            )
            with self.assertRaises(MaterializeError):
                materialize_fixtures(
                    repo_root=work,
                    private_root=store,
                    fixtures=[missing],
                )
            self.assertEqual(_ephemeral_under_inputs(work), [])

            # Invalid path forms rejected by inventory validation
            invalid_docs = [
                {
                    "id": "inputs/demo/a.pdf",
                    "store_path": "/abs/a.pdf",
                    "materialize_path": "inputs/private/abs/a.pdf",
                    "sha256": "0" * 64,
                    "size_bytes": 1,
                    "media_type": "application/pdf",
                },
                {
                    "id": "inputs/demo/b.pdf",
                    "store_path": "demo\\b.pdf",
                    "materialize_path": "inputs/private/demo/b.pdf",
                    "sha256": "0" * 64,
                    "size_bytes": 1,
                    "media_type": "application/pdf",
                },
                {
                    "id": "inputs/demo/c.pdf",
                    "store_path": "demo//c.pdf",
                    "materialize_path": "inputs/private/demo/c.pdf",
                    "sha256": "0" * 64,
                    "size_bytes": 1,
                    "media_type": "application/pdf",
                },
                {
                    "id": "inputs/demo/d.pdf",
                    "store_path": "demo/./d.pdf",
                    "materialize_path": "inputs/private/demo/d.pdf",
                    "sha256": "0" * 64,
                    "size_bytes": 1,
                    "media_type": "application/pdf",
                },
                {
                    "id": "inputs/demo/e.pdf",
                    "store_path": "demo/../e.pdf",
                    "materialize_path": "inputs/private/demo/e.pdf",
                    "sha256": "0" * 64,
                    "size_bytes": 1,
                    "media_type": "application/pdf",
                },
            ]
            for entry in invalid_docs:
                with self.assertRaises(InventoryError):
                    validate_inventory_document(
                        {"schema_version": 1, "fixtures": [entry]}
                    )

    def test_gitignore_and_git_archive_exclude_private_copies(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            work = tmp_path / "repo"
            store = tmp_path / "store"
            self._init_mini_repo(work)
            fixture, payload = _synthetic_fixture(name="ignored.pdf")
            _write(store / fixture.store_path, payload)
            materialize_fixtures(
                repo_root=work,
                private_root=store,
                fixtures=[fixture],
            )
            dest = work / fixture.materialize_path
            self.assertTrue(dest.is_file())

            status = subprocess.run(
                ["git", "status", "--short", "--untracked-files=all"],
                cwd=work,
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertNotIn("inputs/private", status.stdout)

            check_ignore = subprocess.run(
                ["git", "check-ignore", "-v", str(dest.relative_to(work))],
                cwd=work,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(check_ignore.returncode, 0, check_ignore.stderr)

            archive = tmp_path / "tree.tar"
            subprocess.run(
                ["git", "archive", "--format=tar", "-o", str(archive), "HEAD"],
                cwd=work,
                check=True,
            )
            listing = subprocess.run(
                ["tar", "-tf", str(archive)],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertNotIn("inputs/private", listing.stdout)

            # Snapshot/diff style: git archive via zip also excludes ignored paths.
            zip_path = tmp_path / "tree.zip"
            subprocess.run(
                ["git", "archive", "--format=zip", "-o", str(zip_path), "HEAD"],
                cwd=work,
                check=True,
            )
            with zipfile.ZipFile(zip_path) as zf:
                names = zf.namelist()
            self.assertFalse(any(n.startswith("inputs/private/") for n in names))

    def test_inaccessible_store_component_sanitizes_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            store = tmp_path / "store"
            work = tmp_path / "work"
            work.mkdir()
            locked = store / "locked"
            locked.mkdir(parents=True)
            payload = b"secret-bytes"
            target = locked / "file.pdf"
            _write(target, payload, 0o444)
            fixture = PrivateFixture(
                id="inputs/demo/locked.pdf",
                store_path="locked/file.pdf",
                materialize_path="inputs/private/locked/file.pdf",
                sha256=_sha256(payload),
                size_bytes=len(payload),
                media_type="application/pdf",
            )
            root_text = str(store.resolve())
            os.chmod(locked, 0o000)
            try:
                with self.assertRaises(MaterializeError) as ctx:
                    materialize_fixtures(
                        repo_root=work,
                        private_root=store,
                        fixtures=[fixture],
                    )
                message = str(ctx.exception)
                self.assertNotIn(root_text, message)
                self.assertIn("inacessível", message.lower())

                # CLI: sem traceback com path absoluto do store.
                xdg = tmp_path / "xdg"
                cfg = xdg / "nbr12721" / "private-inputs-root"
                cfg.parent.mkdir(parents=True)
                cfg.write_text(f"{root_text}\n", encoding="utf-8")
                inv = {
                    "schema_version": 1,
                    "fixtures": [fixture.to_dict()],
                }
                (work / "manifests").mkdir(parents=True)
                (work / "manifests/private-fixtures-v1.json").write_text(
                    serialize_inventory(inv),
                    encoding="utf-8",
                )
                script = REPO_ROOT / "scripts/private-fixtures/materialize.py"
                result = subprocess.run(
                    ["python3", str(script)],
                    cwd=work,
                    env={
                        **os.environ,
                        "AGENT_LOOP_WORKTREE": str(work),
                        "HOME": str(tmp_path / "home"),
                        "XDG_CONFIG_HOME": str(xdg),
                        "PYTHONPATH": (
                            f"{REPO_ROOT / 'src'}:"
                            f"{REPO_ROOT / 'scripts' / 'private-fixtures'}"
                        ),
                    },
                    capture_output=True,
                    text=True,
                    check=False,
                )
            finally:
                os.chmod(locked, 0o700)
            self.assertNotEqual(result.returncode, 0)
            combined = result.stdout + result.stderr
            self.assertNotIn(root_text, combined)
            self.assertNotIn("PermissionError", combined)
            self.assertNotIn("Traceback", combined)
            self.assertIn("ERROR:", combined)

    def _init_mini_repo(self, work: Path) -> None:
        work.mkdir(parents=True)
        subprocess.run(["git", "init"], cwd=work, check=True, capture_output=True)
        (work / "scripts/agent-loop").mkdir(parents=True)
        (work / "scripts/private-fixtures").mkdir(parents=True)
        (work / "manifests").mkdir()
        (work / "src").mkdir()
        # Copy bootstrap and related scripts from real repo.
        for rel in (
            "scripts/agent-loop/bootstrap.sh",
            "scripts/private-fixtures/materialize.py",
            "scripts/private-fixtures/configure.sh",
            "scripts/private-fixtures/validate-gate.py",
            ".gitignore",
        ):
            src = REPO_ROOT / rel
            dst = work / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(src.read_bytes())
            if rel.endswith(".sh"):
                os.chmod(dst, 0o755)
        # Minimal inventory matching synthetic store is created per-test when needed.
        # For bootstrap none tests, provide empty-valid? Inventory must be non-empty.
        fixture, payload = _synthetic_fixture()
        inventory = {
            "schema_version": 1,
            "fixtures": [fixture.to_dict()],
        }
        (work / "manifests/private-fixtures-v1.json").write_text(
            serialize_inventory(inventory),
            encoding="utf-8",
        )
        # Provide importable packages: sources em src/ e adapter em scripts/.
        pkg_src = REPO_ROOT / "src" / "nbr12721"
        pkg_dst = work / "src" / "nbr12721"
        for path in pkg_src.rglob("*.py"):
            rel = path.relative_to(pkg_src)
            target = pkg_dst / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(path.read_bytes())
        adapter_src = REPO_ROOT / "scripts" / "private-fixtures" / "adapter"
        adapter_dst = work / "scripts" / "private-fixtures" / "adapter"
        for path in adapter_src.rglob("*.py"):
            rel = path.relative_to(adapter_src)
            target = adapter_dst / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(path.read_bytes())
        (work / "README.md").write_text("mini\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=work, check=True)
        subprocess.run(
            [
                "git",
                "-c",
                "user.email=test@example.com",
                "-c",
                "user.name=Test",
                "commit",
                "-m",
                "init",
            ],
            cwd=work,
            check=True,
            capture_output=True,
        )
        # silence unused
        _ = payload


class RuntimeSurfaceTests(unittest.TestCase):
    def test_nbr12721_public_surface_excludes_private_fixtures(self) -> None:
        import importlib

        module = importlib.import_module("nbr12721")
        public = [name for name in dir(module) if not name.startswith("_")]
        self.assertEqual(public, ["normative", "sources"])
        self.assertNotIn("private_fixtures", public)
        with self.assertRaises(ModuleNotFoundError):
            importlib.import_module("nbr12721.private_fixtures")


class ProfileCandidateTests(unittest.TestCase):
    def test_candidate_profile_has_no_private_env_requirement(self) -> None:
        import tomllib

        with (REPO_ROOT / ".agent-loop/project.toml").open("rb") as handle:
            profile = tomllib.load(handle)
        self.assertEqual(profile["environment"]["required"], [])
        commands = profile["validation"]["commands"]
        flat = [" ".join(cmd) for cmd in commands]
        self.assertTrue(
            any("validate-gate.py" in item for item in flat),
            flat,
        )
        self.assertFalse(
            any(item.startswith("sha256sum -c") for item in flat),
            flat,
        )
        self.assertFalse(
            any("validate-public-tree.py" in item for item in flat),
            flat,
        )
        self.assertNotIn("NBR12721_PRIVATE_INPUTS", json.dumps(profile))


class ValidateGateScriptTests(unittest.TestCase):
    def test_validate_gate_none_on_real_repo(self) -> None:
        env = {
            **os.environ,
            "AGENT_LOOP_WORKTREE": str(REPO_ROOT),
            "AGENT_LOOP_TASK_FILE": str(
                REPO_ROOT / "docs/tasks/REPO-003A.md"
            ),
        }
        result = subprocess.run(
            ["python3", "scripts/private-fixtures/validate-gate.py"],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("marker=none", result.stdout)

    def test_validate_gate_resolves_imports_from_worktree_when_frozen(
        self,
    ) -> None:
        source = REPO_ROOT / "scripts/private-fixtures/validate-gate.py"
        with tempfile.TemporaryDirectory() as tmp:
            frozen = (
                Path(tmp)
                / "control-adapter/files/scripts/private-fixtures/validate-gate.py"
            )
            frozen.parent.mkdir(parents=True)
            frozen.write_bytes(source.read_bytes())

            env = {
                **os.environ,
                "AGENT_LOOP_WORKTREE": str(REPO_ROOT),
                "AGENT_LOOP_TASK_FILE": str(
                    REPO_ROOT / "docs/tasks/ARCH-001.md"
                ),
                "PYTHONSAFEPATH": "1",
            }
            env.pop("PYTHONPATH", None)
            result = subprocess.run(
                [sys.executable, str(frozen)],
                cwd=tmp,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertNotIn("ModuleNotFoundError", result.stderr)
        self.assertIn("marker=none", result.stdout)


if __name__ == "__main__":
    unittest.main()
