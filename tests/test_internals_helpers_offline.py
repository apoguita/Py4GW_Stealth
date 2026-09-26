"""Offline tests for the ported ``internals`` helpers.

``read_wstr`` and ``encoded_wstr_to_str`` are small, and both are used by name across the
ported library, so what matters here is the one place the port diverges from the source:
the source dereferences a pointer in its own address space (``ctypes.wstring_at``) because it
runs inside the client, and this port reads the connected client's memory through its reader,
bounded.

The client boundary is faked: a reader with a window of bytes at known addresses, and a client
that hands it over. Nothing here touches a process.
"""

from __future__ import annotations

import unittest
from typing import Any
from unittest.mock import patch

from py4gw.internals import helpers


class FakeReader:
    """A bounded stand-in for ``ProcessMemoryReader``: bytes at addresses, or a refusal."""

    def __init__(self, base: int, data: bytes) -> None:
        self.base = base
        self.data = data
        self.reads: list[tuple[int, int]] = []

    def read(self, address: int, size: int) -> bytes:
        self.reads.append((address, size))
        if address < self.base or address + size > self.base + len(self.data):
            raise OSError(
                f"address 0x{address:X}+{size} is outside this reader's window"
            )
        start = address - self.base
        return self.data[start : start + size]


class FakeClient:
    """The one thing the helper asks a client for: its reader."""

    def __init__(self, reader: FakeReader) -> None:
        self.reader = reader


def wide(text: str, terminator: bool = True) -> bytes:
    """The client's own encoding of a string: UTF-16LE, optionally NUL-terminated."""

    return text.encode("utf-16-le") + (b"\x00\x00" if terminator else b"")


def connected(reader: FakeReader) -> Any:
    """A patch context that makes ``reader`` the connected client's reader."""

    return patch("py4gw.client.current_client", return_value=FakeClient(reader))


class ReadWstrTests(unittest.TestCase):
    """``read_wstr``: a bounded UTF-16 read of the connected client's memory."""

    BASE = 0x100000

    def reader(self, text: str, terminator: bool = True) -> FakeReader:
        return FakeReader(self.BASE, wide(text, terminator))

    def test_a_null_pointer_is_none(self) -> None:
        """The source's own answer for a pointer it will not dereference."""

        self.assertIsNone(helpers.read_wstr(0))

    def test_a_negative_pointer_is_handed_to_the_reader(self) -> None:
        """The source's check is ``if ptr``, so a negative pointer is not a null one."""

        reader = self.reader("Foreman")

        with connected(reader):
            with self.assertRaisesRegex(OSError, "outside this reader's window"):
                helpers.read_wstr(-1)

    def test_a_string_is_read_through_the_connected_client(self) -> None:
        reader = self.reader("Foreman")

        with connected(reader):
            self.assertEqual(helpers.read_wstr(self.BASE), "Foreman")

        self.assertTrue(reader.reads, "the read went through the client's reader")

    def test_the_read_stops_at_the_terminator(self) -> None:
        reader = FakeReader(self.BASE, wide("Foreman") + wide("trailing"))

        with connected(reader):
            self.assertEqual(helpers.read_wstr(self.BASE), "Foreman")

    def test_a_string_without_a_terminator_runs_to_the_limit(self) -> None:
        reader = self.reader("Foreman", terminator=False)

        with connected(reader):
            self.assertEqual(helpers.read_wstr(self.BASE, limit=3), "For")

    def test_a_long_string_is_read_one_code_unit_at_a_time(self) -> None:
        """One unit per read, so the read never goes past the terminator it has not seen."""

        text = "a" * 400
        reader = self.reader(text)

        with connected(reader):
            self.assertEqual(helpers.read_wstr(self.BASE), text)

        self.assertEqual(len(reader.reads), len(text) + 1, "every unit plus the terminator")
        self.assertTrue(all(size == 2 for _, size in reader.reads))

    def test_without_a_client_there_is_nothing_to_read(self) -> None:
        with patch("py4gw.client.current_client", return_value=None):
            self.assertIsNone(helpers.read_wstr(self.BASE))

    def test_an_unreadable_address_raises_the_readers_own_error(self) -> None:
        """``wstring_at`` would fault; the port's reader raises, and the caller decides."""

        reader = self.reader("Foreman")

        with connected(reader):
            with self.assertRaisesRegex(OSError, "outside this reader's window"):
                helpers.read_wstr(self.BASE + 0x10000)

    def test_a_non_ascii_string_is_read_as_code_points(self) -> None:
        reader = self.reader("Caché")

        with connected(reader):
            self.assertEqual(helpers.read_wstr(self.BASE), "Caché")


class EncodedWstrToStrTests(unittest.TestCase):
    """``encoded_wstr_to_str``: codepoints that are not printable, made visible."""

    def test_none_stays_none(self) -> None:
        self.assertIsNone(helpers.encoded_wstr_to_str(None))

    def test_printable_ascii_passes_through(self) -> None:
        self.assertEqual(helpers.encoded_wstr_to_str("Foreman"), "Foreman")
        self.assertEqual(helpers.encoded_wstr_to_str(""), "")

    def test_newline_and_tab_get_their_own_escapes(self) -> None:
        self.assertEqual(helpers.encoded_wstr_to_str("a\nb\tc"), "a\\nb\\tc")

    def test_everything_else_is_escaped_as_four_hex_digits(self) -> None:
        self.assertEqual(
            helpers.encoded_wstr_to_str("\x01\x02\xe9"), "\\x0001\\x0002\\x00E9"
        )

    def test_a_line_feed_gets_the_newline_escape_not_the_numeric_one(self) -> None:
        """``0x0A`` is checked as ``"\\n"`` before the numeric branch, which is the source's order."""

        self.assertEqual(helpers.encoded_wstr_to_str("\x0a"), "\\n")
        self.assertEqual(helpers.encoded_wstr_to_str("\x0d"), "\\x000D")

    def test_the_escape_is_not_truncated_for_a_wide_codepoint(self) -> None:
        """``04X`` is a minimum width, and the source's format does not cut the value."""

        self.assertEqual(helpers.encoded_wstr_to_str("\U0001F600"), "\\x1F600")


if __name__ == "__main__":
    unittest.main()
