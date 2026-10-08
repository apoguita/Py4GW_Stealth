"""Offline check that every name this repository imports from ``py4gw`` still exists.

The offline suite collects ``test_*offline.py``; the live suites and the probe/tool scripts are run
by hand. So when a member is removed from the library -- as the TextParser's additive members were
on 2026-10-11 -- nothing in a normal run notices that a *live* test, a probe or an example still
imports it, and the breakage surfaces only when someone runs that file. This test walks the
repository's own Python, resolves every ``from py4gw... import ...`` against the real modules, and
fails naming each name that no longer resolves.

``from package import name`` also resolves a submodule, which is not an attribute of the package
until something imports it, so both resolutions are tried before a name is called missing.

Excluded: ``external/`` (third-party checkouts, not this project's code) and ``tests/scratch``
(work in progress by definition, and its files are not part of the suite).
"""

from __future__ import annotations

import ast
import importlib
import unittest
from pathlib import Path

#: The repository root, from this file's own location.
_ROOT = Path(__file__).resolve().parent.parent

#: Directories whose Python is not this project's surface to check.
_EXCLUDED = ("external", "__pycache__", "scratch")


def _python_files() -> list[Path]:
    """Every Python file of this project, tests, tools, examples and the root included."""

    found: list[Path] = []
    for pattern in ("tests/**/*.py", "tools/**/*.py", "examples/**/*.py", "*.py"):
        for path in _ROOT.glob(pattern):
            parts = set(path.relative_to(_ROOT).parts)
            if parts & set(_EXCLUDED):
                continue
            found.append(path)
    return sorted(set(found))


def _imported_names(path: Path) -> list[tuple[str, str]]:
    """Every ``(module, name)`` a file imports from ``py4gw``."""

    tree = ast.parse(path.read_text(encoding="utf-8"))
    pairs: list[tuple[str, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or node.module is None:
            continue
        if not node.module.startswith("py4gw"):
            continue
        for alias in node.names:
            if alias.name != "*":
                pairs.append((node.module, alias.name))
    return pairs


class ImportSurfaceTest(unittest.TestCase):
    """What this repository imports from the library has to exist in the library."""

    def test_every_name_imported_from_py4gw_resolves(self) -> None:
        """A removed member names every caller that still imports it, live tests included."""

        problems: list[str] = []
        checked = 0
        for path in _python_files():
            relative = path.relative_to(_ROOT)
            try:
                pairs = _imported_names(path)
            except SyntaxError as error:
                problems.append(f"{relative}: cannot be parsed ({error})")
                continue
            for module_name, name in pairs:
                checked += 1
                try:
                    module = importlib.import_module(module_name)
                except Exception as error:  # noqa: BLE001 - a module that cannot import is a finding
                    problems.append(f"{relative}: {module_name} failed to import ({error})")
                    continue
                if hasattr(module, name):
                    continue
                try:
                    importlib.import_module(f"{module_name}.{name}")
                except Exception:  # noqa: BLE001 - resolves neither way: the name is gone
                    problems.append(f"{relative}: {module_name} has no {name}")

        self.assertGreater(checked, 1000, "the sweep found almost nothing to check")
        self.assertEqual(problems, [], "\n".join(problems))


if __name__ == "__main__":
    unittest.main()
