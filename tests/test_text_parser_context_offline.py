"""Offline parity checks for the external ``TextParser`` reader."""

from __future__ import annotations

import ctypes
import unittest
from typing import Any
from unittest import mock

from py4gw import (
    LanguageSlotStruct,
    TextCacheStruct,
    TextFileSlotStruct,
    TextParser,
    TextParserSubStructStruct,
    TextParserStruct,
)


class _Memory:
    """Small deterministic byte store for bounded nested-read checks."""

    def __init__(self) -> None:
        self._blocks: dict[int, bytes] = {}

    def add(self, address: int, value: bytes) -> None:
        self._blocks[address] = value

    def read(self, address: int, size: int) -> bytes:
        for start, value in self._blocks.items():
            end = start + len(value)
            if start <= address and address + size <= end:
                offset = address - start
                return value[offset : offset + size]
        raise AssertionError(f"unmapped read: 0x{address:08X}+{size}")


class TextParserParityTests(unittest.TestCase):
    """Check every source-defined layout, property, and facade member."""

    def test_source_layouts(self) -> None:
        """The typed cache records retain their source sizes and offsets."""

        self.assertEqual(ctypes.sizeof(TextCacheStruct), 0x04)
        self.assertEqual(ctypes.sizeof(TextParserSubStructStruct), 0x04)
        self.assertEqual(ctypes.sizeof(LanguageSlotStruct), 0x0C)
        self.assertEqual(ctypes.sizeof(TextFileSlotStruct), 0x24)
        self.assertEqual(ctypes.sizeof(TextParserStruct), 0x1D4)
        self.assertEqual(
            [field[0] for field in TextParserStruct._fields_],
            [
                "_h0000",
                "dec_start_ptr",
                "dec_end_ptr",
                "substitute_1",
                "substitute_2",
                "_cache_header",
                "language_slots",
                "_cache_pad",
                "entries_per_file",
                "_pad_post_cache",
                "h0160",
                "h0164",
                "h0168",
                "_h016C",
                "sub_struct_ptr",
                "_h0184",
                "language_id",
            ],
        )
        self.assertEqual(getattr(TextParserStruct, "_cache_header").offset, 0x30)
        self.assertEqual(getattr(TextParserStruct, "language_slots").offset, 0x64)
        self.assertEqual(getattr(TextParserStruct, "entries_per_file").offset, 0x148)
        self.assertEqual(getattr(TextParserStruct, "sub_struct_ptr").offset, 0x180)
        self.assertEqual(getattr(TextParserStruct, "language_id").offset, 0x1D0)

    def test_source_cache_pointer_property_uses_inline_header(self) -> None:
        """The source's 0x34-byte cache header starts with TextCache*."""

        parser = TextParserStruct()
        parser._cache_header[:4] = (0x00200000).to_bytes(4, "little")
        self.assertEqual(parser.cache_ptr, 0x00200000)

    def test_get_file_slot_reads_bounded_slot_and_hash(self) -> None:
        """A valid language slot reads one remote record and its UTF-16 hash."""

        memory = _Memory()
        slot_address = 0x00200000
        hash_address = 0x00300000
        slot = TextFileSlotStruct()
        slot.file_hash_ptr = hash_address
        slot.lang_id = 2
        slot.start_index = 10
        slot.end_index = 20
        memory.add(slot_address, bytes(slot))
        memory.add(hash_address, "items\x00".encode("utf-16-le"))

        parser = TextParserStruct().bind_reader(memory)
        parser.language_slots[0].slot_array_ptr = slot_address
        parser.language_slots[0].slot_count = 1

        result = parser.get_file_slot(0)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.lang_id, 2)
        self.assertEqual(result.start_index, 10)
        self.assertEqual(result.end_index, 20)
        self.assertEqual(result.file_hash, "items")
        self.assertIsNone(parser.get_file_slot(1))
        self.assertIsNone(parser.get_file_slot(0, 11))

    def test_source_nested_properties_are_declared(self) -> None:
        for name in ("cache", "sub_struct", "dec_start", "dec_end", "h0000", "h016c", "h0184"):
            self.assertTrue(hasattr(TextParserStruct, name), name)
        parser = TextParserStruct()
        self.assertIsNone(parser.cache)
        self.assertIsNone(parser.sub_struct)

    def test_source_facade_members_are_declared(self) -> None:
        for name in (
            "get_ptr",
            "_update_ptr",
            "enable",
            "disable",
            "get_context",
        ):
            self.assertTrue(hasattr(TextParser, name), name)
        self.assertTrue(hasattr(TextParser, "_string_table_triggered"))

    def test_callback_enable_is_explicitly_external_unavailable(self) -> None:
        with self.assertRaises(NotImplementedError):
            TextParser.enable()

    def test_static_facade_refresh_has_source_state_semantics_without_client(self) -> None:
        TextParser.disable()
        TextParser._update_ptr()
        self.assertEqual(TextParser.get_ptr(), 0)
        self.assertIsNone(TextParser.get_context())


class _FakeParserReader:
    """The two things the facade asks a client's TextParser reader for.

    ``read`` answers ``None`` for a missing address, which is what the real reader does and
    what makes "no context" distinguishable from "an empty context".
    """

    def __init__(self, address: int, snapshot: TextParserStruct) -> None:
        self._address = address
        self._snapshot = snapshot

    def resolve_address(self) -> int:
        return self._address

    def read(self) -> TextParserStruct | None:
        return self._snapshot if self._address else None


class _FakeClient:
    """A client that hands over one TextParser snapshot."""

    def __init__(self, reader: _FakeParserReader) -> None:
        self.text_parser = reader


class StringTableTriggerTests(unittest.TestCase):
    """The load the first refresh starts, which is ``TextContext.py:152-155``.

    The source's ``_update_ptr`` hands the language to ``_do_load_string_table`` the first time
    it finds a context, and never again. That is the trigger for the whole string table — the
    decode path has no separate "load the table" step for a caller to remember.
    """

    def setUp(self) -> None:
        self.loaded: list[int] = []
        snapshot = TextParserStruct()
        snapshot.language_id = 3
        self.client = _FakeClient(_FakeParserReader(0x00200000, snapshot))

        TextParser.disable()
        TextParser._string_table_triggered = False
        self.addCleanup(setattr, TextParser, "_string_table_triggered", False)

        self._client_patch = mock.patch(
            "py4gw.client.current_client", return_value=self.client
        )
        self._client_patch.start()
        self.addCleanup(self._client_patch.stop)

        self._load_patch = mock.patch(
            "py4gw.internals.string_table._do_load_string_table", self.loaded.append
        )
        self._load_patch.start()
        self.addCleanup(self._load_patch.stop)

    def test_the_first_refresh_starts_the_load_for_the_clients_language(self) -> None:
        TextParser._update_ptr()

        self.assertEqual(self.loaded, [3])
        self.assertIsNotNone(TextParser.get_context())

    def test_the_load_is_started_once(self) -> None:
        TextParser._update_ptr()
        TextParser._update_ptr()

        self.assertEqual(self.loaded, [3], "the source triggers it once")

    def test_a_refresh_with_no_client_starts_nothing(self) -> None:
        with mock.patch("py4gw.client.current_client", return_value=None):
            TextParser._update_ptr()

        self.assertEqual(self.loaded, [])
        self.assertFalse(TextParser._string_table_triggered)

    def test_a_refresh_that_found_no_context_starts_nothing(self) -> None:
        """``_update_ptr``'s own failure path leaves the facade empty and loads no table."""

        client: Any = _FakeClient(_FakeParserReader(0, TextParserStruct()))
        with mock.patch("py4gw.client.current_client", return_value=client):
            TextParser._update_ptr()

        self.assertEqual(self.loaded, [])
        self.assertEqual(TextParser.get_ptr(), 0)
        self.assertIsNone(TextParser.get_context())


if __name__ == "__main__":
    unittest.main(verbosity=2)
