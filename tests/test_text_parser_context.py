"""Live Guild Wars tests for the external TextParser reader."""

from __future__ import annotations

import ctypes
import unittest

from py4gw import (
    GameContext,
    GameContextStruct,
    PatternCatalog,
    ProcessMemoryReader,
    RemoteScanner,
    TextCacheStruct,
    TextParser,
    TextParserStruct,
    TextParserSubStructStruct,
    Win32,
)


class LiveTextParserTests(unittest.TestCase):
    """Verify TextParser through the live GameContext pointer field."""

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
        cls.context = TextParser(cls.reader, cls.game_context)

    @classmethod
    def tearDownClass(cls) -> None:
        """Close the selected process handle after the live checks."""

        if hasattr(cls, "reader"):
            cls.reader.close()

    def test_layout_matches_native_text_parser(self) -> None:
        """Keep the root and pointed-to records aligned with native source."""

        self.assertEqual(ctypes.sizeof(TextCacheStruct), 0x04)
        self.assertEqual(ctypes.sizeof(TextParserSubStructStruct), 0x04)
        self.assertEqual(ctypes.sizeof(TextParserStruct), 0x1D4)
        self.assertEqual(TextParserStruct.cache_ptr.offset, 0x30)
        self.assertEqual(TextParserStruct.sub_struct_ptr.offset, 0x180)
        self.assertEqual(TextParserStruct.language_id.offset, 0x1D0)
        self.assertEqual(GameContextStruct.text_parser.offset, 0x18)

    def test_resolves_live_text_parser_pointer(self) -> None:
        """Follow GameContext.text_parser at the native +0x18 offset."""

        address = self.context.resolve_address()
        if address is None:
            self.skipTest("The connected client has no active TextParser.")
        self.assertGreater(address, 0)
        print(f"Live TextParser: 0x{address:08X}")

    def test_reads_live_text_parser(self) -> None:
        """Read the complete maintained root structure from the client."""

        snapshot = self.context.read()
        if snapshot is None:
            self.skipTest("The connected client has no active TextParser.")
        self.assertEqual(len(bytes(snapshot)), 0x1D4)
        self.assertGreaterEqual(int(snapshot.language_id), 0)
        print(f"Live TextParser language: {snapshot.language_id}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
