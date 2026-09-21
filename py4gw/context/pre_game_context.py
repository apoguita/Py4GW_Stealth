"""External layout and reader for Reforged's ``PreGameContext``."""

from __future__ import annotations

import ctypes
import struct
from ctypes import Structure, c_float, c_int32, c_uint16, c_uint32
from typing import Protocol, cast

from ..scanner import PatternCatalog, RemoteScanner
from .gw_array import GWArray, GWArrayValueView, GWBaseArray, RemoteMemoryReader


class _memory_reader(RemoteMemoryReader, Protocol):
    """The byte-reading operation needed by the external context reader."""


def _decode_wide_field(values: object) -> str:
    """Decode a fixed-width target UTF-16 field up to its first NUL."""

    raw = bytes(values)  # type: ignore[arg-type]
    return raw.decode("utf-16-le", errors="replace").split("\x00", 1)[0]


def _format_encoded_text(value: str) -> str:
    """Keep printable characters and expose encoded values visibly."""

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


class LoginCharacter(Structure):
    """The fixed-width x86 port of Reforged ``LoginCharacter``."""

    _pack_ = 1
    _fields_ = [
        ("appearance_packed", c_uint32),
        ("pvp_flag", c_uint32),
        ("guild_guid_0", c_uint32),
        ("guild_guid_1", c_uint32),
        ("guild_guid_2", c_uint32),
        ("guild_guid_3", c_uint32),
        ("items_data", c_uint32),
        ("items_capacity", c_uint32),
        ("items_count", c_uint32),
        ("items_param", c_uint32),
        ("level", c_uint32),
        ("current_map_id", c_uint32),
        ("field_0x30", c_uint32),
        ("primary_profession", c_uint32),
        ("profession_enum", c_uint32),
        ("field_0x3C", c_uint32),
        ("field_0x40", c_uint32),
        ("field_0x44", c_uint32),
        ("field_0x48", c_uint32),
        ("char_model_ptr", c_uint32),
        ("character_name_enc", c_uint16 * 20),
    ]

    @property
    def guild_guid(self) -> bytes:
        """Return the four GUID words in the source project's byte order."""

        return struct.pack(
            "<IIII",
            self.guild_guid_0,
            self.guild_guid_1,
            self.guild_guid_2,
            self.guild_guid_3,
        )

    @property
    def character_name_encoded_str(self) -> str:
        """Return the fixed-width name with encoded values visible."""

        return _format_encoded_text(_decode_wide_field(self.character_name_enc))

    @property
    def character_name_str(self) -> str:
        """Return the readable character name."""

        return _decode_wide_field(self.character_name_enc)

    @property
    def character_name(self) -> str:
        """Return the Reforged-compatible encoded name representation."""

        return self.character_name_encoded_str


class PreGameContextStruct(Structure):
    """The fixed-width x86 port of Reforged ``PreGameContextStruct``."""

    _pack_ = 1
    _fields_ = [
        ("frame_id", c_uint32),
        ("scene_type", c_uint32),
        ("scene_controller_iface", c_uint32),
        ("camera_pitch_frequency", c_float),
        ("camera_pitch_current", c_float),
        ("camera_pitch_target", c_float),
        ("camera_pitch_velocity", c_float),
        ("RESERVED_0x1C", c_uint32 * 12),
        ("camera_mode", c_uint32),
        ("RESERVED_0x50", c_uint32 * 5),
        ("RESERVED_0x64", c_uint32),
        ("camera_limits_frequency", c_float),
        ("camera_limits_min_current", c_float),
        ("camera_limits_max_current", c_float),
        ("camera_limits_min_target", c_float),
        ("camera_limits_max_target", c_float),
        ("camera_limits_min_velocity", c_float),
        ("camera_limits_max_velocity", c_float),
        ("scroll_offset_frequency", c_float),
        ("scroll_offset_current", c_float),
        ("scroll_offset_target", c_float),
        ("scroll_offset_velocity", c_float),
        ("scroll_speed_frequency", c_float),
        ("scroll_speed_current", c_float),
        ("scroll_speed_target", c_float),
        ("scroll_speed_velocity", c_float),
        ("camera_height", c_float),
        ("camera_height_min", c_float),
        ("camera_height_max", c_float),
        ("camera_rotation_frequency", c_float),
        ("camera_rotation_current", c_float),
        ("camera_rotation_target", c_float),
        ("camera_rotation_velocity", c_float),
        ("RESERVED_0xC0", c_uint32 * 4),
        ("max_characters", c_uint32),
        ("chosen_character_index", c_int32),
        ("preview_character_index", c_int32),
        ("pending_character_index", c_int32),
        ("chars_array", GWBaseArray),
        ("char_creation_flag", c_int32),
        ("create_slot_index", c_int32),
        ("sentinel_guard", c_uint32),
        ("self_link", c_uint32),
        ("list_head", c_uint32),
    ]

    _remote_reader: _memory_reader | None = None

    def bind_reader(self, reader: _memory_reader) -> PreGameContextStruct:
        """Attach the reader needed to follow the remote character array."""

        self._remote_reader = reader
        return self

    def _require_reader(self) -> _memory_reader:
        if self._remote_reader is None:
            raise RuntimeError("This context snapshot is not bound to a memory reader.")
        return self._remote_reader

    @property
    def chars_list(self) -> list[LoginCharacter]:
        """Read the contiguous login-character records from the target array."""

        view = GWArrayValueView(
            self._require_reader(),
            cast(GWArray, self.chars_array),
            LoginCharacter,
        )
        return [cast(LoginCharacter, value) for value in view.to_list()]


assert ctypes.sizeof(LoginCharacter) == 0x78
assert ctypes.sizeof(PreGameContextStruct) == 0x100


class PreGameContext:
    """Resolve and decode one external ``PreGameContext`` snapshot."""

    _RESOLVER = "context.pregame_context_addr"

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

    def resolve_address(self) -> int | None:
        """Return the current target address using the cached resolver."""

        if self._pointer_address is None:
            return self.initialize()
        return self._read_context_address()

    def initialize(self) -> int | None:
        """Scan once and cache the stable pre-game pointer location."""

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

    def read(self) -> PreGameContextStruct | None:
        """Read and decode the complete maintained structure layout."""

        address = self.resolve_address()
        if address is None:
            return None
        raw_context = self._reader.read(
            address, ctypes.sizeof(PreGameContextStruct)
        )
        return PreGameContextStruct.from_buffer_copy(raw_context).bind_reader(
            self._reader
        )

    def _read_context_address(self) -> int | None:
        """Follow the stable global pointer to the current context object."""

        if self._pointer_address is None:
            raise RuntimeError("PreGameContext has not been initialized.")
        context_address = self._scanner.read_uint32(self._pointer_address)
        return context_address or None


def get() -> PreGameContextStruct | None:
    """Read the ``PreGameContext`` of the current selected client, if any."""

    from ..client import current_client

    client = current_client()
    return client.read_pre_game_context() if client is not None else None
