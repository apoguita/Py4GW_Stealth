"""Live Guild Wars tests for the external GameplayContext reader."""

from __future__ import annotations

import ctypes
import unittest

from py4gw import (
    GameplayContext,
    GameplayContextStruct,
    PatternCatalog,
    ProcessMemoryReader,
    RemoteScanner,
    Win32,
)


class LiveGameplayContextTests(unittest.TestCase):
    """Verify GameplayContext against a running Guild Wars client."""

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
        cls.context = GameplayContext(
            cls.reader,
            cls.scanner,
            PatternCatalog.from_directory("offsets"),
        )

    @classmethod
    def tearDownClass(cls) -> None:
        """Close the selected process handle after the live checks."""

        if hasattr(cls, "reader"):
            cls.reader.close()

    def test_layout_matches_native_gameplay_context(self) -> None:
        """Keep the fixed-width layout aligned with the native source."""

        self.assertEqual(ctypes.sizeof(GameplayContextStruct), 0x78)
        self.assertEqual(GameplayContextStruct.h0000.offset, 0x00)
        self.assertEqual(GameplayContextStruct.mission_map_zoom.offset, 0x4C)
        self.assertEqual(GameplayContextStruct.unk.offset, 0x50)

    def test_resolves_live_gameplay_pointer(self) -> None:
        """Resolve and cache the JSON global-pointer location."""

        address = self.context.resolve_address()
        pointer_address = self.context.cached_pointer_address or 0
        self.assertGreater(pointer_address, 0)
        if address is None:
            print("GameplayContext is not active")
            return

        self.assertGreater(address, 0)
        print(f"Live Gameplay global pointer: 0x{pointer_address:08X}")
        print(f"Live GameplayContext: 0x{address:08X}")

    def test_reads_live_gameplay_context_when_available(self) -> None:
        """Read the complete structure whenever gameplay state is available."""

        snapshot = self.context.read()
        if snapshot is None:
            print("GameplayContext is not active")
            return

        self.assertEqual(len(bytes(snapshot)), 0x78)
        self.assertIsInstance(snapshot.mission_map_zoom, float)
        print(f"Live mission map zoom: {snapshot.mission_map_zoom:.3f}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
