"""External reader for the account-wide available-character roster."""

from __future__ import annotations

from ..helpers.target_struct import TargetStruct

import ctypes
from ctypes import Structure, c_uint16, c_uint32
from typing import Any, Protocol, cast

from ..scanner import PatternCatalog, RemoteScanner
from .gw_array import GWArray, GWArrayValueView, RemoteMemoryReader


class _memory_reader(RemoteMemoryReader, Protocol):
    """The byte-reading operation needed by this context reader."""


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


class AvailableCharacterInfoStruct(TargetStruct):
    """The native ``GW::Context::AvailableCharacterInfo`` layout."""

    _pack_ = 1
    _fields_ = [
        ("h0000", c_uint32 * 2),
        ("uuid_ptr", c_uint32 * 4),
        ("player_name_enc", c_uint16 * 20),
        ("props", c_uint32 * 17),
    ]

    @property
    def uuid(self) -> tuple[int, int, int, int]:
        """Return the four UUID words using the Reforged property name."""

        values = tuple(int(value) for value in self.uuid_ptr)
        return (values[0], values[1], values[2], values[3])

    @property
    def player_name_encoded_str(self) -> str:
        """Return the raw fixed-width UTF-16 name before formatting."""

        return _decode_wide_field(self.player_name_enc)

    @property
    def player_name_encoded_string(self) -> str:
        """Return the Reforged-compatible name for the encoded value."""

        return self.player_name_encoded_str

    @property
    def player_name_str(self) -> str:
        """Return the name with encoded values made visible."""

        return _format_encoded_text(self.player_name_encoded_str)

    @property
    def player_name(self) -> str:
        """Return the Reforged-compatible display name."""

        return self.player_name_str

    @property
    def map_id(self) -> int:
        """Return the packed map identifier."""

        return (int(self.props[0]) >> 16) & 0xFFFF

    @property
    def primary(self) -> int:
        """Return the packed primary profession identifier."""

        return (int(self.props[2]) >> 20) & 0xF

    @property
    def secondary(self) -> int:
        """Return the packed secondary profession identifier."""

        return (int(self.props[7]) >> 10) & 0xF

    @property
    def campaign(self) -> int:
        """Return the packed campaign identifier."""

        return int(self.props[7]) & 0xF

    @property
    def level(self) -> int:
        """Return the packed character level."""

        return (int(self.props[7]) >> 4) & 0x3F

    @property
    def is_pvp(self) -> bool:
        """Return whether the packed roster entry represents a PvP character."""

        return bool((int(self.props[7]) >> 9) & 0x1)


class AvailableCharacterArrayStruct(TargetStruct):
    """The native ``GWArray<AvailableCharacterInfo>`` header."""

    _pack_ = 1
    _fields_ = [("available_characters_array", GWArray)]

    _remote_reader: _memory_reader | None = None

    def bind_reader(
        self, reader: _memory_reader
    ) -> AvailableCharacterArrayStruct:
        """Attach the reader used by the remote array view."""

        self._remote_reader = reader
        return self

    @property
    def available_characters_list(self) -> list[AvailableCharacterInfoStruct]:
        """Read every bounded roster entry from the target array."""

        if self._remote_reader is None:
            raise RuntimeError("This context snapshot is not bound to a memory reader.")
        view = GWArrayValueView(
            self._remote_reader,
            cast(GWArray, self.available_characters_array),
            AvailableCharacterInfoStruct,
        )
        return [
            cast(AvailableCharacterInfoStruct, value)
            for value in view.to_list()
        ]

    @property
    def characters(self) -> list[AvailableCharacterInfoStruct]:
        """Return the available roster using a concise property name."""

        return self.available_characters_list


assert ctypes.sizeof(AvailableCharacterInfoStruct) == 0x84
assert ctypes.sizeof(AvailableCharacterArrayStruct) == 0x10

# Reforged names this record ``AvailableCharacterStruct``.  Keep the
# descriptive ``Info`` name as the implementation name while exporting the
# source-compatible alias.
AvailableCharacterStruct = AvailableCharacterInfoStruct


class AvailableCharacterArray:
    """Resolve and read the native account-wide character roster."""

    # Source-compatible static facade state. The injected source updates this
    # through a callback; the external reader refreshes it explicitly.
    _ptr: int = 0
    _cached_ctx: AvailableCharacterArrayStruct | None = None
    _callback_name = "AvailableCharacterArrayContext.UpdatePtr"

    _RESOLVER = "player.available_characters_addr"

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
        self._context_address: int | None = None

    @staticmethod
    def get_ptr() -> int:
        """Return the last externally refreshed roster-array address."""

        return AvailableCharacterArray._ptr

    @staticmethod
    def _update_ptr() -> None:
        """Refresh the source-compatible facade from the selected client."""

        from ..client import current_client

        client = current_client()
        if client is None:
            AvailableCharacterArray._ptr = 0
            AvailableCharacterArray._cached_ctx = None
            return
        try:
            context = client.available_characters
            address = context.resolve_address()
            AvailableCharacterArray._ptr = address or 0
            AvailableCharacterArray._cached_ctx = cast(Any, context.read())
        except (OSError, RuntimeError):
            AvailableCharacterArray._ptr = 0
            AvailableCharacterArray._cached_ctx = None

    @staticmethod
    def enable() -> None:
        """Declare the source callback operation; callbacks require injection."""

        raise NotImplementedError(
            "AvailableCharacterArray.enable requires the in-process callback runtime."
        )

    @staticmethod
    def disable() -> None:
        """Clear the external facade cache."""

        AvailableCharacterArray._ptr = 0
        AvailableCharacterArray._cached_ctx = None

    @staticmethod
    def get_context() -> AvailableCharacterArrayStruct | None:
        """Return the last snapshot refreshed through ``_update_ptr``."""

        return AvailableCharacterArray._cached_ctx

    def resolve_address(self) -> int | None:
        """Return the current native ``GWArray`` address, if available."""

        if self._context_address is None:
            return self.initialize()
        return self._context_address

    def initialize(self) -> int | None:
        """Resolve and cache the stable native roster-array address."""

        if self._context_address is None:
            result = self._patterns.resolve(self._RESOLVER, self._scanner)
            if not result.ok:
                detail = result.message or "the resolver returned no address"
                raise RuntimeError(f"{self._RESOLVER} failed: {detail}")
            self._context_address = result.value
        return self._context_address

    @property
    def cached_context_address(self) -> int | None:
        """Return the cached native array address, if initialized."""

        return self._context_address

    def read(self) -> AvailableCharacterArrayStruct | None:
        """Read the array header and bind its remote roster view."""

        address = self.resolve_address()
        if address is None:
            return None
        raw_context = self._reader.read(
            address, ctypes.sizeof(AvailableCharacterArrayStruct)
        )
        return AvailableCharacterArrayStruct.from_buffer_copy(raw_context).bind_reader(
            self._reader
        )


def get() -> AvailableCharacterArrayStruct | None:
    """Read the available-character roster of the current selected client."""

    from ..client import current_client

    client = current_client()
    return cast(Any, client.read_available_characters() if client is not None else None)
