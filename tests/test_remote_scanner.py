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

    def test_the_nearest_prologue_is_the_answer_and_a_jmp_is_not_an_entry(self) -> None:
        """``Scanner::ToFunctionStart`` is a prologue search and nothing else (``scanner.cpp:205``).

        This test used to pin the opposite. A ``jmp`` whose destination leaves the module counted
        as a patched function entry and the *nearest* candidate of the two won — an inference this
        port added for its own crash recovery, and one that cannot be checked without decoding the
        instruction the byte belongs to. On this build it handed the host ``0x0082D64F`` for
        ``chat.send_chat_func``: the ``e9`` there is the tail of the instruction before the match
        site, its displacement leaves the module, and the real prologue is at ``0x0082D620``. The
        address is inside ``.text``, so the section check that stops the older crash could not catch
        it, and calling it is the crash of 2026-09-25 (reproduced offline by
        ``tools/resolve_offline.py``).

        So the member is the source's again, and the recovery that needs the patched entry lives in
        ``py4gw/client.py`` (``_stale_patch_before``), where the bytes it expects are known and the
        restore can be verified instead of guessed.
        """

        base, image = _make_module()
        data = bytearray(image)
        # .text's virtual address is also its raw offset in this synthetic image.
        text = 0x1000
        data[text + 0x20 : text + 0x23] = b"\x55\x8B\xEC"  # the function's prologue
        detour = base + text + 0x40
        outside = base + 0x100000
        # A jmp that leaves the module, five bytes *nearer* the site than the prologue — the shape
        # that used to win, and the shape the chat crash came from.
        data[text + 0x40 : text + 0x45] = b"\xE9" + struct.pack(
            "<i", outside - (detour + 5)
        )
        scanner = RemoteScanner(
            _TestMemoryReader(base, bytes(data)), base, len(data), 0x10
        )
        scanner.initialize()

        self.assertEqual(
            scanner.to_function_start(base + text + 0x60), base + text + 0x20
        )

        # The same bytes pointing inside the module are an ordinary branch; the answer is unchanged.
        inside = base + text + 0x80
        data[text + 0x40 : text + 0x45] = b"\xE9" + struct.pack(
            "<i", inside - (detour + 5)
        )
        branchy = RemoteScanner(
            _TestMemoryReader(base, bytes(data)), base, len(data), 0x10
        )
        branchy.initialize()

        self.assertEqual(
            branchy.to_function_start(base + text + 0x60), base + text + 0x20
        )

        # With no prologue in range there is no answer — a patched entry is not one.
        data[text + 0x20 : text + 0x23] = b"\x90\x90\x90"
        empty = RemoteScanner(
            _TestMemoryReader(base, bytes(data)), base, len(data), 0x10
        )
        empty.initialize()

        self.assertIsNone(empty.to_function_start(base + text + 0x60, 0x20))

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

    def test_the_image_base_is_the_sources_constant_not_the_headers(self) -> None:
        """``kGwImageBase``, because this client's own loader rewrites its header.

        ``ToRuntimeAddress`` (``dialog_patterns.cpp:23-31``) rebases with the **constant**
        ``0x00400000``. The client's live ``OptionalHeader.ImageBase`` instead reads the
        address it was loaded at (``0x610000``), so a rebase taken from the header is a no-op —
        which is what this port did until 2026-09-25, when it called a dialog loader 0x210000
        below the address the sources mean and faulted the client (``docs/RESEARCH.md``).
        """

        self.assertEqual(self.scanner.image_base, 0x00400000)

        # The same image, loaded away from the base it was linked at: the rebase has to move
        # the address, and by exactly the load delta.
        loaded_at = 0x610000
        relocated = RemoteScanner(
            _TestMemoryReader(loaded_at, self.image),
            loaded_at,
            len(self.image),
            0x10,
        )
        relocated.initialize()

        self.assertEqual(relocated.image_base, 0x00400000)
        self.assertEqual(
            relocated.to_module_address(0x00913920),
            0x00913920 + (loaded_at - 0x00400000),
            "the source's arithmetic, applied to the load delta",
        )
        self.assertNotEqual(
            relocated.to_module_address(0x00913920),
            0x00913920,
            "an unrebased link-time address is what the crash was",
        )

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
