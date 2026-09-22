"""External layout and reader for Reforged's ``InstanceInfo`` context."""

from __future__ import annotations

import ctypes
from ctypes import Structure, c_uint32
from typing import Any, Protocol, TypeVar, cast

from ..scanner import PatternCatalog, RemoteScanner
from .gw_array import RemoteMemoryReader


class _memory_reader(RemoteMemoryReader, Protocol):
    """The byte-reading operation needed by nested context properties."""


_structure_type = TypeVar("_structure_type", bound=Structure)


class MapDimensionsStruct(Structure):
    """The fixed-width native ``MapDimensions`` record."""

    _pack_ = 1
    _fields_ = [
        ("unk", c_uint32),
        ("start_x", c_uint32),
        ("start_y", c_uint32),
        ("end_x", c_uint32),
        ("end_y", c_uint32),
        ("unk1", c_uint32),
    ]


class AreaInfoStruct(Structure):
    """The fixed-width native ``AreaInfo`` record and its useful flags."""

    _pack_ = 1
    _fields_ = [
        ("campaign", c_uint32),
        ("continent", c_uint32),
        ("region", c_uint32),
        ("type", c_uint32),
        ("flags", c_uint32),
        ("thumbnail_id", c_uint32),
        ("min_party_size", c_uint32),
        ("max_party_size", c_uint32),
        ("min_player_size", c_uint32),
        ("max_player_size", c_uint32),
        ("controlled_outpost_id", c_uint32),
        ("fraction_mission", c_uint32),
        ("min_level", c_uint32),
        ("max_level", c_uint32),
        ("needed_pq", c_uint32),
        ("mission_maps_to", c_uint32),
        ("x", c_uint32),
        ("y", c_uint32),
        ("icon_start_x", c_uint32),
        ("icon_start_y", c_uint32),
        ("icon_end_x", c_uint32),
        ("icon_end_y", c_uint32),
        ("icon_start_x_dupe", c_uint32),
        ("icon_start_y_dupe", c_uint32),
        ("icon_end_x_dupe", c_uint32),
        ("icon_end_y_dupe", c_uint32),
        ("file_id", c_uint32),
        ("mission_chronology", c_uint32),
        ("ha_map_chronology", c_uint32),
        ("name_id", c_uint32),
        ("description_id", c_uint32),
    ]

    @property
    def file_id_1(self) -> int:
        """Return the first archive identifier derived by Reforged."""

        return ((int(self.file_id) - 1) % 0xFF00) + 0x100

    @property
    def file_id1(self) -> int:
        """Return the Reforged-compatible spelling of :attr:`file_id_1`."""

        return self.file_id_1

    @property
    def file_id_2(self) -> int:
        """Return the second archive identifier derived by Reforged."""

        return ((int(self.file_id) - 1) // 0xFF00) + 0x100

    @property
    def file_id2(self) -> int:
        """Return the Reforged-compatible spelling of :attr:`file_id_2`."""

        return self.file_id_2

    @property
    def has_enter_button(self) -> bool:
        """Return whether the area exposes an enter button."""

        return bool(int(self.flags) & 0x100 or int(self.flags) & 0x40000)

    @property
    def is_on_world_map(self) -> bool:
        """Return whether the area is marked as a world-map location."""

        return not bool(int(self.flags) & 0x20)

    @property
    def is_pvp(self) -> bool:
        """Return whether the area has the Reforged PvP flags."""

        return bool(int(self.flags) & 0x40001)

    @property
    def is_guild_hall(self) -> bool:
        """Return whether the area is marked as a guild hall."""

        return bool(int(self.flags) & 0x800000)

    @property
    def is_vanquishable_area(self) -> bool:
        """Return whether the area is marked as vanquishable."""

        return bool(int(self.flags) & 0x10000000)

    @property
    def is_unlockable(self) -> bool:
        """Return whether the area is marked as unlockable."""

        return bool(int(self.flags) & 0x10000)

    @property
    def has_mission_maps_to(self) -> bool:
        """Return whether the area has a mission-map destination."""

        return bool(int(self.flags) & 0x8000000)


class InstanceInfoStruct(Structure):
    """The fixed-width x86 port of Reforged ``InstanceInfoStruct``."""

    _pack_ = 1
    _fields_ = [
        ("terrain_info1_ptr", c_uint32),
        ("instance_type", c_uint32),
        ("current_map_info_ptr", c_uint32),
        ("terrain_count", c_uint32),
        ("terrain_info2_ptr", c_uint32),
    ]

    _remote_reader: _memory_reader | None = None

    def bind_reader(
        self, reader: _memory_reader, address: int | None = None
    ) -> InstanceInfoStruct:
        """Attach the reader needed by the nested pointer properties."""

        self._remote_reader = reader
        return self

    @property
    def terrain_info1(self) -> MapDimensionsStruct | None:
        """Read the first terrain bounds record, when its pointer is valid."""

        return self._read_struct(self.terrain_info1_ptr, MapDimensionsStruct)

    @property
    def current_map_info(self) -> AreaInfoStruct | None:
        """Read the current area's complete metadata record."""

        return self._read_struct(self.current_map_info_ptr, AreaInfoStruct)

    @property
    def terrain_info2(self) -> MapDimensionsStruct | None:
        """Read the second terrain bounds record, when its pointer is valid."""

        return self._read_struct(self.terrain_info2_ptr, MapDimensionsStruct)

    def _read_struct(
        self,
        address: int,
        structure_type: type[_structure_type],
    ) -> _structure_type | None:
        """Read one nested fixed-width structure through the bound reader."""

        if not address:
            return None
        if self._remote_reader is None:
            raise RuntimeError("This context snapshot is not bound to a memory reader.")
        raw_value = self._remote_reader.read(
            int(address), ctypes.sizeof(structure_type)
        )
        return structure_type.from_buffer_copy(raw_value)


assert ctypes.sizeof(MapDimensionsStruct) == 0x18
assert ctypes.sizeof(AreaInfoStruct) == 0x7C
assert ctypes.sizeof(InstanceInfoStruct) == 0x14


class InstanceInfo:
    """Resolve and decode one external ``InstanceInfo`` snapshot."""

    # Source-compatible static facade state. The injected source updates this
    # through a callback; the external reader refreshes it explicitly.
    _ptr: int = 0
    _cached_ctx: InstanceInfoStruct | None = None
    _callback_name = "InstanceInfoContext.UpdatePtr"

    _RESOLVER = "map.instance_info_addr"

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
        """Return the last externally refreshed InstanceInfo address."""

        return InstanceInfo._ptr

    @staticmethod
    def _update_ptr() -> None:
        """Refresh the source-compatible facade from the selected client."""

        from ..client import current_client

        client = current_client()
        if client is None:
            InstanceInfo._ptr = 0
            InstanceInfo._cached_ctx = None
            return
        try:
            context = client.instance_info
            address = context.resolve_address()
            InstanceInfo._ptr = address or 0
            InstanceInfo._cached_ctx = cast(Any, context.read())
        except (OSError, RuntimeError):
            InstanceInfo._ptr = 0
            InstanceInfo._cached_ctx = None

    @staticmethod
    def enable() -> None:
        """Declare the source callback operation; callbacks require injection."""

        raise NotImplementedError(
            "InstanceInfo.enable requires the in-process callback runtime."
        )

    @staticmethod
    def disable() -> None:
        """Clear the external facade cache."""

        InstanceInfo._ptr = 0
        InstanceInfo._cached_ctx = None

    @staticmethod
    def get_context() -> InstanceInfoStruct | None:
        """Return the last snapshot refreshed through ``_update_ptr``."""

        return InstanceInfo._cached_ctx

    def resolve_address(self) -> int | None:
        """Return the current ``InstanceInfo`` address, if available."""

        if self._context_address is None:
            return self.initialize()
        return self._context_address or None

    def initialize(self) -> int | None:
        """Scan once and cache the resolved ``InstanceInfo`` address."""

        if self._context_address is None:
            result = self._patterns.resolve(self._RESOLVER, self._scanner)
            if not result.ok:
                detail = result.message or "the resolver returned no address"
                raise RuntimeError(f"{self._RESOLVER} failed: {detail}")
            self._context_address = result.value
        return self._context_address or None

    @property
    def cached_context_address(self) -> int | None:
        """Return the cached target structure address, if initialized."""

        return self._context_address

    def read(self) -> InstanceInfoStruct | None:
        """Read and decode the complete maintained structure layout."""

        address = self.resolve_address()
        if address is None:
            return None
        raw_context = self._reader.read(address, ctypes.sizeof(InstanceInfoStruct))
        return InstanceInfoStruct.from_buffer_copy(raw_context).bind_reader(
            self._reader
        )


def get() -> InstanceInfoStruct | None:
    """Read the ``InstanceInfo`` of the current selected client, if available."""

    from ..client import current_client

    client = current_client()
    return cast(Any, client.read_instance_info() if client is not None else None)
