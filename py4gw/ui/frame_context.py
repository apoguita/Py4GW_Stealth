"""Locate a game context that the client publishes through a UI frame.

Several game contexts are not stored in a module global.  The client allocates
the context, registers it as a frame's ``uictl_context``, and hands the
address to the frame's interaction callback through the message's ``wParam``
field.  An in-process hook therefore sees the pointer only while a callback is
running; an external reader can instead walk the frame array to the same slot.

The context records that use this route store their owning frame id at a fixed
offset, which makes the walk self-checking: a candidate is confirmed only when
the id stored inside the context equals the id of the frame that published it.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..scanner import PatternCatalog, RemoteScanner
from .frame_tree import FrameTree


@dataclass(frozen=True)
class FrameContextCandidate:
    """One frame context pointer considered while locating a game context."""

    frame_id: int
    frame_address: int | None
    context_address: int
    context_frame_id: int | None
    rejection: str

    @property
    def is_confirmed(self) -> bool:
        """Return whether the frame-id cross-check accepted this candidate."""

        return not self.rejection


def locate_frame_published_context(
    tree: FrameTree,
    callback_address: int,
    frame_id_offset: int = 0,
) -> tuple[FrameContextCandidate, ...]:
    """Return every context candidate published by frames using a callback.

    ``callback_address`` is the client's own interaction callback, resolved
    from its signature.  ``frame_id_offset`` is the byte offset of the owning
    frame id inside the context record.

    Candidates are ordered by frame id.  A candidate is confirmed only when the
    stored frame id matches the frame that published it; every other candidate
    carries the reason it was rejected so a caller can report the difference
    between "the map is closed" and "the pointer did not validate".
    """

    candidates: list[FrameContextCandidate] = []
    for frame_id, frame in tree.frames_using_callback(callback_address):
        context_address = tree.context_address_of(frame)
        if not context_address:
            candidates.append(
                FrameContextCandidate(
                    frame_id=frame_id,
                    frame_address=frame.address,
                    context_address=0,
                    context_frame_id=None,
                    rejection="the frame registered no context pointer",
                )
            )
            continue

        try:
            context_frame_id = tree.frames.read_u32(context_address + frame_id_offset)
        except OSError as error:
            candidates.append(
                FrameContextCandidate(
                    frame_id=frame_id,
                    frame_address=frame.address,
                    context_address=context_address,
                    context_frame_id=None,
                    rejection=f"the context address is unreadable: {error}",
                )
            )
            continue

        rejection = ""
        if context_frame_id != frame_id:
            rejection = (
                f"frame-id cross-check failed: the context reports frame "
                f"{context_frame_id} but frame {frame_id} published it"
            )

        candidates.append(
            FrameContextCandidate(
                frame_id=frame_id,
                frame_address=frame.address,
                context_address=context_address,
                context_frame_id=context_frame_id,
                rejection=rejection,
            )
        )
    return tuple(candidates)


class FramePublishedContextSource:
    """Acquire one context root through the UI frame that publishes it.

    Every context reached this way has the same shape: the client's own
    interaction callback is resolved from a signature, the frame that
    registered that callback is found in the frame array, and the frame's
    registered context pointer is cross-checked against the frame id stored
    inside the context.

    A subclass declares the callback resolver name and the byte offset of the
    context's own frame id; everything else is shared.
    """

    def __init__(
        self,
        scanner: RemoteScanner,
        patterns: PatternCatalog,
        frame_tree: FrameTree,
        callback_resolver: str,
        frame_id_offset: int,
    ) -> None:
        """Create a source for one frame-published context."""

        if frame_id_offset < 0:
            raise ValueError("frame_id_offset must not be negative")
        self._scanner = scanner
        self._patterns = patterns
        self._frame_tree = frame_tree
        self._callback_resolver = callback_resolver
        self._frame_id_offset = frame_id_offset
        self._callback_address: int | None = None

    @property
    def callback_resolver(self) -> str:
        """Return the resolver name used to find the client's callback."""

        return self._callback_resolver

    @property
    def frame_id_offset(self) -> int:
        """Return the byte offset of the context's owning frame id."""

        return self._frame_id_offset

    @property
    def callback_address(self) -> int | None:
        """Return the resolved callback address, if it has been resolved."""

        return self._callback_address

    def resolve_callback_address(self) -> int:
        """Resolve and cache the client's interaction callback address."""

        if self._callback_address is None:
            result = self._patterns.resolve(self._callback_resolver, self._scanner)
            if not result.ok:
                detail = result.message or "the resolver returned no address"
                raise RuntimeError(f"{self._callback_resolver} failed: {detail}")
            if result.value < 0x10000:
                raise ValueError(
                    f"{self._callback_resolver} returned an unusable address: "
                    f"0x{result.value:08X}"
                )
            self._callback_address = result.value
        return self._callback_address

    def candidates(self) -> tuple[FrameContextCandidate, ...]:
        """Return every frame context candidate, confirmed or rejected."""

        return locate_frame_published_context(
            self._frame_tree,
            self.resolve_callback_address(),
            self._frame_id_offset,
        )

    def resolve_address(self) -> int | None:
        """Return the frame-published context address, or ``None``.

        ``None`` means no frame published a context that passed the frame-id
        cross-check.  Use ``candidates()`` to distinguish "not published" from
        "published but rejected".
        """

        for candidate in self.candidates():
            if candidate.is_confirmed:
                return candidate.context_address
        return None


__all__ = [
    "FrameContextCandidate",
    "FramePublishedContextSource",
    "locate_frame_published_context",
]
