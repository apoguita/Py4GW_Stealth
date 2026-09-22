"""Live Guild Wars tests for the external Cinematic context reader."""

from __future__ import annotations

import ctypes
import unittest

from py4gw import (
    Cinematic,
    CinematicStruct,
    GameContext,
    PatternCatalog,
    ProcessMemoryReader,
    RemoteScanner,
    Win32,
)


class LiveCinematicContextTests(unittest.TestCase):
    """Verify Cinematic against a running Guild Wars client."""

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
        cls.context = Cinematic(cls.reader, cls.game_context)

    @classmethod
    def tearDownClass(cls) -> None:
        """Close the selected process handle after the live checks."""

        if hasattr(cls, "reader"):
            cls.reader.close()

    def test_layout_matches_native_cinematic(self) -> None:
        """Keep the fixed-width layout aligned with the native source."""

        self.assertEqual(ctypes.sizeof(CinematicStruct), 0x08)
        self.assertEqual(getattr(CinematicStruct, "h0000").offset, 0x00)
        self.assertEqual(getattr(CinematicStruct, "h0004").offset, 0x04)

    def test_resolves_live_cinematic_pointer(self) -> None:
        """Follow GameContext's cinematic pointer without assuming it is active."""

        address = self.context.resolve_address()
        if address is None:
            print("Cinematic context is not active")
            return

        self.assertGreater(address, 0)
        print(f"Live Cinematic: 0x{address:08X}")

    def test_reads_live_cinematic_when_available(self) -> None:
        """Read the complete structure whenever a cinematic is playing."""

        snapshot = self.context.read()
        if snapshot is None:
            print("Cinematic context is not active")
            return

        self.assertEqual(len(bytes(snapshot)), 0x08)
        self.assertIsInstance(snapshot.h0000, int)
        self.assertIsInstance(snapshot.h0004, int)
        print(
            "Live Cinematic fields: "
            f"h0000=0x{snapshot.h0000:08X}, "
            f"h0004=0x{snapshot.h0004:08X}"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
