"""Live read-only checks for the external TradeContext reader."""

from __future__ import annotations

import ctypes
import unittest

from py4gw import (
    GameContext,
    PatternCatalog,
    ProcessMemoryReader,
    RemoteScanner,
    TradeContext,
    TradeContextStruct,
    Win32,
)


class LiveTradeContextTests(unittest.TestCase):
    """Verify the direct GameContext trade pointer and bounded offers."""

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
        cls.context = TradeContext(cls.reader, cls.game_context)

    @classmethod
    def tearDownClass(cls) -> None:
        """Close the selected process handle."""

        if hasattr(cls, "reader"):
            cls.reader.close()

    def test_layout_matches_native_trade_context(self) -> None:
        """Keep the root at the maintained 0x38-byte size."""

        self.assertEqual(ctypes.sizeof(TradeContextStruct), 0x38)

    def test_reads_trade_context_when_active(self) -> None:
        """Read the context when present, otherwise record the closed state."""

        address = self.context.resolve_address()
        if address is None:
            print("Live TradeContext: closed")
            return
        snapshot = self.context.read()
        self.assertIsNotNone(snapshot)
        if snapshot is None:
            return
        self.assertEqual(
            len(snapshot.player_offer.offered_items),
            snapshot.player_offer.items.m_size,
        )
        self.assertEqual(
            len(snapshot.partner_offer.offered_items),
            snapshot.partner_offer.items.m_size,
        )
        print(
            "Live TradeContext: "
            f"0x{address:08X}, "
            f"player_items={len(snapshot.player_offer.offered_items)}, "
            f"partner_items={len(snapshot.partner_offer.offered_items)}"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
