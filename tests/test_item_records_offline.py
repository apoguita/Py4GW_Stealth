"""Offline checks for the external bag and item readers."""

from __future__ import annotations

import ctypes
import unittest
from typing import cast

from py4gw import (
    BagStruct,
    DyeInfoStruct,
    GWArray,
    InventoryStruct,
    ItemContextStruct,
    ItemModifierStruct,
    ItemRarity,
    ItemStruct,
    TradeContext,
)


class _Memory:
    """Small address-keyed reader used to prove pointer boundaries."""

    def __init__(self) -> None:
        self.blocks: dict[int, bytes] = {}
        self.reads: list[tuple[int, int]] = []

    def add(self, address: int, value: bytes) -> None:
        self.blocks[address] = value

    def read(self, address: int, size: int) -> bytes:
        self.reads.append((address, size))
        for base, value in self.blocks.items():
            end = base + len(value)
            if base <= address and address + size <= end:
                start = address - base
                return value[start : start + size]
        raise OSError(f"unmapped test address 0x{address:08X}")


class _TradeLookup:
    """Stand in for the source trade-context item lookup."""

    def __init__(self, offered_ids: set[int]) -> None:
        self.offered_ids = offered_ids

    def is_item_offered(self, item_id: int) -> bool:
        return item_id in self.offered_ids

    def read(self) -> _TradeLookup:
        return self


class ItemRecordOfflineTests(unittest.TestCase):
    """Keep item records fixed-width and lazily traversed."""

    def test_native_layouts(self) -> None:
        """The migrated records match the native x86 sizes and offsets."""

        self.assertEqual(ctypes.sizeof(DyeInfoStruct), 0x03)
        self.assertEqual(ctypes.sizeof(ItemStruct), 0x54)
        self.assertEqual(ctypes.sizeof(ItemModifierStruct), 0x04)
        self.assertEqual(ctypes.sizeof(BagStruct), 0x28)
        self.assertEqual(ctypes.sizeof(InventoryStruct), 0x98)
        self.assertEqual(ItemStruct.mod_struct.offset, 0x10)
        self.assertEqual(ItemStruct.mod_struct_size.offset, 0x14)
        self.assertEqual(ItemStruct.quantity.offset, 0x4C)
        self.assertEqual(BagStruct.items.offset, 0x18)

    def test_dye_nibbles_are_decoded_without_remote_reads(self) -> None:
        """The native packed dye bytes remain local fields."""

        dye = DyeInfoStruct()
        dye.dye_tint = 7
        dye.dye1 = 3
        dye.dye2 = 10
        dye.dye3 = 12
        dye.dye4 = 5
        self.assertEqual((dye.dye_tint, dye.dye1, dye.dye2), (7, 3, 10))
        self.assertEqual((dye.dye3, dye.dye4), (12, 5))

    def test_bag_path_reads_items_without_eager_modifier_traversal(self) -> None:
        """Item traversal remains lazy until a modifier is explicitly requested."""

        memory = _Memory()
        bag_pointer_table = (0x00280000).to_bytes(4, "little")
        item_pointer_table = (
            (0x00400000).to_bytes(4, "little")
            + (0x00400054).to_bytes(4, "little")
        )

        bag = BagStruct()
        bag.bag_type = 1
        bag.index = 0
        bag.items_count = 2
        bag.items_array = GWArray(0x00300000, 2, 2, 0)

        first = ItemStruct()
        first.item_id = 101
        first.mod_struct = 0x00500000
        first.mod_struct_size = 2
        first.quantity = 3

        second = ItemStruct()
        second.item_id = 102
        second.quantity = 1

        memory.add(0x00200000, bag_pointer_table)
        memory.add(0x00300000, item_pointer_table)
        memory.add(0x00280000, bytes(bag))
        memory.add(0x00400000, bytes(first) + bytes(second))

        context = ItemContextStruct()
        context.bags_array = GWArray(0x00200000, 1, 1, 0)
        context.bind_reader(
            memory,
            0x00100000,
            cast(TradeContext, _TradeLookup({101})),
        )

        bags = context.bags()
        self.assertEqual(len(bags), 1)
        items = bags[0].read_items()
        self.assertEqual([item.item_id for item in items], [101, 102])
        self.assertEqual(items[0].modifier_address, 0x00500000)
        self.assertEqual(items[0].modifier_count, 2)
        self.assertTrue(items[0].IsOfferedInTrade())
        self.assertFalse(items[1].IsOfferedInTrade())
        self.assertNotIn((0x00500000, 4), memory.reads)

    def test_modifier_words_match_native_bit_rules(self) -> None:
        """Explicit modifier reads preserve the native word and helpers."""

        memory = _Memory()
        uses = ItemModifierStruct()
        uses.mod = 0x2458012A
        lesser_kit = ItemModifierStruct()
        lesser_kit.mod = 0x25E80300
        memory.add(0x00500000, bytes(uses) + bytes(lesser_kit))

        item = ItemStruct()
        item.quantity = 9
        item.mod_struct = 0x00500000
        item.mod_struct_size = 2
        item.bind_reader(memory, 0x00400000)

        modifiers = item.modifiers
        self.assertEqual(len(modifiers), 2)
        self.assertEqual(modifiers[0].identifier, 0x2458)
        self.assertEqual(modifiers[0].arg1, 1)
        self.assertEqual(modifiers[0].arg2, 0x2A)
        self.assertEqual(modifiers[0].arg, 0x012A)
        self.assertTrue(modifiers[0].is_valid)
        self.assertEqual(modifiers[0].GetIdentifier(), 0x2458)
        self.assertEqual(item.uses, 0x2A)
        self.assertTrue(item.is_lesser_kit)
        self.assertTrue(item.is_salvage_kit)
        self.assertIsNotNone(item.get_modifier(0x2458))
        self.assertIsNone(item.get_modifier(0x9999))

    def test_source_modifier_lookup_checks_the_full_advertised_count(self) -> None:
        """GetModifier does not silently stop at the convenience-view limit."""

        memory = _Memory()
        modifiers = [ItemModifierStruct() for _ in range(70)]
        modifiers[-1].mod = 0x76540123
        memory.add(0x00500000, b"".join(bytes(modifier) for modifier in modifiers))
        item = ItemStruct()
        item.mod_struct = 0x00500000
        item.mod_struct_size = len(modifiers)
        item.bind_reader(memory, 0x00400000)

        found = item.GetModifier(0x7654)

        self.assertIsNotNone(found)
        assert found is not None
        self.assertEqual(found.identifier, 0x7654)

    def test_source_item_properties_use_local_fields_and_bounded_names(self) -> None:
        """Source-backed classification and name reads stay at the item boundary."""

        memory = _Memory()
        item = ItemStruct()
        item.item_id = 201
        item.model_file_id = 31202
        item.type = 2
        item.interaction = 0x20000
        item.single_item_name = 0x00600000
        item.name_enc = 0x00600020
        item.info_string = 0x00600040
        item.is_material_salvageable = 1
        memory.add(0x00600000, b"\x3F\x0A" + "Sword".encode("utf-16-le") + b"\x00\x00")
        memory.add(0x00600020, "Axe".encode("utf-16-le") + b"\x00\x00")
        memory.add(0x00600040, "Weapon".encode("utf-16-le") + b"\x00\x00")
        item.bind_reader(memory, 0x00400000)

        self.assertTrue(item.is_zcoin)
        self.assertFalse(item.is_material)
        self.assertTrue(item.is_weapon)
        self.assertFalse(item.is_armor)
        self.assertEqual(item.rarity, ItemRarity.gold)
        self.assertEqual(item.name_encoded_str, "Axe")
        self.assertEqual(item.name_str, "Axe")
        self.assertEqual(item.info_string_str, "Weapon")

    def test_native_item_helpers_are_callable_methods(self) -> None:
        """The source's Item methods keep method-call behavior in Python."""

        item = ItemStruct()
        item.quantity = 7
        item.type = 11
        item.interaction = 0x08000000 | 0x00080000 | 1

        self.assertTrue(item.GetIsStackable())
        self.assertTrue(item.GetIsInscribable())
        self.assertTrue(item.GetIsIdentified())
        self.assertTrue(item.GetIsMaterial())
        self.assertFalse(item.GetIsZcoin())
        self.assertEqual(item.GetUses(), 7)
        self.assertEqual(item.GetRarity(), ItemRarity.white)
        self.assertTrue(item.IsSparkly())
        self.assertTrue(item.IsPrefixUpgradable())
        self.assertTrue(item.IsSuffixUpgradable())
        self.assertTrue(item.IsTradable())
        self.assertIsNone(item.GetModifier(0x2458))

        source_method_names = (
            "GetIsStackable",
            "GetIsInscribable",
            "GetIsMaterial",
            "GetIsZcoin",
            "GetModifier",
            "IsSparkly",
            "GetIsIdentified",
            "IsPrefixUpgradable",
            "IsSuffixUpgradable",
            "IsUsable",
            "IsTradable",
            "IsInscription",
            "IsBlue",
            "IsPurple",
            "IsGreen",
            "IsGold",
            "IsInventoryItem",
            "IsStorageItem",
            "GetUses",
            "IsTome",
            "IsIdentificationKit",
            "IsLesserKit",
            "IsExpertSalvageKit",
            "IsPerfectSalvageKit",
            "IsSalvageKit",
            "IsRareMaterial",
            "GetRarity",
            "IsWeapon",
            "IsArmor",
            "IsSalvagable",
            "IsOfferedInTrade",
        )
        self.assertTrue(all(callable(getattr(item, name)) for name in source_method_names))
        with self.assertRaisesRegex(RuntimeError, "TradeContext reader"):
            item.IsOfferedInTrade()

    def test_bag_predicates_and_search_preserve_empty_slots(self) -> None:
        """Bag helpers retain native slot indexes, including empty slots."""

        memory = _Memory()
        bag = BagStruct()
        bag.bag_type = 1
        bag.items_array = GWArray(0x00300000, 3, 3, 0)
        first = ItemStruct()
        first.model_id = 9001
        second = ItemStruct()
        second.model_id = 9002
        memory.add(
            0x00300000,
            (0).to_bytes(4, "little")
            + (0x00400000).to_bytes(4, "little")
            + (0x00400054).to_bytes(4, "little"),
        )
        memory.add(0x00400000, bytes(first) + bytes(second))
        bag.bind_reader(memory, 0x00200000)

        self.assertTrue(bag.is_inventory_bag)
        self.assertTrue(bag.IsInventoryBag())
        self.assertEqual(bag.bag_id(), 1)
        self.assertEqual(bag.find1(0), 0)
        self.assertEqual(bag.find1(9002), 2)
        self.assertEqual(bag.find1(123456), BagStruct.npos)
        self.assertEqual(bag.find1(9001, -1), BagStruct.npos)
        self.assertEqual(
            [item is None for item in bag.items_with_slots()], [True, False, False]
        )
        self.assertEqual([item.model_id for item in bag.read_items()], [9001, 9002])

    def test_bag_dye_search_matches_native_packed_dye_rule(self) -> None:
        """find2 selects find_dye only for the native dye model identifier."""

        memory = _Memory()
        dye_item = ItemStruct()
        dye_item.model_id = 146
        dye_item.dye.dye_tint = 3
        dye_item.dye.dye1 = 1
        dye_item.dye.dye2 = 2
        dye_item.dye.dye3 = 3
        dye_item.dye.dye4 = 4
        other_item = ItemStruct()
        other_item.model_id = 9001
        memory.add(
            0x00300000,
            (0x00400000).to_bytes(4, "little")
            + (0x00400054).to_bytes(4, "little"),
        )
        memory.add(0x00400000, bytes(dye_item) + bytes(other_item))
        bag = BagStruct().bind_reader(memory, 0x00200000)
        bag.items = GWArray(0x00300000, 2, 2, 0)

        self.assertEqual(bag.find_dye(146, dye_item.dye), 0)
        self.assertEqual(bag.find2(dye_item), 0)
        self.assertEqual(bag.find2(other_item), 1)

        mismatched_dye = DyeInfoStruct()
        mismatched_dye.dye_tint = 4
        self.assertEqual(bag.find_dye(146, mismatched_dye), BagStruct.npos)


if __name__ == "__main__":
    unittest.main(verbosity=2)
