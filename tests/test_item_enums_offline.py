"""Offline tests for the ported ``item_enums``: the classification and the tables it carries.

**The parity half of this module lives in the shared harness.** ``tests/test_enums_package_offline.py``
loads every source module in the package and compares it with the port name by name, member by member,
value by value — ``item_enums`` is one of the entries in its ``MODULES`` list — so this file does not
repeat that work. What is here is the part the harness does not exercise: **behaviour**, and the
computed answers the source's own members produce.

Source: ``Py4GWCoreLib/enums_src/Item_enums.py`` (449 lines).
"""

from __future__ import annotations

import datetime
import unittest
from typing import get_args

from py4gw.enums_src import item_enums
from py4gw.enums_src.model_enums import ModelID


class ItemTypeClassificationTests(unittest.TestCase):
    """`ItemType`'s own members, and the two sets the `Literal` aliases produce."""

    def test_the_weapon_and_armor_sets_are_the_source_literals(self) -> None:
        """`WEAPON_TYPES` and `ARMOR_TYPES` are exactly the members of the two aliases."""

        self.assertEqual(item_enums.WEAPON_TYPES, frozenset(get_args(item_enums.WeaponType)))
        self.assertEqual(item_enums.ARMOR_TYPES, frozenset(get_args(item_enums.ArmorType)))
        self.assertEqual(len(item_enums.WEAPON_TYPES), 11)
        self.assertEqual(len(item_enums.ARMOR_TYPES), 6)

    def test_is_weapon_type_and_is_armor_type_answer_from_those_sets(self) -> None:
        """The two instance predicates are membership in the sets above."""

        self.assertTrue(item_enums.ItemType.Sword.is_weapon_type())
        self.assertTrue(item_enums.ItemType.Shield.is_weapon_type())
        self.assertFalse(item_enums.ItemType.Chestpiece.is_weapon_type())
        self.assertTrue(item_enums.ItemType.Chestpiece.is_armor_type())
        self.assertTrue(item_enums.ItemType.Boots.is_armor_type())
        self.assertFalse(item_enums.ItemType.Sword.is_armor_type())

    def test_is_weapon_type_literal_answers_the_same_way(self) -> None:
        """The module-level half of the same test."""

        self.assertTrue(item_enums.is_weapon_type_literal(item_enums.ItemType.Bow))
        self.assertFalse(item_enums.is_weapon_type_literal(item_enums.ItemType.Chestpiece))

    def test_a_meta_type_matches_its_members(self) -> None:
        """`matches` and `is_matching_item_type` are the source's two membership tests."""

        sword = item_enums.ItemType.Sword
        self.assertTrue(sword.matches(item_enums.ItemType.Weapon))
        self.assertTrue(sword.matches(item_enums.ItemType.MartialWeapon))
        self.assertTrue(sword.matches(item_enums.ItemType.EquippableItem))
        self.assertTrue(sword.matches(sword))
        self.assertFalse(sword.matches(item_enums.ItemType.SpellcastingWeapon))
        self.assertTrue(
            item_enums.ItemType.is_matching_item_type(sword, item_enums.ItemType.Weapon)
        )
        self.assertFalse(
            item_enums.ItemType.is_matching_item_type(sword, item_enums.ItemType.OffhandOrShield)
        )

    def test_item_types_falls_back_to_the_type_itself(self) -> None:
        """`item_types` is the meta-type list when there is one, and `[self]` when there is not."""

        self.assertEqual(
            item_enums.ItemType.Weapon.item_types,
            item_enums.ITEM_TYPE_META_TYPES[item_enums.ItemType.Weapon],
        )
        self.assertEqual(item_enums.ItemType.Axe.item_types, [item_enums.ItemType.Axe])

    def test_the_meta_type_table_names_the_source_lists(self) -> None:
        """The meta-type entries are the source's own lists, member for member."""

        self.assertEqual(
            item_enums.ITEM_TYPE_META_TYPES[item_enums.ItemType.SpellcastingWeapon],
            [item_enums.ItemType.Staff, item_enums.ItemType.Wand],
        )
        self.assertEqual(
            item_enums.ITEM_TYPE_META_TYPES[item_enums.ItemType.OffhandOrShield],
            [item_enums.ItemType.Offhand, item_enums.ItemType.Shield],
        )
        self.assertEqual(len(item_enums.ITEM_TYPE_META_TYPES[item_enums.ItemType.Weapon]), 9)


class ItemEnumsTablesTests(unittest.TestCase):
    """The bag tables, the limits and the two data tables the module declares."""

    def test_the_bag_tables_are_the_source_ones(self) -> None:
        """`STORAGE_BAGS`, `MAX_BAG_SIZES`, `INVENTORY_BAGS` and the row size."""

        self.assertEqual(len(item_enums.STORAGE_BAGS), 14)
        self.assertEqual(item_enums.BAG_ROW_SLOTS, 5)
        self.assertEqual(item_enums.MAX_BAG_SIZES[item_enums.Bags.Backpack], 20)
        self.assertEqual(item_enums.MAX_BAG_SIZES[item_enums.Bags.BeltPouch], 10)
        self.assertEqual(item_enums.MAX_BAG_SIZES[item_enums.Bags.Bag1], 15)
        self.assertEqual(item_enums.MAX_BAG_SIZES[item_enums.Bags.Bag2], 15)
        self.assertEqual(item_enums.MAX_BAG_SIZES[item_enums.Bags.EquipmentPack], 20)
        for bag in item_enums.STORAGE_BAGS:
            with self.subTest(bag=bag):
                self.assertEqual(item_enums.MAX_BAG_SIZES[bag], 25)
        # The source adds the fourteen storage bags to the five literal entries and nothing else, so
        # the material-storage bag has no entry in this table.
        self.assertEqual(len(item_enums.MAX_BAG_SIZES), 19)
        self.assertNotIn(item_enums.Bags.MaterialStorage, item_enums.MAX_BAG_SIZES)
        self.assertEqual(
            item_enums.INVENTORY_BAGS,
            [
                item_enums.Bags.Backpack,
                item_enums.Bags.BeltPouch,
                item_enums.Bags.Bag1,
                item_enums.Bags.Bag2,
            ],
        )
        self.assertEqual(
            item_enums.INVENTORY_WITH_EQUIPMENT_BAGS,
            item_enums.INVENTORY_BAGS + [item_enums.Bags.EquipmentPack],
        )

    def test_the_limits_are_the_source_values(self) -> None:
        """The stack and gold limits, and the Nick cycle pair."""

        self.assertEqual(item_enums.MAX_STACK_SIZE, 250)
        self.assertEqual(item_enums.MAX_GOLD_STORAGE, 1_000_000)
        self.assertEqual(item_enums.MAX_GOLD_CHARACTER, 100_000)
        self.assertEqual(item_enums.NICK_CYCLE_COUNT, 137)
        self.assertEqual(item_enums.NICK_CYCLE_START_DATE, datetime.datetime(2009, 4, 20))

    def test_the_item_action_numbering_follows_auto(self) -> None:
        """`ItemAction.NONE` is zero and every member after it follows `auto()` from there."""

        self.assertEqual(int(item_enums.ItemAction.NONE), 0)
        self.assertEqual(int(item_enums.ItemAction.Ignore), 1)
        self.assertEqual(
            [int(member) for member in item_enums.ItemAction],
            list(range(len(item_enums.ItemAction))),
        )

    def test_the_material_map_names_its_models(self) -> None:
        """`MaterialMap` is keyed by `ModelID` members and holds the material names."""

        self.assertEqual(len(item_enums.MaterialMap), 36)
        self.assertEqual(item_enums.MaterialMap[ModelID.Bolt_Of_Cloth], "Bolt Of Cloth")
        self.assertEqual(item_enums.MaterialMap[ModelID.Glob_Of_Ectoplasm], "Glob Of Ectoplasm")
        self.assertEqual(item_enums.MaterialMap[ModelID.Vial_Of_Ink], "Vial Of Ink")

    def test_the_damage_ranges_cover_the_weapon_types(self) -> None:
        """`DAMAGE_RANGES` is keyed by weapon types, ten requirement rows each."""

        self.assertEqual(len(item_enums.DAMAGE_RANGES), 11)
        for item_type, rows in item_enums.DAMAGE_RANGES.items():
            with self.subTest(item_type=item_type):
                self.assertEqual(sorted(rows), list(range(10)))
                self.assertTrue(item_enums.ItemType(item_type).is_weapon_type())
        self.assertEqual(item_enums.DAMAGE_RANGES[item_enums.ItemType.Axe][9], (6, 28))
        self.assertEqual(item_enums.DAMAGE_RANGES[item_enums.ItemType.Shield][0], (8, 8))


if __name__ == "__main__":
    unittest.main(verbosity=2)
