"""External layout and reader for Reforged's ``GameplayContext``."""

from __future__ import annotations

import ctypes
from ctypes import Structure, c_float, c_uint32
from typing import Any, Protocol, cast

from ..scanner import PatternCatalog, RemoteScanner
from .gw_array import RemoteMemoryReader


class _memory_reader(RemoteMemoryReader, Protocol):
    """The byte-reading operation needed by the external context reader."""


class GameplayContextStruct(Structure):
    """The fixed-width x86 port of Reforged ``GameplayContextStruct``."""

    _pack_ = 1
    _fields_ = [
        ("h0000", c_uint32 * 0x13),
        ("mission_map_zoom", c_float),
        ("unk", c_uint32 * 10),
    ]


assert ctypes.sizeof(GameplayContextStruct) == 0x78
assert GameplayContextStruct.mission_map_zoom.offset == 0x4C


class GameplayContext:
    """Resolve and decode one external ``GameplayContext`` snapshot."""

    # Source-compatible static facade state. The injected source updates this
    # through a callback; the external reader refreshes it explicitly.
    _ptr: int = 0
    _cached_ctx: GameplayContextStruct | None = None
    _callback_name = "GameplayContext.UpdatePtr"

    _RESOLVER = "context.gameplay_context_addr"

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
        self._pointer_address: int | None = None

    @staticmethod
    def get_ptr() -> int:
        """Return the last externally refreshed GameplayContext address."""

        return GameplayContext._ptr

    @staticmethod
    def _update_ptr() -> None:
        """Refresh the source-compatible facade from the selected client."""

        from ..client import current_client

        client = current_client()
        if client is None:
            GameplayContext._ptr = 0
            GameplayContext._cached_ctx = None
            return
        try:
            context = client.gameplay_context
            address = context.resolve_address()
            GameplayContext._ptr = address or 0
            GameplayContext._cached_ctx = cast(Any, context.read())
        except (OSError, RuntimeError):
            GameplayContext._ptr = 0
            GameplayContext._cached_ctx = None

    @staticmethod
    def enable() -> None:
        """Declare the source callback operation; callbacks require injection."""

        raise NotImplementedError(
            "GameplayContext.enable requires the in-process callback runtime."
        )

    @staticmethod
    def disable() -> None:
        """Clear the external facade cache."""

        GameplayContext._ptr = 0
        GameplayContext._cached_ctx = None

    @staticmethod
    def get_context() -> GameplayContextStruct | None:
        """Return the last snapshot refreshed through ``_update_ptr``."""

        return GameplayContext._cached_ctx

    def resolve_address(self) -> int | None:
        """Return the current target address, or ``None`` when inactive."""

        if self._pointer_address is None:
            return self.initialize()
        return self._read_context_address()

    def initialize(self) -> int | None:
        """Scan once and cache the stable gameplay pointer location."""

        if self._pointer_address is None:
            result = self._patterns.resolve(self._RESOLVER, self._scanner)
            if not result.ok:
                detail = result.message or "the resolver returned no address"
                raise RuntimeError(f"{self._RESOLVER} failed: {detail}")
            self._pointer_address = result.value
        return self._read_context_address()

    @property
    def cached_pointer_address(self) -> int | None:
        """Return the cached global-pointer location, if initialized."""

        return self._pointer_address

    def read(self) -> GameplayContextStruct | None:
        """Read and decode the complete maintained structure layout."""

        address = self.resolve_address()
        if address is None:
            return None
        raw_context = self._reader.read(
            address, ctypes.sizeof(GameplayContextStruct)
        )
        return GameplayContextStruct.from_buffer_copy(raw_context)

    def _read_context_address(self) -> int | None:
        """Follow the stable global pointer to the current context object."""

        if self._pointer_address is None:
            raise RuntimeError("GameplayContext has not been initialized.")
        context_address = self._scanner.read_uint32(self._pointer_address)
        return context_address or None


def get() -> GameplayContextStruct | None:
    """Read the ``GameplayContext`` of the current selected client, if any."""

    from ..client import current_client

    client = current_client()
    return cast(Any, client.read_gameplay_context() if client is not None else None)
