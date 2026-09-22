"""External layout and reader for Reforged's ``Cinematic`` context."""

from __future__ import annotations

import ctypes
from ctypes import Structure, c_uint32
from typing import Any, Protocol, cast

from .game_context import GameContext
from .gw_array import RemoteMemoryReader


class _memory_reader(RemoteMemoryReader, Protocol):
    """The byte-reading operation needed by the external context reader."""


class CinematicStruct(Structure):
    """The fixed-width x86 port of Reforged ``CinematicStruct``."""

    _pack_ = 1
    _fields_ = [
        ("h0000", c_uint32),
        ("h0004", c_uint32),
    ]


assert ctypes.sizeof(CinematicStruct) == 0x08


class Cinematic:
    """Resolve and decode one external ``Cinematic`` snapshot."""

    # Source-compatible static facade state. The injected source updates this
    # through a callback; the external reader refreshes it explicitly.
    _ptr: int = 0
    _cached_ctx: CinematicStruct | None = None
    _callback_name = "CinematicContext.UpdatePtr"

    _GAME_CONTEXT_CINEMATIC_OFFSET = 0x30

    def __init__(self, reader: _memory_reader, game_context: GameContext) -> None:
        """Create a reader using the connected client's cached GameContext."""

        self._reader = reader
        self._game_context = game_context

    @staticmethod
    def get_ptr() -> int:
        """Return the last externally refreshed Cinematic address."""

        return Cinematic._ptr

    @staticmethod
    def _update_ptr() -> None:
        """Refresh the source-compatible facade from the selected client."""

        from ..client import current_client

        client = current_client()
        if client is None:
            Cinematic._ptr = 0
            Cinematic._cached_ctx = None
            return
        try:
            context = client.cinematic
            address = context.resolve_address()
            Cinematic._ptr = address or 0
            Cinematic._cached_ctx = cast(Any, context.read())
        except (OSError, RuntimeError):
            Cinematic._ptr = 0
            Cinematic._cached_ctx = None

    @staticmethod
    def enable() -> None:
        """Declare the source callback operation; callbacks require injection."""

        raise NotImplementedError(
            "Cinematic.enable requires the in-process callback runtime."
        )

    @staticmethod
    def disable() -> None:
        """Clear the external facade cache."""

        Cinematic._ptr = 0
        Cinematic._cached_ctx = None

    @staticmethod
    def get_context() -> CinematicStruct | None:
        """Return the last snapshot refreshed through ``_update_ptr``."""

        return Cinematic._cached_ctx

    def resolve_address(self) -> int | None:
        """Return the current cinematic address, or ``None`` if inactive."""

        game_address = self._game_context.resolve_address()
        raw_pointer = self._reader.read(
            game_address + self._GAME_CONTEXT_CINEMATIC_OFFSET, 4
        )
        address = int.from_bytes(raw_pointer, "little")
        return address or None

    def read(self) -> CinematicStruct | None:
        """Read and decode the current cinematic structure, if present."""

        address = self.resolve_address()
        if address is None:
            return None
        raw_context = self._reader.read(address, ctypes.sizeof(CinematicStruct))
        return CinematicStruct.from_buffer_copy(raw_context)


def get() -> CinematicStruct | None:
    """Read the cinematic context of the current selected client, if any."""

    from ..client import current_client

    client = current_client()
    return cast(Any, client.read_cinematic_context() if client is not None else None)
