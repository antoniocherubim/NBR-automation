"""Gate documental offline: estrutura, links, profile e whitespace."""

from __future__ import annotations

import re
import tempfile
import tomllib
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_USER_DOCS = (
    "README.md",
    "docs/README.md",
    "docs/GETTING_STARTED.md",
    "docs/CONCEPTS.md",
    "docs/GLOSSARY.md",
    "docs/TROUBLESHOOTING.md",
    "docs/PRIVACY.md",
)

README_REQUIRED_HEADINGS = (
    "Automação determinística",
    "Estado inicial",
    "O que já funciona",
    "O que ainda não funciona",
    "Fluxo futuro",
    "Pré-requisitos",
    "Início rápido",
    "inputs/",
    "Mapa da documentação",
    "relatar",
    "Roadmap",
)

STATUS_MARKERS = ("Disponível", "Planejada", "Bloqueada")

TEXT_EXTENSIONS = {".md", ".py", ".toml", ".json", ".sh", ".txt"}
SPECIAL_TEXT_FILES = {".gitignore"}

EXCLUDE_DIR_NAMES = {
    ".git",
    "inputs",
    "__pycache__",
    ".venv",
    "venv",
    "outputs",
    ".agent-loop-local",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    ".eggs",
    "htmlcov",
    ".tox",
    ".nox",
    "node_modules",
    ".egg-info",
}

HOST_ABSOLUTE_PATH_PATTERN = re.compile(
    r"(?:^|[\s`'\"(])"
    r"(?:/home/|/Users/|/tmp/|C:\\\\|D:\\\\)"
)

MARKDOWN_LINK_PATTERN = re.compile(r"\]\(([^)]+)\)")


def discover_text_files(root: Path) -> list[Path]:
    """Lista arquivos textuais relevantes via filesystem (inclui untracked)."""
    found: list[Path] = []

    def excluded(path: Path) -> bool:
        return any(part in EXCLUDE_DIR_NAMES for part in path.parts)

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if excluded(path.relative_to(root)):
            continue
        if path.suffix in TEXT_EXTENSIONS or path.name in SPECIAL_TEXT_FILES:
            found.append(path)

    return sorted(found)


def read_utf8(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise UnicodeDecodeError(
            exc.encoding,
            exc.object,
            exc.start,
            exc.end,
            f"{path}: {exc.reason}",
        ) from exc


def local_markdown_links(markdown: str) -> list[str]:
    links: list[str] = []
    for target in MARKDOWN_LINK_PATTERN.findall(markdown):
        target = target.strip()
        if not target or target.startswith("#"):
            continue
        if "://" in target:
            continue
        path_part = target.split("#", 1)[0].strip()
        if not path_part:
            continue
        links.append(path_part)
    return links


def resolve_local_link(source_file: Path, link: str) -> Path:
    return (source_file.parent / link).resolve()


def lines_with_trailing_whitespace(content: str) -> list[tuple[int, str]]:
    offenders: list[tuple[int, str]] = []
    for index, line in enumerate(content.splitlines(), start=1):
        if line != line.rstrip(" \t"):
            offenders.append((index, line))
    return offenders


class DocumentationGateTests(unittest.TestCase):
    """Validações determinísticas da documentação de usuário."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.text_files = discover_text_files(REPO_ROOT)
        cls.text_file_count = len(cls.text_files)

    def test_required_documents_exist_and_are_utf8(self) -> None:
        for rel in REQUIRED_USER_DOCS:
            path = REPO_ROOT / rel
            with self.subTest(document=rel):
                self.assertTrue(path.is_file(), f"documento obrigatório ausente: {rel}")
                content = read_utf8(path)
                self.assertTrue(content.strip(), f"documento vazio: {rel}")

    def test_readme_has_essential_headings(self) -> None:
        content = read_utf8(REPO_ROOT / "README.md")
        for heading in README_REQUIRED_HEADINGS:
            with self.subTest(heading=heading):
                self.assertIn(heading, content)

    def test_readme_marks_available_and_planned_features(self) -> None:
        content = read_utf8(REPO_ROOT / "README.md")
        for marker in STATUS_MARKERS[:2]:
            self.assertIn(marker, content)

    def test_local_markdown_links_resolve(self) -> None:
        doc_paths = [REPO_ROOT / rel for rel in REQUIRED_USER_DOCS]
        for doc_path in doc_paths:
            content = read_utf8(doc_path)
            for link in local_markdown_links(content):
                resolved = resolve_local_link(doc_path, link)
                with self.subTest(document=doc_path.name, link=link):
                    self.assertTrue(
                        resolved.is_file(),
                        f"link quebrado em {doc_path.relative_to(REPO_ROOT)}: {link}",
                    )

    def test_user_docs_have_no_host_absolute_paths(self) -> None:
        for rel in REQUIRED_USER_DOCS:
            content = read_utf8(REPO_ROOT / rel)
            match = HOST_ABSOLUTE_PATH_PATTERN.search(content)
            self.assertIsNone(
                match,
                f"path absoluto de host em {rel}: {match.group(0) if match else ''}",
            )

    def test_project_profile_lists_required_documentation(self) -> None:
        profile_path = REPO_ROOT / ".agent-loop" / "project.toml"
        with profile_path.open("rb") as handle:
            profile = tomllib.load(handle)
        required_paths = profile["documentation"]["required_paths"]
        self.assertIn("README.md", required_paths)
        self.assertIn("docs/tasks/{task_id}.md", required_paths)
        self.assertIn("ROADMAP.md", required_paths)
        self.assertTrue(profile["documentation"]["required"])

    def test_executor_and_reviewer_require_documentation_policy(self) -> None:
        executor = read_utf8(REPO_ROOT / ".agent-loop" / "executor.md")
        reviewer = read_utf8(REPO_ROOT / ".agent-loop" / "reviewer.md")
        for keyword in ("README.md", "documentação", "evidência"):
            self.assertIn(keyword, executor.lower() if keyword != "README.md" else executor)
        for keyword in ("README", "documentação", "links"):
            self.assertIn(keyword.lower() if keyword != "README" else "README", reviewer)

    def test_no_trailing_whitespace_in_text_files(self) -> None:
        self.assertGreater(self.text_file_count, 0, "nenhum arquivo textual encontrado")
        for path in self.text_files:
            rel = path.relative_to(REPO_ROOT)
            with self.subTest(path=str(rel)):
                content = read_utf8(path)
                offenders = lines_with_trailing_whitespace(content)
                self.assertEqual(
                    offenders,
                    [],
                    f"whitespace final em {rel}: linhas {[line for _, line in offenders]}",
                )

    def test_trailing_whitespace_helper_detects_injected_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp) / "sample.md"
            fixture.write_text("linha limpa\nlinha com espaco \n", encoding="utf-8")
            content = read_utf8(fixture)
            offenders = lines_with_trailing_whitespace(content)
            self.assertEqual(len(offenders), 1)
            self.assertEqual(offenders[0][0], 2)

    def test_invalid_utf8_text_file_would_fail_read(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.txt"
            bad.write_bytes(b"\xff\xfe")
            with self.assertRaises(UnicodeDecodeError) as ctx:
                read_utf8(bad)
            self.assertIn("bad.txt", str(ctx.exception))
            self.assertIn(str(bad), str(ctx.exception))

    def test_discover_text_files_excludes_inputs_and_git(self) -> None:
        rel_paths = {p.relative_to(REPO_ROOT) for p in self.text_files}
        self.assertFalse(any(part == "inputs" for part in rel_paths))
        self.assertFalse(any(part == ".git" for part in rel_paths))

if __name__ == "__main__":
    unittest.main()
