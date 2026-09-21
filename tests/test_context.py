"""Live Guild Wars tests for the external CharContext reader."""

from __future__ import annotations

import ctypes
import unittest

from py4gw import (
    CharContext,
    CharContextStruct,
    PatternCatalog,
    ProcessMemoryReader,
    RemoteScanner,
    Win32,
)


class LiveContextTests(unittest.TestCase):
    """Verify CharContext against a running, logged-in Guild Wars client."""

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
        cls.context = CharContext(
            cls.reader,
            cls.scanner,
            PatternCatalog.from_directory("offsets"),
        )

    @classmethod
    def tearDownClass(cls) -> None:
        """Close the selected process handle after the live checks."""

        if hasattr(cls, "reader"):
            cls.reader.close()

    def test_reads_complete_live_context(self) -> None:
        """Read the complete maintained structure and expose its name."""

        snapshot = self.context.read()
        self.assertEqual(ctypes.sizeof(CharContextStruct), 0x448)
        self.assertEqual(len(bytes(snapshot)), 0x448)
        self.assertEqual(
            snapshot.is_logged_in, bool(snapshot.player_name_str.strip())
        )
        self.assertIsInstance(self.context.is_logged_in, bool)
        description = snapshot.player_name_str or "in selection menus"
        print(f"Live character: {description}")

    def test_resolves_live_context_address(self) -> None:
        """Resolve the current CharContext through the JSON resolver chain."""

        address = self.context.resolve_address()
        self.assertGreater(address, 0)
        print(f"Live CharContext: 0x{address:08X}")

    def test_reads_live_gw_array_views(self) -> None:
        """Read the maintained GW_Array fields through remote memory."""

        snapshot = self.context.read()
        pointer_values = snapshot.h0014_ptrs
        observer_matches = snapshot.observer_matches
        progress_bar = snapshot.progress_bar
        self.assertTrue(
            pointer_values is None or all(isinstance(value, int) for value in pointer_values)
        )
        self.assertTrue(observer_matches is None or all(observer_matches))
        self.assertTrue(progress_bar is None or ctypes.sizeof(progress_bar) == 0x2C)
        print(
            "Live GW_Array values: "
            f"h0014={len(pointer_values or [])}, "
            f"observer_matches={len(observer_matches or [])}"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
