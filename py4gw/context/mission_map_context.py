"""Source-matched structure declarations for the mission-map context.

The native/Reforged pointer is published by an in-process UI callback. Stealth
reaches the same slot read-only by walking the client's UI frame array to the
frame that registered the mission-map callback; see ``py4gw.ui.frame_context``.
"""

from __future__ import annotations

from ..helpers.target_struct import TargetStruct

import ctypes
from ctypes import Structure, c_float, c_uint32
from typing import Any, Protocol, cast

from ..scanner import PatternCatalog, RemoteScanner
from ..ui.frame_context import (
    FrameContextCandidate,
    FramePublishedContextSource,
)
from ..ui.frame_tree import FrameTree
from .gw_array import GWArray, GWArrayView
from .map_context import MapVec2fStruct


class _memory_reader(Protocol):
    """The target-memory operation required by mission-map child records."""

    def read(self, address: int, size: int) -> bytes: ...


class MissionMapSubContext(TargetStruct):
    """The fixed 0x38-byte mission-map subcontext record."""

    _pack_ = 1
    _fields_ = [("h0000", c_uint32 * 0x0E)]


class MissionMapSubContext2(TargetStruct):
    """The fixed 0x58-byte mission-map view and pan-state record."""

    _pack_ = 1
    _fields_ = [
        ("h0000", c_uint32),
        ("player_mission_map_pos", MapVec2fStruct),
        ("h000c", c_uint32),
        ("mission_map_size", MapVec2fStruct),
        ("unk", c_float),
        ("mission_map_pan_offset", MapVec2fStruct),
        ("mission_map_pan_offset2", MapVec2fStruct),
        ("unk2", c_float * 2),
        ("unk3", c_uint32 * 9),
    ]


class MissionMapContextStruct(TargetStruct):
    """The fixed 0x48-byte mission-map context structure."""

    _pack_ = 1
    _fields_ = [
        ("size", MapVec2fStruct),
        ("h0008", c_uint32),
        ("last_mouse_location", MapVec2fStruct),
        ("frame_id", c_uint32),
        ("player_mission_map_pos", MapVec2fStruct),
        ("h0020", GWArray),
        ("h0030", c_uint32),
        ("h0034", c_uint32),
        ("h0038", c_uint32),
        ("h003c", c_uint32),
        ("h0040", c_uint32),
        ("h0044", c_uint32),
    ]

    _remote_reader: _memory_reader | None = None
    _remote_address: int | None = None
    _max_subcontexts = 100_000

    @classmethod
    def read_at(
        cls,
        reader: _memory_reader,
        address: int,
        max_subcontexts: int = 100_000,
    ) -> MissionMapContextStruct:
        """Read a root at a supplied address, without locating that address.

        The native/Reforged callback is responsible for finding this context.
        Keeping address acquisition separate lets the layout and child readers
        be exercised as soon as a caller has a verified address.
        """

        if max_subcontexts <= 0:
            raise ValueError("max_subcontexts must be positive")
        size = ctypes.sizeof(cls)
        if address < 0x10000 or address + size > 0x1_0000_0000:
            raise ValueError("MissionMapContext address is outside x86 address space.")
        raw = reader.read(address, size)
        if len(raw) != size:
            raise ValueError(
                f"MissionMapContext read returned {len(raw)} bytes; expected {size}."
            )
        return cls.from_buffer_copy(raw).bind_reader(
            reader, address, max_subcontexts
        )

    def bind_reader(
        self,
        reader: _memory_reader,
        address: int | None = None,
        max_subcontexts: int = 100_000,
    ) -> MissionMapContextStruct:
        """Bind this copied root to the reader used for its source pointers."""

        if max_subcontexts <= 0:
            raise ValueError("max_subcontexts must be positive")
        self._remote_reader = reader
        self._remote_address = address
        self._max_subcontexts = max_subcontexts
        return self

    @property
    def address(self) -> int | None:
        """Return the target address represented by this structure copy."""

        return self._remote_address

    @property
    def subcontexts(self) -> list[MissionMapSubContext]:
        """Read the source ``GWArray<MissionMapSubContext*>`` contents."""

        if self._remote_reader is None:
            raise RuntimeError("MissionMapContext is not bound to a memory reader.")
        count = int(self.h0020.m_size)
        capacity = int(self.h0020.m_capacity)
        buffer = int(self.h0020.m_buffer)
        if count > capacity or (count and not buffer):
            raise ValueError("MissionMapContext subcontext array has an invalid header.")
        if count > self._max_subcontexts:
            raise ValueError(
                f"Mission-map subcontext count {count} exceeds max_subcontexts "
                f"{self._max_subcontexts}."
            )
        if count and (buffer < 0x10000 or buffer + count * 4 > 0x1_0000_0000):
            raise ValueError("MissionMapContext subcontext pointers exceed x86 address space.")
        if count == 0:
            return []
        view = GWArrayView(self._remote_reader, self.h0020, MissionMapSubContext)
        return view.to_list()

    @property
    def subcontext2(self) -> MissionMapSubContext2 | None:
        """Read the source ``h003c`` pointer, or return ``None`` when null."""

        pointer = int(self.h003c)
        if pointer == 0:
            return None
        if pointer < 0x10000 or pointer + ctypes.sizeof(MissionMapSubContext2) > 0x1_0000_0000:
            raise ValueError("MissionMapContext h003c is outside x86 address space.")
        if self._remote_reader is None:
            raise RuntimeError("MissionMapContext is not bound to a memory reader.")
        raw = self._remote_reader.read(pointer, ctypes.sizeof(MissionMapSubContext2))
        return MissionMapSubContext2.from_buffer_copy(raw)


assert ctypes.sizeof(MissionMapSubContext) == 0x38
assert ctypes.sizeof(MissionMapSubContext2) == 0x58
assert ctypes.sizeof(MissionMapContextStruct) == 0x48
assert MissionMapContextStruct.h0020.offset == 0x20
assert MissionMapContextStruct.h003c.offset == 0x3C

# The owning frame id sits after the size vector and one unknown dword; the
# frame-array walk compares it against the frame that published the pointer.
_FRAME_ID_OFFSET = 0x14
assert MissionMapContextStruct.frame_id.offset == _FRAME_ID_OFFSET


class MissionMapContext:
    """External reader and Reforged-compatible facade for the mission map.

    ``resolve_address`` performs the read-only frame-array acquisition.  The
    static facade members keep the source contract; ``enable`` and
    ``_update_ptr`` still report that in-process callback registration is not
    available to an external controller.
    """

    _ptr: int = 0
    _cached_ctx: MissionMapContextStruct | None = None
    _callback_name = "MissionMapContext.UpdatePtr"

    _CALLBACK_RESOLVER = "map.mission_map_ui_callback_func"

    def __init__(
        self,
        reader: _memory_reader,
        scanner: RemoteScanner,
        patterns: PatternCatalog,
        frame_tree: FrameTree,
    ) -> None:
        """Create a reader that acquires its root through the UI frame array."""

        self._reader = reader
        self._source = FramePublishedContextSource(
            scanner,
            patterns,
            frame_tree,
            self._CALLBACK_RESOLVER,
            _FRAME_ID_OFFSET,
        )

    @property
    def callback_resolver(self) -> str:
        """Return the resolver name for the client's callback signature."""

        return self._source.callback_resolver

    @property
    def callback_address(self) -> int | None:
        """Return the resolved mission-map callback address, if resolved."""

        return self._source.callback_address

    def initialize(self) -> int | None:
        """Resolve the callback signature once and report the current context.

        Returns ``None`` when no frame currently publishes the context, which
        is the expected result while the mission map is closed.
        """

        self._source.resolve_callback_address()
        return self._source.resolve_address()

    def resolve_address(self) -> int | None:
        """Return the frame-published mission-map context address, or ``None``."""

        return self._source.resolve_address()

    def candidates(self) -> tuple[FrameContextCandidate, ...]:
        """Return every frame context candidate, confirmed or rejected."""

        return self._source.candidates()

    def read(self, max_subcontexts: int = 100_000) -> MissionMapContextStruct | None:
        """Read the complete mission-map context, or ``None`` when unpublished."""

        address = self.resolve_address()
        if address is None:
            return None
        return MissionMapContextStruct.read_at(
            self._reader, address, max_subcontexts
        )

    @staticmethod
    def get_ptr() -> int:
        """Return the latest callback-published address (zero externally)."""

        return MissionMapContext._ptr

    @staticmethod
    def _update_ptr() -> None:
        """Preserve the source callback entry point; it requires in-process code."""

        raise NotImplementedError(
            "MissionMapContext._update_ptr requires the in-process shared-memory callback."
        )

    @staticmethod
    def enable() -> None:
        """Preserve the source enable API; callback registration is unavailable."""

        raise NotImplementedError(
            "MissionMapContext.enable requires the in-process callback runtime."
        )

    @staticmethod
    def disable() -> None:
        """Clear the source-compatible cached pointer and structure."""

        MissionMapContext._ptr = 0
        MissionMapContext._cached_ctx = None

    @staticmethod
    def get_context() -> MissionMapContextStruct | None:
        """Return the latest cached structure, if a source callback supplied one."""

        return MissionMapContext._cached_ctx


def get() -> MissionMapContextStruct | None:
    """Read the mission-map context of the current selected client, if published.

    Returns ``None`` when the mission map is closed, because no frame then
    publishes the context.
    """

    from ..client import current_client

    client = current_client()
    return cast(Any, client.read_mission_map_context() if client is not None else None)


__all__ = [
    "MissionMapContext",
    "MissionMapContextStruct",
    "MissionMapSubContext",
    "MissionMapSubContext2",
    "get",
]
