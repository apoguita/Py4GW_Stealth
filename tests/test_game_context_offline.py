"""Offline declaration and layout checks for the GameContext port."""

from __future__ import annotations

import ctypes
import unittest

from py4gw.context.game_context import GameContextStruct


class GameContextParityTests(unittest.TestCase):
    """Check every source-defined GameContext field and native alias."""

    def test_source_field_order_offsets_and_size(self) -> None:
        expected_offsets = {
            "h0000": 0x00,
            "h0004": 0x04,
            "agent_context": 0x08,
            "h000C": 0x0C,
            "h0010": 0x10,
            "map_context": 0x14,
            "text_parser": 0x18,
            "h001C": 0x1C,
            "some_number": 0x20,
            "h0024": 0x24,
            "account_context": 0x28,
            "world_context": 0x2C,
            "cinematic": 0x30,
            "h0034": 0x34,
            "gadget_context": 0x38,
            "guild_context": 0x3C,
            "item_context": 0x40,
            "char_context": 0x44,
            "h0048": 0x48,
            "party_context": 0x4C,
            "h0050": 0x50,
            "h0054": 0x54,
            "trade_context": 0x58,
        }
        self.assertEqual(ctypes.sizeof(GameContextStruct), 0x5C)
        self.assertEqual(
            [field[0] for field in GameContextStruct._fields_],
            list(expected_offsets),
        )
        for name, offset in expected_offsets.items():
            self.assertEqual(getattr(GameContextStruct, name).offset, offset, name)

    def test_native_cpp_field_aliases_preserve_the_same_values(self) -> None:
        snapshot = GameContextStruct()
        snapshot.agent_context = 0x1000
        snapshot.map_context = 0x2000
        snapshot.account_context = 0x3000
        snapshot.world_context = 0x4000
        snapshot.gadget_context = 0x5000
        snapshot.guild_context = 0x6000
        snapshot.item_context = 0x7000
        snapshot.char_context = 0x8000
        snapshot.party_context = 0x9000
        snapshot.trade_context = 0xA000
        self.assertEqual(snapshot.agent, 0x1000)
        self.assertEqual(snapshot.map, 0x2000)
        self.assertEqual(snapshot.account, 0x3000)
        self.assertEqual(snapshot.world, 0x4000)
        self.assertEqual(snapshot.gadget, 0x5000)
        self.assertEqual(snapshot.guild, 0x6000)
        self.assertEqual(snapshot.items, 0x7000)
        self.assertEqual(snapshot.character, 0x8000)
        self.assertEqual(snapshot.party, 0x9000)
        self.assertEqual(snapshot.trade, 0xA000)


if __name__ == "__main__":
    unittest.main(verbosity=2)
