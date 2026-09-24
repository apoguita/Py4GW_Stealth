"""External read-only reader for the source-defined ``MapContext`` root.

This reader follows the existing ``GameContext.map_context`` pointer and reads
the fixed root, spawn arrays, pathing records and safe source-defined links,
and the reachable props arrays. It also provides Reforged-named facade helpers
and pathing caches while keeping each cache scoped to one connected process.
"""

from __future__ import annotations

from ..helpers.target_struct import TargetStruct

import ctypes
import struct
from dataclasses import dataclass
from ctypes import Structure, c_float, c_uint8, c_uint16, c_uint32
from typing import Any, Protocol, TypeVar, cast

from .game_context import GameContext, GameContextStruct
from .gw_array import GWArray, GWArrayValueView, GWBaseArray, GWArrayView, RemoteMemoryReader
from .gw_list import GWLinkStruct, GWListStruct


class _memory_reader(RemoteMemoryReader, Protocol):
    """The byte-reading operation needed by the external map reader."""


_structure_type = TypeVar("_structure_type", bound=Structure)


def _read_struct(
    reader: _memory_reader | None,
    address: int,
    structure_type: type[_structure_type],
) -> _structure_type:
    """Read one fixed-width x86 structure from a validated target address."""

    if address < 0x10000 or address + ctypes.sizeof(structure_type) > 0x1_0000_0000:
        raise ValueError(f"Invalid x86 structure address 0x{address:08X}.")
    if reader is None:
        raise RuntimeError("Remote structure is not bound to a reader.")
    return cast(
        _structure_type,
        structure_type.from_buffer_copy(reader.read(address, ctypes.sizeof(structure_type))),
    )


def _read_node(reader: _memory_reader | None, address: int) -> NodeStruct | None:
    """Read one source ``NodeStruct`` pointer, preserving null as ``None``."""

    if address == 0:
        return None
    return _read_struct(reader, address, NodeStruct)


def _read_trapezoid(
    reader: _memory_reader | None, address: int, max_linked_entries: int
) -> PathingTrapezoidStruct | None:
    """Read one source trapezoid pointer, preserving null as ``None``."""

    if address == 0:
        return None
    return _read_struct(reader, address, PathingTrapezoidStruct).bind_reader(
        cast(_memory_reader, reader), max_linked_entries
    )


def _read_uint32_pointer(reader: _memory_reader | None, address: int) -> int | None:
    """Read one source ``uint32_t*`` helper value, preserving null as ``None``."""

    if address == 0:
        return None
    if address < 0x10000 or address + 4 > 0x1_0000_0000:
        raise ValueError(f"Invalid x86 uint32 address 0x{address:08X}.")
    if reader is None:
        raise RuntimeError("Remote value is not bound to a reader.")
    return int.from_bytes(reader.read(address, 4), "little")


class MapVec2fStruct(TargetStruct):
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


@dataclass(slots=True)
class PathingTrapezoid:
    """Python-owned source snapshot of one pathing trapezoid."""

    id: int
    portal_left: int
    portal_right: int
    XTL: float
    XTR: float
    YT: float
    XBL: float
    XBR: float
    YB: float
    neighbor_ids: list[int]


@dataclass(slots=True)
class Node:
    """Python-owned source snapshot of the common pathing-node fields."""

    type: int
    id: int


@dataclass(slots=True)
class SinkNode:
    """Python-owned source snapshot of one sink node."""

    type: int
    id: int
    trapezoid_ids: list[int]


@dataclass(slots=True)
class XNode:
    """Python-owned source snapshot of one X-split node."""

    type: int
    id: int
    pos: MapVec2fStruct
    dir: MapVec2fStruct
    left_id: int | None
    right_id: int | None


@dataclass(slots=True)
class YNode:
    """Python-owned source snapshot of one Y-split node."""

    type: int
    id: int
    pos: MapVec2fStruct
    left_id: int | None
    right_id: int | None


@dataclass(slots=True)
class Portal:
    """Python-owned source snapshot of one pathing portal."""

    left_layer_id: int
    right_layer_id: int
    flags: int
    pair_index: int
    count: int
    trapezoid_indices: list[int]


@dataclass(slots=True)
class PathingMap:
    """Python-owned source snapshot of a pathing-map plane."""

    zplane: int
    h0004: int
    h0008: int
    h000C: int
    h0010: int
    trapezoid_count: int
    sink_node_count: int
    x_node_count: int
    y_node_count: int
    portal_count: int
    trapezoids: list[PathingTrapezoid]
    sink_nodes: list[SinkNode]
    x_nodes: list[XNode]
    y_nodes: list[YNode]
    portals: list[Portal]
    h0034: int
    h0038: int
    root_node: Node
    root_node_id: int
    h0048: int | None
    h004C: int | None
    h0050: int | None


@dataclass(slots=True)
class TravelPortal:
    """Source travel-portal result containing world position and model ID."""

    x: float
    y: float
    z: float
    model_file_id: int


_PORTAL_MODEL_FILE_IDS = {
    0x4E6B2: "EotN Asura Gate",
    0x3C5AC: "EotN/Nightfall",
    0x0A825: "Prophecies/Factions",
}


def _file_hash_to_file_id(reader: _memory_reader, hash_address: int) -> int:
    """Reproduce the source file-hash conversion using bounded remote reads."""

    if hash_address < 0x10000 or hash_address + 6 > 0x1_0000_0000:
        return 0
    word_0, word_1, word_2 = struct.unpack("<3H", reader.read(hash_address, 6))
    word_3 = 0
    if word_2 != 0:
        if hash_address + 8 > 0x1_0000_0000:
            return 0
        word_3 = int.from_bytes(reader.read(hash_address + 6, 2), "little")
    if not (
        word_0 > 0xFF
        and word_1 > 0xFF
        and (word_2 == 0 or (word_2 > 0xFF and word_3 == 0))
    ):
        return 0
    temp = (word_0 - 0xFF00FF) & 0xFFFFFFFF
    return (temp + word_1 * 0xFF00) & 0xFFFFFFFF


def _get_prop_model_file_id(prop: MapPropStruct, reader: _memory_reader) -> int:
    """Follow the source ``h0034[4] -> sub[1] -> file hash`` pointer chain."""

    pointer = int(prop.h0034[4])
    if pointer < 0x10000 or pointer + 8 > 0x1_0000_0000:
        return 0
    try:
        hash_pointer = int.from_bytes(reader.read(pointer + 4, 4), "little")
        return _file_hash_to_file_id(reader, hash_pointer)
    except Exception:
        return 0


class SpawnEntryStruct(TargetStruct):
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


class MapVec3fStruct(TargetStruct):
    """Three target-process single-precision coordinates."""

    _pack_ = 1
    _fields_ = [("x", c_float), ("y", c_float), ("z", c_float)]


class PathingTrapezoidStruct(TargetStruct):
    """The native 0x30 pathing-trapezoid record."""

    _pack_ = 1
    _fields_ = [
        ("id", c_uint32),
        ("adjacent_ptr", c_uint32 * 4),
        ("portal_left", c_uint16),
        ("portal_right", c_uint16),
        ("XTL", c_float),
        ("XTR", c_float),
        ("YT", c_float),
        ("XBL", c_float),
        ("XBR", c_float),
        ("YB", c_float),
    ]

    _remote_reader: _memory_reader | None = None
    _max_linked_entries = 100_000

    def bind_reader(
        self, reader: _memory_reader, max_linked_entries: int = 100_000
    ) -> PathingTrapezoidStruct:
        """Bind this record for source-defined adjacent-pointer reads."""

        if max_linked_entries <= 0:
            raise ValueError("max_linked_entries must be positive")
        self._remote_reader = reader
        self._max_linked_entries = max_linked_entries
        return self

    def _read_adjacent(self, pointer: int) -> PathingTrapezoidStruct | None:
        if pointer == 0:
            return None
        if pointer < 0x10000 or pointer + ctypes.sizeof(self) > 0x1_0000_0000:
            raise ValueError(f"Invalid x86 trapezoid address 0x{pointer:08X}.")
        if self._remote_reader is None:
            raise RuntimeError("PathingTrapezoid record is not bound to a reader.")
        raw = self._remote_reader.read(pointer, ctypes.sizeof(PathingTrapezoidStruct))
        return PathingTrapezoidStruct.from_buffer_copy(raw).bind_reader(
            self._remote_reader, self._max_linked_entries
        )

    @property
    def adjacent(self) -> list[PathingTrapezoidStruct | None]:
        """Read the four source-defined neighboring trapezoid pointers."""

        return [self._read_adjacent(int(pointer)) for pointer in self.adjacent_ptr]

    @property
    def neighbor_ids(self) -> list[int]:
        """Return IDs for non-null neighbors in source pointer order."""

        return [neighbor.id for neighbor in self.adjacent if neighbor is not None]

    def snapshot(self) -> PathingTrapezoid:
        """Copy this record using the source Python snapshot fields."""

        return PathingTrapezoid(
            id=int(self.id),
            portal_left=int(self.portal_left),
            portal_right=int(self.portal_right),
            XTL=float(self.XTL),
            XTR=float(self.XTR),
            YT=float(self.YT),
            XBL=float(self.XBL),
            XBR=float(self.XBR),
            YB=float(self.YB),
            neighbor_ids=self.neighbor_ids,
        )


class NodeStruct(TargetStruct):
    """The native 0x08 base record for pathing nodes."""

    _pack_ = 1
    _fields_ = [("type", c_uint32), ("id", c_uint32)]

    def snapshot(self) -> Node:
        """Copy the common node fields into the source value record."""

        return Node(type=int(self.type), id=int(self.id))


class SinkNodeStruct(NodeStruct):
    """The source 0x0C record containing a trapezoid pointer-to-pointer."""

    _pack_ = 1
    _fields_ = [("trapezoid_ptr_ptr", c_uint32)]

    _remote_reader: _memory_reader | None = None
    _max_linked_entries = 100_000

    def bind_reader(
        self,
        reader: _memory_reader,
        max_linked_entries: int = 100_000,
    ) -> SinkNodeStruct:
        """Bind the reader used to follow the source pointer/list fields."""

        if max_linked_entries <= 0:
            raise ValueError("max_linked_entries must be positive")
        self._remote_reader = reader
        self._max_linked_entries = max_linked_entries
        return self

    @property
    def trapezoid(self) -> PathingTrapezoidStruct | None:
        """Dereference the source ``PathingTrapezoid**`` once to one record."""

        pointer_to_pointer = int(self.trapezoid_ptr_ptr)
        if pointer_to_pointer == 0:
            return None
        trapezoid_address = _read_uint32_pointer(self._remote_reader, pointer_to_pointer)
        if not trapezoid_address:
            return None
        return _read_trapezoid(
            self._remote_reader, trapezoid_address, self._max_linked_entries
        )

    @property
    def trapezoid_ids(self) -> list[int]:
        """Read trapezoid IDs from the source null-terminated pointer list."""

        pointer_array = int(self.trapezoid_ptr_ptr)
        if pointer_array == 0:
            return []
        if self._remote_reader is None:
            raise RuntimeError("SinkNode is not bound to a memory reader.")
        result: list[int] = []
        for index in range(self._max_linked_entries + 1):
            entry_address = pointer_array + index * ctypes.sizeof(c_uint32)
            trapezoid_address = _read_uint32_pointer(self._remote_reader, entry_address)
            if not trapezoid_address:
                return result
            if index == self._max_linked_entries:
                break
            trapezoid = _read_trapezoid(
                self._remote_reader, trapezoid_address, self._max_linked_entries
            )
            if trapezoid is not None:
                result.append(int(trapezoid.id))
        raise ValueError(
            "SinkNode trapezoid pointer list has no null terminator within "
            f"max_linked_entries={self._max_linked_entries}."
        )

    def snapshot_sinknode(self) -> SinkNode:
        """Copy this node and its source trapezoid-ID list."""

        return SinkNode(
            type=int(self.type), id=int(self.id), trapezoid_ids=self.trapezoid_ids
        )


class XNodeStruct(NodeStruct):
    """The native 0x20 X-split pathing-node record."""

    _pack_ = 1
    _fields_ = [
        ("pos", MapVec2fStruct),
        ("dir", MapVec2fStruct),
        ("left_ptr", c_uint32),
        ("right_ptr", c_uint32),
    ]

    _remote_reader: _memory_reader | None = None

    def bind_reader(self, reader: _memory_reader) -> XNodeStruct:
        """Bind this node for source-defined child-pointer reads."""

        self._remote_reader = reader
        return self

    def _read_node(self, address: int) -> NodeStruct | None:
        return _read_node(self._remote_reader, address)

    @property
    def left(self) -> NodeStruct | None:
        """Read the node referenced by the source ``left`` pointer."""

        return self._read_node(int(self.left_ptr))

    @property
    def right(self) -> NodeStruct | None:
        """Read the node referenced by the source ``right`` pointer."""

        return self._read_node(int(self.right_ptr))

    def snapshot_xnode(self) -> XNode:
        """Copy this X-node and the IDs of its source-linked child nodes."""

        left = self.left
        right = self.right
        return XNode(
            type=int(self.type),
            id=int(self.id),
            pos=MapVec2fStruct.from_buffer_copy(bytes(self.pos)),
            dir=MapVec2fStruct.from_buffer_copy(bytes(self.dir)),
            left_id=int(left.id) if left is not None else None,
            right_id=int(right.id) if right is not None else None,
        )


class YNodeStruct(NodeStruct):
    """The native 0x18 Y-split pathing-node record."""

    _pack_ = 1
    _fields_ = [
        ("pos", MapVec2fStruct),
        ("left_ptr", c_uint32),
        ("right_ptr", c_uint32),
    ]

    _remote_reader: _memory_reader | None = None

    def bind_reader(self, reader: _memory_reader) -> YNodeStruct:
        """Bind this node for source-defined child-pointer reads."""

        self._remote_reader = reader
        return self

    def _read_node(self, address: int) -> NodeStruct | None:
        return _read_node(self._remote_reader, address)

    @property
    def left(self) -> NodeStruct | None:
        """Read the node referenced by the source ``left`` pointer."""

        return self._read_node(int(self.left_ptr))

    @property
    def right(self) -> NodeStruct | None:
        """Read the node referenced by the source ``right`` pointer."""

        return self._read_node(int(self.right_ptr))

    def snapshot_ynode(self) -> YNode:
        """Copy this Y-node and the IDs of its source-linked child nodes."""

        left = self.left
        right = self.right
        return YNode(
            type=int(self.type),
            id=int(self.id),
            pos=MapVec2fStruct.from_buffer_copy(bytes(self.pos)),
            left_id=int(left.id) if left is not None else None,
            right_id=int(right.id) if right is not None else None,
        )


class PortalStruct(TargetStruct):
    """The native 0x14 pathing portal record."""

    _pack_ = 1
    _fields_ = [
        ("left_layer_id", c_uint16),
        ("right_layer_id", c_uint16),
        ("flags", c_uint32),
        ("pair_ptr", c_uint32),
        ("count", c_uint32),
        ("trapezoids_ptr_ptr", c_uint32),
    ]

    @property
    def h0004(self) -> int:
        """Expose the native C++ spelling for the Python ``flags`` word."""

        return int(self.flags)

    _remote_reader: _memory_reader | None = None
    _max_linked_entries = 100_000

    def bind_reader(
        self, reader: _memory_reader, max_linked_entries: int = 100_000
    ) -> PortalStruct:
        """Bind this record for source-defined portal/trapezoid pointers."""

        if max_linked_entries <= 0:
            raise ValueError("max_linked_entries must be positive")
        self._remote_reader = reader
        self._max_linked_entries = max_linked_entries
        return self

    @property
    def pair(self) -> PortalStruct | None:
        """Read the paired portal record, if its pointer is non-null."""

        address = int(self.pair_ptr)
        if address == 0:
            return None
        if self._remote_reader is None:
            raise RuntimeError("Portal record is not bound to a reader.")
        return _read_struct(self._remote_reader, address, PortalStruct).bind_reader(
            self._remote_reader, self._max_linked_entries
        )

    @property
    def trapezoids(self) -> PathingTrapezoidStruct | None:
        """Read the first trapezoid through the source pointer-to-pointer."""

        pointer_array = int(self.trapezoids_ptr_ptr)
        if pointer_array == 0:
            return None
        if self._remote_reader is None:
            raise RuntimeError("Portal record is not bound to a reader.")
        raw = self._remote_reader.read(pointer_array, 4)
        return _read_trapezoid(
            self._remote_reader,
            int.from_bytes(raw, "little"),
            self._max_linked_entries,
        )

    @property
    def trapezoid_indices(self) -> list[int]:
        """Read the source-counted pointer array and return non-null IDs."""

        pointer_array = int(self.trapezoids_ptr_ptr)
        count = int(self.count)
        if pointer_array == 0 or count == 0:
            return []
        if count > self._max_linked_entries:
            raise ValueError(
                f"Portal trapezoid count {count} exceeds max_linked_entries "
                f"{self._max_linked_entries}."
            )
        if self._remote_reader is None:
            raise RuntimeError("Portal record is not bound to a reader.")
        byte_count = count * 4
        if pointer_array < 0x10000 or pointer_array + byte_count > 0x1_0000_0000:
            raise ValueError("Portal trapezoid pointer array is outside x86 address space.")
        raw = self._remote_reader.read(pointer_array, byte_count)
        addresses = struct.unpack(f"<{count}I", raw)
        result: list[int] = []
        for address in addresses:
            trapezoid = _read_trapezoid(
                self._remote_reader, address, self._max_linked_entries
            )
            if trapezoid is not None:
                result.append(int(trapezoid.id))
        return result

    def snapshot(self) -> Portal:
        """Copy this portal, leaving paired-index resolution to its map."""

        return Portal(
            left_layer_id=int(self.left_layer_id),
            right_layer_id=int(self.right_layer_id),
            flags=int(self.flags),
            pair_index=0xFFFFFFFF,
            count=int(self.count),
            trapezoid_indices=self.trapezoid_indices,
        )


class PropModelInfoStruct(TargetStruct):
    """The native 0x18 prop-model metadata record."""

    _pack_ = 1
    _fields_ = [
        ("h0000", c_uint32),
        ("h0004", c_uint32),
        ("h0008", c_uint32),
        ("h000C", c_uint32),
        ("h0010", c_uint32),
        ("h0014", c_uint32),
    ]


class RecObjectStruct(TargetStruct):
    """The native 0x0C resource-object record."""

    _pack_ = 1
    _fields_ = [
        ("h0000", c_uint32),
        ("h0004", c_uint32),
        ("accessKey", c_uint32),
    ]


class PropByTypeStruct(TargetStruct):
    """The native 0x08 prop lookup record."""

    _pack_ = 1
    _fields_ = [("object_id", c_uint32), ("prop_index", c_uint32)]


class MapPropStruct(TargetStruct):
    """The native 0x90 map-prop record, with external pointer fields."""

    _pack_ = 1
    _fields_ = [
        ("h0000", c_uint32 * 5),
        ("uptime_seconds", c_uint32),
        ("h0018", c_uint32),
        ("prop_index", c_uint32),
        ("position", MapVec3fStruct),
        ("model_file_id", c_uint32),
        ("h0030", c_uint32 * 2),
        ("rotation_angle", c_float),
        ("rotation_cos", c_float),
        ("rotation_sin", c_float),
        ("h0034", c_uint32 * 5),
        ("interactive_model_ptr", c_uint32),
        ("h005C", c_uint32 * 4),
        ("appearance_bitmap", c_uint32),
        ("animation_bits", c_uint32),
        ("h0064", c_uint32 * 5),
        ("prop_object_info_ptr", c_uint32),
        ("h008C", c_uint32),
    ]

    _remote_reader: _memory_reader | None = None

    def bind_reader(
        self, reader: _memory_reader, address: int | None = None
    ) -> MapPropStruct:
        """Bind this prop record for its source-defined pointer properties."""

        self._remote_reader = reader
        return self

    @property
    def interactive_model(self) -> RecObjectStruct | None:
        """Read the resource object referenced by ``interactive_model_ptr``."""

        address = int(self.interactive_model_ptr)
        if address == 0:
            return None
        return _read_struct(self._remote_reader, address, RecObjectStruct)

    @property
    def prop_object_info(self) -> PropByTypeStruct | None:
        """Read the prop lookup record referenced by ``prop_object_info_ptr``."""

        address = int(self.prop_object_info_ptr)
        if address == 0:
            return None
        return _read_struct(self._remote_reader, address, PropByTypeStruct)


class PropsContextStruct(TargetStruct):
    """The native 0x1A4 map-props context header."""

    _pack_ = 1
    _fields_ = [
        ("pad1", c_uint32 * 0x1B),
        ("propsByType_array", GWArray),
        ("h007C", c_uint32 * 0x0A),
        ("propModels_array", GWArray),
        ("h00B4", c_uint32 * 0x38),
        ("propArray_array", GWArray),
    ]

    _remote_reader: _memory_reader | None = None
    _remote_address: int | None = None
    _max_prop_entries = 100_000
    _max_prop_list_entries = 100_000

    def bind_reader(
        self,
        reader: _memory_reader,
        address: int | None = None,
        max_prop_entries: int = 100_000,
        max_prop_list_entries: int = 100_000,
    ) -> PropsContextStruct:
        """Bind this header for bounded reads of its source arrays and lists."""

        if max_prop_entries <= 0 or max_prop_list_entries <= 0:
            raise ValueError("PropsContext read limits must be positive")
        self._remote_reader = reader
        self._remote_address = address
        self._max_prop_entries = max_prop_entries
        self._max_prop_list_entries = max_prop_list_entries
        return self

    @property
    def address(self) -> int | None:
        """Return the target address represented by this context header."""

        return self._remote_address

    def _array_values(
        self, array: GWArray, record_type: type[_structure_type]
    ) -> list[_structure_type]:
        if self._remote_reader is None:
            raise RuntimeError("PropsContext is not bound to a reader.")
        view = GWArrayValueView(self._remote_reader, array, record_type)
        if view.size() > view.capacity() or (view.size() and not int(array.m_buffer)):
            raise ValueError("PropsContext array header has invalid size, capacity, or buffer.")
        if not view.valid():
            return []
        if view.size() > self._max_prop_entries:
            raise ValueError(
                f"PropsContext array size {view.size()} exceeds max_prop_entries "
                f"{self._max_prop_entries}."
            )
        result: list[_structure_type] = []
        for index in range(view.size()):
            value = view.get(index)
            if value is not None:
                result.append(cast(_structure_type, value))
        return result

    @property
    def props_by_type(self) -> list[list[PropByTypeStruct]]:
        """Read each source ``TList<PropByType>`` group in array order."""

        headers = self._array_values(self.propsByType_array, GWListStruct)
        if self._remote_reader is None:
            raise RuntimeError("PropsContext is not bound to a reader.")
        if not headers:
            return []
        groups: list[list[PropByTypeStruct]] = []
        for header in headers:
            groups.append(self._read_prop_type_group(header))
        return groups

    def _read_prop_type_group(
        self, header: GWListStruct
    ) -> list[PropByTypeStruct]:
        """Walk one source list, raising rather than hiding broken or long lists."""

        if self._remote_reader is None:
            raise RuntimeError("PropsContext is not bound to a reader.")
        next_node = int(header.link.next_node)
        link_offset = int(header.offset)
        visited: set[int] = set()
        result: list[PropByTypeStruct] = []
        for _ in range(self._max_prop_list_entries):
            if next_node == 0 or next_node & 1:
                return result
            node_address = next_node & ~1
            if node_address < 0x10000 or node_address + ctypes.sizeof(PropByTypeStruct) > 0x1_0000_0000:
                raise ValueError(f"Invalid x86 PropByType address 0x{node_address:08X}.")
            if node_address in visited:
                raise ValueError("PropsContext PropByType list contains a repeated node.")
            visited.add(node_address)
            result.append(
                PropByTypeStruct.from_buffer_copy(
                    self._remote_reader.read(node_address, ctypes.sizeof(PropByTypeStruct))
                )
            )
            next_link_address = node_address + link_offset
            if next_link_address + ctypes.sizeof(GWLinkStruct) > 0x1_0000_0000:
                raise ValueError("PropByType list link exceeds the x86 address space.")
            raw_link = self._remote_reader.read(next_link_address, ctypes.sizeof(GWLinkStruct))
            next_node = int(GWLinkStruct.from_buffer_copy(raw_link).next_node)
        raise ValueError(
            "PropsContext PropByType list reached max_prop_list_entries without its source terminator."
        )

    @property
    def prop_models(self) -> list[PropModelInfoStruct]:
        """Read the source contiguous array of prop-model records."""

        return self._array_values(self.propModels_array, PropModelInfoStruct)

    @property
    def props(self) -> list[MapPropStruct]:
        """Read the source pointer array of map-prop records."""

        if self._remote_reader is None:
            raise RuntimeError("PropsContext is not bound to a reader.")
        view = GWArrayView(self._remote_reader, self.propArray_array, MapPropStruct)
        if view.size() > view.capacity() or (view.size() and not int(self.propArray_array.m_buffer)):
            raise ValueError("PropsContext prop array header has invalid size, capacity, or buffer.")
        if not view.valid():
            return []
        if view.size() > self._max_prop_entries:
            raise ValueError(
                f"PropsContext array size {view.size()} exceeds max_prop_entries "
                f"{self._max_prop_entries}."
            )
        result = view.to_list()
        return [value.bind_reader(self._remote_reader) for value in result]


class BlockingPropStruct(TargetStruct):
    """The native 0x0C collision-only blocking-prop record."""

    _pack_ = 1
    _fields_ = [("pos", MapVec2fStruct), ("radius", c_float)]


class NativePathingTrapezoidStruct(TargetStruct):
    """C++-named view of the same 0x30 pathing-trapezoid record."""

    _pack_ = 1
    _fields_ = [
        ("id", c_uint32),
        ("adjacent", c_uint32 * 4),
        ("portal_left", c_uint16),
        ("portal_right", c_uint16),
        ("XTL", c_float),
        ("XTR", c_float),
        ("YT", c_float),
        ("XBL", c_float),
        ("XBR", c_float),
        ("YB", c_float),
    ]


class NativeSinkNodeStruct(NodeStruct):
    """C++-named view of the native sink-node pointer field."""

    _pack_ = 1
    _fields_ = [("trapezoid", c_uint32)]


class NativeXNodeStruct(NodeStruct):
    """C++-named view of the native X-node pointer fields."""

    _pack_ = 1
    _fields_ = [
        ("pos", MapVec2fStruct),
        ("dir", MapVec2fStruct),
        ("left", c_uint32),
        ("right", c_uint32),
    ]


class NativeYNodeStruct(NodeStruct):
    """C++-named view of the native Y-node pointer fields."""

    _pack_ = 1
    _fields_ = [
        ("pos", MapVec2fStruct),
        ("left", c_uint32),
        ("right", c_uint32),
    ]


class NativePortalStruct(TargetStruct):
    """C++-named view of the same 0x14 pathing-portal record."""

    _pack_ = 1
    _fields_ = [
        ("left_layer_id", c_uint16),
        ("right_layer_id", c_uint16),
        ("h0004", c_uint32),
        ("pair", c_uint32),
        ("count", c_uint32),
        ("trapezoids", c_uint32),
    ]


class NativePathingMapStruct(TargetStruct):
    """C++-named view of the same 0x54 pathing-map record."""

    _pack_ = 1
    _fields_ = [
        ("zplane", c_uint32),
        ("h0004", c_uint32),
        ("h0008", c_uint32),
        ("h000C", c_uint32),
        ("h0010", c_uint32),
        ("trapezoid_count", c_uint32),
        ("trapezoids", c_uint32),
        ("sink_node_count", c_uint32),
        ("sink_nodes", c_uint32),
        ("x_node_count", c_uint32),
        ("x_nodes", c_uint32),
        ("y_node_count", c_uint32),
        ("y_nodes", c_uint32),
        ("h0034", c_uint32),
        ("h0038", c_uint32),
        ("portal_count", c_uint32),
        ("portals", c_uint32),
        ("root_node", c_uint32),
        ("h0048", c_uint32),
        ("h004C", c_uint32),
        ("h0050", c_uint32),
    ]


class NativeMapPropStruct(TargetStruct):
    """C++-named view of the native 0x90 map-prop record."""

    _pack_ = 1
    _fields_ = [
        ("h0000", c_uint32 * 5),
        ("uptime_seconds", c_uint32),
        ("h0018", c_uint32),
        ("prop_index", c_uint32),
        ("position", MapVec3fStruct),
        ("model_file_id", c_uint32),
        ("h0030", c_uint32 * 2),
        ("rotation_angle", c_float),
        ("rotation_cos", c_float),
        ("rotation_sin", c_float),
        ("h0034", c_uint32 * 5),
        ("interactive_model", c_uint32),
        ("h005C", c_uint32 * 4),
        ("appearance_bitmap", c_uint32),
        ("animation_bits", c_uint32),
        ("h0064", c_uint32 * 5),
        ("prop_object_info", c_uint32),
        ("h008C", c_uint32),
    ]


class NativePropsContextStruct(TargetStruct):
    """C++-named view of the native 0x1A4 map-props context."""

    _pack_ = 1
    _fields_ = [
        ("pad1", c_uint32 * 0x1B),
        ("propsByType", GWArray),
        ("h007C", c_uint32 * 0x0A),
        ("propModels", GWArray),
        ("h00B4", c_uint32 * 0x38),
        ("propArray", GWArray),
    ]


class NativeMapContextSub2Struct(TargetStruct):
    """Native nested map subcontext containing the pathing-map array."""

    _pack_ = 1
    _fields_ = [("pad1", c_uint32 * 6), ("pmaps", GWArray)]


class NativeMapContextSub1Struct(TargetStruct):
    """Native nested map subcontext as declared in ``map.h``."""

    _pack_ = 1
    _fields_ = [
        ("sub2", c_uint32),
        ("pathing_map_block", GWArray),
        ("total_trapezoid_count", c_uint32),
        ("h0014", c_uint32 * 0x12),
        ("something_else_for_props", GWArray),
    ]


class NativeMapContextPrefixStruct(TargetStruct):
    """The exact native ``MapContext`` fields declared through offset 0x134.

    The native header does not define a complete size for this root. This
    prefix preserves only its declared fields; the Reforged Python root remains
    separately represented by :class:`MapContextStruct`.
    """

    _pack_ = 1
    _fields_ = [
        ("map_boundaries", c_float * 5),
        ("h0014", c_uint32 * 6),
        ("spawns1", GWArray),
        ("spawns2", GWArray),
        ("spawns3", GWArray),
        ("h005C", c_float * 6),
        ("sub1", c_uint32),
        ("pad1", c_uint8 * 4),
        ("props", c_uint32),
        ("h0080", c_uint32),
        ("terrain", c_uint32),
        ("h0088", c_uint32 * 42),
        ("zones", c_uint32),
    ]


class PathingMapStruct(TargetStruct):
    """The fixed-width source ``PathingMap`` context record.

    Child buffers are read as bounded contiguous arrays. Source-defined links
    are read lazily through the bound external memory reader.
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

    _remote_reader: _memory_reader | None = None
    _remote_address: int | None = None
    _max_pathing_entries = 100_000

    def bind_reader(
        self,
        reader: _memory_reader,
        address: int | None = None,
        max_pathing_entries: int = 100_000,
    ) -> PathingMapStruct:
        """Bind this record so its source arrays can be read externally."""

        if max_pathing_entries <= 0:
            raise ValueError("max_pathing_entries must be positive")
        self._remote_reader = reader
        self._remote_address = address
        self._max_pathing_entries = max_pathing_entries
        return self

    def _read_records(
        self,
        address: int,
        count: int,
        record_type: type[_structure_type],
    ) -> list[_structure_type]:
        """Read a whole source array unless its count exceeds the safety cap."""

        if count <= 0:
            return []
        if address < 0x10000:
            raise ValueError(
                f"Pathing array has {count} entries but an invalid buffer address "
                f"0x{address:08X}."
            )
        if self._remote_reader is None:
            raise RuntimeError("PathingMap record is not bound to a reader.")
        if count > self._max_pathing_entries:
            raise ValueError(
                f"Pathing array count {count} exceeds the configured safety cap "
                f"of {self._max_pathing_entries}."
            )
        bounded_count = count
        record_size = ctypes.sizeof(record_type)
        byte_count = bounded_count * record_size
        if address + byte_count > 0x1_0000_0000:
            raise ValueError("Pathing array extends beyond the x86 address space.")
        raw = self._remote_reader.read(address, byte_count)
        return [
            cast(_structure_type, record_type.from_buffer_copy(
                raw[index * record_size : (index + 1) * record_size]
            ))
            for index in range(bounded_count)
        ]

    @property
    def trapezoids(self) -> list[PathingTrapezoidStruct]:
        """Read the bounded contiguous trapezoid array."""

        reader = self._require_reader()
        return [
            value.bind_reader(reader, self._max_pathing_entries)
            for value in self._read_records(
                int(self.trapezoids_ptr), int(self.trapezoid_count), PathingTrapezoidStruct
            )
        ]

    @property
    def sink_nodes(self) -> list[SinkNodeStruct]:
        """Read sink nodes and bind their source pointer/list reader."""

        reader = self._require_reader()
        return [
            value.bind_reader(reader, self._max_pathing_entries)
            for value in self._read_records(
                int(self.sink_nodes_ptr), int(self.sink_node_count), SinkNodeStruct
            )
        ]

    @property
    def x_nodes(self) -> list[XNodeStruct]:
        """Read the bounded contiguous X-node array."""

        reader = self._require_reader()
        return [
            value.bind_reader(reader)
            for value in self._read_records(
                int(self.x_nodes_ptr), int(self.x_node_count), XNodeStruct
            )
        ]

    @property
    def y_nodes(self) -> list[YNodeStruct]:
        """Read the bounded contiguous Y-node array."""

        reader = self._require_reader()
        return [
            value.bind_reader(reader)
            for value in self._read_records(
                int(self.y_nodes_ptr), int(self.y_node_count), YNodeStruct
            )
        ]

    @property
    def portals(self) -> list[PortalStruct]:
        """Read the bounded contiguous portal array."""

        reader = self._require_reader()
        return [
            value.bind_reader(reader, self._max_pathing_entries)
            for value in self._read_records(
                int(self.portals_ptr), int(self.portal_count), PortalStruct
            )
        ]

    def _require_reader(self) -> _memory_reader:
        if self._remote_reader is None:
            raise RuntimeError("PathingMap record is not bound to a reader.")
        return self._remote_reader

    @property
    def root_node(self) -> NodeStruct | None:
        """Read the source root-node pointer as a base ``NodeStruct``."""

        return _read_node(self._remote_reader, int(self.root_node_ptr))

    @property
    def h0048(self) -> int | None:
        """Read the source ``uint32_t*`` value at offset 0x48."""

        return _read_uint32_pointer(self._remote_reader, int(self.h0048_ptr))

    @property
    def h004C(self) -> int | None:
        """Read the source ``uint32_t*`` value at offset 0x4C."""

        return _read_uint32_pointer(self._remote_reader, int(self.h004C_ptr))

    @property
    def h0050(self) -> int | None:
        """Read the source ``uint32_t*`` value at offset 0x50."""

        return _read_uint32_pointer(self._remote_reader, int(self.h0050_ptr))

    def snapshot(self) -> PathingMap:
        """Create the Python-owned pathing-map snapshot defined by Reforged."""

        root = self.root_node
        if root is None:
            raise ValueError("PathingMap snapshot requires a non-null root node.")
        return PathingMap(
            zplane=int(self.zplane),
            h0004=int(self.h0004),
            h0008=int(self.h0008),
            h000C=int(self.h000C),
            h0010=int(self.h0010),
            trapezoid_count=int(self.trapezoid_count),
            sink_node_count=int(self.sink_node_count),
            x_node_count=int(self.x_node_count),
            y_node_count=int(self.y_node_count),
            portal_count=int(self.portal_count),
            trapezoids=[value.snapshot() for value in self.trapezoids],
            sink_nodes=[],
            x_nodes=[],
            y_nodes=[],
            portals=[value.snapshot() for value in self.portals],
            h0034=int(self.h0034),
            h0038=int(self.h0038),
            root_node=root.snapshot(),
            root_node_id=int(root.id),
            h0048=self.h0048,
            h004C=self.h004C,
            h0050=self.h0050,
        )

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


def snapshot(pathing_map: PathingMapStruct) -> PathingMap:
    """Preserve Reforged's module-level PathingMap snapshot helper."""

    return pathing_map.snapshot()


class MapStaticDataStruct(TargetStruct):
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
    _max_pathing_maps = 100_000
    _max_blocking_props = 100_000

    def bind_reader(
        self,
        reader: _memory_reader,
        address: int | None = None,
        max_pathing_maps: int = 100_000,
        max_blocking_props: int = 100_000,
    ) -> MapStaticDataStruct:
        """Bind this current pathing root to the remote reader."""

        if max_pathing_maps <= 0:
            raise ValueError("max_pathing_maps must be positive")
        if max_blocking_props <= 0:
            raise ValueError("max_blocking_props must be positive")
        self._remote_reader = reader
        self._remote_address = address
        self._max_pathing_maps = max_pathing_maps
        self._max_blocking_props = max_blocking_props
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
        """Read bounded pathing-map records and bind their child arrays."""

        if self._remote_reader is None:
            raise RuntimeError("MapStaticData root is not bound to a reader.")
        view = GWArrayValueView(self._remote_reader, self.pmaps_array, PathingMapStruct)
        if view.size() > view.capacity() or (view.size() and not int(self.pmaps_array.m_buffer)):
            raise ValueError("MapStaticData pathing-map array has an invalid header.")
        if not view.valid():
            return []
        if view.size() > self._max_pathing_maps:
            raise ValueError(
                f"Pathing-map count {view.size()} exceeds max_pathing_maps "
                f"{self._max_pathing_maps}."
            )
        return [
            value.bind_reader(self._remote_reader, int(self.pmaps_array.m_buffer) + index * ctypes.sizeof(PathingMapStruct))
            for index in range(view.size())
            if (value := view.get(index)) is not None
        ]

    @property
    def pathing_maps_snapshot(self) -> list[PathingMap]:
        """Read source snapshots and resolve each portal's paired-list index."""

        maps = self.pathing_maps
        snapshots = [snapshot(pathing_map) for pathing_map in maps]
        portal_size = ctypes.sizeof(PortalStruct)
        portal_addresses: dict[int, tuple[int, int]] = {}

        for map_index, pathing_map in enumerate(maps):
            portals_address = int(pathing_map.portals_ptr)
            portal_count = int(pathing_map.portal_count)
            if not portals_address or not portal_count:
                continue
            for portal_index in range(portal_count):
                portal_addresses[portals_address + portal_index * portal_size] = (
                    map_index,
                    portal_index,
                )

        for map_index, pathing_map in enumerate(maps):
            for portal_index, portal in enumerate(pathing_map.portals):
                paired_location = portal_addresses.get(int(portal.pair_ptr))
                if paired_location is not None:
                    snapshots[map_index].portals[portal_index].pair_index = paired_location[1]
        return snapshots

    @property
    def blocking_props_list(self) -> list[BlockingPropStruct]:
        """Read the native source ``BaseArray<BlockingProp>`` values."""

        if self._remote_reader is None:
            raise RuntimeError("MapStaticData root is not bound to a reader.")
        count = int(self.blocking_props.m_size)
        capacity = int(self.blocking_props.m_capacity)
        address = int(self.blocking_props.m_buffer)
        if count == 0:
            return []
        if count > capacity:
            raise ValueError("MapStaticData blocking-prop size exceeds capacity.")
        if count > self._max_blocking_props:
            raise ValueError(
                f"Blocking-prop count {count} exceeds max_blocking_props "
                f"{self._max_blocking_props}."
            )
        byte_count = count * ctypes.sizeof(BlockingPropStruct)
        if address < 0x10000 or address + byte_count > 0x1_0000_0000:
            raise ValueError("MapStaticData blocking-prop array is outside x86 address space.")
        raw = self._remote_reader.read(address, byte_count)
        size = ctypes.sizeof(BlockingPropStruct)
        return [
            BlockingPropStruct.from_buffer_copy(raw[index * size : (index + 1) * size])
            for index in range(count)
        ]


class PathContextStruct(TargetStruct):
    """The fixed-width Reforged ``PathContext`` root.

    The path context's own arrays and path nodes remain represented by their
    target headers and pointers; they are not traversed by this reader.
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
    _max_pathing_maps = 100_000

    def bind_reader(
        self,
        reader: _memory_reader,
        address: int | None = None,
        max_pathing_maps: int = 100_000,
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

    @property
    def sub2(self) -> MapStaticDataStruct | None:
        """Preserve Reforged's backward-compatible alias for ``static_data``."""

        return self.static_data


class MapContextStruct(TargetStruct):
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
    _max_pathing_maps = 100_000
    _max_prop_entries = 100_000
    _max_prop_list_entries = 100_000

    def bind_reader(
        self,
        reader: _memory_reader,
        address: int | None = None,
        max_spawn_entries: int = 2048,
        max_pathing_maps: int = 100_000,
        max_prop_entries: int = 100_000,
        max_prop_list_entries: int = 100_000,
    ) -> MapContextStruct:
        """Bind this current root view to the target reader and traversal bound."""

        if max_spawn_entries <= 0:
            raise ValueError("max_spawn_entries must be positive")
        if max_pathing_maps <= 0:
            raise ValueError("max_pathing_maps must be positive")
        if max_prop_entries <= 0 or max_prop_list_entries <= 0:
            raise ValueError("PropsContext read limits must be positive")
        self._remote_reader = reader
        self._remote_address = address
        self._max_spawn_entries = max_spawn_entries
        self._max_pathing_maps = max_pathing_maps
        self._max_prop_entries = max_prop_entries
        self._max_prop_list_entries = max_prop_list_entries
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
        """Return the map-props context pointer, if present."""

        return int(self.props_ptr) or None

    @property
    def props(self) -> PropsContextStruct | None:
        """Read the reachable source ``PropsContext`` header and bind its arrays."""

        if self._remote_reader is None or self.props_address is None:
            return None
        address = self.props_address
        raw = self._remote_reader.read(address, ctypes.sizeof(PropsContextStruct))
        return PropsContextStruct.from_buffer_copy(raw).bind_reader(
            self._remote_reader,
            address,
            self._max_prop_entries,
            self._max_prop_list_entries,
        )

    @property
    def travel_portals(self) -> list[TravelPortal]:
        """Find source-recognized travel-portal props in the current map."""

        if self._remote_reader is None:
            raise RuntimeError("MapContext root is not bound to a reader.")
        props_context = self.props
        if props_context is None:
            return []
        result: list[TravelPortal] = []
        for prop in props_context.props:
            model_file_id = _get_prop_model_file_id(prop, self._remote_reader)
            if model_file_id not in _PORTAL_MODEL_FILE_IDS:
                continue
            result.append(
                TravelPortal(
                    x=float(prop.position.x),
                    y=float(prop.position.y),
                    z=float(prop.position.z),
                    model_file_id=model_file_id,
                )
            )
        return result

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
    def path(self) -> PathContextStruct | None:
        """Expose the path context under Reforged's source property name."""

        return self.path_context

    @property
    def sub1(self) -> PathContextStruct | None:
        """Preserve Reforged's backward-compatible alias for ``path``."""

        return self.path_context

    @property
    def pathing_maps(self) -> list[PathingMapStruct]:
        """Return pathing-map records through the source path/static-data chain."""

        path_context = self.path_context
        if path_context is None:
            return []
        static_data = path_context.static_data
        if static_data is None:
            return []
        return static_data.pathing_maps

    @property
    def pathing_maps_snapshot(self) -> list[PathingMap]:
        """Return source-style pathing snapshots through the current map roots."""

        path_context = self.path_context
        if path_context is None:
            return []
        static_data = path_context.static_data
        if static_data is None:
            return []
        return static_data.pathing_maps_snapshot

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
        if view.size() > view.capacity() or (view.size() and not int(array.m_buffer)):
            raise ValueError("MapContext spawn array has an invalid header.")
        if not view.valid():
            return []
        if view.size() > self._max_spawn_entries:
            raise ValueError(
                f"Spawn count {view.size()} exceeds max_spawn_entries "
                f"{self._max_spawn_entries}."
            )
        return [
            value.snapshot()
            for index in range(view.size())
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
assert ctypes.sizeof(MapVec3fStruct) == 0x0C
assert ctypes.sizeof(SpawnEntryStruct) == 0x10
assert ctypes.sizeof(PathingTrapezoidStruct) == 0x30
assert ctypes.sizeof(NodeStruct) == 0x08
assert ctypes.sizeof(SinkNodeStruct) == 0x0C
assert ctypes.sizeof(XNodeStruct) == 0x20
assert ctypes.sizeof(YNodeStruct) == 0x18
assert ctypes.sizeof(PortalStruct) == 0x14
assert ctypes.sizeof(PathingMapStruct) == 0x54
assert ctypes.sizeof(PropModelInfoStruct) == 0x18
assert ctypes.sizeof(RecObjectStruct) == 0x0C
assert ctypes.sizeof(PropByTypeStruct) == 0x08
assert ctypes.sizeof(MapPropStruct) == 0x90
assert ctypes.sizeof(PropsContextStruct) == 0x1A4
assert ctypes.sizeof(BlockingPropStruct) == 0x0C
assert ctypes.sizeof(NativePathingTrapezoidStruct) == 0x30
assert ctypes.sizeof(NativeSinkNodeStruct) == 0x0C
assert ctypes.sizeof(NativeXNodeStruct) == 0x20
assert ctypes.sizeof(NativeYNodeStruct) == 0x18
assert ctypes.sizeof(NativePortalStruct) == 0x14
assert ctypes.sizeof(NativePathingMapStruct) == 0x54
assert ctypes.sizeof(NativeMapPropStruct) == 0x90
assert ctypes.sizeof(NativePropsContextStruct) == 0x1A4
assert ctypes.sizeof(NativeMapContextSub2Struct) == 0x28
assert ctypes.sizeof(NativeMapContextSub1Struct) == 0x70
assert ctypes.sizeof(NativeMapContextPrefixStruct) == 0x134
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


def _get_travel_portals(context: MapContextStruct) -> list[TravelPortal]:
    """Run Reforged's travel-portal helper against a bound external snapshot."""

    return context.travel_portals


class MapContext:
    """Resolve and read the current external ``MapContext`` root."""

    _ptr: int = 0
    _cached_ctx: MapContextStruct | None = None
    _callback_name = "MapContext.UpdatePtr"
    _pathing_maps_cache: dict[tuple[int, int], list[PathingMap]] = {}
    _pathing_maps_cache_raw: dict[tuple[int, int], list[PathingMapStruct]] = {}

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
        max_pathing_maps: int = 100_000,
        max_prop_entries: int = 100_000,
        max_prop_list_entries: int = 100_000,
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
            max_prop_entries,
            max_prop_list_entries,
        )

    def get_travel_portals(self) -> list[TravelPortal]:
        """Read travel portals from the selected client's current map props."""

        context = self.read()
        return context.travel_portals if context is not None else []

    def get_spawns(
        self,
    ) -> tuple[list[SpawnPoint], list[SpawnPoint], list[SpawnPoint]]:
        """Read the three source spawn lists from the current map context."""

        context = self.read()
        if context is None:
            return [], [], []
        return context.spawns1, context.spawns2, context.spawns3

    @staticmethod
    def get_ptr() -> int:
        """Return the most recently refreshed MapContext address."""

        return MapContext._ptr

    @staticmethod
    def _update_ptr() -> None:
        """Refresh the source-compatible facade from the selected client."""

        from ..client import current_client

        client = current_client()
        if client is None:
            MapContext._ptr = 0
            MapContext._cached_ctx = None
            return
        try:
            context = client.map_context
            address = context.resolve_address()
            MapContext._ptr = address or 0
            MapContext._cached_ctx = cast(Any, context.read())
        except (OSError, RuntimeError, ValueError):
            MapContext._ptr = 0
            MapContext._cached_ctx = None

    @staticmethod
    def enable() -> None:
        """Declare source callback registration, which requires in-client code."""

        raise NotImplementedError(
            "MapContext.enable requires the in-process callback runtime."
        )

    @staticmethod
    def disable() -> None:
        """Clear the external facade snapshot and address."""

        MapContext._ptr = 0
        MapContext._cached_ctx = None

    @staticmethod
    def get_context() -> MapContextStruct | None:
        """Return the most recently refreshed external snapshot."""

        return MapContext._cached_ctx

    @staticmethod
    def _pathing_cache_inputs() -> tuple[tuple[int, int], MapContextStruct] | None:
        """Return the current map and key when the readiness gate passes.

        The gate runs first because it is far cheaper than the pathing read it
        guards, and the cache key carries the map id so a map change rebuilds the
        snapshot.  The gate is re-evaluated rather than timed, so there is no
        window in which a stale snapshot is served after a map change.
        """

        from ..client import current_client

        client = current_client()
        if client is None:
            return None
        from ..map import Map

        if not Map.IsMapReady():
            return None
        char_context = client.read_char_context()
        if char_context is None:
            return None
        current_map_id = int(char_context.current_map_id)
        try:
            map_context = client.read_map_context(max_pathing_maps=100_000)
        except (OSError, RuntimeError, ValueError):
            return None
        if map_context is None:
            return None
        return (client.pid, current_map_id), map_context

    @staticmethod
    def GetPathingMaps() -> list[PathingMap]:
        """Return cached source-style pathing snapshots for the current map."""

        inputs = MapContext._pathing_cache_inputs()
        if inputs is None:
            return []
        cache_key, map_context = inputs
        cached = MapContext._pathing_maps_cache.get(cache_key)
        if cached is None:
            cached = map_context.pathing_maps_snapshot
            MapContext._pathing_maps_cache[cache_key] = cached
        return cached

    @staticmethod
    def GetPathingMapsRaw() -> list[PathingMapStruct]:
        """Return cached raw pathing-map records for the current map."""

        inputs = MapContext._pathing_cache_inputs()
        if inputs is None:
            return []
        cache_key, map_context = inputs
        cached = MapContext._pathing_maps_cache_raw.get(cache_key)
        if cached is None:
            cached = map_context.pathing_maps
            MapContext._pathing_maps_cache_raw[cache_key] = cached
        return cached

    @staticmethod
    def ClearPathingCache(map_id: int | None = None) -> None:
        """Clear all pathing caches or a map's entries across connected clients."""

        if map_id is None:
            MapContext._pathing_maps_cache.clear()
            MapContext._pathing_maps_cache_raw.clear()
            return
        for cache in (
            MapContext._pathing_maps_cache,
            MapContext._pathing_maps_cache_raw,
        ):
            for cache_key in tuple(cache):
                if cache_key[1] == map_id:
                    cache.pop(cache_key, None)

    @staticmethod
    def _clear_pathing_cache_for_pid(pid: int) -> None:
        """Remove cached raw records before their process handle is closed."""

        for cache in (
            MapContext._pathing_maps_cache,
            MapContext._pathing_maps_cache_raw,
        ):
            for cache_key in tuple(cache):
                if cache_key[0] == pid:
                    cache.pop(cache_key, None)

    @staticmethod
    def GetTravelPortals() -> list[TravelPortal]:
        """Read travel portal positions from the currently selected client."""

        from ..client import current_client

        client = current_client()
        if client is None:
            return []
        context = client.read_map_context(max_pathing_maps=100_000)
        return _get_travel_portals(context) if context is not None else []

    @staticmethod
    def GetSpawns() -> tuple[list[SpawnPoint], list[SpawnPoint], list[SpawnPoint]]:
        """Read the three spawn groups from the currently selected client."""

        from ..client import current_client

        client = current_client()
        if client is None:
            return [], [], []
        return client.map_context.get_spawns()


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
    "PathingMap",
    "PathContextStruct",
    "PathingMapStruct",
    "PathingTrapezoid",
    "Portal",
    "SpawnEntryStruct",
    "SpawnPoint",
    "TravelPortal",
    "Node",
    "SinkNode",
    "XNode",
    "YNode",
]
