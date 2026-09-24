"""External reader for the native ``GuildContext`` hierarchy.

The structures in this module mirror the fixed-width x86 records used by the
Guild Wars client.  Pointer fields are target-process addresses and are only
followed through the bound :class:`ProcessMemoryReader`.
"""

from __future__ import annotations

from ..helpers.target_struct import TargetStruct

import ctypes
from ctypes import Structure, Union, c_uint8, c_uint16, c_uint32
from typing import Any, Protocol, TypeVar, cast

from .game_context import GameContext, GameContextStruct
from .gw_array import GWArray, GWArrayValueView, GWArrayView, RemoteMemoryReader


class _memory_reader(RemoteMemoryReader, Protocol):
    """The byte-reading operation needed by nested guild records."""


_structure_type = TypeVar("_structure_type", bound=Structure)
_value_type = TypeVar("_value_type")


def _decode_wide_field(values: object) -> str:
    """Decode a fixed-width target UTF-16 field up to its first NUL."""

    raw = bytes(values)  # type: ignore[arg-type]
    return raw.decode("utf-16-le", errors="replace").split("\x00", 1)[0]


def _format_encoded_text(value: str) -> str:
    """Display printable text while preserving Guild Wars encoded values."""

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


class GHKeyStruct(Union):
    """The source/native-compatible guild-hall key view.

    Reforged exposes four key bytes while the native header exposes four
    32-bit words.  Both views address the same first 0x10 target bytes.
    """

    _fields_ = [
        ("key_data", c_uint8 * 4),
        ("k", c_uint32 * 4),
    ]

    @classmethod
    def from_hex(cls, hex_string: str) -> GHKeyStruct:
        """Create a key from Reforged's eight-hex-character form.

        The Python source models four bytes while the native structure keeps a
        0x10-byte x86 record.  The source form is therefore copied into the
        first four target bytes and the remaining native words stay zero.
        """

        if len(hex_string) != 8:
            raise ValueError("Hex string must be exactly 8 characters long.")
        try:
            raw = bytes.fromhex(hex_string)
        except ValueError as error:
            raise ValueError("Hex string must contain only hexadecimal digits.") from error
        key = cls()
        ctypes.memmove(ctypes.addressof(key), raw, len(raw))
        return key

    @property
    def as_string(self) -> str:
        """Return the source-compatible four-byte hexadecimal value."""

        return "".join(f"{int(value):02X}" for value in self.key_data)

    @property
    def is_valid(self) -> bool:
        """Return whether at least one key word is non-zero."""

        return any(int(value) != 0 for value in self.k)


class CapeDesignStruct(TargetStruct):
    """The native 0x1C cape-design value."""

    _pack_ = 1
    _fields_ = [
        ("cape_bg_color", c_uint32),
        ("cape_detail_color", c_uint32),
        ("cape_emblem_color", c_uint32),
        ("cape_shape", c_uint32),
        ("cape_detail", c_uint32),
        ("cape_emblem", c_uint32),
        ("cape_trim", c_uint32),
    ]


class TownAllianceStruct(TargetStruct):
    """The native 0x78 faction-town alliance record."""

    _pack_ = 1
    _fields_ = [
        ("rank", c_uint32),
        ("allegiance", c_uint32),
        ("faction", c_uint32),
        ("name_enc", c_uint16 * 32),
        ("tag_enc", c_uint16 * 5),
        ("_padding", c_uint8 * 2),
        ("cape", CapeDesignStruct),
        ("map_id", c_uint32),
    ]

    @property
    def name(self) -> object:
        """Return the native C++ field spelling for ``name_enc``."""

        return self.name_enc

    @property
    def tag(self) -> object:
        """Return the native C++ field spelling for ``tag_enc``."""

        return self.tag_enc

    @property
    def name_encoded_str(self) -> str:
        """Return the raw encoded alliance name."""

        return _decode_wide_field(self.name_enc)

    @property
    def name_str(self) -> str:
        """Return a display-safe alliance name."""

        return _format_encoded_text(self.name_encoded_str)

    @property
    def tag_encoded_str(self) -> str:
        """Return the raw encoded alliance tag."""

        return _decode_wide_field(self.tag_enc)

    @property
    def tag_str(self) -> str:
        """Return a display-safe alliance tag."""

        return _format_encoded_text(self.tag_encoded_str)


class GuildHistoryEventStruct(TargetStruct):
    """The native 0x208 guild-history event."""

    _pack_ = 1
    _fields_ = [
        ("time1", c_uint32),
        ("time2", c_uint32),
        ("name_enc", c_uint16 * 256),
    ]

    @property
    def name(self) -> object:
        """Return the native C++ field spelling for ``name_enc``."""

        return self.name_enc

    @property
    def name_encoded_str(self) -> str:
        """Return the raw encoded history name."""

        return _decode_wide_field(self.name_enc)

    @property
    def name_str(self) -> str:
        """Return a display-safe history name."""

        return _format_encoded_text(self.name_encoded_str)


class GuildStruct(TargetStruct):
    """The native 0xAC guild record."""

    _pack_ = 1
    _fields_ = [
        ("key", GHKeyStruct),
        ("h0010", c_uint32 * 5),
        ("index", c_uint32),
        ("rank", c_uint32),
        ("features", c_uint32),
        ("name_enc", c_uint16 * 32),
        ("rating", c_uint32),
        ("faction", c_uint32),
        ("faction_point", c_uint32),
        ("qualifier_point", c_uint32),
        ("tag_enc", c_uint16 * 8),
        ("cape", CapeDesignStruct),
    ]

    @property
    def name(self) -> object:
        """Return the native C++ field spelling for ``name_enc``."""

        return self.name_enc

    @property
    def tag(self) -> object:
        """Return the native C++ field spelling for ``tag_enc``."""

        return self.tag_enc

    @property
    def name_encoded_str(self) -> str:
        """Return the raw encoded guild name."""

        return _decode_wide_field(self.name_enc)

    @property
    def name_str(self) -> str:
        """Return a display-safe guild name."""

        return _format_encoded_text(self.name_encoded_str)

    @property
    def tag_encoded_str(self) -> str:
        """Return the raw encoded guild tag."""

        return _decode_wide_field(self.tag_enc)

    @property
    def tag_str(self) -> str:
        """Return a display-safe guild tag."""

        return _format_encoded_text(self.tag_encoded_str)


class GuildPlayerStruct(TargetStruct):
    """The native 0x174 guild-roster member record."""

    _pack_ = 1
    _fields_ = [
        ("vtable", c_uint32),
        ("name_ptr", c_uint32),
        ("invited_name_enc", c_uint16 * 20),
        ("current_name_enc", c_uint16 * 20),
        ("inviter_name_enc", c_uint16 * 20),
        ("invite_time", c_uint32),
        ("promoter_name_enc", c_uint16 * 20),
        ("h00AC", c_uint32 * 12),
        ("offline", c_uint32),
        ("member_type", c_uint32),
        ("status", c_uint32),
        ("h00E8", c_uint32 * 35),
    ]

    @property
    def invited_name(self) -> object:
        """Return the native C++ field spelling for ``invited_name_enc``."""

        return self.invited_name_enc

    @property
    def current_name(self) -> object:
        """Return the native C++ field spelling for ``current_name_enc``."""

        return self.current_name_enc

    @property
    def inviter_name(self) -> object:
        """Return the native C++ field spelling for ``inviter_name_enc``."""

        return self.inviter_name_enc

    @property
    def promoter_name(self) -> object:
        """Return the native C++ field spelling for ``promoter_name_enc``."""

        return self.promoter_name_enc

    _remote_reader: _memory_reader | None = None
    _remote_address: int | None = None

    def bind_reader(
        self, reader: _memory_reader, address: int | None = None
    ) -> GuildPlayerStruct:
        """Attach the reader used by the indirect name pointer."""

        self._remote_reader = reader
        self._remote_address = address
        return self

    def _read_name_pointer(self) -> str | None:
        pointer = int(self.name_ptr)
        if pointer < 0x10000 or self._remote_reader is None:
            return None
        raw = bytearray()
        for index in range(256):
            pair = self._remote_reader.read(pointer + index * 2, 2)
            if pair == b"\x00\x00":
                break
            raw.extend(pair)
        return bytes(raw).decode("utf-16-le", errors="replace")

    @property
    def name_encoded_str(self) -> str | None:
        """Read the encoded name through the target pointer."""

        return self._read_name_pointer()

    @property
    def name_str(self) -> str | None:
        """Return a display-safe roster name."""

        encoded = self.name_encoded_str
        return _format_encoded_text(encoded) if encoded is not None else None

    def _fixed_name(self, field_name: str) -> str:
        return _decode_wide_field(getattr(self, field_name))

    @property
    def invited_name_encoded_str(self) -> str:
        return self._fixed_name("invited_name_enc")

    @property
    def invited_name_str(self) -> str:
        return _format_encoded_text(self.invited_name_encoded_str)

    @property
    def current_name_encoded_str(self) -> str:
        return self._fixed_name("current_name_enc")

    @property
    def current_name_str(self) -> str:
        return _format_encoded_text(self.current_name_encoded_str)

    @property
    def inviter_name_encoded_str(self) -> str:
        return self._fixed_name("inviter_name_enc")

    @property
    def inviter_name_str(self) -> str:
        return _format_encoded_text(self.inviter_name_encoded_str)

    @property
    def promoter_name_encoded_str(self) -> str:
        return self._fixed_name("promoter_name_enc")

    @property
    def promoter_name_str(self) -> str:
        return _format_encoded_text(self.promoter_name_encoded_str)


class GuildContextStruct(TargetStruct):
    """The complete fixed-width native ``GuildContext`` layout."""

    _pack_ = 1
    _fields_ = [
        ("h0000", c_uint32), ("h0004", c_uint32), ("h0008", c_uint32),
        ("h000C", c_uint32), ("h0010", c_uint32), ("h0014", c_uint32),
        ("h0018", c_uint32), ("h001C", c_uint32), ("h0020_array", GWArray),
        ("h0030", c_uint32), ("player_name_enc", c_uint16 * 20),
        ("h005C", c_uint32), ("player_guild_index", c_uint32),
        ("player_gh_key", GHKeyStruct), ("h0074", c_uint32),
        ("announcement_enc", c_uint16 * 256),
        ("announcement_author_enc", c_uint16 * 20),
        ("player_guild_rank", c_uint32), ("h02A4", c_uint32),
        ("factions_outpost_guilds_array", GWArray),
        ("kurzick_town_count", c_uint32), ("luxon_town_count", c_uint32),
        ("h02C0", c_uint32), ("h02C4", c_uint32), ("h02C8", c_uint32),
        ("player_guild_history_array", GWArray), ("h02DC", c_uint32 * 7),
        ("guild_array_array", GWArray), ("h0308", c_uint32 * 4),
        ("h0318_array", GWArray), ("h0328", c_uint32),
        ("h032C_array", GWArray), ("h033C", c_uint32 * 7),
        ("player_roster_array", GWArray),
    ]

    _remote_reader: _memory_reader | None = None
    _remote_address: int | None = None

    def bind_reader(
        self, reader: _memory_reader, address: int | None = None
    ) -> GuildContextStruct:
        """Attach the reader and target address used by array properties."""

        self._remote_reader = reader
        self._remote_address = address
        return self

    def _require_reader(self) -> _memory_reader:
        if self._remote_reader is None:
            raise RuntimeError("This guild snapshot is not bound to a memory reader.")
        return self._remote_reader

    def _values(
        self, array: GWArray, element_type: type[_value_type]
    ) -> list[_value_type]:
        return list(GWArrayValueView(self._require_reader(), array, element_type))

    @property
    def h0020_ptrs(self) -> list[int] | None:
        values = [int(cast(Any, value)) for value in self._values(self.h0020_array, c_uint32)]
        return values or None

    @property
    def h0020(self) -> GWArray:
        """Return the native C++ auxiliary-array header."""

        return self.h0020_array

    @property
    def player_name_encoded_str(self) -> str:
        return _decode_wide_field(self.player_name_enc)

    @property
    def player_name_str(self) -> str | None:
        encoded = self.player_name_encoded_str
        return _format_encoded_text(encoded) if encoded else None

    @property
    def announcement_encoded_str(self) -> str:
        return _decode_wide_field(self.announcement_enc)

    @property
    def announcement_str(self) -> str | None:
        encoded = self.announcement_encoded_str
        return _format_encoded_text(encoded) if encoded else None

    @property
    def announcement_author_encoded_str(self) -> str:
        return _decode_wide_field(self.announcement_author_enc)

    @property
    def announcement_author_str(self) -> str | None:
        encoded = self.announcement_author_encoded_str
        return _format_encoded_text(encoded) if encoded else None

    @property
    def factions_outpost_guilds(self) -> list[TownAllianceStruct] | None:
        values = cast(
            list[TownAllianceStruct],
            self._values(self.factions_outpost_guilds_array, TownAllianceStruct),
        )
        return values or None

    @property
    def player_guild_history(self) -> list[GuildHistoryEventStruct] | None:
        values = [
            value
            for value in GWArrayView(
                self._require_reader(),
                self.player_guild_history_array,
                GuildHistoryEventStruct,
            ).to_list()
        ]
        return values or None

    @property
    def guild_array(self) -> list[GuildStruct] | None:
        values = [
            value
            for value in GWArrayView(
                self._require_reader(), self.guild_array_array, GuildStruct
            ).to_list()
        ]
        return values or None

    @property
    def h0318_ptrs(self) -> list[int] | None:
        values = [int(cast(Any, value)) for value in self._values(self.h0318_array, c_uint32)]
        return values or None

    @property
    def h0318(self) -> GWArray:
        """Return the native C++ auxiliary-array header."""

        return self.h0318_array

    @property
    def h032C_ptrs(self) -> list[int] | None:
        values = [int(cast(Any, value)) for value in self._values(self.h032C_array, c_uint32)]
        return values or None

    @property
    def h032C(self) -> GWArray:
        """Return the native C++ auxiliary-array header."""

        return self.h032C_array

    @property
    def player_roster(self) -> list[GuildPlayerStruct] | None:
        values = [
            value
            for value in GWArrayView(
                self._require_reader(), self.player_roster_array, GuildPlayerStruct
            ).to_list()
        ]
        return values or None

    @property
    def guilds(self) -> list[GuildStruct] | None:
        """Return guild records using the native C++ collection spelling."""

        return self.guild_array


assert ctypes.sizeof(GHKeyStruct) == 0x10
assert ctypes.sizeof(CapeDesignStruct) == 0x1C
assert ctypes.sizeof(TownAllianceStruct) == 0x78
assert ctypes.sizeof(GuildHistoryEventStruct) == 0x208
assert ctypes.sizeof(GuildStruct) == 0xAC
assert ctypes.sizeof(GuildPlayerStruct) == 0x174
# The native header's historical size comment says 0x3BC, but its maintained
# field offsets end at the 0x368-byte roster array.  The concrete ctypes layout
# follows those offsets and the Reforged Python structure.
assert ctypes.sizeof(GuildContextStruct) == 0x368
assert GuildContextStruct.player_name_enc.offset == 0x34
assert GuildContextStruct.player_gh_key.offset == 0x64
assert GuildContextStruct.announcement_enc.offset == 0x78
assert GuildContextStruct.factions_outpost_guilds_array.offset == 0x2A8
assert GuildContextStruct.guild_array_array.offset == 0x2F8
assert GuildContextStruct.player_roster_array.offset == 0x358


class GuildContext:
    """Resolve and read the current native ``GuildContext``."""

    _ptr: int = 0
    _cached_ctx: GuildContextStruct | None = None
    _callback_name = "GuildContext.UpdatePtr"

    def __init__(self, reader: _memory_reader, game_context: GameContext) -> None:
        """Create a reader using the connected client's cached GameContext."""

        self._reader = reader
        self._game_context = game_context

    @staticmethod
    def get_ptr() -> int:
        """Return the last externally refreshed GuildContext address."""

        return GuildContext._ptr

    @staticmethod
    def _update_ptr() -> None:
        """Refresh the source-compatible facade from the selected client."""

        from ..client import current_client

        client = current_client()
        if client is None:
            GuildContext._ptr = 0
            GuildContext._cached_ctx = None
            return
        try:
            context = client.guild_context
            address = context.resolve_address()
            GuildContext._ptr = address or 0
            GuildContext._cached_ctx = cast(Any, context.read())
        except (OSError, RuntimeError):
            GuildContext._ptr = 0
            GuildContext._cached_ctx = None

    @staticmethod
    def enable() -> None:
        """Declare the source callback operation; callbacks require injection."""

        raise NotImplementedError(
            "GuildContext.enable requires the in-process callback runtime."
        )

    @staticmethod
    def disable() -> None:
        """Clear the external facade cache."""

        GuildContext._ptr = 0
        GuildContext._cached_ctx = None

    @staticmethod
    def get_context() -> GuildContextStruct | None:
        """Return the last snapshot refreshed through ``_update_ptr``."""

        return GuildContext._cached_ctx

    def resolve_address(self) -> int | None:
        """Return the current guild-context address, if available."""

        game_address = self._game_context.resolve_address()
        raw_pointer = self._reader.read(
            game_address + GameContextStruct.guild_context.offset, 4
        )
        address = int.from_bytes(raw_pointer, "little")
        return address or None

    def read(self) -> GuildContextStruct | None:
        """Read and decode the complete maintained guild structure."""

        address = self.resolve_address()
        if address is None:
            return None
        raw_context = self._reader.read(address, ctypes.sizeof(GuildContextStruct))
        return GuildContextStruct.from_buffer_copy(raw_context).bind_reader(
            self._reader, address
        )


def get() -> GuildContextStruct | None:
    """Read the GuildContext of the current selected client, if available."""

    from ..client import current_client

    client = current_client()
    return cast(Any, client.read_guild_context() if client is not None else None)


def get_guild_array() -> GWArray | None:
    """Return the current native guild-array header, if available."""

    from ..client import current_client

    client = current_client()
    snapshot = client.read_guild_context() if client is not None else None
    return snapshot.guild_array_array if snapshot is not None else None


# Native context-method spelling retained for source ports.
GetGuildArray = get_guild_array


# Keep the source-project spellings available alongside Stealth's explicit
# ``Struct`` names for users porting Reforged context code.
GHKey = GHKeyStruct
CapeDesign = CapeDesignStruct
TownAlliance = TownAllianceStruct
GuildHistoryEvent = GuildHistoryEventStruct
Guild = GuildStruct
GuildPlayer = GuildPlayerStruct
