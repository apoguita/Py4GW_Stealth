"""External reader and layout for Reforged's ``CharContext``.

The field names and order are ported from Reforged's
``Py4GWCoreLib/native_src/context/CharContext.py`` and its accompanying
``CharContext.pyi``. Pointer fields use fixed-width target integers here so
the layout can be decoded from bytes read from another process.
"""

from __future__ import annotations

import ctypes
from ctypes import Structure, c_float, c_int32, c_uint8, c_uint16, c_uint32
from typing import TYPE_CHECKING, Protocol

from ..scanner import PatternCatalog, RemoteScanner
from .gw_array import GWArray, GWArrayValueView, GWArrayView, RemoteMemoryReader

if TYPE_CHECKING:
    from .game_context import GameContext


class _memory_reader(RemoteMemoryReader, Protocol):
    """The byte-reading operation needed by the external context reader."""


class ObserverMatchFlags(Structure):
    """The maintained Reforged observer-match flag layout."""

    _pack_ = 1
    _fields_ = [
        ("type", c_uint32),
        ("reserved", c_uint32),
        ("version", c_uint32),
        ("state", c_uint32),
        ("level", c_uint32),
        ("config1", c_uint32),
        ("config2", c_uint32),
        ("score1", c_uint32),
        ("score2", c_uint32),
        ("score3", c_uint32),
        ("stat1", c_uint32),
        ("stat2", c_uint32),
        ("data1", c_uint32),
        ("data2", c_uint32),
    ]


class ObserverMatch(Structure):
    """The maintained Reforged observer-match layout."""

    _pack_ = 1
    _fields_ = [
        ("match_id", c_uint32),
        ("match_id_dup", c_uint32),
        ("map_id", c_uint32),
        ("age", c_uint32),
        ("flags", ObserverMatchFlags),
        ("team_name1_ptr", c_uint32),
        ("unknown1", c_uint32 * 0xA),
        ("team_name2_ptr", c_uint32),
    ]

    _remote_reader: _memory_reader | None = None

    def bind_reader(
        self, reader: _memory_reader, address: int | None = None
    ) -> ObserverMatch:
        """Attach the reader needed to follow this match's target pointers."""

        self._remote_reader = reader
        return self

    def _read_team_name(self, address: int) -> str | None:
        if address < 0x10000:
            return None
        if self._remote_reader is None:
            raise RuntimeError("This observer match is not bound to a memory reader.")
        characters: list[str] = []
        for offset in range(0, 512, 2):
            raw = self._remote_reader.read(address + offset, 2)
            code_point = int.from_bytes(raw, "little")
            if code_point == 0:
                break
            characters.append(chr(code_point))
        return "".join(characters)

    @property
    def team_name1_encoded_str(self) -> str | None:
        """Read team one as a wide string from the target process."""

        return self._read_team_name(self.team_name1_ptr)

    @property
    def team_name1_str(self) -> str | None:
        """Read team one with Guild Wars encoded values made visible."""

        encoded = self.team_name1_encoded_str
        return _format_encoded_text(encoded) if encoded is not None else None

    @property
    def team_name2_encoded_str(self) -> str | None:
        """Read team two as a wide string from the target process."""

        return self._read_team_name(self.team_name2_ptr)

    @property
    def team_name2_str(self) -> str | None:
        """Read team two with Guild Wars encoded values made visible."""

        encoded = self.team_name2_encoded_str
        return _format_encoded_text(encoded) if encoded is not None else None


class ProgressBar(Structure):
    """The maintained Reforged progress-bar layout."""

    _pack_ = 1
    _fields_ = [
        ("pips", c_uint32),
        ("color", c_uint8 * 4),
        ("background", c_uint8 * 4),
        ("unk", c_uint32 * 7),
        ("progress", c_float),
    ]


def _decode_wide_field(values: object) -> str:
    """Decode a fixed-width target UTF-16 field up to its first NUL."""

    raw = bytes(values)  # type: ignore[arg-type]
    return raw.decode("utf-16-le", errors="replace").split("\x00", 1)[0]


def _format_encoded_text(value: str) -> str:
    """Keep printable characters and expose non-printable encoded values."""

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


class CharContextStruct(Structure):
    """The complete fixed-width port of Reforged ``CharContextStruct``.

    Pointer fields are stored as ``uint32`` target addresses. They are not
    dereferenced automatically because this structure lives outside the game
    process.
    """

    _pack_ = 1
    _fields_ = [
        ("h0000_array", GWArray),
        ("h0010", c_uint32),
        ("h0014_array", GWArray),
        ("h0024", c_uint32 * 4),
        ("h0034_array", GWArray),
        ("h0044_array", GWArray),
        ("h0054", c_uint32 * 4),
        ("player_uuid_ptr", c_uint32 * 4),
        ("player_name_enc", c_uint16 * 0x14),
        ("h009C", c_uint32 * 20),
        ("h00EC_array", GWArray),
        ("h00FC", c_uint32 * 37),
        ("world_flags", c_uint32),
        ("token1", c_uint32),
        ("map_id", c_uint32),
        ("is_explorable", c_uint32),
        ("host", c_uint8 * 0x18),
        ("token2", c_uint32),
        ("h01BC", c_uint32 * 27),
        ("district_number", c_int32),
        ("language", c_uint32),
        ("observe_map_id", c_uint32),
        ("current_map_id", c_uint32),
        ("observe_map_type", c_uint32),
        ("current_map_type", c_uint32),
        ("h0240", c_uint32 * 5),
        ("observer_matches_array", GWArray),
        ("h0264", c_uint32 * 17),
        ("player_flags", c_uint32),
        ("player_number", c_uint32),
        ("h02B0", c_uint32 * 40),
        ("progress_bar_ptr", c_uint32),
        ("h0354", c_uint32 * 29),
        ("player_email_ptr", c_uint16 * 0x40),
    ]

    _remote_reader: _memory_reader | None = None

    def bind_reader(
        self, reader: _memory_reader, address: int | None = None
    ) -> CharContextStruct:
        """Attach the reader needed to follow this snapshot's target pointers."""

        self._remote_reader = reader
        return self

    def _require_reader(self) -> _memory_reader:
        if self._remote_reader is None:
            raise RuntimeError("This context snapshot is not bound to a memory reader.")
        return self._remote_reader

    def _pointer_values(self, array: GWArray) -> list[int] | None:
        values = GWArrayValueView(self._require_reader(), array, c_uint32).to_list()
        return [int(value) for value in values] if values else None

    @property
    def player_uuid(self) -> tuple[int, int, int, int]:
        """Return the four UUID words from the target structure."""

        values = tuple(int(value) for value in self.player_uuid_ptr)
        return (values[0], values[1], values[2], values[3])

    @property
    def is_logged_in(self) -> bool:
        """Return whether this snapshot contains a logged-in character."""

        return bool(self.player_name_str.strip())

    @property
    def h0000_ptrs(self) -> list[int] | None:
        """Return the values stored in ``h0000_array``."""

        return self._pointer_values(self.h0000_array)

    @property
    def h0014_ptrs(self) -> list[int] | None:
        """Return the values stored in ``h0014_array``."""

        return self._pointer_values(self.h0014_array)

    @property
    def h0034_ptrs(self) -> list[int] | None:
        """Return the values stored in ``h0034_array``."""

        return self._pointer_values(self.h0034_array)

    @property
    def h0044_ptrs(self) -> list[int] | None:
        """Return the values stored in ``h0044_array``."""

        return self._pointer_values(self.h0044_array)

    @property
    def h00EC_ptrs(self) -> list[int] | None:
        """Return the values stored in ``h00EC_array``."""

        return self._pointer_values(self.h00EC_array)

    @property
    def observer_matches(self) -> list[ObserverMatch] | None:
        """Read the observer-match objects referenced by the target array."""

        matches = GWArrayView(
            self._require_reader(), self.observer_matches_array, ObserverMatch
        ).to_list()
        for match in matches:
            match.bind_reader(self._require_reader())
        return matches or None

    @property
    def progress_bar(self) -> ProgressBar | None:
        """Read the progress-bar object referenced by the target pointer."""

        if self.progress_bar_ptr < 0x10000:
            return None
        raw = self._require_reader().read(self.progress_bar_ptr, ctypes.sizeof(ProgressBar))
        return ProgressBar.from_buffer_copy(raw)

    @property
    def player_name_encoded_str(self) -> str:
        """Return the fixed-width player name with encoded values visible."""

        return _format_encoded_text(_decode_wide_field(self.player_name_enc))

    @property
    def player_name_str(self) -> str:
        """Return the readable player name."""

        return _decode_wide_field(self.player_name_enc)

    @property
    def player_email_encoded_str(self) -> str:
        """Return the fixed-width email with encoded values visible."""

        return _format_encoded_text(_decode_wide_field(self.player_email_ptr))

    @property
    def player_email_str(self) -> str:
        """Return the readable player email."""

        return _decode_wide_field(self.player_email_ptr)


assert ctypes.sizeof(ProgressBar) == 0x2C
assert ctypes.sizeof(CharContextStruct) == 0x448


class CharContext:
    """Resolve and decode one external ``CharContext`` snapshot."""

    _BASE_RESOLVER = "context.base_ptr"
    _GAME_CONTEXT_OFFSET = 0x18
    _CHAR_CONTEXT_OFFSET = 0x44

    def __init__(
        self,
        reader: _memory_reader,
        scanner: RemoteScanner,
        patterns: PatternCatalog,
        game_context: GameContext | None = None,
    ) -> None:
        """Create a reader backed by one process and its offset catalog."""

        self._reader = reader
        self._scanner = scanner
        self._patterns = patterns
        self._game_context = game_context
        self._base_pointer_address: int | None = None

    def resolve_address(self) -> int:
        """Return the current target address using the cached resolver."""

        if self._game_context is not None:
            return self._read_context_address()
        if self._base_pointer_address is None:
            return self.initialize()
        return self._read_context_address()

    def initialize(self) -> int:
        """Scan once and cache the stable ``context.base_ptr`` address.

        The signature scan locates a module-global pointer location. That
        location is stable for the lifetime of a connected process, while the
        values reached through it may change when the client changes state.
        The dynamic pointer chain is therefore re-read for each context
        snapshot without repeating the module scan.
        """

        if self._game_context is not None:
            self._game_context.initialize()
            return self._read_context_address()
        self._base_pointer_address = self._resolve_base_pointer()
        return self._read_context_address()

    @property
    def cached_base_pointer_address(self) -> int | None:
        """Return the cached module-global pointer location, if initialized."""

        if self._game_context is not None:
            return self._game_context.cached_base_pointer_address
        return self._base_pointer_address

    def _resolve_base_pointer(self) -> int:
        """Run the JSON resolver that requires the signature scan."""

        result = self._patterns.resolve(self._BASE_RESOLVER, self._scanner)
        if not result.ok:
            detail = result.message or "the resolver returned no address"
            raise RuntimeError(f"{self._BASE_RESOLVER} failed: {detail}")

        return result.value

    def _read_context_address(self) -> int:
        """Follow the current dynamic context pointers from the cache."""

        if self._base_pointer_address is None:
            if self._game_context is None:
                raise RuntimeError("CharContext has not been initialized.")
            game_context = self._game_context.resolve_address()
        else:
            base_context = self._scanner.read_uint32(self._base_pointer_address)
            if not base_context:
                raise RuntimeError("The resolved base context pointer is null.")
            game_context = self._scanner.read_uint32(
                base_context + self._GAME_CONTEXT_OFFSET
            )
        if not game_context:
            raise RuntimeError("The GameContext pointer is null.")
        char_context = self._scanner.read_uint32(
            game_context + self._CHAR_CONTEXT_OFFSET
        )
        if not char_context:
            raise RuntimeError("The CharContext pointer is null.")
        return char_context

    @property
    def is_logged_in(self) -> bool:
        """Return whether the current target has a logged-in character."""

        try:
            return self.read().is_logged_in
        except (OSError, RuntimeError):
            return False

    def read(self) -> CharContextStruct:
        """Read and decode the complete maintained structure layout."""

        address = self.resolve_address()
        raw_context = self._reader.read(address, ctypes.sizeof(CharContextStruct))
        return CharContextStruct.from_buffer_copy(raw_context).bind_reader(self._reader)

    def read_player_name(self) -> str:
        """Read the current player name through the complete context layout."""

        return self.read().player_name_str


def get() -> CharContextStruct | None:
    """Read the CharContext of the current selected client, if any."""

    from ..client import current_client

    client = current_client()
    return client.read_char_context() if client is not None else None
