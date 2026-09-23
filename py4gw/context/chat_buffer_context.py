"""External read-only readers for the Guild Wars chat ring buffer."""

from __future__ import annotations

from ..target_struct import TargetStruct

import ctypes
from ctypes import Structure, c_uint16, c_uint32
from datetime import datetime, timezone
from typing import Protocol

from ..scanner import PatternCatalog, RemoteScanner
from .gw_array import RemoteMemoryReader


class _memory_reader(RemoteMemoryReader, Protocol):
    """The byte-reading operation needed by the chat reader."""


CHAT_LOG_LENGTH = 0x200


class FileTimeStruct(TargetStruct):
    """Windows ``FILETIME`` layout used by native chat messages."""

    _pack_ = 1
    _fields_ = [
        ("dwLowDateTime", c_uint32),
        ("dwHighDateTime", c_uint32),
    ]


def _decode_wide_bytes(raw: bytes) -> str:
    """Decode target UTF-16 text up to the first NUL character."""

    even_length = len(raw) - (len(raw) % 2)
    decoded = raw[:even_length].decode("utf-16-le", errors="replace")
    return decoded.split("\x00", 1)[0]


class ChatMessageStruct(TargetStruct):
    """The fixed header of one native ``ChatMessage`` record."""

    _pack_ = 1
    _fields_ = [
        ("channel", c_uint32),
        ("unk1", c_uint32),
        ("timestamp", FileTimeStruct),
        ("message", c_uint16 * 0),
    ]

    _remote_reader: _memory_reader | None = None
    _message_address: int | None = None
    _max_message_chars = 512

    def bind_reader(
        self,
        reader: _memory_reader,
        message_address: int,
        max_message_chars: int = 512,
    ) -> ChatMessageStruct:
        """Attach the reader and target address for the variable text field."""

        if message_address < 0x10000:
            raise ValueError("message_address is not a plausible target address.")
        if max_message_chars <= 0:
            raise ValueError("max_message_chars must be positive.")
        self._remote_reader = reader
        self._message_address = message_address
        self._max_message_chars = max_message_chars
        return self

    @property
    def timestamp_100ns(self) -> int:
        """Return the native FILETIME value as 100-nanosecond ticks."""

        return (int(self.timestamp.dwHighDateTime) << 32) | int(
            self.timestamp.dwLowDateTime
        )

    @property
    def timestamp_utc(self) -> datetime | None:
        """Return the FILETIME as UTC, or ``None`` for an invalid value."""

        try:
            unix_seconds = self.timestamp_100ns / 10_000_000 - 11_644_473_600
            return datetime.fromtimestamp(unix_seconds, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None

    @property
    def message_address(self) -> int | None:
        """Return the remote address of this variable-length message."""

        return self._message_address

    @property
    def message_str(self) -> str:
        """Read the raw encoded UTF-16 message payload from the target.

        The native ``ChatMessage::message`` field is an encoded wide-string,
        not guaranteed display text. This property preserves that source
        value; it does not provide Reforged's decoded ``GetChatHistory``
        result.
        """

        if self._remote_reader is None or self._message_address is None:
            raise RuntimeError("ChatMessage is not bound to a memory reader.")

        payload_address = self._message_address + ctypes.sizeof(ChatMessageStruct)
        try:
            raw = self._remote_reader.read(
                payload_address,
                self._max_message_chars * 2,
            )
        except OSError:
            raw_bytes = bytearray()
            for index in range(self._max_message_chars):
                pair = self._remote_reader.read(payload_address + index * 2, 2)
                if pair == b"\x00\x00":
                    break
                raw_bytes.extend(pair)
            raw = bytes(raw_bytes)
        return _decode_wide_bytes(raw)

    @property
    def message_encoded_str(self) -> str:
        """Return the source-compatible name for the raw encoded message."""

        return self.message_str

    @property
    def message_codepoints(self) -> tuple[int, ...]:
        """Return the raw UTF-16 codepoints used by the message encoding."""

        return tuple(ord(character) for character in self.message_str)


class ChatBufferStruct(TargetStruct):
    """The native 0x80C chat ring-buffer structure."""

    _CHAT_LOG_LENGTH = CHAT_LOG_LENGTH
    _pack_ = 1
    _fields_ = [
        ("next", c_uint32),
        ("unk1", c_uint32),
        ("unk2", c_uint32),
        ("messages", c_uint32 * _CHAT_LOG_LENGTH),
    ]

    _remote_reader: _memory_reader | None = None
    _max_message_count = _CHAT_LOG_LENGTH
    _max_message_chars = 512

    def bind_reader(
        self,
        reader: _memory_reader,
        max_message_count: int = _CHAT_LOG_LENGTH,
        max_message_chars: int = 512,
    ) -> ChatBufferStruct:
        """Attach the reader and bounds used for message traversal."""

        if max_message_count <= 0 or max_message_count > self._CHAT_LOG_LENGTH:
            raise ValueError("max_message_count must be between 1 and 0x200.")
        if max_message_chars <= 0:
            raise ValueError("max_message_chars must be positive.")
        self._remote_reader = reader
        self._max_message_count = max_message_count
        self._max_message_chars = max_message_chars
        return self

    @property
    def message_records(self) -> list[ChatMessageStruct]:
        """Read bounded message headers from non-null ring-buffer slots."""

        if self._remote_reader is None:
            raise RuntimeError("ChatBuffer is not bound to a memory reader.")

        records: list[ChatMessageStruct] = []
        for pointer in list(self.messages)[: self._max_message_count]:
            address = int(pointer)
            if address < 0x10000:
                continue
            try:
                raw_header = self._remote_reader.read(
                    address,
                    ctypes.sizeof(ChatMessageStruct),
                )
            except OSError:
                continue
            records.append(
                ChatMessageStruct.from_buffer_copy(raw_header).bind_reader(
                    self._remote_reader,
                    address,
                    self._max_message_chars,
                )
            )
        return records

    @property
    def next_index(self) -> int:
        """Readable alias for the source ``next`` ring index."""

        return int(self.next)

    @property
    def message_pointers(self) -> ctypes.Array[c_uint32]:
        """Compatibility alias for the source ``messages`` pointer array."""

        return self.messages


assert ctypes.sizeof(ChatMessageStruct) == 0x10
assert ctypes.sizeof(ChatBufferStruct) == 0x80C
assert ctypes.sizeof(FileTimeStruct) == 0x08
assert ChatBufferStruct.messages.offset == 0x0C


class ChatBuffer:
    """Resolve and read the current external chat log and typing state."""

    _BUFFER_RESOLVER = "chat.chat_buffer_addr"
    _TYPING_RESOLVER = "chat.is_typing_frame_id"

    def __init__(
        self,
        reader: _memory_reader,
        scanner: RemoteScanner,
        patterns: PatternCatalog,
        max_message_count: int = ChatBufferStruct._CHAT_LOG_LENGTH,
        max_message_chars: int = 512,
    ) -> None:
        """Create a bounded read-only chat-buffer reader."""

        if max_message_count <= 0 or max_message_count > 0x200:
            raise ValueError("max_message_count must be between 1 and 0x200.")
        if max_message_chars <= 0:
            raise ValueError("max_message_chars must be positive.")
        self._reader = reader
        self._scanner = scanner
        self._patterns = patterns
        self._max_message_count = max_message_count
        self._max_message_chars = max_message_chars
        self._buffer_pointer_address: int | None = None
        self._typing_pointer_address: int | None = None

    def initialize(self) -> int | None:
        """Resolve stable global pointer slots without requiring chat activity."""

        if self._buffer_pointer_address is None:
            buffer_result = self._patterns.resolve(
                self._BUFFER_RESOLVER,
                self._scanner,
            )
            if buffer_result.ok:
                self._buffer_pointer_address = buffer_result.value

        if self._typing_pointer_address is None:
            typing_result = self._patterns.resolve(
                self._TYPING_RESOLVER,
                self._scanner,
            )
            if typing_result.ok:
                self._typing_pointer_address = typing_result.value

        if self._buffer_pointer_address is None:
            return None
        address = self._scanner.read_uint32(self._buffer_pointer_address)
        return address or None

    def resolve_address(self) -> int | None:
        """Return the current ChatBuffer object address, if active."""

        if self._buffer_pointer_address is None:
            self.initialize()
        if self._buffer_pointer_address is None:
            return None
        address = self._scanner.read_uint32(self._buffer_pointer_address)
        return address or None

    @property
    def cached_pointer_address(self) -> int | None:
        """Return the stable global slot containing the ChatBuffer pointer."""

        return self._buffer_pointer_address

    @property
    def cached_typing_pointer_address(self) -> int | None:
        """Return the stable global slot containing the typing frame ID."""

        return self._typing_pointer_address

    def is_typing(self) -> bool:
        """Return whether the target currently reports an active typing frame."""

        if self._typing_pointer_address is None:
            self.initialize()
        if self._typing_pointer_address is None:
            return False
        return self._scanner.read_uint32(self._typing_pointer_address) != 0

    def read(self) -> ChatBufferStruct | None:
        """Read and bind the current chat ring buffer, if available."""

        address = self.resolve_address()
        if address is None:
            return None
        raw_buffer = self._reader.read(address, ctypes.sizeof(ChatBufferStruct))
        return ChatBufferStruct.from_buffer_copy(raw_buffer).bind_reader(
            self._reader,
            self._max_message_count,
            self._max_message_chars,
        )


def get() -> ChatBufferStruct | None:
    """Read the current chat buffer for the selected client, if connected."""

    from ..client import current_client

    client = current_client()
    return client.read_chat_buffer() if client is not None else None
