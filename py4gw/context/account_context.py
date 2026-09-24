"""External read-only reader for the native ``AccountContext`` root.

The account context is reached through the current ``GameContext``.  This
reader deliberately stops at the root and reports its array headers; it does
not materialize account-wide unlock arrays as part of a normal snapshot.
"""

from __future__ import annotations

from ..helpers.target_struct import TargetStruct

import ctypes
from ctypes import Structure, c_uint8, c_uint32
from typing import Protocol, TypeVar, cast

from .game_context import GameContext, GameContextStruct
from .gw_array import GWArray, GWArrayValueView, RemoteMemoryReader


class _memory_reader(RemoteMemoryReader, Protocol):
    """The byte-reading operation needed by this context reader."""


_value_type = TypeVar("_value_type")


class AccountUnlockedCountStruct(TargetStruct):
    """The native 0x0C account-unlocked-count record."""

    _pack_ = 1
    _fields_ = [
        ("id", c_uint32),
        ("unk1", c_uint32),
        ("unk2", c_uint32),
    ]

    @property
    def unknown_1(self) -> int:
        """Compatibility spelling for the native ``unk1`` field."""

        return int(self.unk1)

    @property
    def unknown_2(self) -> int:
        """Compatibility spelling for the native ``unk2`` field."""

        return int(self.unk2)


class AccountUnlockedItemInfoStruct(TargetStruct):
    """The native 0x0C unlocked-PvP-item record."""

    _pack_ = 1
    _fields_ = [
        ("name_id", c_uint32),
        ("mod_struct_index", c_uint32),
        ("mod_struct_size", c_uint32),
    ]


class AccountContextStruct(TargetStruct):
    """The fixed-width x86 0x138-byte native account root."""

    _pack_ = 1
    _fields_ = [
        ("account_unlocked_counts", GWArray),
        ("h0010", c_uint8 * 0xA4),
        ("unlocked_pvp_heros", GWArray),
        ("h00C4", GWArray),
        ("unlocked_pvp_item_info", GWArray),
        ("unlocked_pvp_items", GWArray),
        ("h0104", c_uint8 * 0x30),
        ("unlocked_account_skills", GWArray),
        ("account_flags", c_uint32),
    ]

    _remote_reader: _memory_reader | None = None
    _remote_address: int | None = None

    def bind_reader(
        self, reader: _memory_reader, address: int | None = None
    ) -> AccountContextStruct:
        """Attach the target address represented by this root snapshot."""

        self._remote_reader = reader
        self._remote_address = address
        return self

    @property
    def address(self) -> int | None:
        """Return the target address represented by this snapshot."""

        return self._remote_address

    @property
    def array_sizes(self) -> dict[str, int]:
        """Return advertised sizes without traversing any account arrays."""

        return {
            "account_unlocked_counts": int(self.account_unlocked_counts.m_size),
            "unlocked_pvp_heros": int(self.unlocked_pvp_heros.m_size),
            "h00C4": int(self.h00C4.m_size),
            "unlocked_pvp_item_info": int(self.unlocked_pvp_item_info.m_size),
            "unlocked_pvp_items": int(self.unlocked_pvp_items.m_size),
            "unlocked_account_skills": int(self.unlocked_account_skills.m_size),
        }

    def _array_values(
        self, array: GWArray, element_type: type[_value_type]
    ) -> list[_value_type] | None:
        """Read one bounded child array, preserving an unavailable result."""

        if not array.m_buffer or not array.m_size or array.m_size > array.m_capacity:
            return None
        if self._remote_reader is None:
            raise RuntimeError("This account snapshot is not bound to a memory reader.")
        return cast(
            list[_value_type],
            GWArrayValueView(self._remote_reader, array, element_type).to_list(),
        )

    @property
    def account_unlocked_count_list(self) -> list[AccountUnlockedCountStruct] | None:
        """Read the account unlock counters used by native item helpers."""

        return self._array_values(
            self.account_unlocked_counts, AccountUnlockedCountStruct
        )

    @property
    def unlocked_pvp_hero_ids(self) -> list[int] | None:
        """Read the legacy account-wide PvP hero identifiers."""

        values = self._array_values(self.unlocked_pvp_heros, c_uint32)
        return [int(value) for value in values] if values is not None else None

    @property
    def h00C4_values(self) -> list[int] | None:
        """Read the native auxiliary unlocked-item words."""

        values = self._array_values(self.h00C4, c_uint32)
        return [int(value) for value in values] if values is not None else None

    @property
    def unlocked_pvp_item_info_list(self) -> list[AccountUnlockedItemInfoStruct] | None:
        """Read the native unlocked-PvP-item metadata records."""

        return self._array_values(
            self.unlocked_pvp_item_info, AccountUnlockedItemInfoStruct
        )

    @property
    def unlocked_pvp_item_words(self) -> list[int] | None:
        """Read the native bitwise unlocked-PvP-item words."""

        values = self._array_values(self.unlocked_pvp_items, c_uint32)
        return [int(value) for value in values] if values is not None else None

    @property
    def unlocked_account_skill_words(self) -> list[int] | None:
        """Read the native account-unlocked skill bitset words."""

        values = self._array_values(self.unlocked_account_skills, c_uint32)
        return [int(value) for value in values] if values is not None else None

    def get_unlocked_count(self, unlock_id: int) -> AccountUnlockedCountStruct | None:
        """Return one account unlock counter by its native identifier."""

        if unlock_id < 0:
            return None
        for value in self.account_unlocked_count_list or []:
            if int(value.id) == unlock_id:
                return value
        return None

    @property
    def material_storage_stack_size(self) -> int:
        """Return the native material-storage stack-size calculation."""

        unlock = self.get_unlocked_count(0x83)
        if unlock is None:
            return 250
        return int(unlock.unknown_1) * 250 + 250

    def is_account_skill_unlocked(self, skill_id: int) -> bool:
        """Return whether the native account skill bitset contains an ID."""

        if skill_id < 0:
            return False
        words = self.unlocked_account_skill_words
        word_index = skill_id // 32
        if words is None or word_index >= len(words):
            return False
        return bool(int(words[word_index]) & (1 << (skill_id % 32)))


assert ctypes.sizeof(AccountUnlockedCountStruct) == 0x0C
assert ctypes.sizeof(AccountUnlockedItemInfoStruct) == 0x0C
assert ctypes.sizeof(AccountContextStruct) == 0x138
assert AccountContextStruct.unlocked_pvp_heros.offset == 0xB4
assert AccountContextStruct.h00C4.offset == 0xC4
assert AccountContextStruct.unlocked_pvp_item_info.offset == 0xD4
assert AccountContextStruct.unlocked_pvp_items.offset == 0xE4
assert AccountContextStruct.unlocked_account_skills.offset == 0x124
assert AccountContextStruct.account_flags.offset == 0x134


class AccountContext:
    """Resolve and read the current account-context root."""

    def __init__(self, reader: _memory_reader, game_context: GameContext) -> None:
        """Create a reader using the selected client's game context."""

        self._reader = reader
        self._game_context = game_context

    def resolve_address(self) -> int | None:
        """Return the current account-context address, if available."""

        game_address = self._game_context.resolve_address()
        raw_pointer = self._reader.read(
            game_address + GameContextStruct.account_context.offset, 4
        )
        address = int.from_bytes(raw_pointer, "little")
        return address or None

    def read(self) -> AccountContextStruct | None:
        """Read the fixed root and leave its child arrays lazy."""

        address = self.resolve_address()
        if address is None:
            return None
        raw_context = self._reader.read(address, ctypes.sizeof(AccountContextStruct))
        return AccountContextStruct.from_buffer_copy(raw_context).bind_reader(
            self._reader, address
        )


def get() -> AccountContextStruct | None:
    """Read the current client's account context, if one is available."""

    from ..client import current_client

    client = current_client()
    return client.read_account_context() if client is not None else None
