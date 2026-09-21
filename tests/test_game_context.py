"""Live Guild Wars tests for the external GameContext reader."""

from __future__ import annotations

import ctypes
import unittest

from py4gw import (
    GameContext,
    GameContextStruct,
    PatternCatalog,
    ProcessMemoryReader,
    RemoteScanner,
    Win32,
)


class LiveGameContextTests(unittest.TestCase):
    """Verify GameContext against a running Guild Wars client."""

    @classmethod
    def setUpClass(cls) -> None:
        """Open the first discovered client with read-only access."""

        cls.win32 = Win32()
        clients = cls.win32.find_guild_wars()
        if not clients:
            raise unittest.SkipTest("Start Guild Wars before running this test.")

        cls.pid = int(clients[0]["pid"])
        module = cls.win32.get_main_module(cls.pid)
        cls.reader = ProcessMemoryReader(cls.win32, cls.pid)
        cls.scanner = RemoteScanner(
            cls.reader,
            int(module["base_address"]),
            int(module["size"]),
        )
        cls.scanner.initialize()
        cls.context = GameContext(
            cls.reader,
            cls.scanner,
            PatternCatalog.from_directory("offsets"),
        )

    @classmethod
    def tearDownClass(cls) -> None:
        """Close the selected process handle after the live checks."""

        if hasattr(cls, "reader"):
            cls.reader.close()

    def test_layout_matches_native_game_context(self) -> None:
        """Keep the external fixed-width layout aligned with the native source."""

        self.assertEqual(ctypes.sizeof(GameContextStruct), 0x5C)
        self.assertEqual(GameContextStruct.agent_context.offset, 0x08)
        self.assertEqual(GameContextStruct.map_context.offset, 0x14)
        self.assertEqual(GameContextStruct.char_context.offset, 0x44)
        self.assertEqual(GameContextStruct.party_context.offset, 0x4C)
        self.assertEqual(GameContextStruct.trade_context.offset, 0x58)

    def test_resolves_live_game_context_address(self) -> None:
        """Resolve the current GameContext through the JSON resolver chain."""

        address = self.context.resolve_address()
        self.assertGreater(address, 0)
        self.assertIsNotNone(self.context.cached_base_pointer_address)
        print(f"Live GameContext: 0x{address:08X}")

    def test_reads_live_game_context(self) -> None:
        """Read the complete maintained GameContext structure."""

        snapshot = self.context.read()
        self.assertEqual(len(bytes(snapshot)), 0x5C)
        self.assertIsInstance(snapshot.char_context, int)
        self.assertIsInstance(snapshot.world_context, int)
        print(
            "Live GameContext pointers: "
            f"char=0x{snapshot.char_context:08X}, "
            f"world=0x{snapshot.world_context:08X}"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
