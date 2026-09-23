"""Live read-only checks for the external ItemContext root."""

from __future__ import annotations

import ctypes
import unittest

from py4gw import (
    GameContext,
    ItemContext,
    ItemContextStruct,
    ItemModifierStruct,
    PatternCatalog,
    ProcessMemoryReader,
    RemoteScanner,
    Win32,
)


class LiveItemContextTests(unittest.TestCase):
    """Verify the direct GameContext item pointer and root arrays."""

    @classmethod
    def setUpClass(cls) -> None:
        """Open the first running client with read-only access."""

        cls.win32 = Win32()
        clients = cls.win32.find_guild_wars()
        if not clients:
            raise unittest.SkipTest("Start Guild Wars before running this test.")
        cls.pid = int(clients[0]["pid"])
        module = cls.win32.get_main_module(cls.pid)
        cls.reader = ProcessMemoryReader(cls.win32, cls.pid)
        cls.scanner = RemoteScanner(
            cls.reader, int(module["base_address"]), int(module["size"])
        )
        cls.scanner.initialize()
        cls.game_context = GameContext(
            cls.reader, cls.scanner, PatternCatalog.from_directory("offsets")
        )
        cls.game_context.initialize()
        cls.context = ItemContext(
            cls.reader,
            cls.game_context,
            cls.scanner,
            PatternCatalog.from_directory("offsets"),
        )
        cls.context.initialize()

    @classmethod
    def tearDownClass(cls) -> None:
        """Close the selected process handle."""

        if hasattr(cls, "reader"):
            cls.reader.close()

    def test_layout_matches_native_item_context(self) -> None:
        """Keep the root at the maintained 0x10C-byte size."""

        self.assertEqual(ctypes.sizeof(ItemContextStruct), 0x10C)

    def test_reads_item_root_and_array_headers(self) -> None:
        """Read the root and the maintained bag-based item path."""

        address = self.context.resolve_address()
        if address is None:
            self.skipTest("The client has no active ItemContext.")
        snapshot = self.context.read()
        self.assertIsNotNone(snapshot)
        if snapshot is None:
            return
        self.assertEqual(len(bytes(snapshot)), 0x10C)
        self.assertGreaterEqual(snapshot.array_sizes["bags_array"], 0)
        self.assertGreaterEqual(snapshot.array_sizes["item_array"], 0)
        bags = snapshot.bags()
        item_count = sum(len(bag.read_items()) for bag in bags)
        first_item = next(
            (item for bag in bags for item in bag.read_items() if item.item_id), None
        )
        if first_item is not None:
            self.assertIsInstance(first_item.GetIsStackable(), bool)
            self.assertIsInstance(first_item.IsOfferedInTrade(), bool)
            print(
                "First item: "
                f"id={first_item.item_id}, model={first_item.model_id}, "
                f"type={first_item.type}, rarity={first_item.rarity.name}, "
                f"weapon={first_item.is_weapon}, armor={first_item.is_armor}, "
                f"material={first_item.is_material}, name={first_item.name_str!r}"
            )
        print(
            "Live ItemContext: "
            f"0x{address:08X}, bags={snapshot.array_sizes['bags_array']}, "
            f"item_array_size={snapshot.array_sizes['item_array']}, "
            f"read_bags={len(bags)}, read_items={item_count}"
        )

    def test_reads_source_auxiliary_tables(self) -> None:
        """Verify native item-global tables through cached JSON resolvers."""

        self.assertFalse(self.context.auxiliary_resolution_errors)
        self.assertIsNotNone(self.context.storage_open_address)
        self.assertIsNotNone(self.context.is_storage_open)
        formula_count = self.context.GetItemFormulaCount()
        self.assertGreater(formula_count, 0)
        self.assertEqual(len(self.context.read_item_formulas()), formula_count)
        formulas = self.context.read_item_formulas(limit=8)
        upgrades = self.context.read_pvp_item_upgrades(limit=8)
        pvp_items = self.context.read_pvp_items(limit=8)
        composite = self.context.read_composite_model_info(146)
        self.assertEqual(len(formulas), 8)
        self.assertEqual(len(upgrades), 8)
        self.assertEqual(len(pvp_items), 8)
        self.assertIsNotNone(composite)
        if composite is not None:
            self.assertEqual(len(composite.file_id_list), 11)
        print(
            "Live Item globals: "
            f"formulas={len(self.context.read_item_formulas())}, "
            f"pvp_upgrades={len(self.context.read_pvp_item_upgrades())}, "
            f"pvp_items={len(self.context.read_pvp_items())}, "
            f"composite_146={self.context.get_composite_model_ids(146)}"
        )

    def test_reads_live_item_modifiers(self) -> None:
        """Read the source-defined modifier words only when requested."""

        snapshot = self.context.read()
        if snapshot is None:
            self.skipTest("The client has no active ItemContext.")
        first_item = next(
            (
                item
                for bag in snapshot.bags()
                for item in bag.read_items()
                if item.item_id
            ),
            None,
        )
        if first_item is None or first_item.modifier_count == 0:
            self.skipTest("The live inventory has no item with modifiers.")
        modifiers = first_item.modifiers
        self.assertLessEqual(len(modifiers), 64)
        self.assertTrue(all(isinstance(modifier, ItemModifierStruct) for modifier in modifiers))
        uses_modifier = first_item.get_modifier(0x2458)
        expected_uses = uses_modifier.arg2 if uses_modifier is not None else first_item.quantity
        self.assertEqual(first_item.uses, expected_uses)
        print(
            "Live item modifiers: "
            f"item={first_item.item_id}, count={len(modifiers)}, "
            f"identifiers={[hex(modifier.identifier) for modifier in modifiers]}"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
