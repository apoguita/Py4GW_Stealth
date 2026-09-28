"""Offline parity test: the ported ``mods_types`` against the Reforged source it transcribes.

Same rule as the other ported modules, applied to a declaration file: **the source's names and the
source's values, nothing else**. The source is *loaded* and compared rather than quoted, so a renamed
member, a re-numbered id, a dropped upgrade or a reordered catalog fails here instead of at an item's
modifier decode.

Two things a comparison like this has to get right:

- A member of the source's ``ItemType`` and a member of this port's ``ItemType`` are different objects,
  so every value goes through :func:`_normalise`, which reduces an enum member to its class name,
  member name and value, and a container to the same treatment for its items, keeping order. That is
  what makes this a comparison of *declarations* rather than of object identity — and it matters here,
  because ``ItemUpgrade``'s 283 members carry `{ItemType: ItemUpgradeId}` maps.
- ``Model_enums.py`` (which the source's import chain reaches) does ``import PySkill``, the injected
  runtime's module. :func:`_install_pyskill_stub` gives it the ported ``GetSkillIDByName``, which is
  what native's own constructor calls (``skill_bindings.cpp:29-30``).
"""

from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from enum import Enum
from pathlib import Path
from typing import Any, cast

from py4gw import mods_types

SOURCE_ROOT = Path(r"C:\Users\Apo\Py4GW_Reforged\Py4GWCoreLib")
SOURCE_FILE = SOURCE_ROOT / "mods_types.py"

#: The names the source module imports rather than declares.
_IMPORTED = {"Enum", "IntEnum", "auto", "TypeAlias", "ItemType"}


def _normalise(value: Any) -> Any:
    """Reduce a value to something two modules can be compared through."""

    if isinstance(value, Enum):
        return ("enum", type(value).__name__, value.name, value.value)
    if isinstance(value, dict):
        return ("dict", [(_normalise(key), _normalise(item)) for key, item in value.items()])
    if isinstance(value, (set, frozenset)):
        return ("set", sorted(repr(_normalise(item)) for item in value))
    if isinstance(value, (list, tuple)):
        return ("seq", type(value).__name__, [_normalise(item) for item in value])
    return ("value", type(value).__name__, value)


def _install_pyskill_stub() -> None:
    """Make ``Model_enums.py``'s ``import PySkill`` resolvable, with native's own definition."""

    if "PySkill" in sys.modules:
        return

    from py4gw.enums_src import skill_names

    class _SkillID:
        def __init__(self, name: str) -> None:
            self.id = skill_names.GetSkillIDByName(str(name))

    class _Skill:
        def __init__(self, name: str) -> None:
            self.id = _SkillID(name)

    stub = types.ModuleType("PySkill")
    stub.Skill = _Skill  # type: ignore[attr-defined]
    sys.modules["PySkill"] = stub


def _load_source() -> Any:
    """Load the source module itself, satisfying its absolute import of the source package."""

    if not SOURCE_FILE.is_file():
        raise unittest.SkipTest(f"the Reforged source is not on this machine: {SOURCE_FILE}")

    _install_pyskill_stub()

    # ``from Py4GWCoreLib.enums_src.Item_enums import ItemType`` — the source's own package layout,
    # registered as paths so the import machinery finds its modules without executing the package's
    # ``__init__`` (which is not what this test is about).
    for package_name, path in (
        ("Py4GWCoreLib", SOURCE_ROOT),
        ("Py4GWCoreLib.enums_src", SOURCE_ROOT / "enums_src"),
    ):
        if package_name not in sys.modules:
            package = types.ModuleType(package_name)
            package.__path__ = [str(path)]  # type: ignore[attr-defined]
            sys.modules[package_name] = package

    full_name = "Py4GWCoreLib.mods_types"
    existing = sys.modules.get(full_name)
    if existing is not None:
        return existing

    spec = importlib.util.spec_from_file_location(full_name, SOURCE_FILE)
    if spec is None or spec.loader is None:  # pragma: no cover - reported as a skip above
        raise unittest.SkipTest(f"the Reforged source could not be loaded: {SOURCE_FILE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = module
    spec.loader.exec_module(module)
    return module


def _public(module: Any) -> list[str]:
    """Return a module's public names, in the order they appear in it."""

    return [name for name in vars(module) if not name.startswith("_") and name != "annotations"]


@unittest.skipUnless(
    SOURCE_FILE.is_file(), f"the Reforged source is not present at {SOURCE_FILE}"
)
class ModsTypesParityTests(unittest.TestCase):
    """Every name the source declares exists here, with the same value."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = _load_source()

    def test_the_same_names_are_declared(self) -> None:
        """The port declares every public name of the source, and no name of its own."""

        theirs = set(_public(self.source))
        ours = set(_public(mods_types))
        self.assertEqual(sorted(theirs - ours), [], "names the source declares and the port does not")
        self.assertEqual(sorted(ours - theirs), [], "names the port declares and the source does not")

    def test_every_enum_matches_member_for_member(self) -> None:
        """Each enum has the same members, in the same order, with the same values and aliases.

        Iteration order is compared by member **name**, because iterating the source's enum and this
        port's enum yields members of two different classes, and members compare by identity.
        """

        compared = 0
        for name in _public(self.source):
            if name in _IMPORTED:
                continue
            theirs = getattr(self.source, name)
            if not isinstance(theirs, type) or not hasattr(theirs, "__members__"):
                continue
            ours = getattr(mods_types, name)
            with self.subTest(enum=name):
                self.assertEqual(
                    [(member, _normalise(value.value)) for member, value in ours.__members__.items()],
                    [(member, _normalise(value.value)) for member, value in theirs.__members__.items()],
                )
                self.assertEqual(
                    [member.name for member in ours],
                    [member.name for member in cast(Any, theirs)],
                    "the enum's iteration order (aliases are skipped by iteration)",
                )
            compared += 1
        self.assertEqual(compared, 7, f"seven enums should compare; {compared} did")

    def test_the_item_upgrade_methods_survive(self) -> None:
        """``ItemUpgrade`` carries the same four members on this side as on the source's."""

        theirs = self.source.ItemUpgrade
        ours = mods_types.ItemUpgrade
        their_extra = {
            name
            for name in vars(theirs)
            if not name.startswith("_") and name not in theirs.__members__
        }
        our_extra = {
            name for name in vars(ours) if not name.startswith("_") and name not in ours.__members__
        }
        self.assertEqual(sorted(our_extra), sorted(their_extra))
        self.assertEqual(
            sorted(our_extra), ["get_item_type", "has_id", "item_type_id_map", "upgrade_ids"]
        )

    def test_every_other_declaration_matches(self) -> None:
        """The alias and the one function compare equal to the source's own.

        ``ModifierIdentifierSpec`` is a ``TypeAlias`` over this module's own enum, so its text differs
        from the source's by exactly one thing: the module the two live in. That prefix is normalised
        away, and the aliases are then compared character for character.
        """

        compared = 0
        for name in _public(self.source):
            if name in _IMPORTED:
                continue
            theirs = getattr(self.source, name)
            if isinstance(theirs, type) and hasattr(theirs, "__members__"):
                continue
            ours = getattr(mods_types, name)
            with self.subTest(name=name):
                if isinstance(theirs, types.FunctionType):
                    self.assertEqual(ours.__name__, theirs.__name__)
                else:
                    self.assertEqual(
                        repr(ours).replace("py4gw.mods_types.", ""),
                        repr(theirs).replace("Py4GWCoreLib.mods_types.", ""),
                    )
            compared += 1
        self.assertEqual(compared, 2, f"two names should compare; {compared} did")

    def test_the_upgrade_catalog_answers_the_same_way(self) -> None:
        """The four ``ItemUpgrade`` members answer identically for every member of the catalog."""

        for name, theirs in self.source.ItemUpgrade.__members__.items():
            ours = mods_types.ItemUpgrade[name]
            with self.subTest(upgrade=name):
                self.assertEqual(
                    _normalise(ours.item_type_id_map), _normalise(theirs.item_type_id_map)
                )
                self.assertEqual(
                    _normalise(ours.upgrade_ids),
                    _normalise(theirs.upgrade_ids),
                )
                for upgrade_id in ours.upgrade_ids:
                    self.assertEqual(
                        _normalise(ours.get_item_type(upgrade_id)),
                        _normalise(theirs.get_item_type(getattr(self.source.ItemUpgradeId, upgrade_id.name))),
                    )
                    self.assertTrue(theirs.has_id(getattr(self.source.ItemUpgradeId, upgrade_id.name)))

    def test_any_of_refuses_an_empty_call_on_both_sides(self) -> None:
        """`any_of` is the source's own function, including its `ValueError`."""

        self.assertEqual(
            _normalise(mods_types.any_of(mods_types.ModifierIdentifier.Damage)),
            ("seq", "tuple", [("enum", "ModifierIdentifier", "Damage", 634)]),
        )
        with self.assertRaises(ValueError) as ours:
            mods_types.any_of()
        with self.assertRaises(ValueError) as theirs:
            self.source.any_of()
        self.assertEqual(str(ours.exception), str(theirs.exception))


class ModsTypesBehaviourTests(unittest.TestCase):
    """The catalog's own answers, driven on this side alone."""

    def test_the_identifier_values_are_the_ones_item_uses(self) -> None:
        """The five identifiers `Item.Properties` and `Item.Mods` name by hand."""

        self.assertEqual(int(mods_types.ModifierIdentifier.Damage), 0x27A)
        self.assertEqual(int(mods_types.ModifierIdentifier.Damage2), 0x248)
        self.assertEqual(int(mods_types.ModifierIdentifier.Armor1), 0x27B)
        self.assertEqual(int(mods_types.ModifierIdentifier.Armor2), 0x23C)
        self.assertEqual(int(mods_types.ModifierIdentifier.AttributeRequirement), 0x279)
        self.assertEqual(int(mods_types.ModifierIdentifier.Energy), 0x27C)
        self.assertEqual(int(mods_types.ModifierIdentifier.Energy2), 0x22C)
        self.assertEqual(int(mods_types.ModifierIdentifier.None_), 0xFFFF)
        self.assertEqual(int(mods_types.ModifierIdentifier.Empty), 0x0000)

    def test_a_single_upgrade_carries_one_id(self) -> None:
        """A member whose value is one id: `upgrade_ids` wraps it and `get_item_type` is Unknown."""

        self.assertEqual(
            mods_types.ItemUpgrade.Unknown.upgrade_ids,
            (mods_types.ItemUpgradeId.Unknown,),
        )
        self.assertEqual(
            mods_types.ItemUpgrade.Unknown.get_item_type(mods_types.ItemUpgradeId.Unknown),
            mods_types.ItemType.Unknown,
        )
        self.assertTrue(mods_types.ItemUpgrade.Unknown.has_id(mods_types.ItemUpgradeId.Unknown))

    def test_a_per_weapon_upgrade_carries_a_map(self) -> None:
        """A member whose value is a map: seven weapon ids, and the type read back from the id."""

        icy = mods_types.ItemUpgrade.Icy
        self.assertEqual(len(icy.item_type_id_map), 7)
        self.assertEqual(icy.item_type_id_map[mods_types.ItemType.Axe], mods_types.ItemUpgradeId.Icy_Axe)
        self.assertEqual(icy.get_item_type(mods_types.ItemUpgradeId.Icy_Sword), mods_types.ItemType.Sword)
        self.assertTrue(icy.has_id(mods_types.ItemUpgradeId.Icy_Bow))
        self.assertFalse(icy.has_id(mods_types.ItemUpgradeId.Ebon_Axe))
        self.assertEqual(len(icy.upgrade_ids), 7)

    def test_the_upgrade_id_table_holds_the_inherent_zero(self) -> None:
        """`ItemUpgradeId.Inherent` is the zero the source comments as "not actually an upgrade"."""

        self.assertEqual(int(mods_types.ItemUpgradeId.Inherent), 0x0000)
        self.assertEqual(int(mods_types.ItemUpgradeId.Unknown), -1)
        self.assertEqual(int(mods_types.ItemUpgradeId.Icy_Axe), 0x0081)


if __name__ == "__main__":
    unittest.main(verbosity=2)
