"""Live Guild Wars tests for the external available-character roster."""

from __future__ import annotations

import ctypes
import unittest

from py4gw import (
    AvailableCharacterArray,
    AvailableCharacterArrayStruct,
    AvailableCharacterInfoStruct,
    PatternCatalog,
    ProcessMemoryReader,
    RemoteScanner,
    Win32,
)


class LiveAvailableCharacterTests(unittest.TestCase):
    """Verify the native account-wide roster and its packed properties."""

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
        cls.context = AvailableCharacterArray(
            cls.reader,
            cls.scanner,
            PatternCatalog.from_directory("offsets"),
        )

    @classmethod
    def tearDownClass(cls) -> None:
        """Close the selected process handle after the live checks."""

        if hasattr(cls, "reader"):
            cls.reader.close()

    def test_layout_matches_native_roster(self) -> None:
        """Keep the native entry and GWArray header layouts exact."""

        self.assertEqual(ctypes.sizeof(AvailableCharacterInfoStruct), 0x84)
        self.assertEqual(ctypes.sizeof(AvailableCharacterArrayStruct), 0x10)
        self.assertEqual(
            getattr(AvailableCharacterInfoStruct, "player_name_enc").offset, 0x18
        )
        self.assertEqual(getattr(AvailableCharacterInfoStruct, "props").offset, 0x40)

    def test_resolves_live_roster_array(self) -> None:
        """Resolve the copied player.available_characters_addr chain."""

        address = self.context.resolve_address()
        self.assertIsNotNone(address)
        assert address is not None
        self.assertGreater(address, 0)
        print(f"Live available-character GWArray: 0x{address:08X}")

    def test_reads_live_roster_entries(self) -> None:
        """Read live names and packed properties from the roster entries."""

        snapshot = self.context.read()
        if snapshot is None:
            self.skipTest("The account roster is not available in this client.")
        entries = snapshot.available_characters_list
        self.assertLessEqual(len(entries), snapshot.available_characters_array.m_capacity)
        if not entries:
            print("Live available-character roster is empty")
            return

        first = entries[0]
        self.assertTrue(first.player_name_str)
        self.assertGreaterEqual(first.level, 0)
        print(
            "Live available characters: "
            f"count={len(entries)}, first={first.player_name_str}, "
            f"level={first.level}, map={first.map_id}"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
