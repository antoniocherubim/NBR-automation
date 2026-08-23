"""Validação offline da workflow CI e ensaio local de artifact.zip sanitizado."""

from __future__ import annotations

import hashlib
import importlib.util
import re
import subprocess
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "validate-and-package.yml"
VALIDATE_SCRIPT = REPO_ROOT / "scripts" / "ci" / "validate-artifact-zip.py"
PUBLIC_TREE_SCRIPT = REPO_ROOT / "scripts" / "ci" / "validate-public-tree.py"

CHECKOUT_SHA = "de0fac2e4500dabe0009e67214ff5f5447ce83dd"
UPLOAD_SHA = "043fb46d1a93c77aae656e7c1c64a875d1fc6a0a"

FORBIDDEN_TRIGGER_TOKENS = (
    "pull_request:",
    "pull_request_target:",
    "schedule:",
    "release:",
    "workflow_call:",
    "repository_dispatch:",
)

FORBIDDEN_COMMAND_PATTERNS = (
    re.compile(r"\bpip\s+install\b"),
    re.compile(r"\bapt-get\b"),
    re.compile(r"\bapt\s+install\b"),
    re.compile(r"\bcurl\b"),
    re.compile(r"\bwget\b"),
)

FLOATING_ACTION_REF = re.compile(
    r"uses:\s*actions/(checkout|upload-artifact)@(main|master|v\d+(?:\.\d+)?)\b"
)


def read_workflow() -> str:
    return WORKFLOW_PATH.read_text(encoding="utf-8")


def _load_candidate_snapshot():
    import sys

    helper = str(REPO_ROOT / "scripts" / "ci")
    src = str(REPO_ROOT / "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    if helper not in sys.path:
        sys.path.insert(0, helper)
    import candidate_snapshot

    return candidate_snapshot


class CiWorkflowStaticTests(unittest.TestCase):
    """Checagens estruturais da workflow sem parser YAML externo."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = read_workflow()
        cls.lines = cls.workflow.splitlines()

    def test_workflow_file_exists_and_is_utf8(self) -> None:
        self.assertTrue(WORKFLOW_PATH.is_file())
        self.assertTrue(self.workflow.strip())

    def test_allowed_triggers_only(self) -> None:
        self.assertIn("push:", self.workflow)
        self.assertIn("branches:", self.workflow)
        self.assertIn("- main", self.workflow)
        self.assertIn("workflow_dispatch:", self.workflow)
        for token in FORBIDDEN_TRIGGER_TOKENS:
            with self.subTest(token=token):
                self.assertNotIn(token, self.workflow)

    def test_runner_timeout_permissions_concurrency(self) -> None:
        self.assertIn("runs-on: ubuntu-24.04", self.workflow)
        self.assertIn("timeout-minutes:", self.workflow)
        self.assertIn("permissions:", self.workflow)
        self.assertIn("contents: read", self.workflow)
        self.assertIn("concurrency:", self.workflow)
        self.assertIn("cancel-in-progress: true", self.workflow)

    def test_actions_pinned_with_version_comments(self) -> None:
        self.assertIn(
            f"actions/checkout@{CHECKOUT_SHA} # v6.0.2",
            self.workflow,
        )
        self.assertIn(
            f"actions/upload-artifact@{UPLOAD_SHA} # v7.0.1",
            self.workflow,
        )
        self.assertIsNone(FLOATING_ACTION_REF.search(self.workflow))

    def test_checkout_without_persisted_credentials(self) -> None:
        self.assertIn("persist-credentials: false", self.workflow)

    def test_gates_before_archive_and_upload(self) -> None:
        text = self.workflow
        gate_pos = text.index("validate-public-tree.py")
        archive_pos = text.index(
            'git archive --format=zip --output=artifact.zip "$GITHUB_SHA"'
        )
        upload_pos = text.index(f"actions/upload-artifact@{UPLOAD_SHA}")
        self.assertLess(gate_pos, archive_pos)
        self.assertLess(archive_pos, upload_pos)

    def test_no_sha256sum_check_of_tracked_inputs(self) -> None:
        self.assertNotIn("sha256sum -c SHA256SUMS", self.workflow)

    def test_ci_uses_only_project_validation_commands(self) -> None:
        self.assertNotIn("scripts/agent-loop/", self.workflow)
        self.assertIn("python3 -m compileall", self.workflow)
        self.assertIn("python3 -m unittest discover", self.workflow)

    def test_git_archive_uses_github_sha(self) -> None:
        self.assertIn(
            'git archive --format=zip --output=artifact.zip "$GITHUB_SHA"',
            self.workflow,
        )

    def test_upload_direct_with_retention_and_error_policy(self) -> None:
        self.assertIn("path: artifact.zip", self.workflow)
        self.assertIn("archive: false", self.workflow)
        self.assertIn("if-no-files-found: error", self.workflow)
        self.assertIn("retention-days: 7", self.workflow)

    def test_no_secrets_or_write_permissions(self) -> None:
        lowered = self.workflow.lower()
        self.assertNotIn("secrets.", lowered)
        self.assertNotIn("contents: write", lowered)
        self.assertNotIn("id-token: write", lowered)
        for pattern in FORBIDDEN_COMMAND_PATTERNS:
            self.assertIsNone(pattern.search(self.workflow), msg=pattern.pattern)

    def test_summary_describes_sanitized_tree_only(self) -> None:
        self.assertIn("árvore Git sanitizada", self.workflow)
        self.assertNotIn(
            "o pacote inclui norma licenciada",
            self.workflow.lower(),
        )

    def test_validate_scripts_exist(self) -> None:
        self.assertTrue(VALIDATE_SCRIPT.is_file())
        self.assertTrue(PUBLIC_TREE_SCRIPT.is_file())

    def test_documentation_mentions_ci_available_state(self) -> None:
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        getting_started = (REPO_ROOT / "docs" / "GETTING_STARTED.md").read_text(
            encoding="utf-8"
        )
        privacy = (REPO_ROOT / "docs" / "PRIVACY.md").read_text(encoding="utf-8")
        for keyword in ("artifact.zip", "7 dias"):
            self.assertIn(keyword, readme)
            self.assertIn(keyword, getting_started)
            self.assertIn(keyword, privacy)
        self.assertIn("Disponível", readme)
        self.assertIn("terminou com sucesso", readme)
        self.assertIn("terminou com sucesso", getting_started)
        self.assertIn("terminou com sucesso", privacy)
        self.assertNotIn("candidate aguardando integração", readme.lower())


def _run_validate_candidate(zip_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "python3",
            str(VALIDATE_SCRIPT),
            str(zip_path),
            "CANDIDATE",
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
    )


def _append_directory_entry(zip_path: Path, directory_name: str) -> None:
    """Acrescenta uma entrada de diretório (nome terminado em '/') ao ZIP."""
    if not directory_name.endswith("/"):
        directory_name = f"{directory_name}/"
    info = zipfile.ZipInfo(directory_name)
    with zipfile.ZipFile(zip_path, "a") as zf:
        zf.writestr(info, b"")


class ArtifactZipRehearsalTests(unittest.TestCase):
    """Ensaio local offline com snapshot candidato sanitizado."""

    def test_local_candidate_archive_matches_tree_and_crc(self) -> None:
        candidate_snapshot = _load_candidate_snapshot()
        files = candidate_snapshot.candidate_file_map(REPO_ROOT, base="HEAD")
        expected_count = len(files)
        self.assertGreater(expected_count, 0)

        with tempfile.TemporaryDirectory() as tmp:
            zip_path = Path(tmp) / "artifact.zip"
            candidate_snapshot.write_candidate_zip(REPO_ROOT, zip_path, files)
            self.assertTrue(zip_path.is_file())

            size = zip_path.stat().st_size
            digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
            self.assertGreater(size, 0)
            self.assertEqual(len(digest), 64)

            result = _run_validate_candidate(zip_path)
            self.assertEqual(
                result.returncode,
                0,
                msg=result.stderr or result.stdout,
            )

            with zipfile.ZipFile(zip_path, "r") as zf:
                names = {info.filename for info in zf.infolist() if not info.is_dir()}
                self.assertFalse(
                    any(name.startswith("inputs/private/") for name in names)
                )
                self.assertFalse(
                    any(
                        name.startswith("inputs/normativa/")
                        or name.startswith("inputs/template/")
                        or name.startswith("inputs/projetos_modelo/")
                        for name in names
                    )
                )
                self.assertFalse(
                    any(name.startswith(".git/") or name == ".git" for name in names)
                )
                self.assertNotIn("artifact.zip", names)
                for info in zf.infolist():
                    if info.is_dir():
                        continue
                    zf.read(info.filename)

            self.assertEqual(len(names), expected_count)

    def test_rejects_unsafe_directory_entry(self) -> None:
        candidate_snapshot = _load_candidate_snapshot()
        files = candidate_snapshot.candidate_file_map(REPO_ROOT, base="HEAD")
        with tempfile.TemporaryDirectory() as tmp:
            zip_path = Path(tmp) / "artifact.zip"
            candidate_snapshot.write_candidate_zip(REPO_ROOT, zip_path, files)
            _append_directory_entry(zip_path, "../")
            result = _run_validate_candidate(zip_path)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("inseguro", result.stderr.lower())

    def test_rejects_unexpected_directory_entry(self) -> None:
        candidate_snapshot = _load_candidate_snapshot()
        files = candidate_snapshot.candidate_file_map(REPO_ROOT, base="HEAD")
        with tempfile.TemporaryDirectory() as tmp:
            zip_path = Path(tmp) / "artifact.zip"
            candidate_snapshot.write_candidate_zip(REPO_ROOT, zip_path, files)
            _append_directory_entry(zip_path, "not-tracked-dir/")
            result = _run_validate_candidate(zip_path)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("inesperada", result.stderr.lower())

    def test_rejects_duplicate_directory_entry(self) -> None:
        candidate_snapshot = _load_candidate_snapshot()
        files = candidate_snapshot.candidate_file_map(REPO_ROOT, base="HEAD")
        # Escolhe um prefixo de diretório que exista no snapshot candidato.
        sample = next(iter(files))
        directory = sample.rsplit("/", 1)[0] + "/"
        with tempfile.TemporaryDirectory() as tmp:
            zip_path = Path(tmp) / "artifact.zip"
            candidate_snapshot.write_candidate_zip(REPO_ROOT, zip_path, files)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                _append_directory_entry(zip_path, directory)
                _append_directory_entry(zip_path, directory)
            result = _run_validate_candidate(zip_path)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("duplicado", result.stderr.lower())


if __name__ == "__main__":
    unittest.main()
