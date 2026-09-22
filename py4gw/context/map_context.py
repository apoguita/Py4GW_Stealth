"""External read-only reader for the source-defined ``MapContext`` root.

This first slice follows the existing ``GameContext.map_context`` pointer and
reads the current fixed root, its three bounded spawn arrays, and the first
pathing context roots. Trapezoids, nodes, portals, and map-prop trees remain
unmigrated. This module does not create Reforged-style pathing snapshots or
caches.
"""

from __future__ import annotations

import ctypes
import struct
from dataclasses import dataclass
from ctypes import Structure, c_float, c_uint32
from typing import Protocol

from .game_context import GameContext, GameContextStruct
from .gw_array import GWArray, GWArrayValueView, GWBaseArray, RemoteMemoryReader


class _memory_reader(RemoteMemoryReader, Protocol):
    """The byte-reading operation needed by the external map reader."""


class MapVec2fStruct(Structure):
    """Two target-process single-precision coordinates."""

    _pack_ = 1
    _fields_ = [("x", c_float), ("y", c_float)]


@dataclass(frozen=True, slots=True)
class SpawnPoint:
    """A materialized map spawn entry from one native spawn array."""

    x: float
    y: float
    angle: float
    tag: str

    @property
    def map_id(self) -> int | None:
        """Return the numeric zone ID encoded by the spawn tag, if any."""

        return int(self.tag) if self.tag.isdigit() else None

    @property
    def is_default(self) -> bool:
        """Return whether this is the native ``0000`` fallback spawn."""

        return self.tag == "0000"


class SpawnEntryStruct(Structure):
    """The fixed-width x86 0x10-byte native spawn entry."""

    _pack_ = 1
    _fields_ = [
        ("x", c_float),
        ("y", c_float),
        ("angle", c_float),
        ("tag_raw", c_uint32),
    ]

    @property
    def tag(self) -> str:
        """Decode the source's big-endian FourCC spawn tag."""

        raw = struct.pack(">I", int(self.tag_raw))
        return "".join(chr(value) if 32 <= value < 127 else "" for value in raw)

    def snapshot(self) -> SpawnPoint:
        """Copy this target record into a small Python-owned value."""

        return SpawnPoint(float(self.x), float(self.y), float(self.angle), self.tag)


class PathingMapStruct(Structure):
    """The fixed-width source ``PathingMap`` context record.

    This is intentionally only the map-level context. Its trapezoid, node, and
    portal buffers are exposed as target addresses and counts; no graph is
    materialized here.
    """

    _pack_ = 1
    _fields_ = [
        ("zplane", c_uint32),
        ("h0004", c_uint32),
        ("h0008", c_uint32),
        ("h000C", c_uint32),
        ("h0010", c_uint32),
        ("trapezoid_count", c_uint32),
        ("trapezoids_ptr", c_uint32),
        ("sink_node_count", c_uint32),
        ("sink_nodes_ptr", c_uint32),
        ("x_node_count", c_uint32),
        ("x_nodes_ptr", c_uint32),
        ("y_node_count", c_uint32),
        ("y_nodes_ptr", c_uint32),
        ("h0034", c_uint32),
        ("h0038", c_uint32),
        ("portal_count", c_uint32),
        ("portals_ptr", c_uint32),
        ("root_node_ptr", c_uint32),
        ("h0048_ptr", c_uint32),
        ("h004C_ptr", c_uint32),
        ("h0050_ptr", c_uint32),
    ]

    @property
    def trapezoids_address(self) -> int | None:
        """Return the target trapezoid buffer address, if present."""

        return int(self.trapezoids_ptr) or None

    @property
    def portals_address(self) -> int | None:
        """Return the target portal buffer address, if present."""

        return int(self.portals_ptr) or None

    @property
    def sink_nodes_address(self) -> int | None:
        """Return the target sink-node buffer address, if present."""

        return int(self.sink_nodes_ptr) or None

    @property
    def x_nodes_address(self) -> int | None:
        """Return the target X-node buffer address, if present."""

        return int(self.x_nodes_ptr) or None

    @property
    def y_nodes_address(self) -> int | None:
        """Return the target Y-node buffer address, if present."""

        return int(self.y_nodes_ptr) or None

    @property
    def root_node_address(self) -> int | None:
        """Return the target pathing root-node address, if present."""

        return int(self.root_node_ptr) or None


class MapStaticDataStruct(Structure):
    """The fixed-width ``MapStaticData`` pathing context root."""

    _pack_ = 1
    _fields_ = [
        ("h0000", c_uint32 * 6),
        ("pmaps_array", GWArray),
        ("h0028", c_uint32 * 4),
        ("blocking_props", GWBaseArray),
        ("h0044", c_uint32 * 16),
        ("trapezoid_count", c_uint32),
        ("h0088", c_uint32),
        ("map_id", c_uint32),
        ("h0090", c_uint32 * 4),
    ]

    _remote_reader: _memory_reader | None = None
    _remote_address: int | None = None
    _max_pathing_maps = 32

    def bind_reader(
        self,
        reader: _memory_reader,
        address: int | None = None,
        max_pathing_maps: int = 32,
    ) -> MapStaticDataStruct:
        """Bind this current pathing root to the remote reader."""

        if max_pathing_maps <= 0:
            raise ValueError("max_pathing_maps must be positive")
        self._remote_reader = reader
        self._remote_address = address
        self._max_pathing_maps = max_pathing_maps
        return self

    @property
    def address(self) -> int | None:
        """Return the target address represented by this root."""

        return self._remote_address

    @property
    def pathing_map_sizes(self) -> tuple[int, int]:
        """Return the advertised pathing-map size and capacity."""

        return int(self.pmaps_array.m_size), int(self.pmaps_array.m_capacity)

    @property
    def pathing_maps(self) -> list[PathingMapStruct]:
        """Read bounded map-level records without traversing graph children."""

        if self._remote_reader is None:
            raise RuntimeError("MapStaticData root is not bound to a reader.")
        view = GWArrayValueView(self._remote_reader, self.pmaps_array, PathingMapStruct)
        if not view.valid():
            return []
        return [
            value
            for index in range(min(view.size(), self._max_pathing_maps))
            if (value := view.get(index)) is not None
        ]


class PathContextStruct(Structure):
    """The fixed-width Reforged ``PathContext`` root.

    The arrays and path nodes remain represented by their target headers and
    pointers. This first migration does not traverse or snapshot them.
    """

    _pack_ = 1
    _fields_ = [
        ("static_data_ptr", c_uint32),
        ("blocked_planes", GWBaseArray),
        ("path_nodes", GWBaseArray),
        ("node_cache", c_uint32 * 5),
        ("open_list", c_uint32 * 5),
        ("free_ipath_node", c_uint32 * 3),
        ("allocated_path_nodes", GWBaseArray),
        ("h005C", c_uint32),
        ("h0060", c_uint32),
        ("waypoints", GWArray),
        ("node_stack", GWArray),
        ("h0084", c_uint32 * 4),
    ]

    _remote_reader: _memory_reader | None = None
    _remote_address: int | None = None
    _max_pathing_maps = 32

    def bind_reader(
        self,
        reader: _memory_reader,
        address: int | None = None,
        max_pathing_maps: int = 32,
    ) -> PathContextStruct:
        """Bind this current pathing context to the remote reader."""

        if max_pathing_maps <= 0:
            raise ValueError("max_pathing_maps must be positive")
        self._remote_reader = reader
        self._remote_address = address
        self._max_pathing_maps = max_pathing_maps
        return self

    @property
    def address(self) -> int | None:
        """Return the target address represented by this context."""

        return self._remote_address

    @property
    def static_data_address(self) -> int | None:
        """Return the ``MapStaticData`` target address, if present."""

        return int(self.static_data_ptr) or None

    @property
    def static_data(self) -> MapStaticDataStruct | None:
        """Read the current ``MapStaticData`` root without child snapshots."""

        if self._remote_reader is None or self.static_data_address is None:
            return None
        address = self.static_data_address
        raw = self._remote_reader.read(address, ctypes.sizeof(MapStaticDataStruct))
        return MapStaticDataStruct.from_buffer_copy(raw).bind_reader(
            self._remote_reader,
            address,
            self._max_pathing_maps,
        )


class MapContextStruct(Structure):
    """The fixed-width x86 0x138-byte Reforged ``MapContext`` root.

    The native header names the first five words as ``map_boundaries`` while
    the Reforged Python layer interprets the same bytes as ``map_type``,
    ``start_pos``, and ``end_pos``.  Both views are exposed here so the
    difference is visible instead of silently choosing one interpretation.
    """

    _pack_ = 1
    _fields_ = [
        ("map_type", c_uint32),
        ("start_pos", MapVec2fStruct),
        ("end_pos", MapVec2fStruct),
        ("h0014", c_uint32 * 6),
        ("spawns1_array", GWArray),
        ("spawns2_array", GWArray),
        ("spawns3_array", GWArray),
        ("h005C", c_float * 6),
        ("path_ptr", c_uint32),
        ("path_engine_ptr", c_uint32),
        ("props_ptr", c_uint32),
        ("h0080", c_uint32),
        ("terrain", c_uint32),
        ("h0088", c_uint32),
        ("map_id", c_uint32),
        ("h0090", c_uint32 * 40),
        ("zones", c_uint32),
        ("h0134", c_uint32),
    ]

    _remote_reader: _memory_reader | None = None
    _remote_address: int | None = None
    _max_spawn_entries = 2048
    _max_pathing_maps = 32

    def bind_reader(
        self,
        reader: _memory_reader,
        address: int | None = None,
        max_spawn_entries: int = 2048,
        max_pathing_maps: int = 32,
    ) -> MapContextStruct:
        """Bind this current root view to the target reader and traversal bound."""

        if max_spawn_entries <= 0:
            raise ValueError("max_spawn_entries must be positive")
        if max_pathing_maps <= 0:
            raise ValueError("max_pathing_maps must be positive")
        self._remote_reader = reader
        self._remote_address = address
        self._max_spawn_entries = max_spawn_entries
        self._max_pathing_maps = max_pathing_maps
        return self

    @property
    def address(self) -> int | None:
        """Return the target address represented by this snapshot."""

        return self._remote_address

    @property
    def path_address(self) -> int | None:
        """Return the path-context pointer without traversing its graph."""

        return int(self.path_ptr) or None

    @property
    def props_address(self) -> int | None:
        """Return the map-props pointer without traversing its records."""

        return int(self.props_ptr) or None

    @property
    def terrain_address(self) -> int | None:
        """Return the native terrain pointer, if present."""

        return int(self.terrain) or None

    @property
    def zones_address(self) -> int | None:
        """Return the native zones pointer, if present."""

        return int(self.zones) or None

    @property
    def path_context(self) -> PathContextStruct | None:
        """Read the current ``PathContext`` root without graph traversal."""

        if self._remote_reader is None or self.path_address is None:
            return None
        address = self.path_address
        raw = self._remote_reader.read(address, ctypes.sizeof(PathContextStruct))
        return PathContextStruct.from_buffer_copy(raw).bind_reader(
            self._remote_reader,
            address,
            self._max_pathing_maps,
        )

    @property
    def map_boundaries(self) -> tuple[float, ...]:
        """Expose the native header's five-float boundary interpretation."""

        raw = bytes(self)[: ctypes.sizeof(c_float) * 5]
        return tuple(float(value) for value in struct.unpack("<5f", raw))

    @property
    def spawn_array_sizes(self) -> dict[str, int]:
        """Return spawn counts without reading any spawn records."""

        return {
            "spawns1": int(self.spawns1_array.m_size),
            "spawns2": int(self.spawns2_array.m_size),
            "spawns3": int(self.spawns3_array.m_size),
        }

    def _read_spawns(self, array: GWArray) -> list[SpawnPoint]:
        """Read one bounded value array and materialize its spawn points."""

        if self._remote_reader is None:
            raise RuntimeError("MapContext root view is not bound to a reader.")
        view = GWArrayValueView(
            self._remote_reader,
            array,
            SpawnEntryStruct,
        )
        if not view.valid():
            return []
        return [
            value.snapshot()
            for index in range(min(view.size(), self._max_spawn_entries))
            if (value := view.get(index)) is not None
        ]

    @property
    def spawns1(self) -> list[SpawnPoint]:
        """Read the bounded first native spawn array."""

        return self._read_spawns(self.spawns1_array)

    @property
    def spawns2(self) -> list[SpawnPoint]:
        """Read the bounded second native spawn array."""

        return self._read_spawns(self.spawns2_array)

    @property
    def spawns3(self) -> list[SpawnPoint]:
        """Read the bounded third native spawn array."""

        return self._read_spawns(self.spawns3_array)


assert ctypes.sizeof(MapVec2fStruct) == 0x08
assert ctypes.sizeof(SpawnEntryStruct) == 0x10
assert ctypes.sizeof(PathingMapStruct) == 0x54
assert ctypes.sizeof(MapStaticDataStruct) == 0xA0
assert ctypes.sizeof(PathContextStruct) == 0x94
assert ctypes.sizeof(MapContextStruct) == 0x138
assert MapStaticDataStruct.pmaps_array.offset == 0x18
assert PathContextStruct.static_data_ptr.offset == 0x00
assert MapContextStruct.spawns1_array.offset == 0x2C
assert MapContextStruct.path_ptr.offset == 0x74
assert MapContextStruct.props_ptr.offset == 0x7C
assert MapContextStruct.map_id.offset == 0x8C
assert MapContextStruct.zones.offset == 0x130


class MapContext:
    """Resolve and read the current external ``MapContext`` root."""

    def __init__(self, reader: _memory_reader, game_context: GameContext) -> None:
        """Create a reader using the selected client's GameContext."""

        self._reader = reader
        self._game_context = game_context

    def resolve_address(self) -> int | None:
        """Return the current map-context address, if available."""

        game_address = self._game_context.resolve_address()
        raw_pointer = self._reader.read(
            game_address + GameContextStruct.map_context.offset,
            ctypes.sizeof(c_uint32),
        )
        address = int.from_bytes(raw_pointer, "little")
        return address or None

    def read(
        self,
        max_spawn_entries: int = 2048,
        max_pathing_maps: int = 32,
    ) -> MapContextStruct | None:
        """Read the current fixed root and bind bounded spawn-array views."""

        address = self.resolve_address()
        if address is None:
            return None
        raw_context = self._reader.read(address, ctypes.sizeof(MapContextStruct))
        return MapContextStruct.from_buffer_copy(raw_context).bind_reader(
            self._reader,
            address,
            max_spawn_entries,
            max_pathing_maps,
        )


def get() -> MapContextStruct | None:
    """Read the current client's map context, if one is available."""

    from ..client import current_client

    client = current_client()
    return client.read_map_context() if client is not None else None


__all__ = [
    "MapContext",
    "MapContextStruct",
    "MapStaticDataStruct",
    "MapVec2fStruct",
    "PathContextStruct",
    "PathingMapStruct",
    "SpawnEntryStruct",
    "SpawnPoint",
]
