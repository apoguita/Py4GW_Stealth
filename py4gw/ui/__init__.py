"""Read-only access to the Guild Wars UI frame primitives.

This package holds the target-side UI declarations and the frame-tree reads
that were previously missing from the external controller.  It is deliberately
separate from ``py4gw.context``: these are user-interface engine primitives,
not game contexts, even though some contexts are located through them.

Nothing in this package creates, destroys, or dispatches a frame, and nothing
writes to the target process.
"""

from __future__ import annotations

from .frame import (
    Frame,
    FrameArray,
    FrameInteractionCallback,
    FrameInteractionCallbackStruct,
    FramePosition,
    FramePositionStruct,
    FrameRelation,
    FrameRelationStruct,
    FrameStruct,
    InteractionMessage,
    InteractionMessageStruct,
    TooltipInfo,
    TooltipInfoStruct,
    UIInteractionCallbackStruct,
    UIMessage,
    is_valid_frame_pointer,
)
from .frame_context import (
    FrameContextCandidate,
    FramePublishedContextSource,
    locate_frame_published_context,
)
from .frame_tree import FrameTree

__all__ = [
    "Frame",
    "FrameArray",
    "FrameContextCandidate",
    "FrameInteractionCallback",
    "FrameInteractionCallbackStruct",
    "FramePosition",
    "FramePositionStruct",
    "FramePublishedContextSource",
    "FrameRelation",
    "FrameRelationStruct",
    "FrameStruct",
    "FrameTree",
    "InteractionMessage",
    "InteractionMessageStruct",
    "TooltipInfo",
    "TooltipInfoStruct",
    "UIInteractionCallbackStruct",
    "UIMessage",
    "is_valid_frame_pointer",
    "locate_frame_published_context",
]