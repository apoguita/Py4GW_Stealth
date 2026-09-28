"""Offline parity test: the ported ``mods_upgrades`` against the Reforged source it transcribes.

The source is four dictionary tables and nothing else, so the comparison is exact and total: every
table, every key, **key order included**, and every value compared as it stands. The source is loaded
by absolute path (it has no imports, so it loads standalone) rather than quoted, so a dropped upgrade, a
retyped roll range or a changed description line fails here instead of inside an item's tooltip.

Source: ``Py4GWCoreLib/mods_upgrades.py`` (727 lines).
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from typing import Any

from py4gw import mods_upgrades

SOURCE_FILE = Path(r"C:\Users\Apo\Py4GW_Reforged\Py4GWCoreLib\mods_upgrades.py")

#: The four tables the source declares, with the sizes the port must reproduce.
TABLES = {
    "UPGRADE_SLOT": 279,
    "UPGRADE_VAR": 102,
    "UPGRADE_RANGE": 60,
    "UPGRADE_DESC": 263,
}


def _load_source() -> Any:
    """Load the source module itself, or skip when the checkout is not on this machine."""

    if not SOURCE_FILE.is_file():
        raise unittest.SkipTest(f"the Reforged source is not on this machine: {SOURCE_FILE}")

    full_name = "_reforged_mods_upgrades"
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


@unittest.skipUnless(SOURCE_FILE.is_file(), f"the Reforged source is not present at {SOURCE_FILE}")
class ModsUpgradesParityTests(unittest.TestCase):
    """Every table, entry for entry, against the source."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = _load_source()

    def test_the_same_tables_are_declared(self) -> None:
        """The port declares the source's four tables, and nothing else public."""

        theirs = {name for name in vars(self.source) if not name.startswith("_")}
        ours = {name for name in vars(mods_upgrades) if not name.startswith("_")}
        self.assertEqual(sorted(theirs - ours), [])
        self.assertEqual(sorted(ours - theirs), [])

    def test_every_table_has_the_same_entries(self) -> None:
        """Each table equals the source's, key for key and value for value."""

        for name, size in TABLES.items():
            with self.subTest(table=name):
                theirs = getattr(self.source, name)
                ours = getattr(mods_upgrades, name)
                self.assertEqual(len(ours), size, "the declared size")
                self.assertEqual(len(theirs), size, "the source's own size")
                self.assertEqual(ours, theirs)

    def test_every_table_keeps_the_source_key_order(self) -> None:
        """A dict's key order is part of the source's declaration, so it is compared too."""

        for name in TABLES:
            with self.subTest(table=name):
                theirs = getattr(self.source, name)
                ours = getattr(mods_upgrades, name)
                self.assertEqual(list(ours.keys()), list(theirs.keys()))

    def test_the_value_types_are_the_source_s(self) -> None:
        """`UPGRADE_RANGE` holds pairs, the other three hold scalars and strings."""

        for key, value in mods_upgrades.UPGRADE_RANGE.items():
            with self.subTest(upgrade=key):
                self.assertIsInstance(value, tuple)
                self.assertEqual(len(value), 2)
                self.assertIsInstance(value[0], int)
                self.assertIsInstance(value[1], int)
        for name in ("UPGRADE_SLOT", "UPGRADE_VAR"):
            for key, value in getattr(mods_upgrades, name).items():
                with self.subTest(table=name, upgrade=key):
                    self.assertIsInstance(key, str)
                    self.assertIsInstance(value, int)
        for key, value in mods_upgrades.UPGRADE_DESC.items():
            with self.subTest(identifier=key):
                self.assertIsInstance(key, int)
                self.assertIsInstance(value, str)


class ModsUpgradesContentsTests(unittest.TestCase):
    """A few entries read directly, so the tables are known to say what they are for."""

    def test_the_slot_values_are_the_documented_ones(self) -> None:
        """`UPGRADE_SLOT` holds the slot values its own comment names.

        The comment lists six slots (0 Inherent, 1 Prefix, 2 Suffix, 3 Inscription, 4 Rune,
        5 Insignia); the table itself carries only the three an upgrade can occupy here, which is what
        is asserted — not the range the comment mentions.
        """

        self.assertEqual(mods_upgrades.UPGRADE_SLOT["Adept"], 1)
        self.assertEqual(mods_upgrades.UPGRADE_SLOT["AptitudeNotAttitude"], 3)
        self.assertEqual(sorted(set(mods_upgrades.UPGRADE_SLOT.values())), [1, 2, 3])

    def test_a_roll_range_is_a_minimum_and_a_maximum(self) -> None:
        """`UPGRADE_RANGE` pairs read minimum first, as `is_better` and `upgrade_is_maxed` expect."""

        for name, (low, high) in mods_upgrades.UPGRADE_RANGE.items():
            with self.subTest(upgrade=name):
                self.assertLessEqual(low, high)

    def test_the_descriptions_are_the_modifier_lines(self) -> None:
        """`UPGRADE_DESC` is keyed by modifier identifier and holds the game-style line."""

        self.assertEqual(mods_upgrades.UPGRADE_DESC[0x218], "Health +10")
        self.assertIn("Health +30", mods_upgrades.UPGRADE_DESC[0x219])
        self.assertTrue(all(value for value in mods_upgrades.UPGRADE_DESC.values()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
