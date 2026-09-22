"""Offline layout checks for the external ItemContext root."""

from __future__ import annotations

import ctypes
import unittest

from py4gw import (
    CompositeModelInfoStruct,
    GWArray,
    ItemContextStruct,
    ItemFormulaStruct,
    PvPItemInfoStruct,
    PvPItemUpgradeInfoStruct,
)


class ItemContextOfflineTests(unittest.TestCase):
    """Keep the root layout fixed-width and array inspection local."""

    def test_native_layout_offsets(self) -> None:
        """The root matches the native 0x10C definition."""

        self.assertEqual(ctypes.sizeof(ItemContextStruct), 0x10C)
        self.assertEqual(ItemContextStruct.bags_array.offset, 0x24)
        self.assertEqual(ItemContextStruct.item_array.offset, 0xB8)
        self.assertEqual(ItemContextStruct.inventory_table.offset, 0xE4)
        self.assertEqual(ItemContextStruct.inventory_ptr.offset, 0xF8)
        self.assertEqual(ctypes.sizeof(ItemFormulaStruct), 0x14)
        self.assertEqual(ctypes.sizeof(PvPItemUpgradeInfoStruct), 0x28)
        self.assertEqual(ctypes.sizeof(PvPItemInfoStruct), 0x24)
        self.assertEqual(ctypes.sizeof(CompositeModelInfoStruct), 0x30)

    def test_array_headers_are_reported_without_traversal(self) -> None:
        """The root exposes counts without reading bags or items."""

        context = ItemContextStruct()
        context.bags_array = GWArray(0x100000, 23, 5, 0)
        context.item_array = GWArray(0x110000, 256, 12, 0)
        self.assertEqual(context.array_sizes["bags_array"], 5)
        self.assertEqual(context.array_sizes["item_array"], 12)


if __name__ == "__main__":
    unittest.main(verbosity=2)
