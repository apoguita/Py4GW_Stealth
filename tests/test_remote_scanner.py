"""Offline tests for remote-scanner logic using a test read transport."""

from __future__ import annotations

import struct
import unittest

from py4gw import Pattern, RemoteScanner


class _TestMemoryReader:
    """Read from one synthetic module image."""

    def __init__(self, base: int, image: bytes) -> None:
        self.base = base
        self.image = image

    def read(self, address: int, size: int) -> bytes:
        """Return one bounded image slice."""

        start = address - self.base
        end = start + size
        if start < 0 or end > len(self.image):
            raise OSError(299, "partial copy")
        return self.image[start:end]


def _make_module() -> tuple[int, bytes]:
    """Build a minimal x86 PE image with three virtual sections."""

    base = 0x400000
    image = bytearray(0x3000)
    image[0:2] = b"MZ"
    struct.pack_into("<I", image, 0x3C, 0x80)
    image[0x80:0x84] = b"PE\x00\x00"
    struct.pack_into("<HH", image, 0x84, 0x14C, 3)
    struct.pack_into("<H", image, 0x94, 0xE0)
    struct.pack_into("<H", image, 0x98, 0x10B)

    section_offset = 0x178
    for index, (name, address) in enumerate(
        ((b".text", 0x1000), (b".rdata", 0x2000), (b".data", 0x2800))
    ):
        offset = section_offset + index * 40
        image[offset : offset + len(name)] = name
        struct.pack_into("<III", image, offset + 8, 0x100, address, 0x100)
    return base, bytes(image)


class RemoteScannerTests(unittest.TestCase):
    """Verify section parsing and chunked address scanning."""

    def setUp(self) -> None:
        """Create one synthetic module for each test."""

        self.base, self.image = _make_module()
        self.reader = _TestMemoryReader(self.base, self.image)
        self.scanner = RemoteScanner(self.reader, self.base, len(self.image), 0x10)
        self.scanner.initialize()

    def test_initializes_expected_sections(self) -> None:
        """PE section virtual addresses become target ranges."""

        text = self.scanner.get_section_range("text")
        self.assertEqual(text.start, self.base + 0x1000)
        self.assertEqual(text.end, self.base + 0x1100)
        self.assertTrue(self.scanner.is_valid_ptr(self.base + 0x1050, "text"))
        self.assertFalse(self.scanner.is_valid_ptr(self.base + 0x1500, "text"))

    def test_finds_pattern_across_read_chunk_boundary(self) -> None:
        """Overlap reads preserve matches split between chunks."""

        data = bytearray(self.image)
        pattern_address = self.base + 0x1000 + 0x0F
        data[0x1000 + 0x0F : 0x1000 + 0x12] = b"ABC"
        scanner = RemoteScanner(
            _TestMemoryReader(self.base, bytes(data)), self.base, len(data), 0x10
        )
        scanner.initialize()

        self.assertEqual(scanner.find(Pattern(b"ABC", "xxx")), pattern_address)

    def test_resolves_near_call_and_function_start(self) -> None:
        """x86 relative calls and standard prologues resolve in target space."""

        data = bytearray(self.image)
        call_address = self.base + 0x1000 + 0x20
        target_address = self.base + 0x1000 + 0x60
        displacement = target_address - (call_address + 5)
        data[0x1020] = 0xE8
        struct.pack_into("<i", data, 0x1021, displacement)
        data[0x1050:0x1053] = b"\x55\x8B\xEC"
        scanner = RemoteScanner(
            _TestMemoryReader(self.base, bytes(data)), self.base, len(data), 0x40
        )
        scanner.initialize()

        self.assertEqual(scanner.function_from_near_call(call_address), target_address)
        self.assertEqual(scanner.to_function_start(target_address), self.base + 0x1050)

    def test_scans_explicit_range_backwards(self) -> None:
        """Native-style descending ranges return the nearest match first."""

        data = bytearray(self.image)
        data[0x1030:0x1033] = b"ABC"
        data[0x1060:0x1063] = b"ABC"
        scanner = RemoteScanner(
            _TestMemoryReader(self.base, bytes(data)), self.base, len(data), 0x10
        )
        scanner.initialize()

        matches = scanner.find_in_range(
            Pattern(b"ABC", "xxx"), self.base + 0x1070, self.base + 0x1000
        )
        self.assertEqual(matches, [self.base + 0x1060, self.base + 0x1030])

    def test_finds_ansi_string_use(self) -> None:
        """A string in rdata can be resolved to its code reference."""

        data = bytearray(self.image)
        string_address = self.base + 0x2040
        data[0x2040:0x2045] = b"Hello"
        use_address = self.base + 0x1030
        data[0x1030:0x1034] = string_address.to_bytes(4, "little")
        scanner = RemoteScanner(
            _TestMemoryReader(self.base, bytes(data)), self.base, len(data), 0x40
        )
        scanner.initialize()

        self.assertEqual(scanner.find_use_of_string("Hello"), use_address)

    def test_finds_wide_string_use(self) -> None:
        """UTF-16 literals use the same address-reference path."""

        data = bytearray(self.image)
        encoded = "Wide".encode("utf-16-le") + b"\x00\x00"
        string_address = self.base + 0x2060
        data[0x2060 : 0x2060 + len(encoded)] = encoded
        use_address = self.base + 0x1040
        data[0x1040:0x1044] = string_address.to_bytes(4, "little")
        scanner = RemoteScanner(
            _TestMemoryReader(self.base, bytes(data)), self.base, len(data), 0x40
        )
        scanner.initialize()

        self.assertEqual(scanner.find_use_of_string("Wide", wide=True), use_address)

    def test_finds_native_assertion_sequence(self) -> None:
        """Assertion file/message literals resolve to the native call pattern."""

        data = bytearray(self.image)
        file_address = self.base + 0x2020
        message_address = self.base + 0x2040
        data[0x2020:0x2020 + 8] = b"test.cpp"
        data[0x2040:0x2040 + 7] = b"failure"
        data[0x1060:0x1060 + 10] = (
            b"\xBA"
            + file_address.to_bytes(4, "little")
            + b"\xB9"
            + message_address.to_bytes(4, "little")
        )
        scanner = RemoteScanner(
            _TestMemoryReader(self.base, bytes(data)), self.base, len(data), 0x40
        )
        scanner.initialize()

        self.assertEqual(
            scanner.find_assertion("test.cpp", "failure"),
            self.base + 0x1060,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
