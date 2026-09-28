"""Offline parity test: ``py4gw/frame_tree``'s table modules against Reforged's ``FrameTree`` package.

Five of that package's seven modules are pure data, so the comparison is exact and total: every public
name, every table entry, **key order included**, and — for ``FrameId`` — every constant with its value, in
declaration order. The source modules have no imports of their own, so they load standalone; the port is
compared against the source's own objects rather than against anything restated here.

The package's two other modules are covered at the end: ``frame.py`` (the logic — both of its classes are
declared in full, in the source's own member order) and the package's ``__init__``, whose re-export list is
compared name for name against the source's.
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
import unittest
from pathlib import Path
from typing import Any

SOURCE_DIR = Path(r"C:\Users\Apo\Py4GW_Reforged\Py4GWCoreLib\FrameTree")

#: (port module, source file) for the five table modules, and the sizes the port must reproduce.
TABLES = {
    "frame_window_keys": ("frame_window_keys.py", {"WINDOW_FRAME_KEYS": 0}),
    "frame_names": (
        "frame_names.py",
        {
            "FRAME_NAMES_CONFIRMED": 0,
            "FRAME_NAMES_OBSERVED": 0,
            "FRAME_NAMES_HARVESTED": 0,
            "FRAME_NAMES_RECONSTRUCTED": 0,
            "FRAME_NAMES": 0,
            "NAME_TO_HASH": 0,
        },
    ),
    "frame_aliases": ("frame_aliases.py", {"FRAME_ALIASES": 0}),
    "frame_registry": ("frame_registry.py", {"REGISTRY": 0, "DYNAMIC_KEYS": 0}),
    "frame_ids": ("frame_ids.py", {"FrameId": 0}),
}


def _load_source(file_name: str) -> Any:
    """Load one source module by path, or skip when the checkout is not on this machine."""

    path = SOURCE_DIR / file_name
    if not path.is_file():
        raise unittest.SkipTest(f"the Reforged source is not on this machine: {path}")

    full_name = f"_reforged_frame_tree_{path.stem}"
    existing = sys.modules.get(full_name)
    if existing is not None:
        return existing

    spec = importlib.util.spec_from_file_location(full_name, path)
    if spec is None or spec.loader is None:  # pragma: no cover - reported as a skip above
        raise unittest.SkipTest(f"the Reforged source could not be loaded: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = module
    spec.loader.exec_module(module)
    return module


def _public(module: Any) -> list[str]:
    """Return a module's public names, in declaration order."""

    return [name for name in vars(module) if not name.startswith("_")]


def _normalise(value: Any) -> Any:
    """Reduce a value to something two modules can be compared through.

    ``FrameId`` is a **hierarchy of nested classes** (``FrameId.ScreenFrame.C6.SalvageMaterialsDialog.
    YesButton`` is the address the salvage dialog uses), so a class is compared by name and by its own
    members, recursively — the source's class and this port's are two different objects with the same shape.
    """

    if isinstance(value, type):
        return (
            "class",
            value.__name__,
            [
                (member, _normalise(item))
                for member, item in vars(value).items()
                if not member.startswith("__")
            ],
        )
    return value


@unittest.skipUnless(
    SOURCE_DIR.is_dir(), f"the Reforged source is not present at {SOURCE_DIR}"
)
class FrameTreeTableTests(unittest.TestCase):
    """Every table, entry for entry, against the source."""

    def test_the_same_public_names_are_declared(self) -> None:
        """Each ported module declares the source's names and nothing of its own."""

        for port_name, (file_name, _expected) in TABLES.items():
            with self.subTest(module=port_name):
                source = _load_source(file_name)
                port = importlib.import_module(f"py4gw.frame_tree.{port_name}")
                self.assertEqual(sorted(_public(port)), sorted(_public(source)))

    def test_every_table_has_the_source_entries(self) -> None:
        """Dictionaries equal entry for entry; sets equal as sets; `FrameId` member for member."""

        for port_name, (file_name, expected) in TABLES.items():
            source = _load_source(file_name)
            port = importlib.import_module(f"py4gw.frame_tree.{port_name}")
            for name in expected:
                with self.subTest(module=port_name, table=name):
                    theirs = getattr(source, name)
                    ours = getattr(port, name)
                    if isinstance(theirs, type):
                        self.assertEqual(
                            _normalise(ours),
                            _normalise(theirs),
                            "every FrameId constant, in declaration order",
                        )
                    elif isinstance(theirs, dict):
                        self.assertEqual(ours, theirs)
                    else:
                        self.assertEqual(ours, theirs)

    def test_every_table_keeps_the_source_key_order(self) -> None:
        """A dict's key order is part of the source's declaration, so it is compared too."""

        for port_name, (file_name, expected) in TABLES.items():
            source = _load_source(file_name)
            port = importlib.import_module(f"py4gw.frame_tree.{port_name}")
            for name in expected:
                theirs = getattr(source, name)
                if not isinstance(theirs, dict):
                    continue
                with self.subTest(module=port_name, table=name):
                    self.assertEqual(list(getattr(port, name).keys()), list(theirs.keys()))

    def test_the_tables_are_not_empty(self) -> None:
        """A size floor per module, so a table that came across empty cannot pass.

        The floors are measured, not guessed: the source's ``REGISTRY`` holds 195 entries and ``FrameId``
        reaches ~195 nested members, whatever their files' line counts suggest.
        """

        floors = {
            "frame_window_keys": {"WINDOW_FRAME_KEYS": 1},
            "frame_names": {"FRAME_NAMES_CONFIRMED": 400, "FRAME_NAMES": 1, "NAME_TO_HASH": 1},
            "frame_aliases": {"FRAME_ALIASES": 1000},
            "frame_registry": {"REGISTRY": 100, "DYNAMIC_KEYS": 1},
        }
        for port_name, expected in floors.items():
            port = importlib.import_module(f"py4gw.frame_tree.{port_name}")
            for name, floor in expected.items():
                with self.subTest(module=port_name, table=name):
                    self.assertGreaterEqual(len(getattr(port, name)), floor)
        from py4gw.frame_tree.frame_ids import FrameId

        self.assertGreaterEqual(
            len([member for member in vars(FrameId) if not member.startswith("__")]), 100
        )


class FrameTreePackageTests(unittest.TestCase):
    """The package's two non-table modules: the logic module and the `__init__` that re-exports it."""

    def test_the_logic_module_is_ported_in_full(self) -> None:
        """`frame.py` declares both classes' whole surface, in the source's own member order.

        Which members *answer* is `FRAME_TREE_PORT.md`'s subject; this test is about the surface, which is what
        the sections were grown to match.
        """

        module = importlib.import_module("py4gw.frame_tree.frame")
        for name in ("FrameState", "resolve_key", "FrameTree", "_FrameTree", "Frame"):
            with self.subTest(name=name):
                self.assertTrue(hasattr(module, name))
        self.assertTrue(hasattr(module._FrameTree, "overlay"), "the tree's whole surface is declared")
        self.assertTrue(hasattr(module.Frame, "click"), "so is Frame's")

    def test_the_package_reexports_the_sources_own_names(self) -> None:
        """The source's `__init__` is a re-export list, and the port's is the same list.

        The source file cannot be imported standalone — its imports are package-relative — so its `__all__` is
        read out of its AST and compared with the port's, name for name and in order; every name is then
        resolved on the port's package.
        """

        import ast

        source = SOURCE_DIR / "__init__.py"
        if not source.exists():
            self.fail("the source package is not at %s" % source)
        tree = ast.parse(source.read_text(encoding="utf-8"))
        source_all: list[str] = []
        found = False
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            if not any(getattr(target, "id", "") == "__all__" for target in node.targets):
                continue
            if isinstance(node.value, ast.List):
                source_all = [str(getattr(element, "value", "")) for element in node.value.elts]
                found = True
        self.assertTrue(found, "the source __init__ has no __all__")

        package = importlib.import_module("py4gw.frame_tree")
        self.assertEqual(package.__all__, source_all)
        for name in source_all:
            with self.subTest(name=name):
                self.assertTrue(hasattr(package, name), "%s is not re-exported" % name)

    def test_the_package_is_importable(self) -> None:
        """The package exists and its modules import through it."""

        package = importlib.import_module("py4gw.frame_tree")
        self.assertTrue(hasattr(package, "__file__"))
        self.assertIn("frame_tree", str(package.__file__))


if __name__ == "__main__":
    unittest.main(verbosity=2)
