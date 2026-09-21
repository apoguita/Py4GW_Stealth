"""External reader for the native ``PartyContext`` hierarchy."""

from __future__ import annotations

import ctypes
from ctypes import Structure, c_uint8, c_uint16, c_uint32
from typing import Protocol, TypeVar

from ..scanner import PatternCatalog, RemoteScanner
from .game_context import GameContext, GameContextStruct
from .gw_array import GWArray, GWArrayValueView, GWArrayView, RemoteMemoryReader
from .gw_list import GWLinkStruct, GWListStruct, RemoteGWListView


class _memory_reader(RemoteMemoryReader, Protocol):
    """The byte-reading operation needed by this context reader."""


_structure_type = TypeVar("_structure_type", bound=Structure)


def _decode_wide_field(values: object) -> str:
    """Decode a fixed-width target UTF-16 field up to its first NUL."""

    raw = bytes(values)  # type: ignore[arg-type]
    return raw.decode("utf-16-le", errors="replace").split("\x00", 1)[0]


def _format_encoded_text(value: str) -> str:
    """Keep printable characters and expose Guild Wars encoded values."""

    output: list[str] = []
    for character in value:
        code_point = ord(character)
        if 32 <= code_point <= 126:
            output.append(character)
        elif character == "\n":
            output.append("\\n")
        elif character == "\t":
            output.append("\\t")
        else:
            output.append(f"\\x{code_point:04X}")
    return "".join(output)


class PlayerPartyMemberStruct(Structure):
    """The native 0x0C player-party member record."""

    _pack_ = 1
    _fields_ = [
        ("login_number", c_uint32),
        ("called_target_id", c_uint32),
        ("state", c_uint32),
    ]

    @property
    def is_connected(self) -> bool:
        """Return whether the member is connected."""

        return bool(int(self.state) & 1)

    @property
    def is_ticked(self) -> bool:
        """Return whether the member is ticked by the party state."""

        return bool(int(self.state) & 2)


class HeroPartyMemberStruct(Structure):
    """The native 0x18 hero-party member record."""

    _pack_ = 1
    _fields_ = [
        ("agent_id", c_uint32),
        ("owner_player_id", c_uint32),
        ("hero_id", c_uint32),
        ("h000C", c_uint32),
        ("h0010", c_uint32),
        ("level", c_uint32),
    ]


class HenchmanPartyMemberStruct(Structure):
    """The native 0x34 henchman-party member record."""

    _pack_ = 1
    _fields_ = [
        ("agent_id", c_uint32),
        ("h0004", c_uint32 * 10),
        ("profession", c_uint32),
        ("level", c_uint32),
    ]


class PartyInfoStruct(Structure):
    """The native 0x84 party-information record."""

    _pack_ = 1
    _fields_ = [
        ("party_id", c_uint32),
        ("players_array", GWArray),
        ("henchmen_array", GWArray),
        ("heroes_array", GWArray),
        ("others_array", GWArray),
        ("h0044", c_uint32 * 14),
        ("invite_link", GWLinkStruct),
    ]

    _remote_reader: _memory_reader | None = None
    _remote_address: int | None = None

    def bind_reader(
        self, reader: _memory_reader, address: int | None = None
    ) -> PartyInfoStruct:
        """Attach the reader and target address used by nested properties."""

        self._remote_reader = reader
        self._remote_address = address
        return self

    def _require_reader(self) -> _memory_reader:
        if self._remote_reader is None:
            raise RuntimeError("This party record is not bound to a memory reader.")
        return self._remote_reader

    def _read_array_values(
        self,
        array: GWArray,
        element_type: type[_structure_type],
    ) -> list[_structure_type]:
        view = GWArrayValueView(self._require_reader(), array, element_type)
        return [value for value in view.to_list()]

    @property
    def players(self) -> list[PlayerPartyMemberStruct]:
        """Read the current player members."""

        return self._read_array_values(self.players_array, PlayerPartyMemberStruct)

    @property
    def henchmen(self) -> list[HenchmanPartyMemberStruct]:
        """Read the current henchman members."""

        return self._read_array_values(self.henchmen_array, HenchmanPartyMemberStruct)

    @property
    def heroes(self) -> list[HeroPartyMemberStruct]:
        """Read the current hero members."""

        return self._read_array_values(self.heroes_array, HeroPartyMemberStruct)

    @property
    def others(self) -> list[int]:
        """Read the current ally, minion, and pet agent IDs."""

        view = GWArrayValueView(self._require_reader(), self.others_array, c_uint32)
        return [int(value) for value in view.to_list()]

    @property
    def invite_links(self) -> list[PartyInfoStruct]:
        """Follow the forward invite-party link chain safely."""

        reader = self._require_reader()
        next_node = int(self.invite_link.next_node)
        visited: set[int] = set()
        result: list[PartyInfoStruct] = []
        for _ in range(1024):
            node_address = next_node & ~1
            if not next_node or next_node & 1 or node_address < 0x10000:
                break
            if node_address in visited:
                break
            visited.add(node_address)
            raw_value = reader.read(node_address, ctypes.sizeof(PartyInfoStruct))
            node = PartyInfoStruct.from_buffer_copy(raw_value).bind_reader(
                reader, node_address
            )
            result.append(node)
            next_node = int(node.invite_link.next_node)
        return result


class PartySearchStruct(Structure):
    """The native 0x94 party-search record."""

    _pack_ = 1
    _fields_ = [
        ("party_search_id", c_uint32),
        ("party_search_type", c_uint32),
        ("hardmode", c_uint32),
        ("district", c_uint32),
        ("language", c_uint32),
        ("party_size", c_uint32),
        ("hero_count", c_uint32),
        ("message", c_uint16 * 32),
        ("party_leader", c_uint16 * 20),
        ("primary", c_uint32),
        ("secondary", c_uint32),
        ("level", c_uint32),
        ("timestamp", c_uint32),
    ]

    @property
    def message_encoded_str(self) -> str:
        """Return the raw party-search message."""

        return _decode_wide_field(self.message)

    @property
    def message_str(self) -> str:
        """Return the formatted party-search message."""

        return _format_encoded_text(self.message_encoded_str)

    @property
    def party_leader_encoded_str(self) -> str:
        """Return the raw party-leader name."""

        return _decode_wide_field(self.party_leader)

    @property
    def party_leader_str(self) -> str:
        """Return the formatted party-leader name."""

        return _format_encoded_text(self.party_leader_encoded_str)


class PartyContextStruct(Structure):
    """The complete fixed-width native ``PartyContext`` layout."""

    _pack_ = 1
    _fields_ = [
        ("h0000", c_uint32),
        ("h0004_array", GWArray),
        ("flag", c_uint32),
        ("h0018", c_uint32),
        ("request_list", GWListStruct),
        ("requests_count", c_uint32),
        ("sending_list", GWListStruct),
        ("sending_count", c_uint32),
        ("h003C", c_uint32),
        ("parties_array", GWArray),
        ("h0050", c_uint32),
        ("player_party_ptr", c_uint32),
        ("h0058", c_uint8 * 104),
        ("party_search_array", GWArray),
    ]

    _remote_reader: _memory_reader | None = None
    _remote_address: int | None = None

    def bind_reader(
        self, reader: _memory_reader, address: int | None = None
    ) -> PartyContextStruct:
        """Attach the reader and target address used by nested properties."""

        self._remote_reader = reader
        self._remote_address = address
        return self

    def _require_reader(self) -> _memory_reader:
        if self._remote_reader is None:
            raise RuntimeError("This context snapshot is not bound to a memory reader.")
        return self._remote_reader

    @property
    def in_hard_mode(self) -> bool:
        """Return whether the party is in hard mode."""

        return bool(int(self.flag) & 0x10)

    @property
    def is_defeated(self) -> bool:
        """Return whether the party is defeated."""

        return bool(int(self.flag) & 0x20)

    @property
    def is_party_leader(self) -> bool:
        """Return whether the current character is the party leader."""

        return bool((int(self.flag) >> 7) & 1)

    @property
    def h0004_ptrs(self) -> list[int]:
        """Read the maintained auxiliary pointer values."""

        view = GWArrayValueView(self._require_reader(), self.h0004_array, c_uint32)
        return [int(value) for value in view.to_list()]

    @property
    def requests(self) -> list[PartyInfoStruct]:
        """Read the intrusive request-party list."""

        if self._remote_address is None:
            raise RuntimeError("This context snapshot has no target address.")
        view = RemoteGWListView(
            self._require_reader(),
            self.request_list,
            self._remote_address + PartyContextStruct.request_list.offset,
            PartyInfoStruct,
        )
        return view.to_list()

    @property
    def sending(self) -> list[PartyInfoStruct]:
        """Read the intrusive outgoing-party list."""

        if self._remote_address is None:
            raise RuntimeError("This context snapshot has no target address.")
        view = RemoteGWListView(
            self._require_reader(),
            self.sending_list,
            self._remote_address + PartyContextStruct.sending_list.offset,
            PartyInfoStruct,
        )
        return view.to_list()

    @property
    def parties(self) -> list[PartyInfoStruct]:
        """Read all party records from the target pointer array."""

        view = GWArrayView(
            self._require_reader(), self.parties_array, PartyInfoStruct
        )
        return [value for value in view.to_list()]

    @property
    def player_party(self) -> PartyInfoStruct | None:
        """Read the current character's party record, if available."""

        address = int(self.player_party_ptr)
        if not address:
            return None
        reader = self._require_reader()
        raw_value = reader.read(address, ctypes.sizeof(PartyInfoStruct))
        return PartyInfoStruct.from_buffer_copy(raw_value).bind_reader(reader, address)

    @property
    def party_searches(self) -> list[PartySearchStruct]:
        """Read current party-search entries from the target pointer array."""

        view = GWArrayView(
            self._require_reader(), self.party_search_array, PartySearchStruct
        )
        return [value for value in view.to_list()]


assert ctypes.sizeof(PlayerPartyMemberStruct) == 0x0C
assert ctypes.sizeof(HeroPartyMemberStruct) == 0x18
assert ctypes.sizeof(HenchmanPartyMemberStruct) == 0x34
assert ctypes.sizeof(PartyInfoStruct) == 0x84
assert ctypes.sizeof(PartySearchStruct) == 0x94
assert ctypes.sizeof(PartyContextStruct) == 0xD0
assert PartyContextStruct.player_party_ptr.offset == 0x54
assert PartyContextStruct.party_search_array.offset == 0xC0


class PartyContext:
    """Resolve and read the current native ``PartyContext``."""

    def __init__(self, reader: _memory_reader, game_context: GameContext) -> None:
        """Create a reader using the connected client's cached GameContext."""

        self._reader = reader
        self._game_context = game_context

    def resolve_address(self) -> int | None:
        """Return the current party-context address, if available."""

        game_address = self._game_context.resolve_address()
        raw_pointer = self._reader.read(
            game_address + GameContextStruct.party_context.offset, 4
        )
        address = int.from_bytes(raw_pointer, "little")
        return address or None

    def read(self) -> PartyContextStruct | None:
        """Read and decode the complete maintained party structure."""

        address = self.resolve_address()
        if address is None:
            return None
        raw_context = self._reader.read(address, ctypes.sizeof(PartyContextStruct))
        return PartyContextStruct.from_buffer_copy(raw_context).bind_reader(
            self._reader, address
        )


def get() -> PartyContextStruct | None:
    """Read the PartyContext of the current selected client, if available."""

    from ..client import current_client

    client = current_client()
    return client.read_party_context() if client is not None else None
