"""External reader for the native ``TextParser`` context.

The native context is not located by a separate signature.  It is the
``text_parser`` field of the currently resolved ``GameContext`` at offset
``0x18``.  This module follows that pointer and reads the complete fixed-width
x86 root structure through the external process reader.
"""

from __future__ import annotations

import ctypes
from ctypes import Structure, c_uint32
from typing import Protocol, TypeVar

from .game_context import GameContext, GameContextStruct
from .gw_array import RemoteMemoryReader


class _memory_reader(RemoteMemoryReader, Protocol):
    """The byte-reading operation needed by nested context properties."""


_structure_type = TypeVar("_structure_type", bound=Structure)


class TextCacheStruct(Structure):
    """The native ``TextCache`` record referenced by ``TextParser``."""

    _pack_ = 1
    _fields_ = [("h0000", c_uint32)]


class TextParserSubStructStruct(Structure):
    """The native one-word sub-structure referenced by ``TextParser``."""

    _pack_ = 1
    _fields_ = [("h0000", c_uint32)]


class TextParserStruct(Structure):
    """The fixed-width x86 port of native ``GW::Context::TextParser``."""

    _pack_ = 1
    _fields_ = [
        ("h0000", c_uint32 * 8),
        ("dec_start", c_uint32),
        ("dec_end", c_uint32),
        ("substitute_1", c_uint32),
        ("substitute_2", c_uint32),
        ("cache_ptr", c_uint32),
        ("h0034", c_uint32 * 75),
        ("h0160", c_uint32),
        ("h0164", c_uint32),
        ("h0168", c_uint32),
        ("h016c", c_uint32 * 5),
        ("sub_struct_ptr", c_uint32),
        ("h0184", c_uint32 * 19),
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
    def cache(self) -> TextCacheStruct | None:
        """Read the native cache record when its target pointer is valid."""

        return self._read_struct(self.cache_ptr, TextCacheStruct)

    @property
    def sub_struct(self) -> TextParserSubStructStruct | None:
        """Read the native auxiliary record when its target pointer is valid."""

        return self._read_struct(self.sub_struct_ptr, TextParserSubStructStruct)

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
assert ctypes.sizeof(TextParserSubStructStruct) == 0x04
assert ctypes.sizeof(TextParserStruct) == 0x1D4
assert TextParserStruct.cache_ptr.offset == 0x30
assert TextParserStruct.sub_struct_ptr.offset == 0x180
assert TextParserStruct.language_id.offset == 0x1D0


class TextParser:
    """Read the current ``TextParser`` through ``GameContext``."""

    def __init__(self, reader: _memory_reader, game_context: GameContext) -> None:
        """Create a reader using the connected client's cached GameContext."""

        self._reader = reader
        self._game_context = game_context

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
    return client.read_text_parser() if client is not None else None
