"""Offline layout and bounded-decoding checks for ChatBuffer."""

from __future__ import annotations

import ctypes
import unittest

from py4gw import ChatBufferStruct, ChatMessageStruct


class _FakeReader:
    """Small addressable byte store for variable-length message tests."""

    def __init__(self, memory: dict[int, bytes]) -> None:
        self._memory = memory

    def read(self, address: int, size: int) -> bytes:
        for start, value in self._memory.items():
            end = start + len(value)
            if start <= address and address + size <= end:
                offset = address - start
                return value[offset : offset + size]
        raise OSError(f"unmapped fake address 0x{address:08X}")


class ChatBufferOfflineTests(unittest.TestCase):
    """Check fixed-width chat records without a live client."""

    def test_layout_matches_native_offsets(self) -> None:
        """The native header and ring-buffer sizes remain fixed-width."""

        self.assertEqual(ctypes.sizeof(ChatMessageStruct), 0x10)
        self.assertEqual(ctypes.sizeof(ChatBufferStruct), 0x80C)
        self.assertEqual(ChatBufferStruct.message_pointers.offset, 0x0C)

    def test_decodes_bounded_message_payload(self) -> None:
        """A remote message header and raw UTF-16 payload read correctly."""

        address = 0x20000
        message = ChatMessageStruct()
        message.channel = 7
        message.timestamp_low = 123
        message.timestamp_high = 456
        raw_header = bytes(message)
        payload = "Hello external reader\x00".encode("utf-16-le")
        reader = _FakeReader({address: raw_header + payload + b"\x00" * 1024})
        decoded = ChatMessageStruct.from_buffer_copy(raw_header).bind_reader(
            reader,
            address,
        )

        self.assertEqual(decoded.channel, 7)
        self.assertEqual(decoded.timestamp_100ns, (456 << 32) | 123)
        self.assertEqual(decoded.message_str, "Hello external reader")
        self.assertEqual(decoded.message_encoded_str, "Hello external reader")
        self.assertEqual(
            decoded.message_codepoints,
            tuple(ord(character) for character in "Hello external reader"),
        )

    def test_preserves_encoded_codepoints(self) -> None:
        """Encoded chat payloads remain available without fake display text."""

        address = 0x24000
        message = ChatMessageStruct()
        raw_header = bytes(message)
        encoded = "\u076b\u010a\u0ba9\u0107Aries The Arcane\x01\x01"
        payload = (encoded + "\x00").encode("utf-16-le")
        reader = _FakeReader({address: raw_header + payload + b"\x00" * 1024})
        decoded = ChatMessageStruct.from_buffer_copy(raw_header).bind_reader(
            reader,
            address,
        )

        self.assertEqual(decoded.message_encoded_str, encoded)
        self.assertEqual(
            decoded.message_codepoints[:4],
            (0x076B, 0x010A, 0x0BA9, 0x0107),
        )

    def test_message_pointer_traversal_is_bounded(self) -> None:
        """The reader never traverses more than the configured slot bound."""

        address = 0x30000
        message = ChatMessageStruct()
        raw_header = bytes(message)
        root = ChatBufferStruct()
        root.message_pointers[0] = address
        root.message_pointers[1] = address
        reader = _FakeReader({address: raw_header + b"\x00" * 1024})
        root.bind_reader(reader, max_message_count=1)

        self.assertEqual(len(root.messages), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
