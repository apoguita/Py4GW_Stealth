"""Live Guild Wars tests for the external GuildContext reader."""

from __future__ import annotations

import ctypes
import unittest

from py4gw import (
    CapeDesignStruct,
    GHKeyStruct,
    GameContext,
    GuildContext,
    GuildContextStruct,
    GuildHistoryEventStruct,
    GuildPlayerStruct,
    GuildStruct,
    PatternCatalog,
    ProcessMemoryReader,
    RemoteScanner,
    TownAllianceStruct,
    Win32,
)


class LiveGuildContextTests(unittest.TestCase):
    """Verify GuildContext and its nested remote arrays against Guild Wars."""

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
        patterns = PatternCatalog.from_directory("offsets")
        cls.game_context = GameContext(cls.reader, cls.scanner, patterns)
        cls.game_context.initialize()
        cls.context = GuildContext(cls.reader, cls.game_context)

    @classmethod
    def tearDownClass(cls) -> None:
        """Close the selected process handle after the live checks."""

        if hasattr(cls, "reader"):
            cls.reader.close()

    def test_layout_matches_native_guild_context(self) -> None:
        """Keep the maintained nested structures at their native offsets."""

        self.assertEqual(ctypes.sizeof(GHKeyStruct), 0x10)
        self.assertEqual(ctypes.sizeof(CapeDesignStruct), 0x1C)
        self.assertEqual(ctypes.sizeof(TownAllianceStruct), 0x78)
        self.assertEqual(ctypes.sizeof(GuildHistoryEventStruct), 0x208)
        self.assertEqual(ctypes.sizeof(GuildStruct), 0xAC)
        self.assertEqual(ctypes.sizeof(GuildPlayerStruct), 0x174)
        self.assertEqual(ctypes.sizeof(GuildContextStruct), 0x368)
        self.assertEqual(GuildContextStruct.player_name_enc.offset, 0x34)
        self.assertEqual(GuildContextStruct.player_gh_key.offset, 0x64)
        self.assertEqual(GuildContextStruct.guild_array_array.offset, 0x2F8)
        self.assertEqual(GuildContextStruct.player_roster_array.offset, 0x358)

    def test_resolves_live_guild_context(self) -> None:
        """Follow the direct GameContext.guild pointer."""

        address = self.context.resolve_address()
        if address is None:
            self.skipTest("The connected client has no active GuildContext.")
        self.assertGreater(address, 0)
        print(f"Live GuildContext: 0x{address:08X}")

    def test_reads_live_guild_context_and_nested_data(self) -> None:
        """Read the maintained root fields and nested guild arrays."""

        snapshot = self.context.read()
        if snapshot is None:
            self.skipTest("The connected client has no active GuildContext.")

        self.assertEqual(len(bytes(snapshot)), 0x368)
        self.assertIsInstance(snapshot.player_name_str, str)
        guilds = snapshot.guild_array
        roster = snapshot.player_roster
        history = snapshot.player_guild_history
        print(
            "Live guild: "
            f"player={snapshot.player_name_str or 'in selection menus'}, "
            f"guild_index={int(snapshot.player_guild_index)}, "
            f"guilds={len(guilds)}, roster={len(roster)}, history={len(history)}"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
