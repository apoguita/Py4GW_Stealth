"""External read-only reader for the native ``GadgetContext`` root."""

from __future__ import annotations

import ctypes
from ctypes import Structure, c_uint32
from typing import Protocol

from .game_context import GameContext, GameContextStruct
from .gw_array import GWArray, GWArrayValueView, RemoteMemoryReader


class _memory_reader(RemoteMemoryReader, Protocol):
    """The byte-reading operation needed by gadget records."""


def _read_encoded_wide(reader: _memory_reader, address: int, limit: int = 256) -> str:
    """Read one bounded UTF-16 string through a target-process pointer."""

    if address < 0x10000:
        return ""
    raw = bytearray()
    for index in range(limit):
        pair = reader.read(address + index * 2, 2)
        if pair == b"\x00\x00":
            break
        raw.extend(pair)
    return bytes(raw).decode("utf-16-le", errors="replace")


class GadgetInfoStruct(Structure):
    """The native 0x10 gadget-info record."""

    _pack_ = 1
    _fields_ = [
        ("h0000", c_uint32),
        ("h0004", c_uint32),
        ("h0008", c_uint32),
        ("name_enc", c_uint32),
    ]

    _remote_reader: _memory_reader | None = None

    def bind_reader(
        self, reader: _memory_reader, address: int | None = None
    ) -> GadgetInfoStruct:
        """Attach the reader used by the indirect name pointer."""

        self._remote_reader = reader
        return self

    @property
    def name_encoded(self) -> str:
        """Read the bounded encoded name, or an empty string if unavailable."""

        if self._remote_reader is None:
            return ""
        return _read_encoded_wide(self._remote_reader, int(self.name_enc))


class GadgetContextStruct(Structure):
    """The fixed-width x86 0x10-byte native gadget root."""

    _pack_ = 1
    _fields_ = [("gadget_info_array", GWArray)]

    _remote_reader: _memory_reader | None = None
    _remote_address: int | None = None

    def bind_reader(
        self, reader: _memory_reader, address: int | None = None
    ) -> GadgetContextStruct:
        """Attach the reader used by the lazy gadget-info view."""

        self._remote_reader = reader
        self._remote_address = address
        return self

    @property
    def address(self) -> int | None:
        """Return the target address represented by this snapshot."""

        return getattr(self, "_remote_address", None)

    @property
    def array_size(self) -> int:
        """Return the advertised gadget-info count."""

        return int(self.gadget_info_array.m_size)

    def gadget_infos(self, limit: int = 256) -> list[GadgetInfoStruct]:
        """Read at most ``limit`` value records from the target array."""

        if self._remote_reader is None:
            raise RuntimeError("GadgetContext snapshot is not bound to a reader.")
        view = GWArrayValueView(
            self._remote_reader, self.gadget_info_array, GadgetInfoStruct
        )
        if not view.valid():
            return []
        return [
            value
            for index in range(min(view.size(), max(0, limit)))
            if (value := view.get(index)) is not None
        ]

assert ctypes.sizeof(GadgetInfoStruct) == 0x10
assert ctypes.sizeof(GadgetContextStruct) == 0x10


class GadgetContext:
    """Resolve and read the current gadget-context root."""

    def __init__(self, reader: _memory_reader, game_context: GameContext) -> None:
        """Create a reader using the selected client's game context."""

        self._reader = reader
        self._game_context = game_context

    def resolve_address(self) -> int | None:
        """Return the current gadget-context address, if available."""

        game_address = self._game_context.resolve_address()
        raw_pointer = self._reader.read(
            game_address + GameContextStruct.gadget_context.offset, 4
        )
        address = int.from_bytes(raw_pointer, "little")
        return address or None

    def read(self) -> GadgetContextStruct | None:
        """Read the fixed root; gadget records remain lazy and bounded."""

        address = self.resolve_address()
        if address is None:
            return None
        raw_context = self._reader.read(address, ctypes.sizeof(GadgetContextStruct))
        snapshot = GadgetContextStruct.from_buffer_copy(raw_context)
        return snapshot.bind_reader(self._reader, address)


def get() -> GadgetContextStruct | None:
    """Read the current client's gadget context, if one is available."""

    from ..client import current_client

    client = current_client()
    return client.read_gadget_context() if client is not None else None
