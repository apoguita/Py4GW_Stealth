"""External read-only reader for the native ``TradeContext``."""

from __future__ import annotations

import ctypes
from ctypes import Structure, c_uint32
from typing import Protocol

from .game_context import GameContext, GameContextStruct
from .gw_array import GWArray, GWArrayValueView, RemoteMemoryReader


class _memory_reader(RemoteMemoryReader, Protocol):
    """The byte-reading operation needed by trade records."""


class TradeItemStruct(Structure):
    """The native 0x08 offered-item record."""

    _pack_ = 1
    _fields_ = [("item_id", c_uint32), ("quantity", c_uint32)]


class TradePlayerStruct(Structure):
    """The native 0x14 offer record for one side of a trade."""

    _pack_ = 1
    _fields_ = [("gold", c_uint32), ("items_array", GWArray)]

    _remote_reader: _memory_reader | None = None

    def bind_reader(
        self, reader: _memory_reader, address: int | None = None
    ) -> TradePlayerStruct:
        """Attach the reader used by the offered-item array."""

        self._remote_reader = reader
        return self

    @property
    def items(self) -> list[TradeItemStruct]:
        """Read at most 64 offered items."""

        if self._remote_reader is None:
            raise RuntimeError("TradePlayer snapshot is not bound to a reader.")
        view = GWArrayValueView(self._remote_reader, self.items_array, TradeItemStruct)
        if not view.valid():
            return []
        return [
            value
            for index in range(min(view.size(), 64))
            if (value := view.get(index)) is not None
        ]


class TradeContextStruct(Structure):
    """The native fixed-width x86 0x38 trade root."""

    _pack_ = 1
    _fields_ = [
        ("flags", c_uint32),
        ("h0004", c_uint32 * 3),
        ("player", TradePlayerStruct),
        ("partner", TradePlayerStruct),
    ]

    _remote_reader: _memory_reader | None = None

    def bind_reader(
        self, reader: _memory_reader, address: int | None = None
    ) -> TradeContextStruct:
        """Attach the reader used by both trade-side arrays."""

        self._remote_reader = reader
        return self

    def _bound_player(self, value: TradePlayerStruct) -> TradePlayerStruct:
        """Return a bound copy of one embedded trade-side record."""

        if self._remote_reader is None:
            raise RuntimeError("TradeContext snapshot is not bound to a reader.")
        return TradePlayerStruct.from_buffer_copy(bytes(value)).bind_reader(
            self._remote_reader
        )

    @property
    def player_offer(self) -> TradePlayerStruct:
        """Return the current player's offer with its item reader bound."""

        return self._bound_player(self.player)

    @property
    def partner_offer(self) -> TradePlayerStruct:
        """Return the partner's offer with its item reader bound."""

        return self._bound_player(self.partner)

    def offered_item(self, item_id: int) -> TradeItemStruct | None:
        """Return the current player's offered item with this ID, if any."""

        return next(
            (item for item in self.player_offer.items if int(item.item_id) == item_id),
            None,
        )

    def is_item_offered(self, item_id: int) -> bool:
        """Return whether the current player offered an item ID."""

        return self.offered_item(item_id) is not None

    @property
    def is_trade_initiated(self) -> bool:
        """Return whether the trade has been initiated."""

        return bool(int(self.flags) & 0x1)

    @property
    def is_trade_offered(self) -> bool:
        """Return whether an offer has been sent."""

        return bool(int(self.flags) & 0x2)

    @property
    def is_trade_accepted(self) -> bool:
        """Return whether the trade has been accepted."""

        return bool(int(self.flags) & 0x4)


assert ctypes.sizeof(TradeItemStruct) == 0x08
assert ctypes.sizeof(TradePlayerStruct) == 0x14
assert ctypes.sizeof(TradeContextStruct) == 0x38


class TradeContext:
    """Resolve and read the current trade context through ``GameContext``."""

    def __init__(self, reader: _memory_reader, game_context: GameContext) -> None:
        """Create a reader using the selected client's cached game context."""

        self._reader = reader
        self._game_context = game_context

    def resolve_address(self) -> int | None:
        """Return the current trade-context address, if active."""

        game_address = self._game_context.resolve_address()
        raw_pointer = self._reader.read(
            game_address + GameContextStruct.trade_context.offset, 4
        )
        address = int.from_bytes(raw_pointer, "little")
        return address or None

    def read(self) -> TradeContextStruct | None:
        """Read the fixed trade root and its bounded offer arrays."""

        address = self.resolve_address()
        if address is None:
            return None
        raw_context = self._reader.read(address, ctypes.sizeof(TradeContextStruct))
        return TradeContextStruct.from_buffer_copy(raw_context).bind_reader(
            self._reader, address
        )


def get() -> TradeContextStruct | None:
    """Read the current client's trade context, if one is active."""

    from ..client import current_client

    client = current_client()
    return client.read_trade_context() if client is not None else None
