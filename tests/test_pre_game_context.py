"""Live Guild Wars tests for the external PreGameContext reader."""

from __future__ import annotations

import ctypes
import unittest

from py4gw import (
    LoginCharacter,
    PatternCatalog,
    PreGameContext,
    PreGameContextStruct,
    ProcessMemoryReader,
    RemoteScanner,
    Win32,
)


class LivePreGameContextTests(unittest.TestCase):
    """Verify PreGameContext against a running Guild Wars client."""

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
        cls.context = PreGameContext(
            cls.reader,
            cls.scanner,
            PatternCatalog.from_directory("offsets"),
        )

    @classmethod
    def tearDownClass(cls) -> None:
        """Close the selected process handle after the live checks."""

        if hasattr(cls, "reader"):
            cls.reader.close()

    def test_layout_matches_native_pregame_context(self) -> None:
        """Keep both external fixed-width layouts aligned with the source."""

        self.assertEqual(ctypes.sizeof(LoginCharacter), 0x78)
        self.assertEqual(ctypes.sizeof(PreGameContextStruct), 0x100)
        self.assertEqual(getattr(PreGameContextStruct, "camera_mode").offset, 0x4C)
        self.assertEqual(getattr(PreGameContextStruct, "max_characters").offset, 0xD0)
        self.assertEqual(getattr(PreGameContextStruct, "chars_array").offset, 0xE0)

    def test_resolves_live_pregame_pointer_location(self) -> None:
        """Resolve and cache the JSON global-pointer location."""

        self.context.initialize()
        pointer_address = self.context.cached_pointer_address or 0
        self.assertGreater(pointer_address, 0)
        print(f"Live PreGame global pointer: 0x{pointer_address:08X}")

    def test_reads_live_pregame_context_when_available(self) -> None:
        """Read the pre-game structure or report that the client is in-game."""

        snapshot = self.context.read()
        if snapshot is None:
            print("PreGameContext is not active; client is outside the selection menus")
            return

        self.assertEqual(len(bytes(snapshot)), 0x100)
        characters = snapshot.chars_list
        self.assertTrue(all(isinstance(character, LoginCharacter) for character in characters))
        print(
            "Live pre-game characters: "
            + ", ".join(character.character_name_str for character in characters)
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
