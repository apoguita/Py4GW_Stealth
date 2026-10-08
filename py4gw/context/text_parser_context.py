"""External reader for the native ``TextParser`` context.

The native context is not located by a separate signature.  It is the
``text_parser`` field of the currently resolved ``GameContext`` at offset
``0x18``.  This module follows that pointer and reads the complete fixed-width
x86 root structure through the external process reader.

**What is here is what the source declares.** ``TextParserStruct``'s fields, the two
nested records, ``TextFileSlotStruct.file_hash``, ``get_file_slot`` and the
``TextParser`` facade are Reforged's own Python surface (``TextContext.py`` and
``TextContext.pyi``). This module used to carry a second set of members beside them --
``dec_start``/``dec_end``/``cache_ptr``/``h0000``/``h016c``/``h0184`` and the two
dereferencing properties ``cache``/``sub_struct``, with a ``TextCacheStruct`` and a
``TextParserSubStructStruct`` to hold their results. Those spellings belong to
**Native's header** (``GW/context/text_parser.h``: ``TextCache* cache``, ``SubStruct1*
sub_struct``), and Native binds none of them -- there is no ``TextParserStruct`` in
Native's bindings at all. For a class ported from Reforged's Python, Reforged's Python is
the shape authority and Native's header is only the layout authority, so they were
additions: a member that exists in neither source's declared surface. They are gone, and
`sub_struct` is why they were found -- it read offset ``+0x180`` as a pointer and this
client holds ``0x4C`` there, so displaying the context raised
``ReadProcessMemory(address=0x4C, size=0x4) failed with Windows error 299`` inside a GUI
event handler. A record that only *declares* that field (``sub_struct_ptr``) is what both
sources have, and what this module now carries.
"""

from __future__ import annotations

from ..helpers.target_struct import TargetStruct

import ctypes
from ctypes import c_uint8, c_uint16, c_uint32
from typing import Any, Protocol, cast

from .game_context import GameContext, GameContextStruct
from .gw_array import RemoteMemoryReader


class _memory_reader(RemoteMemoryReader, Protocol):
    """The byte-reading operation needed by nested context properties."""


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
        """Attach the reader ``get_file_slot`` reads its slot records through."""

        self._remote_reader = reader
        return self

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


assert ctypes.sizeof(TextFileSlotStruct) == 0x24
assert ctypes.sizeof(LanguageSlotStruct) == 0x0C
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

            # The source's line here is ``_do_load_string_table(TextParser._cached_ctx.language_id)``,
            # which reads every string file of the language on the game thread — free in-process, and
            # the script that later asks for a name never waits for it. **The port does not read it
            # here, and that is measured rather than preferred**: outside the client each file is a
            # ~2.1 s dat record (open ~1.1 s, read and decompress 91 KB ~0.9 s), so loading the whole
            # language is minutes of the client's own work, and *nothing in this library reads that
            # table any more* — a name is decoded by the client itself (``Agent.GetNameByID``, Native's
            # ``AsyncGetAgentName`` route), which is what the dat work was buying. Measured live, the
            # background load also competed with those decodes for the game thread, which is what made
            # a name search slower than it needed to be.
            #
            # ``load_string_table`` is the source's own entry point to that table and stays available:
            # a caller that wants an entry rendered on the host asks for it, and the read then happens
            # once, on a worker, behind that caller.
            pass

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
