"""Smoke tests offline usando somente a biblioteca padrão."""

from __future__ import annotations

import importlib
import unittest


class TestPackageSmoke(unittest.TestCase):
    def test_import_package(self) -> None:
        module = importlib.import_module("nbr12721")
        self.assertEqual(module.__version__, "0.0.0")

    def test_package_has_minimal_surface(self) -> None:
        module = importlib.import_module("nbr12721")
        self.assertEqual(module.__version__, "0.0.0")
        public = [name for name in dir(module) if not name.startswith("_")]
        self.assertEqual(public, ["artifacts", "normative", "sources"])
        self.assertFalse(hasattr(module, "private_fixtures"))



if __name__ == "__main__":
    unittest.main()
