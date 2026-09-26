"""External reader for the native ``TextParser`` context.

The native context is not located by a separate signature.  It is the
``text_parser`` field of the currently resolved ``GameContext`` at offset
``0x18``.  This module follows that pointer and reads the complete fixed-width
x86 root structure through the external process reader.
"""

from __future__ import annotations

from ..helpers.target_struct import TargetStruct

import ctypes
from ctypes import Structure, c_uint8, c_uint16, c_uint32
from typing import Any, Protocol, TypeVar, cast

from .game_context import GameContext, GameContextStruct
from .gw_array import RemoteMemoryReader


class _memory_reader(RemoteMemoryReader, Protocol):
    """The byte-reading operation needed by nested context properties."""


_structure_type = TypeVar("_structure_type", bound=Structure)


class TextCacheStruct(TargetStruct):
    """The native ``TextCache`` record referenced by ``TextParser``."""

    _pack_ = 1
    _fields_ = [("h0000", c_uint32)]


class TextParserSubStructStruct(TargetStruct):
    """The native one-word sub-structure referenced by ``TextParser``."""

    _pack_ = 1
    _fields_ = [("h0000", c_uint32)]


class TextFileSlotStruct(TargetStruct):
    """The Reforged 0x24-byte text-file slot record."""

    _pack_ = 1
    _fields_ = [
        ("_pad0", c_uint8 * 8),
        ("file_hash_ptr", c_uint32),
        ("_pad1", c_uint32),
        ("lang_id", c_uint32),
        ("start_index", c_uint32),
        ("end_index", c_uint32),
        ("_pad2", c_uint8 * 8),
    ]

    _remote_reader: _memory_reader | None = None

    def bind_reader(self, reader: _memory_reader) -> TextFileSlotStruct:
        """Attach the reader used by the indirect file-hash pointer."""

        self._remote_reader = reader
        return self

    @property
    def file_hash(self) -> str:
        """Read the bounded target UTF-16 file hash string."""

        address = int(self.file_hash_ptr)
        if address < 0x10000:
            return ""
        if self._remote_reader is None:
            raise RuntimeError("This text-file slot is not bound to a memory reader.")
        characters: list[str] = []
        for index in range(256):
            code_point = int.from_bytes(
                self._remote_reader.read(address + index * 2, 2), "little"
            )
            if code_point == 0:
                break
            characters.append(chr(code_point))
        return "".join(characters)


class LanguageSlotStruct(TargetStruct):
    """The Reforged 0x0C per-language file-slot header."""

    _pack_ = 1
    _fields_ = [
        ("slot_array_ptr", c_uint32),
        ("_h0004", c_uint32),
        ("slot_count", c_uint32),
    ]


class TextParserStruct(TargetStruct):
    """The fixed-width x86 port of native ``GW::Context::TextParser``."""

    _pack_ = 1
    _fields_ = [
        ("_h0000", c_uint32 * 8),
        ("dec_start_ptr", c_uint32),
        ("dec_end_ptr", c_uint32),
        ("substitute_1", c_uint32),
        ("substitute_2", c_uint32),
        # Reforged declares this complete inline region as one 0x34-byte
        # header. Its first four bytes are the native TextCache* pointer.
        ("_cache_header", c_uint8 * 0x34),
        ("language_slots", LanguageSlotStruct * 11),
        ("_cache_pad", c_uint8 * 0x60),
        ("entries_per_file", c_uint32),
        ("_pad_post_cache", c_uint8 * 0x14),
        ("h0160", c_uint32),
        ("h0164", c_uint32),
        ("h0168", c_uint32),
        ("_h016C", c_uint32 * 5),
        ("sub_struct_ptr", c_uint32),
        ("_h0184", c_uint32 * 19),
        ("language_id", c_uint32),
    ]

    _remote_reader: _memory_reader | None = None

    def bind_reader(
        self, reader: _memory_reader, address: int | None = None
    ) -> TextParserStruct:
        """Attach the reader used by the nested pointer properties."""

        self._remote_reader = reader
        return self

    @property
    def dec_start(self) -> int:
        """Return the native spelling of the decode-start pointer."""

        return int(self.dec_start_ptr)

    @property
    def dec_end(self) -> int:
        """Return the native spelling of the decode-end pointer."""

        return int(self.dec_end_ptr)

    @property
    def cache_ptr(self) -> int:
        """Return the native cache pointer stored at ``_cache_header``."""

        return int.from_bytes(bytes(self._cache_header[:4]), "little")

    @property
    def h0000(self) -> tuple[int, ...]:
        """Return the legacy root-header words."""

        return tuple(int(value) for value in self._h0000)

    @property
    def h016c(self) -> tuple[int, ...]:
        """Return the legacy spelling of the post-cache words."""

        return tuple(int(value) for value in self._h016C)

    @property
    def h0184(self) -> tuple[int, ...]:
        """Return the legacy spelling of the trailing words."""

        return tuple(int(value) for value in self._h0184)

    @property
    def cache(self) -> TextCacheStruct | None:
        """Read the native cache record when its target pointer is valid."""

        return self._read_struct(self.cache_ptr, TextCacheStruct)

    @property
    def sub_struct(self) -> TextParserSubStructStruct | None:
        """Read the native auxiliary record when its target pointer is valid."""

        return self._read_struct(self.sub_struct_ptr, TextParserSubStructStruct)

    def get_file_slot(
        self, slot_idx: int, language: int = 0
    ) -> TextFileSlotStruct | None:
        """Read one bounded text-file slot for a language."""

        if slot_idx < 0 or language < 0 or language >= len(self.language_slots):
            return None
        language_slot = self.language_slots[language]
        slot_count = int(language_slot.slot_count)
        slot_address = int(language_slot.slot_array_ptr)
        if not slot_address or slot_idx >= slot_count:
            return None
        if self._remote_reader is None:
            raise RuntimeError("This context snapshot is not bound to a memory reader.")
        address = slot_address + slot_idx * ctypes.sizeof(TextFileSlotStruct)
        raw_value = self._remote_reader.read(address, ctypes.sizeof(TextFileSlotStruct))
        return TextFileSlotStruct.from_buffer_copy(raw_value).bind_reader(
            self._remote_reader
        )

    def _read_struct(
        self,
        address: int,
        structure_type: type[_structure_type],
    ) -> _structure_type | None:
        """Read one nested fixed-width structure through the bound reader."""

        if not address:
            return None
        if self._remote_reader is None:
            raise RuntimeError("This context snapshot is not bound to a memory reader.")
        raw_value = self._remote_reader.read(
            int(address), ctypes.sizeof(structure_type)
        )
        return structure_type.from_buffer_copy(raw_value)


assert ctypes.sizeof(TextCacheStruct) == 0x04
assert ctypes.sizeof(TextFileSlotStruct) == 0x24
assert ctypes.sizeof(LanguageSlotStruct) == 0x0C
assert ctypes.sizeof(TextParserSubStructStruct) == 0x04
assert ctypes.sizeof(TextParserStruct) == 0x1D4
assert TextParserStruct._cache_header.offset == 0x30
assert TextParserStruct.sub_struct_ptr.offset == 0x180
assert TextParserStruct.language_id.offset == 0x1D0


class TextParser:
    """Read the current ``TextParser`` through ``GameContext``."""

    # Source-compatible static facade state. The injected source updates this
    # through a callback; the external reader refreshes it explicitly.
    _ptr: int = 0
    _cached_ctx: TextParserStruct | None = None
    _callback_name = "TextParser.UpdatePtr"
    _string_table_triggered: bool = False

    def __init__(self, reader: _memory_reader, game_context: GameContext) -> None:
        """Create a reader using the connected client's cached GameContext."""

        self._reader = reader
        self._game_context = game_context

    @staticmethod
    def get_ptr() -> int:
        """Return the last externally refreshed TextParser address."""

        return TextParser._ptr

    @staticmethod
    def _update_ptr() -> None:
        """Refresh the source-compatible facade from the selected client.

        The first successful refresh also starts the string-table load, which is what the
        source does here (``TextContext.py:152-155``): a context that exists means a client
        exists, and the table is the one thing that only has to be read once. The load is
        ``_do_load_string_table``'s own, and it decides for itself whether it has already run.
        """

        from ..client import current_client

        client = current_client()
        if client is None:
            TextParser._ptr = 0
            TextParser._cached_ctx = None
            return
        try:
            context = client.text_parser
            address = context.resolve_address()
            TextParser._ptr = address or 0
            TextParser._cached_ctx = cast(Any, context.read())
        except (OSError, RuntimeError):
            TextParser._ptr = 0
            TextParser._cached_ctx = None

        if TextParser._cached_ctx is not None and not TextParser._string_table_triggered:
            TextParser._string_table_triggered = True
            from ..internals.string_table import _do_load_string_table

            _do_load_string_table(TextParser._cached_ctx.language_id)

    @staticmethod
    def enable() -> None:
        """Declare the source callback operation; callbacks require injection."""

        raise NotImplementedError(
            "TextParser.enable requires the in-process callback runtime."
        )

    @staticmethod
    def disable() -> None:
        """Clear the external facade cache."""

        TextParser._ptr = 0
        TextParser._cached_ctx = None

    @staticmethod
    def get_context() -> TextParserStruct | None:
        """Return the last snapshot refreshed through ``_update_ptr``."""

        return TextParser._cached_ctx

    def resolve_address(self) -> int | None:
        """Return the current target address, or ``None`` when unavailable."""

        game_address = self._game_context.resolve_address()
        raw_pointer = self._reader.read(
            game_address + GameContextStruct.text_parser.offset, 4
        )
        address = int.from_bytes(raw_pointer, "little")
        return address or None

    def read(self) -> TextParserStruct | None:
        """Read and decode the complete maintained native structure."""

        address = self.resolve_address()
        if address is None:
            return None
        raw_context = self._reader.read(address, ctypes.sizeof(TextParserStruct))
        return TextParserStruct.from_buffer_copy(raw_context).bind_reader(self._reader)


def get() -> TextParserStruct | None:
    """Read the TextParser of the current selected client, if available."""

    from ..client import current_client

    client = current_client()
    return cast(Any, client.read_text_parser() if client is not None else None)
