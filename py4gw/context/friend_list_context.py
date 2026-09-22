"""External read-only layout and reader for the Guild Wars friend list."""

from __future__ import annotations

import ctypes
from ctypes import Structure, c_uint8, c_uint16, c_uint32
from enum import IntEnum
from typing import Protocol

from ..scanner import PatternCatalog, RemoteScanner
from .gw_array import GWArray, RemoteMemoryReader


class _memory_reader(RemoteMemoryReader, Protocol):
    """The byte-reading operation needed by the friend-list reader."""


class FriendType(IntEnum):
    """Native ``GW::Constants::FriendType`` values."""

    unknown = 0
    friend = 1
    ignore = 2
    player = 3
    trade = 4


class FriendStatus(IntEnum):
    """Native ``GW::Constants::FriendStatus`` values."""

    offline = 0
    online = 1
    dnd = 2
    away = 3
    unknown = 4


def _decode_wide_array(values: ctypes.Array[c_uint16]) -> str:
    """Decode a bounded target UTF-16 character array up to its NUL."""

    characters: list[str] = []
    for value in values:
        code_unit = int(value)
        if code_unit == 0:
            break
        characters.append(chr(code_unit))
    return "".join(characters)


class FriendStruct(Structure):
    """The fixed-width x86 native ``Friend`` record.

    The native header's comment beside ``charname`` says ``+0x2C``, but its
    declared ``wchar_t alias[20]`` occupies ``0x28`` bytes on Windows. The
    concrete declared layout therefore places the character name at ``0x40``
    and the record size at ``0x70``.
    """

    _pack_ = 1
    _fields_ = [
        ("friend_type", c_uint32),
        ("status", c_uint32),
        ("uuid", c_uint8 * 16),
        ("alias", c_uint16 * 20),
        ("character_name", c_uint16 * 20),
        ("friend_id", c_uint32),
        ("zone_id", c_uint32),
    ]

    @property
    def type(self) -> FriendType:
        """Return the decoded native friend type when known."""

        try:
            return FriendType(int(self.friend_type))
        except ValueError:
            return FriendType.unknown

    @property
    def friend_status(self) -> FriendStatus:
        """Return the decoded native online status when known."""

        try:
            return FriendStatus(int(self.status))
        except ValueError:
            return FriendStatus.unknown

    @property
    def alias_str(self) -> str:
        """Return the decoded alias."""

        return _decode_wide_array(self.alias)

    @property
    def character_name_str(self) -> str:
        """Return the decoded character name."""

        return _decode_wide_array(self.character_name)

    @property
    def charname(self) -> ctypes.Array[c_uint16]:
        """Return the native ``charname`` field under its source name."""

        return self.character_name

    @property
    def charname_str(self) -> str:
        """Return the source-compatible decoded character name."""

        return self.character_name_str

    @property
    def uuid_bytes(self) -> bytes:
        """Return the raw 16-byte account identifier."""

        return bytes(self.uuid)


class FriendListStruct(Structure):
    """The fixed-width x86 native ``FriendList`` root record."""

    _pack_ = 1
    _fields_ = [
        ("friends_array", GWArray),
        ("unknown_0010", c_uint8 * 20),
        ("number_of_friends", c_uint32),
        ("number_of_ignores", c_uint32),
        ("number_of_partners", c_uint32),
        ("number_of_trades", c_uint32),
        ("unknown_0034", c_uint8 * 108),
        ("player_status", c_uint32),
    ]

    _remote_reader: _memory_reader | None = None
    _max_friend_records = 512

    def bind_reader(
        self,
        reader: _memory_reader,
        max_friend_records: int = 512,
    ) -> FriendListStruct:
        """Attach the external reader and bound pointer-array traversal."""

        if max_friend_records <= 0:
            raise ValueError("max_friend_records must be positive.")
        self._remote_reader = reader
        self._max_friend_records = max_friend_records
        return self

    @property
    def status(self) -> FriendStatus:
        """Return the decoded player's own friend-list status."""

        try:
            return FriendStatus(int(self.player_status))
        except ValueError:
            return FriendStatus.unknown

    @property
    def friends(self) -> list[FriendStruct]:
        """Read the bounded list of current friend records."""

        if self._remote_reader is None:
            raise RuntimeError("FriendList is not bound to a memory reader.")

        array = self.friends_array
        size = int(array.m_size)
        capacity = int(array.m_capacity)
        if not array.m_buffer or size > capacity:
            return []

        records: list[FriendStruct] = []
        for index in range(min(size, self._max_friend_records)):
            record = self._read_friend_at(index)
            if record is not None:
                records.append(record)
        return records

    def _read_friend_at(self, index: int) -> FriendStruct | None:
        """Read one bounded friend-array entry without changing its index."""

        if self._remote_reader is None:
            raise RuntimeError("FriendList is not bound to a memory reader.")
        array = self.friends_array
        size = int(array.m_size)
        if (
            index < 0
            or index >= size
            or index >= self._max_friend_records
            or not array.m_buffer
            or size > int(array.m_capacity)
        ):
            return None
        pointer_raw = self._remote_reader.read(int(array.m_buffer) + index * 4, 4)
        pointer = int.from_bytes(pointer_raw, "little")
        if pointer < 0x10000:
            return None
        try:
            raw_record = self._remote_reader.read(pointer, ctypes.sizeof(FriendStruct))
        except OSError:
            return None
        return FriendStruct.from_buffer_copy(raw_record)

    def get_friend(self, index: int) -> FriendStruct | None:
        """Return one friend record by its native array index."""

        return self._read_friend_at(index)

    def find_friend(
        self,
        alias: str | None = None,
        character_name: str | None = None,
        friend_type: FriendType = FriendType.friend,
    ) -> FriendStruct | None:
        """Find a friend by alias or character name and optional type."""

        if alias is None and character_name is None:
            return None
        array_size = min(int(self.friends_array.m_size), self._max_friend_records)
        for index in range(array_size):
            friend = self._read_friend_at(index)
            if friend is None:
                continue
            if friend_type != FriendType.unknown and friend.type != friend_type:
                continue
            if alias is not None and friend.alias_str == alias:
                return friend
            if character_name is not None and friend.character_name_str == character_name:
                return friend
        return None

    def get_friend_by_uuid(self, uuid: bytes) -> FriendStruct | None:
        """Find a friend by its 16-byte account UUID."""

        if len(uuid) != 16:
            return None
        array_size = min(int(self.friends_array.m_size), self._max_friend_records)
        for index in range(array_size):
            friend = self._read_friend_at(index)
            if friend is not None and friend.uuid_bytes == uuid:
                return friend
        return None

    def get_number_of_friends(self, friend_type: FriendType = FriendType.friend) -> int:
        """Return the native count for one friend category."""

        return {
            FriendType.friend: int(self.number_of_friends),
            FriendType.ignore: int(self.number_of_ignores),
            FriendType.player: int(self.number_of_partners),
            FriendType.trade: int(self.number_of_trades),
        }.get(friend_type, 0)

    def get_number_of_ignores(self) -> int:
        """Return the native ignore count."""

        return int(self.number_of_ignores)

    def get_number_of_partners(self) -> int:
        """Return the native partner count."""

        return int(self.number_of_partners)

    def get_number_of_traders(self) -> int:
        """Return the native trade-friend count."""

        return int(self.number_of_trades)

    def get_my_status(self) -> FriendStatus:
        """Return the native current player's friend status."""

        return self.status


assert ctypes.sizeof(FriendStruct) == 0x70
assert ctypes.sizeof(FriendListStruct) == 0xA4
assert FriendListStruct.number_of_friends.offset == 0x24
assert FriendListStruct.player_status.offset == 0xA0


class FriendList:
    """Resolve and read the current external friend-list root."""

    _RESOLVER = "friend_list.friend_list_addr"

    def __init__(
        self,
        reader: _memory_reader,
        scanner: RemoteScanner,
        patterns: PatternCatalog,
        max_friend_records: int = 512,
    ) -> None:
        """Create a bounded read-only friend-list reader."""

        if max_friend_records <= 0:
            raise ValueError("max_friend_records must be positive.")
        self._reader = reader
        self._scanner = scanner
        self._patterns = patterns
        self._max_friend_records = max_friend_records
        self._context_address: int | None = None

    def resolve_address(self) -> int | None:
        """Return the cached native friend-list object address."""

        if self._context_address is None:
            return self.initialize()
        return self._context_address

    def initialize(self) -> int | None:
        """Resolve and cache the friend-list object address once."""

        if self._context_address is None:
            result = self._patterns.resolve(self._RESOLVER, self._scanner)
            if not result.ok:
                detail = result.message or "the resolver returned no address"
                raise RuntimeError(f"{self._RESOLVER} failed: {detail}")
            self._context_address = result.value
        return self._context_address or None

    @property
    def cached_context_address(self) -> int | None:
        """Return the cached native friend-list object address."""

        return self._context_address

    def read(self) -> FriendListStruct | None:
        """Read the root and bind its bounded friend-record view."""

        address = self.resolve_address()
        if address is None:
            return None
        raw_context = self._reader.read(
            address,
            ctypes.sizeof(FriendListStruct),
        )
        return FriendListStruct.from_buffer_copy(raw_context).bind_reader(
            self._reader,
            self._max_friend_records,
        )


def get() -> FriendListStruct | None:
    """Read the friend list for the current selected client, if connected."""

    from ..client import current_client

    client = current_client()
    return client.read_friend_list() if client is not None else None
