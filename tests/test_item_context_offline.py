"""Offline layout checks for the external ItemContext root."""

from __future__ import annotations

import ctypes
import unittest

from py4gw import (
    BagStruct,
    CompositeModelInfoStruct,
    DyeInfoStruct,
    GWArray,
    InventoryStruct,
    InventoryTableEntryStruct,
    ItemClickParamStruct,
    ItemContextStruct,
    ItemFormulaStruct,
    ItemModifierStruct,
    ItemStruct,
    MaterialCostStruct,
    PvPItemInfoStruct,
    PvPItemUpgradeInfoStruct,
    SalvageSessionInfoStruct,
    WeaponSetStruct,
)
from py4gw.context.item_context import (
    ItemArray as ItemContextItemArray,
    ItemContext,
    ItemDataStruct as ItemContextItemDataStruct,
    MerchItemArray,
)


class ItemContextOfflineTests(unittest.TestCase):
    """Keep the root layout fixed-width and array inspection local."""

    def test_native_layout_offsets(self) -> None:
        """The root matches the native 0x10C definition."""

        self.assertEqual(ctypes.sizeof(ItemContextStruct), 0x10C)
        self.assertEqual(ItemContextStruct.bags_array.offset, 0x24)
        self.assertEqual(ItemContextStruct.item_array.offset, 0xB8)
        self.assertEqual(ItemContextStruct.inventory_table.offset, 0xE4)
        self.assertEqual(ItemContextStruct.inventory.offset, 0xF8)
        self.assertEqual(ctypes.sizeof(BagStruct), 0x28)
        self.assertEqual(ctypes.sizeof(ItemStruct), 0x54)
        self.assertEqual(ctypes.sizeof(ItemModifierStruct), 0x04)
        self.assertEqual(ctypes.sizeof(ItemContextItemDataStruct), 0x10)
        self.assertEqual(ctypes.sizeof(InventoryStruct), 0x98)
        self.assertEqual(ctypes.sizeof(ItemFormulaStruct), 0x14)
        self.assertEqual(ctypes.sizeof(MaterialCostStruct), 0x10)
        self.assertEqual(ctypes.sizeof(WeaponSetStruct), 0x08)
        self.assertEqual(ctypes.sizeof(PvPItemUpgradeInfoStruct), 0x28)
        self.assertEqual(ctypes.sizeof(PvPItemInfoStruct), 0x24)
        self.assertEqual(ctypes.sizeof(CompositeModelInfoStruct), 0x30)
        self.assertEqual(ctypes.sizeof(SalvageSessionInfoStruct), 0x24)
        self.assertEqual(ctypes.sizeof(ItemClickParamStruct), 0x0C)
        self.assertEqual(ctypes.sizeof(InventoryTableEntryStruct), 0x0C)
        self.assertEqual(MaterialCostStruct.h000c.offset, 0x0C)
        self.assertEqual(WeaponSetStruct.offhand.offset, 0x04)
        self.assertEqual(SalvageSessionInfoStruct.kit_id.offset, 0x20)
        self.assertEqual(ItemClickParamStruct.type.offset, 0x08)
        self.assertEqual(InventoryTableEntryStruct.start.offset, 0x08)
        self.assertEqual(ItemContextItemDataStruct.type.offset, 0x04)
        self.assertEqual(ItemContextItemDataStruct.dye.offset, 0x05)
        self.assertEqual(ItemContextItemDataStruct.value.offset, 0x08)
        self.assertEqual(ItemContextItemDataStruct.interaction.offset, 0x0C)
        self.assertIs(ItemContextItemArray, GWArray)
        self.assertIs(MerchItemArray, GWArray)

    def test_native_field_names_and_order(self) -> None:
        """Every declared native item record retains source field order."""

        self.assertEqual(
            [name for name, *_ in DyeInfoStruct._fields_],
            ["dye_tint", "dye1", "dye2", "dye3", "dye4"],
        )
        self.assertEqual(
            [field[0] for field in ItemContextItemDataStruct._fields_],
            ["model_file_id", "type", "dye", "value", "interaction"],
        )
        self.assertEqual(
            [field[0] for field in ItemStruct._fields_],
            [
                "item_id",
                "agent_id",
                "bag_equipped",
                "bag",
                "mod_struct",
                "mod_struct_size",
                "customized",
                "model_file_id",
                "type",
                "dye",
                "value",
                "h0026",
                "interaction",
                "model_id",
                "info_string",
                "name_enc",
                "complete_name_enc",
                "single_item_name",
                "h0040",
                "item_formula",
                "is_material_salvageable",
                "h004B",
                "quantity",
                "equipped",
                "profession",
                "slot",
            ],
        )
        self.assertEqual(
            [field[0] for field in BagStruct._fields_],
            [
                "bag_type",
                "index",
                "_unknown0",
                "container_item",
                "items_count",
                "bag_array",
                "items",
            ],
        )
        self.assertEqual(
            [field[0] for field in ItemStruct._fields_][-4:],
            ["quantity", "equipped", "profession", "slot"],
        )
        self.assertEqual(
            [field[0] for field in PvPItemInfoStruct._fields_], ["unk"]
        )
        self.assertEqual(
            [field[0] for field in MaterialCostStruct._fields_],
            ["material", "amount", "h0008", "h000c"],
        )
        self.assertEqual(
            [field[0] for field in WeaponSetStruct._fields_], ["weapon", "offhand"]
        )
        self.assertEqual(
            [field[0] for field in SalvageSessionInfoStruct._fields_],
            [
                "vtable",
                "frame_id",
                "item_id",
                "salvagable_1",
                "salvagable_2",
                "salvagable_3",
                "chosen_salvagable",
                "h001c",
                "kit_id",
            ],
        )
        self.assertEqual(
            [field[0] for field in ItemClickParamStruct._fields_],
            ["unk0", "slot", "type"],
        )
        self.assertEqual(
            [field[0] for field in InventoryTableEntryStruct._fields_],
            ["stride", "end", "start"],
        )
        self.assertEqual(
            [field[0] for field in InventoryStruct._fields_],
            [
                "bags",
                "bundle",
                "storage_panes_unlocked",
                "weapon_sets",
                "active_weapon_set",
                "h0088",
                "gold_character",
                "gold_storage",
            ],
        )
        self.assertEqual(
            [field[0] for field in ItemContextStruct._fields_][-4:],
            ["inventory_table", "h00F4", "inventory", "h00FC"],
        )
        expected_fields = {
            ItemContextItemDataStruct: [
                "model_file_id", "type", "dye", "value", "interaction"
            ],
            MaterialCostStruct: ["material", "amount", "h0008", "h000c"],
            ItemFormulaStruct: [
                "h0000", "gold_cost", "skill_point_cost",
                "material_cost_count", "material_cost_buffer",
            ],
            BagStruct: [
                "bag_type", "index", "_unknown0", "container_item",
                "items_count", "bag_array", "items",
            ],
            ItemModifierStruct: ["mod"],
            ItemStruct: [
                "item_id", "agent_id", "bag_equipped", "bag", "mod_struct",
                "mod_struct_size", "customized", "model_file_id", "type", "dye",
                "value", "h0026", "interaction", "model_id", "info_string",
                "name_enc", "complete_name_enc", "single_item_name", "h0040",
                "item_formula", "is_material_salvageable", "h004B", "quantity",
                "equipped", "profession", "slot",
            ],
            WeaponSetStruct: ["weapon", "offhand"],
            InventoryStruct: [
                "bags", "bundle", "storage_panes_unlocked", "weapon_sets",
                "active_weapon_set", "h0088", "gold_character", "gold_storage",
            ],
            PvPItemUpgradeInfoStruct: [
                "file_id", "name_id", "upgrade_type", "campaign_id",
                "interaction", "is_dev", "profession", "h0018",
                "mod_struct_size", "mod_struct",
            ],
            PvPItemInfoStruct: ["unk"],
            CompositeModelInfoStruct: ["class_flags", "file_ids"],
            SalvageSessionInfoStruct: [
                "vtable", "frame_id", "item_id", "salvagable_1",
                "salvagable_2", "salvagable_3", "chosen_salvagable", "h001c",
                "kit_id",
            ],
            ItemClickParamStruct: ["unk0", "slot", "type"],
            InventoryTableEntryStruct: ["stride", "end", "start"],
            ItemContextStruct: [
                "h0000", "h0010", "h0020", "bags_array", "h0034", "h0038",
                "h003C", "h0040", "h0050", "h0060", "h0064", "h0068",
                "h006C", "h0070", "h0074", "h0078", "h007C", "h0080",
                "h0084", "h0088", "h008C", "h0090", "h0094", "h0098",
                "h009C", "h00A0", "h00A4", "h00A8", "h00AC", "h00B0",
                "h00B4", "item_array", "h00C8", "h00CC", "h00D0", "h00D4",
                "h00D8", "h00DC", "h00E0", "inventory_table", "h00F4",
                "inventory", "h00FC",
            ],
        }
        for structure, expected in expected_fields.items():
            with self.subTest(structure=structure.__name__):
                self.assertEqual([field[0] for field in structure._fields_], expected)

    def test_inventory_union_field_views(self) -> None:
        """C++ union aliases remain accessible over the native arrays."""

        inventory = InventoryStruct()
        bag_names = (
            "unused_bag", "backpack", "belt_pouch", "bag1", "bag2",
            "equipment_pack", "material_storage", "unclaimed_items",
            "storage1", "storage2", "storage3", "storage4", "storage5",
            "storage6", "storage7", "storage8", "storage9", "storage10",
            "storage11", "storage12", "storage13", "storage14",
            "equipped_items",
        )
        for index, name in enumerate(bag_names):
            inventory.bags[index] = 0x100000 + index * 0x100
            self.assertEqual(getattr(inventory, name), 0x100000 + index * 0x100)

        for index in range(4):
            weapon = 0x200000 + index * 0x100
            offhand = weapon + 0x40
            inventory.weapon_sets[index].weapon = weapon
            inventory.weapon_sets[index].offhand = offhand
            self.assertEqual(getattr(inventory, f"weapon_set{index}"), weapon)
            self.assertEqual(getattr(inventory, f"offhand_set{index}"), offhand)

    def test_array_headers_are_reported_without_traversal(self) -> None:
        """The root exposes counts without reading bags or items."""

        context = ItemContextStruct()
        context.bags_array = GWArray(0x100000, 23, 5, 0)
        context.item_array = GWArray(0x110000, 256, 12, 0)
        self.assertEqual(context.array_sizes["bags_array"], 5)
        self.assertEqual(context.array_sizes["item_array"], 12)

    def test_item_formula_count_matches_native_helper(self) -> None:
        """Expose the count returned by native GetItemFormulaCount()."""

        context = ItemContext.__new__(ItemContext)
        context._auxiliary_initialized = True
        context._auxiliary_addresses = {"item_formulas_count": 1501}

        self.assertEqual(context.get_item_formula_count(), 1501)
        self.assertEqual(context.GetItemFormulaCount(), 1501)

        context._auxiliary_addresses = {}
        self.assertEqual(context.GetItemFormulaCount(), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
