"""Offline tests for the ported game-data enums (``py4gw/enums_src/game_data_enums.py``).

The rule this file enforces is the porting rule for an enum module: **the source's names and the
source's values, nothing else**. So the source module is not quoted here — it is *loaded* from the
Reforged checkout at test time and compared with the port: every public name, every enum member in
the source's order, every alias, every name table, and the two members that carry behaviour.

That is what makes a re-numbering, a rename, an added member, a dropped alias or a substituted enum
fail here instead of at a call site: ``Agent`` refused ``AgentAllegiance`` for exactly that reason,
and this test is what keeps the substitute from creeping back in.

The one member that cannot be ported — ``DyeColor.from_dye_info``, whose first line imports the
native binding type ``PyItem.DyeInfo`` — is pinned as refusing and naming what it needs.
"""

from __future__ import annotations

import importlib.util
import unittest
from enum import Enum
from pathlib import Path
from typing import Any

from py4gw.enums_src import game_data_enums as port

#: Reforged's own file. It is the specification, so it is loaded rather than transcribed.
SOURCE = Path(
    r"C:\Users\Apo\Py4GW_Reforged\Py4GWCoreLib\enums_src\GameData_enums.py"
)


def _load_source() -> Any:
    """Load the source module itself, or skip when the checkout is not on this machine."""

    if not SOURCE.is_file():
        raise unittest.SkipTest(f"the Reforged source is not on this machine: {SOURCE}")
    spec = importlib.util.spec_from_file_location("_reforged_game_data_enums", SOURCE)
    if spec is None or spec.loader is None:
        raise unittest.SkipTest(f"the Reforged source could not be loaded: {SOURCE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _public_names(module: Any) -> set[str]:
    """Every name the module defines or imports without a leading underscore."""

    return {name for name in vars(module) if not name.startswith("_")}


def _normalized(value: Any) -> Any:
    """A comparable shape for an enum, a table, a sequence or a plain value.

    An enum member is compared by its *class name*, its member name and its value, so an enum that
    was re-numbered, renamed or declared in another class cannot pass by comparing equal as an int.
    """

    if isinstance(value, Enum):
        return ("enum", type(value).__name__, value.name, value.value)
    if isinstance(value, dict):
        return ("dict", [(_normalized(key), _normalized(item)) for key, item in value.items()])
    if isinstance(value, (list, tuple)):
        return ("seq", type(value).__name__, [_normalized(item) for item in value])
    return value


class GameDataEnumTests(unittest.TestCase):
    """Pin the ported module against the source, name by name and value by value."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = _load_source()

    def test_every_public_name_is_the_source_s(self) -> None:
        """Nothing dropped, nothing added: the same public surface, ``Enum`` included."""

        self.assertEqual(_public_names(port), _public_names(self.source))

    def test_every_enum_declares_the_source_s_members_in_order(self) -> None:
        """Members, order, aliases and values, for every enum in the file."""

        for name, value in sorted(vars(self.source).items()):
            if not isinstance(value, type) or not issubclass(value, Enum):
                continue
            with self.subTest(enum=name):
                ported = getattr(port, name)
                self.assertEqual(
                    [(member, item.value) for member, item in value.__members__.items()],
                    [(member, item.value) for member, item in ported.__members__.items()],
                )

    def test_every_table_matches_the_source_s(self) -> None:
        """The name tables and the derived tables, keyed and valued the same."""

        for name in sorted(_public_names(self.source)):
            if name in ("Enum", "IntEnum"):
                continue
            value = getattr(self.source, name)
            if isinstance(value, type) or callable(value):
                continue
            with self.subTest(table=name):
                self.assertEqual(_normalized(value), _normalized(getattr(port, name)))

    def test_attribute_profession_mapping_is_built_the_same_way(self) -> None:
        """``PROFESSION_ATTRIBUTES`` drives ``_ATTRIBUTE_TO_PROFESSION`` in both modules."""

        expected = {
            attribute.name: profession.name
            for attribute, profession in self.source._ATTRIBUTE_TO_PROFESSION.items()
        }
        ported = {
            attribute.name: profession.name
            for attribute, profession in port._ATTRIBUTE_TO_PROFESSION.items()
        }
        self.assertEqual(expected, ported)

    def test_attribute_behaviour_matches_for_every_member(self) -> None:
        """``get_profession`` and ``is_primary``, member by member."""

        for member in self.source.Attribute.__members__:
            with self.subTest(attribute=member):
                source_member = self.source.Attribute[member]
                ported_member = port.Attribute[member]
                self.assertEqual(
                    source_member.get_profession().name, ported_member.get_profession().name
                )
                self.assertEqual(source_member.is_primary, ported_member.is_primary)

    def test_the_unportable_member_refuses_and_names_pyitem(self) -> None:
        """``DyeColor.from_dye_info`` needs ``PyItem.DyeInfo``, and says so."""

        with self.assertRaises(NotImplementedError) as caught:
            port.DyeColor.from_dye_info(None)
        message = str(caught.exception)
        self.assertIn("DyeColor.from_dye_info", message)
        self.assertIn("PyItem.DyeInfo", message)
        self.assertIn("The source's member works", message)


if __name__ == "__main__":
    unittest.main()
