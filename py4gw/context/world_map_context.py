"""Source-matched structure declaration for the world-map context.

Reforged Native obtains this pointer inside a UI callback: it calls the
original callback, then dereferences the message's ``wParam`` field.  Stealth
reaches the same slot without a hook by walking the client's UI frame array to
the frame that registered the world-map callback, and reading that frame's
registered context pointer.  See ``py4gw.ui.frame_context``.

The frame-id cross-check is what makes the walk trustworthy: the context
records its owning frame id, so a candidate is only accepted when the stored
id equals the id of the frame that published it.
"""

from __future__ import annotations

from ..target_struct import TargetStruct

import ctypes
from ctypes import Structure, c_float, c_uint32
from typing import Any, Protocol, cast

from ..scanner import PatternCatalog, RemoteScanner
from ..ui.frame_context import (
    FrameContextCandidate,
    FramePublishedContextSource,
)
from ..ui.frame_tree import FrameTree
from .map_context import MapVec2fStruct


class _memory_reader(Protocol):
    """The target-memory operation needed to read a context at a known address."""

    def read(self, address: int, size: int) -> bytes: ...


class WorldMapContextStruct(TargetStruct):
    """The fixed 0x224-byte Reforged/native world-map context."""

    _pack_ = 1
    _fields_ = [
        ("frame_id", c_uint32),
        ("h0004", c_uint32),
        ("h0008", c_uint32),
        ("h000c", c_float),
        ("h0010", c_float),
        ("h0014", c_uint32),
        ("h0018", c_float),
        ("h001c", c_float),
        ("h0020", c_float),
        ("h0024", c_float),
        ("h0028", c_float),
        ("h002c", c_float),
        ("h0030", c_float),
        ("h0034", c_float),
        ("zoom", c_float),
        ("top_left", MapVec2fStruct),
        ("bottom_right", MapVec2fStruct),
        ("h004c", c_uint32 * 7),
        ("h0068", c_float),
        ("h006c", c_float),
        ("params", c_uint32 * 0x6D),
    ]

    @classmethod
    def read_at(cls, reader: _memory_reader, address: int) -> WorldMapContextStruct:
        """Read the fixed root from a supplied address without resolving it.

        The source obtains this address through a UI callback. This method is
        the structure-reading half only; it deliberately does not locate or
        emulate that callback.
        """

        size = ctypes.sizeof(cls)
        if address < 0x10000 or address + size > 0x1_0000_0000:
            raise ValueError("WorldMapContext address is outside x86 address space.")
        raw = reader.read(address, size)
        if len(raw) != size:
            raise ValueError(
                f"WorldMapContext read returned {len(raw)} bytes; expected {size}."
            )
        return cls.from_buffer_copy(raw)


assert ctypes.sizeof(WorldMapContextStruct) == 0x224
assert WorldMapContextStruct.zoom.offset == 0x38
assert WorldMapContextStruct.top_left.offset == 0x3C
assert WorldMapContextStruct.bottom_right.offset == 0x44
assert WorldMapContextStruct.params.offset == 0x70

# The owning frame id is the context's first field.  The frame-array walk
# compares it against the index of the frame that published the pointer.
_FRAME_ID_OFFSET = 0x0
assert WorldMapContextStruct.frame_id.offset == _FRAME_ID_OFFSET


class WorldMapContext:
    """External reader and Reforged-compatible facade for the world map.

    ``resolve_address`` performs the read-only frame-array acquisition.  The
    static facade members keep the source contract; ``enable`` and
    ``_update_ptr`` still report that in-process callback registration is not
    available to an external controller.
    """

    _ptr: int = 0
    _cached_ctx: WorldMapContextStruct | None = None
    _callback_name = "WorldMapContext.UpdatePtr"

    _CALLBACK_RESOLVER = "map.world_map_ui_callback_func"

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
        """Return the resolved world-map callback address, if resolved."""

        return self._source.callback_address

    def initialize(self) -> int | None:
        """Resolve the callback signature once and report the current context.

        Returns ``None`` when no frame currently publishes the context, which
        is the expected result while the world map is closed.
        """

        self._source.resolve_callback_address()
        return self._source.resolve_address()

    def resolve_address(self) -> int | None:
        """Return the frame-published world-map context address, or ``None``.

        ``None`` means no frame published a context that passed the frame-id
        cross-check.  It does not distinguish "the map is closed" from "a
        candidate was rejected"; use ``candidates()`` for that detail.
        """

        return self._source.resolve_address()

    def candidates(self) -> tuple[FrameContextCandidate, ...]:
        """Return every frame context candidate, confirmed or rejected.

        The rejection reason distinguishes a frame with no registered context,
        an unreadable candidate address, and a frame-id mismatch.
        """

        return self._source.candidates()

    def read(self) -> WorldMapContextStruct | None:
        """Read the complete world-map context, or ``None`` when unpublished."""

        address = self.resolve_address()
        if address is None:
            return None
        return WorldMapContextStruct.read_at(self._reader, address)

    @staticmethod
    def get_ptr() -> int:
        """Return the latest callback-published address (zero externally)."""

        return WorldMapContext._ptr

    @staticmethod
    def _update_ptr() -> None:
        """Preserve the source callback entry point; it requires in-process code."""

        raise NotImplementedError(
            "WorldMapContext._update_ptr requires the in-process shared-memory callback."
        )

    @staticmethod
    def enable() -> None:
        """Preserve the source enable API; callback registration is unavailable."""

        raise NotImplementedError(
            "WorldMapContext.enable requires the in-process callback runtime."
        )

    @staticmethod
    def disable() -> None:
        """Clear the source-compatible cached pointer and structure."""

        WorldMapContext._ptr = 0
        WorldMapContext._cached_ctx = None

    @staticmethod
    def get_context() -> WorldMapContextStruct | None:
        """Return the latest cached structure, if a source callback supplied one."""

        return WorldMapContext._cached_ctx


def get() -> WorldMapContextStruct | None:
    """Read the world-map context of the current selected client, if published.

    Returns ``None`` when the world map is closed, because no frame then
    publishes the context.
    """

    from ..client import current_client

    client = current_client()
    return cast(Any, client.read_world_map_context() if client is not None else None)


__all__ = ["WorldMapContext", "WorldMapContextStruct", "get"]
