"""External reader for the Reforged/native ``SalvageSessionInfo``.

The native root is ``GW::Context::SalvageSessionInfo`` from
``include/GW/context/item.h``. Reforged does not obtain it from a global: its
salvage-popup UI callback reads the pointer from the interaction message's
``wParam`` on ``kInitFrame`` and clears it on ``kDestroyFrame``.

Stealth reaches the same slot read-only by walking the client's UI frame array
to the frame that registered the salvage-popup callback. The session record
stores its owning frame id at ``+0x4``, which is the cross-check that accepts
a candidate.

No Reforged Python module corresponds to this structure; the field names and
layout are ported from the native header.
"""

from __future__ import annotations

from ..target_struct import TargetStruct

import ctypes
from ctypes import Structure, c_uint32
from typing import Protocol

from ..scanner import PatternCatalog, RemoteScanner
from ..ui.frame_context import (
    FrameContextCandidate,
    FramePublishedContextSource,
)
from ..ui.frame_tree import FrameTree


class _memory_reader(Protocol):
    """The target-memory operation needed to read a context at a known address."""

    def read(self, address: int, size: int) -> bytes: ...


class SalvageSessionInfoStruct(TargetStruct):
    """The fixed 0x24-byte native salvage-session record."""

    _pack_ = 1
    _fields_ = [
        ("vtable", c_uint32),
        ("frame_id", c_uint32),
        ("item_id", c_uint32),
        ("salvagable_1", c_uint32),
        ("salvagable_2", c_uint32),
        ("salvagable_3", c_uint32),
        ("chosen_salvagable", c_uint32),
        ("h001c", c_uint32),
        ("kit_id", c_uint32),
    ]

    @classmethod
    def read_at(
        cls, reader: _memory_reader, address: int
    ) -> SalvageSessionInfoStruct:
        """Read the fixed root from a supplied address without resolving it."""

        size = ctypes.sizeof(cls)
        if address < 0x10000 or address + size > 0x1_0000_0000:
            raise ValueError(
                "SalvageSessionInfo address is outside x86 address space."
            )
        raw = reader.read(address, size)
        if len(raw) != size:
            raise ValueError(
                f"SalvageSessionInfo read returned {len(raw)} bytes; expected {size}."
            )
        return cls.from_buffer_copy(raw)


assert ctypes.sizeof(SalvageSessionInfoStruct) == 0x24
assert SalvageSessionInfoStruct.frame_id.offset == 0x4
assert SalvageSessionInfoStruct.item_id.offset == 0x8
assert SalvageSessionInfoStruct.kit_id.offset == 0x20

# The owning frame id follows the vtable pointer.
_FRAME_ID_OFFSET = 0x4
assert SalvageSessionInfoStruct.frame_id.offset == _FRAME_ID_OFFSET


class SalvageSessionInfo:
    """External reader for the frame-published salvage session.

    ``chosen_salvagable`` is ``3`` for a materials salvage in the native
    header's own comment; the field is read raw and no meaning is inferred
    beyond the source comment.
    """

    _ptr: int = 0
    _cached_ctx: SalvageSessionInfoStruct | None = None
    _callback_name = "SalvageSessionInfo.UpdatePtr"

    _CALLBACK_RESOLVER = "item.salvage_popup_uicallback_func"

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
        """Return the resolved salvage-popup callback address, if resolved."""

        return self._source.callback_address

    def initialize(self) -> int | None:
        """Resolve the callback signature once and report the current session.

        Returns ``None`` when no frame currently publishes the session, which
        is the expected result while the salvage popup is closed.
        """

        self._source.resolve_callback_address()
        return self._source.resolve_address()

    def resolve_address(self) -> int | None:
        """Return the frame-published salvage session address, or ``None``."""

        return self._source.resolve_address()

    def candidates(self) -> tuple[FrameContextCandidate, ...]:
        """Return every frame context candidate, confirmed or rejected."""

        return self._source.candidates()

    def read(self) -> SalvageSessionInfoStruct | None:
        """Read the salvage session, or ``None`` when no popup is open."""

        address = self.resolve_address()
        if address is None:
            return None
        return SalvageSessionInfoStruct.read_at(self._reader, address)

    @staticmethod
    def get_ptr() -> int:
        """Return the latest callback-published address (zero externally)."""

        return SalvageSessionInfo._ptr

    @staticmethod
    def _update_ptr() -> None:
        """Preserve the source callback entry point; it requires in-process code."""

        raise NotImplementedError(
            "SalvageSessionInfo._update_ptr requires the in-process callback runtime."
        )

    @staticmethod
    def enable() -> None:
        """Preserve the source enable API; callback registration is unavailable."""

        raise NotImplementedError(
            "SalvageSessionInfo.enable requires the in-process callback runtime."
        )

    @staticmethod
    def disable() -> None:
        """Clear the cached pointer and structure."""

        SalvageSessionInfo._ptr = 0
        SalvageSessionInfo._cached_ctx = None

    @staticmethod
    def get_context() -> SalvageSessionInfoStruct | None:
        """Return the latest cached structure, if one was supplied."""

        return SalvageSessionInfo._cached_ctx


SalvageSessionInfoRecord = SalvageSessionInfoStruct


def get() -> SalvageSessionInfoStruct | None:
    """Read the salvage session of the current selected client, if open."""

    from ..client import current_client

    client = current_client()
    return client.read_salvage_session() if client is not None else None


__all__ = [
    "SalvageSessionInfo",
    "SalvageSessionInfoRecord",
    "SalvageSessionInfoStruct",
]
