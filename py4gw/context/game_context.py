"""External layout and reader for Reforged's ``GameContext``."""

from __future__ import annotations

import ctypes
from ctypes import Structure, c_uint32
from typing import Protocol

from ..scanner import PatternCatalog, RemoteScanner
from .gw_array import RemoteMemoryReader


class _memory_reader(RemoteMemoryReader, Protocol):
    """The byte-reading operation needed by the external context reader."""


class GameContextStruct(Structure):
    """The fixed-width x86 port of Reforged ``GameContextStruct``.

    The original in-process Python structure uses ``c_void_p`` for the first
    two fields. Stealth always uses four-byte target addresses because the
    Guild Wars client and these layouts are x86, even when the controller's
    Python interpreter has a different host pointer size.
    """

    _pack_ = 1
    _fields_ = [
        ("h0000", c_uint32),
        ("h0004", c_uint32),
        ("agent_context", c_uint32),
        ("h000C", c_uint32),
        ("h0010", c_uint32),
        ("map_context", c_uint32),
        ("text_parser", c_uint32),
        ("h001C", c_uint32),
        ("some_number", c_uint32),
        ("h0024", c_uint32),
        ("account_context", c_uint32),
        ("world_context", c_uint32),
        ("cinematic", c_uint32),
        ("h0034", c_uint32),
        ("gadget_context", c_uint32),
        ("guild_context", c_uint32),
        ("item_context", c_uint32),
        ("char_context", c_uint32),
        ("h0048", c_uint32),
        ("party_context", c_uint32),
        ("h0050", c_uint32),
        ("h0054", c_uint32),
        ("trade_context", c_uint32),
    ]

    # Native C++ field spellings remain available alongside the Reforged
    # Python names. These aliases do not change the target layout.
    @property
    def agent(self) -> int:
        return int(self.agent_context)

    @property
    def map(self) -> int:
        return int(self.map_context)

    @property
    def account(self) -> int:
        return int(self.account_context)

    @property
    def world(self) -> int:
        return int(self.world_context)

    @property
    def gadget(self) -> int:
        return int(self.gadget_context)

    @property
    def guild(self) -> int:
        return int(self.guild_context)

    @property
    def items(self) -> int:
        return int(self.item_context)

    @property
    def character(self) -> int:
        return int(self.char_context)

    @property
    def party(self) -> int:
        return int(self.party_context)

    @property
    def trade(self) -> int:
        return int(self.trade_context)


assert ctypes.sizeof(GameContextStruct) == 0x5C


class GameContext:
    """Resolve and decode one external ``GameContext`` snapshot."""

    _BASE_RESOLVER = "context.base_ptr"
    _GAME_CONTEXT_OFFSET = 0x18

    def __init__(
        self,
        reader: _memory_reader,
        scanner: RemoteScanner,
        patterns: PatternCatalog,
    ) -> None:
        """Create a reader backed by one process and its offset catalog."""

        self._reader = reader
        self._scanner = scanner
        self._patterns = patterns
        self._base_pointer_address: int | None = None

    def resolve_address(self) -> int:
        """Return the current target address using the cached resolver."""

        if self._base_pointer_address is None:
            return self.initialize()
        return self._read_context_address()

    def initialize(self) -> int:
        """Scan once and cache the stable ``context.base_ptr`` address."""

        if self._base_pointer_address is None:
            self._base_pointer_address = self._resolve_base_pointer()
        return self._read_context_address()

    @property
    def cached_base_pointer_address(self) -> int | None:
        """Return the cached module-global pointer location, if initialized."""

        return self._base_pointer_address

    def read(self) -> GameContextStruct:
        """Read and decode the complete maintained structure layout."""

        address = self.resolve_address()
        raw_context = self._reader.read(address, ctypes.sizeof(GameContextStruct))
        return GameContextStruct.from_buffer_copy(raw_context)

    def _resolve_base_pointer(self) -> int:
        """Run the JSON resolver that locates the base-context pointer."""

        result = self._patterns.resolve(self._BASE_RESOLVER, self._scanner)
        if not result.ok:
            detail = result.message or "the resolver returned no address"
            raise RuntimeError(f"{self._BASE_RESOLVER} failed: {detail}")
        return result.value

    def _read_context_address(self) -> int:
        """Follow the native base-context slot to the current GameContext."""

        if self._base_pointer_address is None:
            raise RuntimeError("GameContext has not been initialized.")

        base_context = self._scanner.read_uint32(self._base_pointer_address)
        if not base_context:
            raise RuntimeError("The resolved base context pointer is null.")

        game_context = self._scanner.read_uint32(
            base_context + self._GAME_CONTEXT_OFFSET
        )
        if not game_context:
            raise RuntimeError("The GameContext pointer is null.")
        return game_context


def get() -> GameContextStruct | None:
    """Read the ``GameContext`` of the current selected client, if any."""

    from ..client import current_client

    client = current_client()
    return client.read_game_context() if client is not None else None
