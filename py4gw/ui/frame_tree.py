"""Read-only traversal of the Guild Wars UI frame tree.

``FrameArray`` resolves and reads the client's frame-array records.  This
module adds the relationships the array alone does not express: a frame's
parent, its children, its registered context pointer, and a lookup by the
interaction callback the client registered on a frame.

Every operation reads target memory.  Nothing here creates, destroys,
relabels, or dispatches a frame.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Iterator

from .frame import (
    FrameArray,
    FrameStruct,
    is_valid_frame_pointer,
)


class FrameTree:
    """A read-only view over one client's UI frame array and relations.

    Some frame callbacks are registered through a short x86 ``jmp`` thunk, so a
    frame's stored callback address can be a trampoline rather than the handler
    a signature resolves. ``thunk_target`` supplies the near-call/jump follower
    used to look through that indirection; without it only direct matches are
    found.
    """

    def __init__(
        self,
        frames: FrameArray,
        thunk_target: Callable[[int], int | None] | None = None,
    ) -> None:
        """Create a tree view over an already constructed frame-array reader."""

        self._frames = frames
        self._thunk_target = thunk_target

    @property
    def frames(self) -> FrameArray:
        """Return the underlying frame-array reader."""

        return self._frames

    def size(self) -> int:
        """Return the number of frame slots the client currently advertises."""

        return self._frames.size()

    def by_id(self, frame_id: int) -> FrameStruct | None:
        """Return one frame by its index in the global frame array."""

        return self._frames.get(frame_id)

    def iter_frames(self) -> Iterator[tuple[int, FrameStruct]]:
        """Yield ``(frame_id, frame)`` for every valid slot in the array."""

        return self._frames.iter_frames()

    def root(self) -> FrameStruct | None:
        """Return the first frame that reports no parent.

        The native tree obtains its root through a separate
        ``ui.get_root_frame_func`` resolver.  Deriving it from the relation
        records avoids a second signature and yields the same first parentless
        frame for the current client layout; this is a Steer-owned choice, not
        a source-identical operation.
        """

        for _, frame in self._frames.iter_frames():
            if int(frame.relation.parent) == 0:
                return frame
        return None

    def parent_of(self, frame: FrameStruct) -> FrameStruct | None:
        """Return a frame's parent frame, or ``None`` for a root frame.

        Mirrors the native ``FrameRelation::GetParent``: the stored field is a
        ``FrameRelation*``, so the owning frame starts one ``relation`` field
        earlier in the record.
        """

        relation_pointer = int(frame.relation.parent)
        if relation_pointer < 0x10000:
            return None
        frame_pointer = relation_pointer - FrameStruct.relation.offset
        if not is_valid_frame_pointer(frame_pointer):
            return None
        return self._read_frame_at(frame_pointer)

    def children_of(self, frame: FrameStruct) -> list[FrameStruct]:
        """Return every frame whose parent is the supplied frame.

        Reforged Native finds children by scanning the frame array and
        comparing each candidate's resolved parent, so this does the same
        instead of walking the intrusive sibling list.
        """

        address = frame.address
        if address is None:
            raise ValueError(
                "FrameTree.children_of needs a frame read through FrameArray "
                "so its target address is known."
            )

        children: list[FrameStruct] = []
        for frame_id, candidate_pointer in self._frames.iter_slots():
            if candidate_pointer == address:
                continue
            relation_pointer = self._frames.read_u32(
                candidate_pointer + FrameStruct.relation.offset
            )
            if relation_pointer < 0x10000:
                continue
            if relation_pointer - FrameStruct.relation.offset != address:
                continue
            candidate = self._frames.get(frame_id)
            if candidate is not None:
                children.append(candidate)
        return children

    def context_address_of(self, frame: FrameStruct) -> int:
        """Return the frame's registered context pointer, or zero.

        Delegates to ``FrameArray.frame_context_address``, which reproduces
        the native ``GetFrameContext`` selection order.
        """

        return self._frames.frame_context_address(frame)

    def frames_using_callback(
        self, callback_address: int
    ) -> list[tuple[int, FrameStruct]]:
        """Return ``(frame_id, frame)`` for frames registered with a callback.

        A frame matches when it registers the address directly, or when it
        registers an x86 jump thunk that resolves to it.  The client registers
        thunks for some callbacks while the signature resolver yields the real
        handler, so both forms have to be accepted.

        A frame may register several interaction callbacks, so a frame appears
        once per match at most.  Ordered by frame id.  The callback entries are
        read per frame without transferring the whole frame record, so frames
        that register nothing are skipped cheaply.
        """

        if callback_address < 0x10000:
            return []

        matches: list[tuple[int, FrameStruct]] = []
        for frame_id, frame_pointer in self._frames.iter_slots():
            for callback in self._frames.read_callbacks_at(frame_pointer):
                registered = int(callback.callback)
                if registered == callback_address or (
                    self._resolve_thunk(registered) == callback_address
                ):
                    frame = self._frames.get(frame_id)
                    if frame is not None:
                        matches.append((frame_id, frame))
                    break
        return matches

    def _resolve_thunk(self, address: int) -> int | None:
        """Return a registered callback's final target, or ``None``."""

        if self._thunk_target is None or address < 0x10000:
            return None
        try:
            target = self._thunk_target(address)
        except (OSError, ValueError):
            return None
        if target is None or target == address:
            return None
        return target

    def _read_frame_at(self, address: int) -> FrameStruct | None:
        """Read one frame record at a raw target address."""

        frame_id = self._frames.frame_id_for_address(address)
        if frame_id is None:
            return None
        return self._frames.get(frame_id)


__all__ = ["FrameTree"]
