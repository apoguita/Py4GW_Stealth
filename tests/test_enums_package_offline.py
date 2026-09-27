"""Offline tests for the ported ``enums_src`` package, module by module.

Same rule as ``tests/test_enums_offline.py``, applied to the whole package: **the source's names
and the source's values, nothing else**. The Reforged module is not quoted here — it is *loaded*
from the checkout at test time and compared with the port, so a rename, a re-numbering, an added
member, a dropped alias or a substituted table fails here instead of at a call site.

The modules whose source imports a native binding module are not in the list, because they are not
ported yet: ``Model_enums.py`` (``import PySkill``), ``Texture_enums.py`` (``import PySystem``), and
``Item_enums.py``/``Calendar_enums.py``, which import ``Model_enums.ModelID`` and so follow it.
"""

from __future__ import annotations

import dataclasses
import importlib
import importlib.util
import types
import unittest
from enum import Enum
from pathlib import Path
from typing import Any

SOURCE_DIR = Path(r"C:\Users\Apo\Py4GW_Reforged\Py4GWCoreLib\enums_src")
PORT_PACKAGE = "py4gw.enums_src"

#: (port module, source file) for every module the package holds today.
MODULES = (
    ("event_enums", "Event_enums.py"),
    ("game_data_enums", "GameData_enums.py"),
    ("hero_enums", "Hero_enums.py"),
    ("io_enums", "IO_enums.py"),
    ("map_enums", "Map_enums.py"),
    ("multiboxing_enums", "Multiboxing_enums.py"),
    ("packet_enums", "Packet_enums.py"),
    ("player_enums", "Player_enums.py"),
    ("py4gw_enums", "Py4GW_enums.py"),
    ("quest_enums", "Quest_enums.py"),
    ("region_enums", "Region_enums.py"),
    ("title_enums", "Title_enums.py"),
    ("ui_enums", "UI_enums.py"),
    ("whiteboard_enums", "Whiteboard_enums.py"),
)

#: Names the source modules import rather than define; skipped when comparing tables.
IMPORTED = {
    "Enum",
    "IntEnum",
    "IntFlag",
    "Flag",
    "auto",
    "dataclass",
    "List",
    "Dict",
    "Tuple",
    "TypeIs",
    "TypeAlias",
    "cast",
    "get_args",
    "Literal",
    "enum",
    "date",
    "timedelta",
    "os",
    "Type",
    "Optional",
    "Set",
    "Any",
}


def _load_source(port_name: str, source_file: str) -> Any:
    """Load the Reforged module itself, or skip when the checkout is not on this machine."""

    path = SOURCE_DIR / source_file
    if not path.is_file():
        raise unittest.SkipTest(f"the Reforged source is not on this machine: {path}")
    spec = importlib.util.spec_from_file_location(f"_reforged_{port_name}", path)
    if spec is None or spec.loader is None:
        raise unittest.SkipTest(f"the Reforged source could not be loaded: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _public_names(module: Any) -> set[str]:
    """Every name the module defines or imports without a leading underscore."""

    return {name for name in vars(module) if not name.startswith("_")}


def _normalized(value: Any) -> Any:
    """A comparable shape for an enum, a dataclass, a table, a sequence or a plain value.

    An enum member is compared by its *class name*, its member name and its value, so an enum that
    was re-numbered, renamed or declared in another class cannot pass by comparing equal as an int.
    A dataclass — ``EventFieldDescriptor``, ``TitleTier`` and the rest — is compared by its class
    name and its fields, because the two modules' instances are different objects holding the same
    values and identity comparison would be meaningless.
    """

    if isinstance(value, Enum):
        return ("enum", type(value).__name__, value.name, value.value)
    if isinstance(value, types.ModuleType):
        # ``import enum`` is a public name in some source modules; a module is not a table.
        return ("module", value.__name__)
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return (
            "dataclass",
            type(value).__name__,
            [
                (field.name, _normalized(getattr(value, field.name)))
                for field in dataclasses.fields(value)
            ],
        )
    if isinstance(value, dict):
        return ("dict", [(_normalized(key), _normalized(item)) for key, item in value.items()])
    if isinstance(value, (list, tuple)):
        return ("seq", type(value).__name__, [_normalized(item) for item in value])
    if hasattr(value, "__dict__") and not isinstance(value, type) and not callable(value):
        # ``TitleTier`` and friends: plain objects in the source's own shape, compared field by
        # field because the two modules' instances are different objects holding the same values.
        return (
            "object",
            type(value).__name__,
            [(name, _normalized(item)) for name, item in sorted(vars(value).items())],
        )
    return value


class EnumsPackageTests(unittest.TestCase):
    """Pin every ported enums module against its source, name by name and value by value."""

    maxDiff = None

    def _pair(self, port_name: str, source_file: str) -> tuple[Any, Any]:
        return importlib.import_module(f"{PORT_PACKAGE}.{port_name}"), _load_source(
            port_name, source_file
        )

    def test_the_package_holds_every_module_the_sources_give_it(self) -> None:
        """The list above is the Reforged mirrors, plus the native-mirror module beside them."""

        held = {
            path.stem
            for path in (Path(__file__).resolve().parent.parent / "py4gw" / "enums_src").glob(
                "*.py"
            )
            if path.name != "__init__.py"
        }
        self.assertEqual(
            held,
            {port_name for port_name, _ in MODULES} | {"skill_names"},
            "py4gw/enums_src holds the Reforged mirrors above and skill_names.py, the port of "
            "native's generated GW::skillbar table (see the package docstring)",
        )

    def test_every_module_has_the_source_s_public_names(self) -> None:
        """Nothing dropped, nothing added: the same public surface, imported names included."""

        for port_name, source_file in MODULES:
            with self.subTest(module=port_name):
                port, source = self._pair(port_name, source_file)
                self.assertEqual(_public_names(port), _public_names(source))

    def test_every_enum_declares_the_source_s_members_in_order(self) -> None:
        """Members, order, aliases and values, for every enum in every module."""

        for port_name, source_file in MODULES:
            port, source = self._pair(port_name, source_file)
            for name, value in sorted(vars(source).items()):
                if not isinstance(value, type) or not issubclass(value, Enum):
                    continue
                with self.subTest(module=port_name, enum=name):
                    ported = getattr(port, name)
                    self.assertEqual(
                        [(member, item.value) for member, item in value.__members__.items()],
                        [(member, item.value) for member, item in ported.__members__.items()],
                    )

    def test_every_table_matches_the_source_s(self) -> None:
        """The name tables and the derived tables, keyed and valued the same."""

        for port_name, source_file in MODULES:
            port, source = self._pair(port_name, source_file)
            for name in sorted(_public_names(source)):
                if name in IMPORTED:
                    continue
                value = getattr(source, name)
                if isinstance(value, type) or callable(value):
                    continue
                with self.subTest(module=port_name, table=name):
                    self.assertEqual(_normalized(value), _normalized(getattr(port, name)))


if __name__ == "__main__":
    unittest.main()
