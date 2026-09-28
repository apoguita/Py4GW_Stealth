"""FrameTree - the single handler for Guild Wars native UI frames.

    from py4gw.frame_tree import Frame, FrameId

    f = Frame(FrameId.SalvageWindow.Options.Option1)
    if f.exists:
        f.click()

Modules:
  frame          the Frame handle and the tree snapshot
  frame_ids      generated key constants (Pylance-checkable)
  frame_registry nested registry: anchor name + relative child codes
  frame_names    hash <-> engine frame name
  frame_aliases  legacy label-keyed paths, kept as the registry's source data

**This file is the source's own re-export list**, and the package it fronts is ported in full: the five
tables verbatim, ``frame.py`` with both of its classes declared in full and in the source's own member order
(``FRAME_TREE_PORT.md`` records which members answer and which name a client-side input), and this
``__init__``. Two adaptations, both of them paths: the example above is the port's package
(``py4gw.frame_tree``) where the source writes ``Py4GWCoreLib.FrameTree``, and the source's closing pointer
to its own design document (``docs/ui/frame-tree/frame-tree-design.md``) refers to a file that lives in
Reforged, not here.
"""

from .frame import (
    alias_by_path,
    key_by_path,
    RELATION_FIRST_CHILD,
    RELATION_LAST_CHILD,
    RELATION_NEXT_SIBLING,
    RELATION_PREV_SIBLING,
    Frame,
    FrameError,
    FrameKeyError,
    FrameNotFound,
    FrameState,
    FrameTree,
    resolve_key,
)
from .frame_ids import FrameId
from .frame_names import (
    FRAME_NAMES,
    FRAME_NAMES_CONFIRMED,
    FRAME_NAMES_HARVESTED,
    FRAME_NAMES_OBSERVED,
    FRAME_NAMES_RECONSTRUCTED,
    NAME_TO_HASH,
)
from .frame_registry import DYNAMIC_KEYS, REGISTRY
from .frame_window_keys import WINDOW_FRAME_KEYS

__all__ = [
    "Frame",
    "FrameId",
    "FrameTree",
    "FrameError",
    "FrameKeyError",
    "FrameNotFound",
    "FrameState",
    "RELATION_FIRST_CHILD",
    "RELATION_LAST_CHILD",
    "RELATION_NEXT_SIBLING",
    "RELATION_PREV_SIBLING",
    "resolve_key",
    "alias_by_path",
    "key_by_path",
    "REGISTRY",
    "DYNAMIC_KEYS",
    "WINDOW_FRAME_KEYS",
    "FRAME_NAMES",
    "FRAME_NAMES_CONFIRMED",
    "FRAME_NAMES_OBSERVED",
    "FRAME_NAMES_HARVESTED",
    "FRAME_NAMES_RECONSTRUCTED",
    "NAME_TO_HASH",
]
