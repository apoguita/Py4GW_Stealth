"""Live Guild Wars tests for the external TextParser reader.

Read-only: a direct ``ProcessMemoryReader``, no connection and no elevation. What these checks are
for is the thing the offline suite could not do before -- reading this record **against a real
client**, where the fields hold whatever the client holds. That is where the removed additive
members were found: `sub_struct` followed offset +0x180 as a pointer, this client holds 0x4C there,
and an offline test with a zeroed record could not see it because the port's guard returns before
reading. The checks below therefore follow the source's own helper (`get_file_slot`) and its bounded
hash read, and assert the declared layout; nothing here reads a field as a pointer unless the source
declares it one.
"""

from __future__ import annotations

import ctypes
import unittest

from py4gw import (
    GameContext,
    GameContextStruct,
    LanguageSlotStruct,
    PatternCatalog,
    ProcessMemoryReader,
    RemoteScanner,
    TextFileSlotStruct,
    TextParser,
    TextParserStruct,
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

    def test_layout_matches_the_source_text_parser(self) -> None:
        """Keep the root record aligned with the source the port reads it from."""

        self.assertEqual(ctypes.sizeof(TextParserStruct), 0x1D4)
        self.assertEqual(ctypes.sizeof(TextFileSlotStruct), 0x24)
        self.assertEqual(ctypes.sizeof(LanguageSlotStruct), 0x0C)
        self.assertEqual(getattr(TextParserStruct, "_cache_header").offset, 0x30)
        self.assertEqual(getattr(TextParserStruct, "sub_struct_ptr").offset, 0x180)
        self.assertEqual(getattr(TextParserStruct, "language_id").offset, 0x1D0)
        self.assertEqual(getattr(GameContextStruct, "text_parser").offset, 0x18)

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

    def test_follows_the_source_helper_to_a_real_file_slot(self) -> None:
        """The one member that follows a pointer is the source's own, and it is bounded.

        ``get_file_slot`` is Reforged's helper, and its own guards are what this checks against the
        live client: an out-of-range language or slot is ``None`` (no read at all), and a slot whose
        array pointer is set reads one record whose UTF-16 hash decodes. Before this, no live check
        followed any pointer in this record -- which is how a property the source does not declare
        managed to follow +0x180 for months.
        """

        snapshot = self.context.read()
        if snapshot is None:
            self.skipTest("The connected client has no active TextParser.")
        self.assertIsNone(snapshot.get_file_slot(0, len(snapshot.language_slots)))
        self.assertIsNone(snapshot.get_file_slot(-1))
        language_slot = snapshot.language_slots[0]
        if not int(language_slot.slot_array_ptr) or not int(language_slot.slot_count):
            self.skipTest("The connected client has no file slot array for language 0.")
        slot = snapshot.get_file_slot(0)
        self.assertIsNotNone(slot)
        assert slot is not None
        self.assertIsInstance(slot.file_hash, str)
        print(f"Live file slot 0 hash: {slot.file_hash!r}")
        self.assertIsNone(snapshot.get_file_slot(int(language_slot.slot_count)))
        # The declared field is a word, not a pointer to follow: this is the value at +0x180 and
        # reading it must not read through it.
        self.assertIsInstance(int(snapshot.sub_struct_ptr), int)


if __name__ == "__main__":
    unittest.main(verbosity=2)
