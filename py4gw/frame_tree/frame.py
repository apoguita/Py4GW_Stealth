"""Port of Reforged's ``Py4GWCoreLib/FrameTree/frame.py`` (1620 lines) — **the first section**.

**What this file is, and what it is not yet.** The source module is the logic of the ``FrameTree``
package: ``FrameError``/``FrameKeyError``/``FrameNotFound``, ``resolve_key``, the two reverse-identity
lookups, ``FrameState``, the ``_FrameTree`` singleton (41 members) and ``Frame`` (**115 members**). This
file carries the first of those: **lines 44-269** — the constants, the three exception classes,
``resolve_key``, the reverse tables and ``_position_unusable``, and ``FrameState``. Everything up to
``_FrameTree`` is here; ``_FrameTree`` and ``Frame`` are the next sections, and they are the two that are
built on the injected runtime's UI manager.

**Two imports could not be carried, and they are the module's whole dependency story.** The source does
``import PyOverlay`` and ``import PyUIManager`` (``:47-48``) and reaches
``PyUIManager.UIManager`` **52 times**, ``PyUIManager.UIFrame`` five times and ``PyOverlay.Vec2f`` eight.
Those are the injected runtime's modules; this port has neither. The one place the *ported* section needs
them is ``FrameState.__init__``, whose own docstring says so — "constructing this is the *only* place a
``PyUIManager.UIFrame`` comes into existence" — and the port answers it with the read that binding wraps:
``PyUIManager.UIFrame(frame_id)`` is native's frame record by id, which this port reads as
``client.frame_array.get(frame_id)`` (``py4gw/ui/frame.py``, documented there as "matching the native
``GetFrameById``"). The same decision applies to the 52 ``PyUIManager.UIManager`` calls when ``_FrameTree``
and ``Frame`` are ported: each one is a native ``ui::*`` function, and each gets resolved member by member
the way ``PySkill`` was in ``model_enums`` — never guessed as a group.

``__all__`` is the source's list (``:55-67``) minus the two names the later sections bring (``Frame`` and
``FrameTree``); a list that named definitions this file does not have would break ``import *``.
"""

from __future__ import annotations

import re
import struct
from typing import Any, Iterator, Optional

from .frame_aliases import FRAME_ALIASES
from .frame_ids import FrameId
from .frame_names import FRAME_NAMES, NAME_TO_HASH
from .frame_registry import DYNAMIC_KEYS, REGISTRY
from ..game_thread.shared_block import CallForm

__all__ = [
    "FrameError",
    "FrameKeyError",
    "FrameNotFound",
    "FrameState",
    "RELATION_FIRST_CHILD",
    "RELATION_LAST_CHILD",
    "RELATION_NEXT_SIBLING",
    "RELATION_PREV_SIBLING",
    "resolve_key",
]

_MOUSE_HOVER_STATE = 9

#: ``ui.send_frame_ui_message_func`` (``offsets/ui.json``, resolved from ``ui_patterns.cpp``): the
#: client's own callbacks-based UI-message sender, which native holds as
#: ``g_send_frame_ui_message_original`` (``ui_methods.cpp:1332-1345``).
_SEND_FRAME_UI_MESSAGE_FUNC = "ui.send_frame_ui_message_func"

#: ``ui::UIMessage::kMouseClick2`` (``constants/ui.h:19``): the message ``ui::ButtonClick`` sends.
_K_MOUSE_CLICK_2 = 0x31

#: ``ui::packet::ActionState::MouseUp`` (``ui.h:570``).
_MOUSE_UP = 0x7

#: ``Frame::IsCreated()`` (``ui.h:496``): ``(frame_state & 0x4) != 0``.
_FRAME_STATE_CREATED = 0x4

#: Where the two structs ``ui::ButtonClick`` hands the client live in the block's data region
#: (``ui_methods.cpp:1259-1273``): a five-word ``packet::MouseAction`` and the three-word
#: ``ButtonParam`` its ``wparam`` points at. Native builds both on its own stack; this project has no
#: frame in the client, so they go where a pointer argument can reach them. The region's other users
#: hold 0-15 (the render capture slot and the DAT reader's hash and size), 4 onward (the watched
#: message's string) and 16-296 (the chat buffer), and the camera writes at ``0x200``.
_MOUSE_ACTION_OFFSET = 0x300
_BUTTON_PARAM_OFFSET = 0x320

# native relation_kind values for get_related_frame_id
RELATION_FIRST_CHILD = 0
RELATION_LAST_CHILD = 1
RELATION_NEXT_SIBLING = 2
RELATION_PREV_SIBLING = 3


# --------------------------------------------------------------------------
def _unported(member: str, requirement: str) -> NotImplementedError:
    """Build the error raised by a member this port has not built yet."""

    return NotImplementedError(
        f"{member} is declared but not built here yet: it needs {requirement}. "
        "The source's member works; this port raises at the call site and names the work "
        "item instead of returning a wrong value."
    )


class FrameError(Exception):
    """Base for every FrameTree failure."""


class FrameKeyError(FrameError):
    """The registry key does not exist, or names a per-session dynamic entry."""


class FrameNotFound(FrameError):
    """The key is valid but no live frame matches it."""


# --------------------------------------------------------------------------
def resolve_key(key: str) -> tuple[str, tuple[int, ...]]:
    """Registry key -> (anchor frame name, relative child codes)."""

    parts = key.split(".")
    entry = REGISTRY.get(parts[0])
    if entry is None:
        raise FrameKeyError("unknown registry key %r (no top-level %r)" % (key, parts[0]))

    if isinstance(entry, str):
        anchor, kids = entry, {}
    else:
        anchor, kids = entry[0], (entry[1] if len(entry) > 1 else {})

    tail: list[int] = []
    for i, seg in enumerate(parts[1:], 1):
        if seg not in kids:
            raise FrameKeyError(
                "unknown registry key %r: %r has no child %r"
                % (key, ".".join(parts[:i]), seg)
            )
        node = kids[seg]
        if isinstance(node, int):
            tail.append(node)
            kids = {}
        else:
            tail.append(node[0])
            kids = node[1]
    return anchor, tuple(tail)


# --------------------------------------------------------------------------
# Reverse identity tables.  A live frame knows only its hash and child codes, so
# to name an arbitrary frame we invert the registry and the alias map onto the
# same "<anchor_hash>,<code>,<code>" form that Frame.path() produces.  Both are
# built once, on first use.
_alias_by_path: Optional[dict[str, str]] = None
_key_by_path: Optional[dict[str, str]] = None


def _path_of(anchor_name: str, codes) -> Optional[str]:
    h = NAME_TO_HASH.get(anchor_name)
    if h is None:
        return None
    return ",".join([str(h)] + [str(c) for c in codes])


def alias_by_path() -> dict[str, str]:
    """"<hash>,<codes>" -> prose alias, inverted from FRAME_ALIASES."""

    global _alias_by_path
    if _alias_by_path is None:
        out: dict[str, str] = {}
        for key, label in FRAME_ALIASES.items():
            parts = key.split(",")
            p = _path_of(parts[0], parts[1:])
            if p is not None:
                out.setdefault(p, label)
        _alias_by_path = out
    return _alias_by_path


def key_by_path() -> dict[str, str]:
    """"<hash>,<codes>" -> dotted registry key, inverted from REGISTRY."""

    global _key_by_path
    if _key_by_path is None:
        out: dict[str, str] = {}

        def walk(prefix: str, anchor: str, tail: list, kids: dict) -> None:
            p = _path_of(anchor, tail)
            if p is not None:
                out.setdefault(p, prefix)
            for name, node in (kids or {}).items():
                if isinstance(node, int):
                    walk(prefix + "." + name, anchor, tail + [node], {})
                else:
                    walk(prefix + "." + name, anchor, tail + [node[0]],
                         node[1] if len(node) > 1 else {})

        for top, entry in REGISTRY.items():
            if isinstance(entry, str):
                walk(top, entry, [], {})
            else:
                walk(top, entry[0], [], entry[1] if len(entry) > 1 else {})
        _key_by_path = out
    return _key_by_path


# --------------------------------------------------------------------------
def _position_unusable(p: Any) -> bool:
    """True for the zeroed position struct the engine leaves on a missed lookup.

    A real frame always has a positive viewport scale; a zero scale, or a
    rectangle collapsed onto the origin, means the read did not land.
    """

    if p is None:
        return True
    try:
        if float(getattr(p, "viewport_scale_x", 0.0)) <= 0.0:
            return True
        if float(getattr(p, "viewport_scale_y", 0.0)) <= 0.0:
            return True
        return not any((
            float(getattr(p, "left_on_screen", 0.0)),
            float(getattr(p, "top_on_screen", 0.0)),
            float(getattr(p, "right_on_screen", 0.0)),
            float(getattr(p, "bottom_on_screen", 0.0)),
        ))
    except Exception:
        return True


# --------------------------------------------------------------------------
class FrameState:
    """One live read of a frame, valid only for the tick that produced it.

    Constructing this is the *only* place a PyUIManager.UIFrame comes into
    existence.  `is_created` / `is_visible` come from that single read; the
    position object is fetched on first use because most frames never need it.

    The port's answer for that one read is the frame record by id
    (``client.frame_array.get(frame_id)``); see the module docstring.
    """

    __slots__ = ("frame_id", "frame", "is_created", "is_visible", "tick",
                 "_position", "_previous", "_landed", "served")

    def __init__(self, frame_id: int, tick: int = 0, previous: Any = None) -> None:
        from ..client import require_client

        self._previous = previous
        self._landed: Optional[bool] = None
        self.served = 0        # ticks this copy has stood in for a failed read
        self.frame_id = frame_id
        self.tick = tick
        try:
            self.frame = require_client().frame_array.get(frame_id)
        except Exception:
            self.frame = None
        f = self.frame
        self.is_created = bool(getattr(f, "is_created", False)) if f is not None else False
        self.is_visible = bool(getattr(f, "is_visible", False)) if f is not None else False
        self._position: Any = None

    @property
    def landed(self) -> bool:
        """Did this read produce usable data?

        The engine fills the whole frame struct in one pass, so when its lookup
        misses, everything zeroes together - state, geometry, viewport.  There is
        therefore one verdict for the whole snapshot rather than a test per
        field: either the read landed, or the copy is worthless and the previous
        one should be served instead.
        """

        if self._landed is None:
            if self.frame is None or not (self.is_created or self.is_visible):
                self._landed = False
            else:
                self._landed = not _position_unusable(
                    getattr(self.frame, "position", None))
        return self._landed

    @property
    def blank(self) -> bool:
        return not self.landed

    @property
    def position(self) -> Any:
        """Geometry for this frame, holding the last good read.

        Frame geometry barely changes tick to tick, so an unusable read is far
        more likely to be a missed lookup than a real move.  Rather than hand
        back zeros - which collapse every projection onto the origin - reuse the
        previous copy until a usable one arrives.
        """

        if self._position is None:
            fresh = self.frame.position if self.frame is not None else None
            if _position_unusable(fresh) and self._previous is not None:
                inherited = self._previous.position
                if not _position_unusable(inherited):
                    self._position = inherited
                    self._previous = None      # value carried; drop the chain
                    return inherited
            self._position = fresh
            self._previous = None
        return self._position


# --------------------------------------------------------------------------
class _FrameTree:
    """The live tree.  Owns the structure snapshot and the per-frame state cache.

    Refresh is lazy per tick, not an eager sweep: the PreUpdate callback only
    bumps a counter.  The structure snapshot is rebuilt on the first resolution
    of a tick, and per-frame state is read on first touch of that frame.  A tick
    in which no frame is touched costs nothing.

    **What is ported so far**, in the source's own order: ``__init__`` (``:288-303``), ``enable``
    (``:306-314``), ``disable`` (``:316-322``), ``_on_tick`` (``:324-326``), ``rebuild`` (``:329-370``) and
    ``ensure`` (``:372-375``). The thirty-five that follow in the source — the tree's queries and its twelve
    other injected members — are the next section; ``FRAME_TREE_PORT.md`` §2 carries the whole map.

    **The tick-keyed snapshot, and the port's answer.** The source rebuilds once per tick, where that tick is
    a registration with the injected ``PyCallback``, and serves the snapshot in between. This port has no
    frame loop, so ``enable`` and ``disable`` — which exist only to make and drop that registration — raise
    and name it, while ``ensure`` rebuilds on the call: the same adaptation ``@frame_cache`` got, since with
    no frame boundary to key a memo to, the member reads when it is called. ``_CALLBACK``, ``BUFFER_TICKS``,
    ``tick``, ``_built_tick`` and ``_on_tick`` are the source's own and stay as written, so the snapshot's
    shape is unchanged.
    """

    _CALLBACK = "FrameTree.Tick"
    BUFFER_TICKS = 5      # passes a good copy may stand in for a failed read.
                          # Counted in polls, not time: the system reads every
                          # frame, so this is at most 5 frames behind, whatever
                          # the framerate.

    def __init__(self) -> None:
        self.version = 0          # bumps on every structure rebuild
        self.tick = 0             # bumps every PreUpdate
        self._built_tick = -1
        self._parent: dict[int, int] = {}
        self._code: dict[int, int] = {}
        self._hash: dict[int, int] = {}
        self._children: dict[int, dict[int, list[int]]] = {}
        self._order: list[int] = []
        self._by_hash: dict[int, list[int]] = {}
        self._state: dict[int, FrameState] = {}
        self._registered = False
        self.stale = False   # last rebuild came back empty; showing the previous tree
        self._root_id = 0    # last good UI root id
        self._viewport_height = 0.0
        self._overlay: Any = None

    # -- lifecycle --------------------------------------------------------
    def enable(self) -> None:
        """``_FrameTree.enable`` (``frame.py:306-314``).

        The source registers ``self._on_tick`` with the injected ``PyCallback`` at ``Phase.PreUpdate,
        priority=6`` — that registration *is* the tick this tree's snapshot is keyed to, and this port has
        no frame loop to register with, so the member names that instead of registering nothing.
        """

        raise _unported(
            "FrameTree.enable",
            "the injected per-frame callback registry (PyCallback.PyCallback.Register at "
            "Phase.PreUpdate), which is Reforged's frame loop — this port has no frame boundary to "
            "register a tick with",
        )

    def disable(self) -> None:
        """``_FrameTree.disable`` (``frame.py:316-322``): the other half of that registration."""

        raise _unported(
            "FrameTree.disable",
            "the injected per-frame callback registry (PyCallback.PyCallback.RemoveByName), which is "
            "Reforged's frame loop",
        )

    def _on_tick(self) -> None:
        """Invalidate.  Deliberately does no work beyond the counter."""

        self.tick += 1

    # -- structure snapshot -----------------------------------------------
    def rebuild(self) -> None:
        """``_FrameTree.rebuild`` (``frame.py:329-370``).

        The source walks ``PyUIManager.UIManager.get_frame_array()`` and constructs a
        ``PyUIManager.UIFrame`` per id to read ``parent_id``, ``child_offset_id`` and ``frame_hash``. The
        port walks the same array through ``client.frame_array``, whose ``iter_frames()`` yields a frame id
        together with its record — one pass, the record's own fields, nothing constructed.
        """

        from ..client import require_client

        parent: dict[int, int] = {}
        code: dict[int, int] = {}
        fhash: dict[int, int] = {}
        children: dict[int, dict[int, list[int]]] = {}
        order: list[int] = []
        by_hash: dict[int, list[int]] = {}

        for fid, fr in require_client().frame_array.iter_frames():
            fid = int(fid)
            order.append(fid)
            if fr is None:
                continue
            pid = int(getattr(fr, "parent_id", 0) or 0)
            cod = int(getattr(fr, "child_offset_id", 0) or 0)
            h = int(getattr(fr, "frame_hash", 0) or 0)
            parent[fid] = pid
            code[fid] = cod
            fhash[fid] = h
            # a code is normally unique per parent, but siblings can collide -
            # keep every one so enumeration does not silently lose frames
            children.setdefault(pid, {}).setdefault(cod, []).append(fid)
            if h:
                by_hash.setdefault(h, []).append(fid)

        # The engine returns an EMPTY array whenever its frame array pointer is
        # null - during map load, UI teardown, or before the UI context exists.
        # That is not "the UI is gone", it is "we cannot see it this tick".
        # Swapping an empty snapshot in makes every handle stop resolving for a
        # frame or two, which is what made overlays flicker.  Keep the last good
        # tree instead and try again next tick.
        self._built_tick = self.tick
        if not order and self._order:
            self.stale = True
            return

        self.stale = False
        self._parent, self._code, self._hash = parent, code, fhash
        self._children, self._order, self._by_hash = children, order, by_hash
        self.version += 1

    def ensure(self) -> None:
        """``_FrameTree.ensure`` (``frame.py:372-375``), with the tick gate answered by the call.

        The source is ``self.enable(); if self._built_tick != self.tick: self.rebuild()`` — the
        registration starts the tick that makes that test true once per frame. With no ticker, the same
        test would be false after the first rebuild and the tree would be pinned for the life of the
        process, so the port rebuilds whenever it is asked (``FRAME_TREE_PORT.md`` §2).
        """

        self.rebuild()

    # -- per-frame live copy (``frame.py:378-423``) ------------------------
    def state(self, frame_id: int) -> FrameState:
        """The live copy of one frame for this tick, read at most once.

        Entries are overwritten in place rather than cleared each tick.  A frame
        that is still in the tree but reads back blank - GetContext bailing on a
        transient null - keeps its previous copy, so a caller reading geometry
        never sees a one-frame hole.  A frame that has genuinely left the tree
        gets the blank read, because then it really is gone.

        **The port drops one test and keeps the rest.** The source opens with
        ``if previous is not None and previous.tick == self.tick: return previous`` (`:387-389`) — the memo
        that makes it "read at most once per tick". Nothing advances `tick` here, so that test would hand
        back the *first* copy of a frame for the life of the process; the member reads when it is called, as
        `ensure` does (`FRAME_TREE_PORT.md` §2). The buffer rule below is kept exactly: what it counts is
        polls, which the source's own comment says, so it needs no tick to keep its meaning.
        """

        previous = self._state.get(frame_id)

        fresh = FrameState(frame_id, self.tick, previous)
        if (not fresh.landed and previous is not None and previous.landed
                and previous.served < self.BUFFER_TICKS):
            # The read did not land but we have a good copy from a moment ago.
            # Geometry barely moves between ticks, so redrawing from the buffer
            # is far closer to the truth than a zeroed struct - and one bad tick
            # is enough to blank an overlay or flip it into a fallback mode.
            # Bounded, so a frame that stops reporting eventually tells the truth.
            previous.served += 1
            previous.tick = self.tick
            return previous

        self._state[frame_id] = fresh
        if len(self._state) > 4096:
            self._prune()
        return fresh

    def _prune(self) -> None:
        """Drop copies nothing has touched for a while.

        The cutoff is the source's own (``self.tick - 240``, `:410`). With no ticker it never advances, so
        this cannot fire here — recorded as a limitation rather than given an invented clock: the port drops
        the tick-keyed *gate* on the reads (`state`, `ensure`) and leaves this age rule as written.
        """

        cutoff = self.tick - 240
        for fid in [f for f, st in self._state.items() if st.tick < cutoff]:
            del self._state[fid]

    def invalidate(self, frame_id: Optional[int] = None) -> None:
        """Drop cached live copies so the next read hits the game again.

        Only needed when something is expected to change *within* a tick; the
        tick boundary invalidates everything on its own.
        """

        if frame_id is None:
            self._state.clear()
        else:
            self._state.pop(int(frame_id), None)

    # -- structure queries (``frame.py:426-526``) --------------------------
    def anchor_ids(self, anchor) -> list[int]:
        """``_FrameTree.anchor_ids`` (``frame.py:426-460``).

        Two injected calls sit in this member, and each was resolved to the native function it wraps:

        * ``PyUIManager.UIManager.get_frame_id_by_hash(h)`` is native ``GetFrameIDByHash``
          (``ui_methods.cpp:575-588``): scan the frame array in id order and take the first valid frame
          whose ``frame_hash_id`` matches.  Native's ``IsFrameValid`` (``:405-407``) rejects a null or
          ``-1`` record pointer, which here is a slot that read back ``None`` — so the port's scan is the
          same scan over the same array.
        * ``PyUIManager.UIManager.get_frame_id_by_label(label)`` is native ``GetFrameIDByLabel``
          (``:570-573``) → ``GetFrameByLabel`` (``:556-568``), whose *first* step is ``GetHashByLabel``
          (``:542-546``): the client's own ``CreateHashFromWChar`` over a wide string.  **This port cannot
          hash an arbitrary label** — the offline name table is the source's own earlier step and is
          already taken above, and hashing a label the table does not know is a call into the client with
          a wide string, a call form the capability layer does not have yet
          (``docs/TARGET_SIDE_WORK.md``).  Raising there names that work item; the source's own
          ``except Exception`` turns a failing lookup into 0, so what runs next is the source's own
          failure path, not a behaviour added here.
        """

        from ..client import require_client

        if isinstance(anchor, int):
            h = anchor
            label = ""
        else:
            label = str(anchor)
            h = NAME_TO_HASH.get(label)
            if h is None:
                raise FrameKeyError("no known frame named %r" % label)

        found = self._by_hash.get(h)
        if found:
            return found

        # A name-table hash comes from offline RE and can lag the client.  When
        # resolving a registry anchor, the client can hash the literal label
        # itself; prefer that authoritative fallback before treating the frame
        # as absent.  Dynamic callers that supply a raw hash still use the
        # hash lookup below.
        if label:
            try:
                raise _unported(
                    "_FrameTree.anchor_ids",
                    "PyUIManager.UIManager.get_frame_id_by_label — the client's own "
                    "CreateHashFromWChar over a wide string (native ui_methods.cpp:542-573), i.e. the "
                    "wide-string call form; the offline name table is the source's earlier step and is "
                    "already taken above",
                )
            except Exception:
                fid = 0
            if fid:
                return [fid]

        # The snapshot has not seen this hash - it may be a tick behind, or the
        # sweep may have missed it.  Ask the engine directly, the way the legacy
        # code always did, rather than reporting the frame as gone.
        try:
            # PyUIManager.UIManager.get_frame_id_by_hash(h) → native GetFrameIDByHash
            # (``ui_methods.cpp:575-588``): `if (!(hash && frame_array)) return 0;` then the first valid
            # frame whose relation.frame_hash_id matches, scanning by frame id.
            fid = 0
            if h:
                for cand, record in require_client().frame_array.iter_frames():
                    if record is not None and int(getattr(record, "frame_hash", 0) or 0) == int(h):
                        fid = int(cand)
                        break
        except Exception:
            fid = 0
        return [fid] if fid else []

    def child_of(self, frame_id: int, code: int) -> Optional[int]:
        got = self._children.get(frame_id, {}).get(code)
        return got[0] if got else None

    def children_at(self, frame_id: int, code: int) -> list[int]:
        """Every child under `code` - normally one, occasionally colliding siblings."""
        return list(self._children.get(frame_id, {}).get(code, ()))

    def children_of(self, frame_id: int) -> list[int]:
        out: list[int] = []
        for ids in self._children.get(frame_id, {}).values():
            out.extend(ids)
        return sorted(out)

    def child_codes_of(self, frame_id: int) -> list[int]:
        return sorted(self._children.get(frame_id, {}).keys())

    def parent_of(self, frame_id: int) -> int:
        return self._parent.get(frame_id, 0)

    def hash_of(self, frame_id: int) -> int:
        return self._hash.get(frame_id, 0)

    def code_of(self, frame_id: int) -> int:
        return self._code.get(frame_id, 0)

    def known(self, frame_id: int) -> bool:
        return frame_id in self._parent

    def live(self, frame_id: int) -> bool:
        """Ask the engine directly whether this frame is real.

        The structure snapshot is at best a tick old, and an id handed to us by
        another subsystem - a native context, say - can be valid before we have
        ever seen it in a frame-array sweep.  Treating "not in my snapshot" as
        "does not exist" is what made geometry collapse to the origin for a
        frame at a time; the legacy code asked the engine every call and never
        had that failure.  This is that check, served from the per-tick copy.

        The port's answer for the raw read is the same one ``rebuild`` uses —
        ``client.frame_array.get(int(frame_id))`` — which re-reads the array slot
        rather than consulting anything this class kept.
        """

        from ..client import require_client

        if not frame_id:
            return False
        # a RAW read - never the retained copy, or existence would feed on the
        # very cache it is meant to validate and a removed frame would never die
        try:
            f = require_client().frame_array.get(int(frame_id))
        except Exception:
            return False
        return bool(
            f is not None
            and (getattr(f, "is_created", False) or getattr(f, "is_visible", False))
        )

    # -- tree-wide bindings (tier 2) --------------------------------------
    def all_ids(self) -> list[int]:
        """Every live frame id, in native frame-array order."""

        self.ensure()
        return list(self._order)

    def all_frames(self) -> list["Frame"]:
        return [Frame.from_id(f) for f in self.all_ids()]

    def children_map(self) -> dict[int, list[int]]:
        """parent id -> child ids, children in native frame-array order."""

        self.ensure()
        out: dict[int, list[int]] = {}
        for fid in self._order:
            out.setdefault(self._parent.get(fid, 0), []).append(fid)
        return out

    @staticmethod
    def _as_id(frame_or_id: Any) -> int:
        """Accept a Frame or a raw id, so callers never have to unwrap."""
        if isinstance(frame_or_id, Frame):
            return frame_or_id._target_id()
        return int(frame_or_id or 0)

    def descendants(self, frame: Any) -> list["Frame"]:
        """Breadth-first descendant handles."""
        return [Frame.from_id(i) for i in self.descendants_of(frame)]

    def descendants_of(self, frame_id: Any) -> list[int]:
        """Breadth-first descendants, native order within each level."""
        from collections import deque

        frame_id = self._as_id(frame_id)
        kids = self.children_map()
        out: list[int] = []
        queue = deque([frame_id])
        while queue:
            cur = queue.popleft()
            for c in kids.get(cur, []):
                out.append(c)
                queue.append(c)
        return out

    def root(self) -> "Frame":
        """The UI root.  Cached: it never changes, and a transient 0 from the
        engine would otherwise zero out every viewport-relative calculation.

        ``PyUIManager.UIManager.get_root_frame_id`` is native ``GetRootFrame`` (``ui_methods.cpp:415-417``),
        whose whole body is the client's own ``g_get_root_frame_func`` — and the catalog carries that pointer
        (``offsets/ui.json:414-416``, scanned from the ``get_root_frame`` pattern), so this port calls it the
        way native does: no arguments, giving a ``Frame*``.  Native's binding then answers
        ``root ? root->frame_id : 0``, which here is one word read at ``+FrameStruct.frame_id.offset`` (this
        port declares it at ``0xBC``).  The source's ``self._root_id`` cache is kept as written: a transient
        zero from the engine would otherwise zero every viewport-relative calculation.

        Like every call in this port it needs the capability layer, so a read-only connection is refused by
        the call itself rather than answered with a stand-in.
        """

        from ..client import require_client
        from ..ui.frame import FrameStruct

        client = require_client()
        record = client.call_function("ui.get_root_frame_func", CallForm.NO_ARGS)
        pointer = int(record.result)
        fid = 0
        if pointer:
            fid = int(client.frame_array.read_u32(pointer + FrameStruct.frame_id.offset) or 0)
        if fid:
            self._root_id = fid
        return Frame.from_id(fid or self._root_id)

    def viewport_height(self) -> float:
        """Screen height of the UI root, held across transient misses.

        The source is ``self.root().viewport_dimensions()`` plus the ``self._viewport_height`` cache, so this
        member answers exactly when `root` does — it names the root read rather than failing obscurely, and
        the body below is the source's, unchanged.
        """

        _, height = self.root().viewport_dimensions()
        if height:
            self._viewport_height = height
        return self._viewport_height

    def hierarchy(self) -> list[tuple[int, int, int, int]]:
        """Native flat hierarchy dump: (frame_id, parent_id, code, hash) rows.

        **That docstring is the source's, and native's own code disagrees with it — recorded, not corrected.**
        ``GetFrameHierarchy`` (``ui_methods.cpp:1866-1884``) skips any frame that is not valid, created **and
        visible**, and pushes ``(parent->relation.frame_hash_id, frame->relation.frame_hash_id,
        parent->frame_id, frame->frame_id)`` — parent hash first, then the frame's own hash, then the two ids.
        The port returns that order, read off the same frame array `rebuild` walks: the parent's two words are
        read at the parent's relation pointer, which is the rule `parent_id_native` already uses.
        """

        from ..client import require_client
        from ..ui.frame import FrameRelationStruct, FrameStruct

        array = require_client().frame_array
        out: list[tuple[int, int, int, int]] = []
        for frame_id, record in array.iter_frames():
            if record is None:
                continue
            if not (getattr(record, "is_created", False) and getattr(record, "is_visible", False)):
                continue
            relation = getattr(record, "relation", None)
            own_hash = int(getattr(relation, "frame_hash_id", 0) or 0) if relation is not None else 0
            parent_relation = int(getattr(relation, "parent", 0) or 0) if relation is not None else 0
            parent_hash = 0
            parent_id = 0
            if parent_relation:
                parent_hash = int(array.read_u32(
                    parent_relation + FrameRelationStruct.frame_hash_id.offset) or 0)
                parent_id = int(array.read_u32(
                    parent_relation - FrameStruct.relation.offset + FrameStruct.frame_id.offset) or 0)
            out.append((parent_hash, own_hash, parent_id, int(frame_id)))
        return out

    def overlay_frames(self) -> list["Frame"]:
        """``get_overlay_frame_ids`` (``frame.py:573-574``).

        Native ``GetOverlayFrames`` (``ui_methods.cpp:622-634``) scans the frame array and returns the id of
        every frame that is valid and **created**.  ``GetPopupFrames`` (``:636-648``) has a byte-identical
        body, so `popup_frames` repeats this scan — the two native functions are one function written twice,
        and the port keeps both members' own scans rather than adding a helper the sources do not have.
        """

        from ..client import require_client

        out: list[int] = []
        for frame_id, record in require_client().frame_array.iter_frames():
            if record is None:
                continue
            if getattr(record, "is_created", False):
                out.append(int(frame_id))
        return [Frame.from_id(int(i)) for i in out]

    def popup_frames(self) -> list["Frame"]:
        """``get_popup_frame_ids`` (``frame.py:576-577``) — the same scan as `overlay_frames`.

        ``GetPopupFrames`` (``ui_methods.cpp:636-648``) is byte-for-byte ``GetOverlayFrames``: valid and
        created frames, in array order.
        """

        from ..client import require_client

        out: list[int] = []
        for frame_id, record in require_client().frame_array.iter_frames():
            if record is None:
                continue
            if getattr(record, "is_created", False):
                out.append(int(frame_id))
        return [Frame.from_id(int(i)) for i in out]

    def by_hash(self, frame_hash: int) -> "Frame":
        """Handle on the frame carrying `frame_hash` (native lookup).

        ``PyUIManager.UIManager.get_frame_id_by_hash`` → native ``GetFrameIDByHash``
        (``ui_methods.cpp:575-588``), the same read ``anchor_ids`` makes: the frame array scanned in id
        order for the first valid frame whose ``frame_hash_id`` matches.
        """

        from ..client import require_client

        fid = 0
        if frame_hash:
            for cand, record in require_client().frame_array.iter_frames():
                if record is not None and int(getattr(record, "frame_hash", 0) or 0) == int(frame_hash):
                    fid = int(cand)
                    break
        return Frame.from_id(int(fid or 0))

    def by_label(self, label: str) -> "Frame":
        """Handle on the frame at a legacy alias label (native lookup).

        Needs ``PyUIManager.UIManager.get_frame_id_by_label``, which is native ``GetFrameIDByLabel``
        (``ui_methods.cpp:570-573``) → ``GetFrameByLabel`` (``:556-568``): hash the label with the client's
        own ``CreateHashFromWChar`` (``:542-546``), then scan for that hash. Hashing a label the offline
        table does not know is a call into the client with a wide string, and that call form is not in the
        capability layer yet (``docs/TARGET_SIDE_WORK.md``). Unlike ``anchor_ids``, this member makes no
        fallback, so it raises rather than returning a plausible id.
        """

        raise _unported(
            "_FrameTree.by_label",
            "PyUIManager.UIManager.get_frame_id_by_label — the client's CreateHashFromWChar over a wide "
            "string (native ui_methods.cpp:542-573), i.e. the wide-string call form",
        )

    def hash_for_label(self, label: str) -> int:
        """The hash the client computes for `label` (``frame.py:587-588``).

        ``PyUIManager.UIManager.get_hash_by_label`` is native ``GetHashByLabel``
        (``ui_methods.cpp:542-546``), whose whole body is the client's ``CreateHashFromWChar(label, -1)`` —
        a call, not a read, and it needs the wide-string call form that is still outstanding
        (``docs/TARGET_SIDE_WORK.md``). The port therefore names the work item instead of returning a
        number; ``Frame.from_label`` is the source's own offline-table route and is ported.
        """

        raise _unported(
            "_FrameTree.hash_for_label",
            "PyUIManager.UIManager.get_hash_by_label — native GetHashByLabel (ui_methods.cpp:542-546), the "
            "client's CreateHashFromWChar over a wide string, i.e. the wide-string call form",
        )

    def coords_for_hash(self, frame_hash: int) -> list[tuple[int, int]]:
        """``get_frame_coords_by_hash`` (``frame.py:590-591``).

        Native ``GetFrameCoordsByHash`` (``ui_methods.cpp:1886-1900``) finds the frame with
        ``GetFrameIDByHash`` — the scan `by_hash` makes, hash ``0`` answering nothing — then returns two corner
        pairs, ``(screen_left, screen_top)`` and ``(screen_right, screen_bottom)``, each word cast to
        ``uint32_t`` (which is the truncating cast reproduced here).
        """

        from ..client import require_client

        if not frame_hash:
            return []
        array = require_client().frame_array
        found = 0
        for frame_id, record in array.iter_frames():
            relation = getattr(record, "relation", None) if record is not None else None
            if relation is not None and int(getattr(relation, "frame_hash_id", 0) or 0) == int(frame_hash):
                found = int(frame_id)
                break
        if not found:
            return []
        record = array.get(found)
        position = getattr(record, "position", None) if record is not None else None
        if position is None:
            return []
        return [
            (int(getattr(position, "screen_left", 0.0)) & 0xFFFFFFFF,
             int(getattr(position, "screen_top", 0.0)) & 0xFFFFFFFF),
            (int(getattr(position, "screen_right", 0.0)) & 0xFFFFFFFF,
             int(getattr(position, "screen_bottom", 0.0)) & 0xFFFFFFFF),
        ]

    def child_by_parent_hash(self, parent_hash: int, child_offsets: list[int]) -> "Frame":
        """``get_child_frame_id`` (``frame.py:593-596``).

        Native ``GetChildFrameID`` (``ui_methods.cpp:589-607``) starts at ``GetFrameIDByHash(parent_hash)`` and
        then walks one ``g_get_child_frame_id_func(id, offset)`` per code — the client's own lookup, the same
        function `Frame.child_native` and `Frame.child_path_native` wait on.
        """

        raise _unported(
            "_FrameTree.child_by_parent_hash",
            "PyUIManager.UIManager.get_child_frame_id — native GetChildFrameID (ui_methods.cpp:589-607): one "
            "client call per code through g_get_child_frame_id_func",
        )

    def frames_at_path(self, anchor: Any, codes: list[int]) -> list["Frame"]:
        """Every frame whose code path from `anchor` is exactly `codes`.

        `Frame(key)` stops at the first match; this returns all of them, which is
        what dialog option enumeration needs.  Served from the snapshot, so it
        costs a dict walk per frame rather than a UIFrame construction.
        """
        self.ensure()
        return self._frames_at(set(self.anchor_ids(anchor)), codes)

    def frames_under(self, anchor_frame_id: Any, codes: list[int]) -> list["Frame"]:
        """`frames_at_path` anchored on one known frame instead of a hash."""
        self.ensure()
        anchor_frame_id = self._as_id(anchor_frame_id)
        if not anchor_frame_id:
            return []
        return self._frames_at({int(anchor_frame_id)}, codes)

    def _frames_at(self, anchor_ids: set, codes: list[int]) -> list["Frame"]:
        if not anchor_ids:
            return []
        depth = len(codes)
        out: list[int] = []
        for fid in self._order:
            trace = fid
            walked: list[int] = []
            for _ in range(depth):
                walked.insert(0, self.code_of(trace))
                pid = self.parent_of(trace)
                if not pid:
                    break
                trace = pid
            if trace in anchor_ids and walked == list(codes):
                out.append(fid)
        return [Frame.from_id(f) for f in out]

    def sort_by_vertical(self, frames: list["Frame"]) -> list["Frame"]:
        """Top of screen first."""
        return sorted(frames, key=lambda f: f.rect[1])

    def color_frames(self, anchor: Any, codes: list[int], debug: bool = False) -> None:
        """Tint every frame at a code path a distinct colour - a debug aid.

        The body is `sort_by_vertical(frames_at_path(...))` — both ported — and then a `Frame.draw(colour)`
        per frame, with a debug branch that logs through ``ConsoleLog``.  Drawing needs the injected overlay
        (``FrameTree.overlay``, `frame.py:669-672` → ``PyOverlay.Overlay()``) and the log needs Reforged's
        ``Py4GWCoreLib`` module, which this port has not ported — so the member names both rather than porting
        a body whose only effect would be a call it cannot make.
        """

        raise _unported(
            "_FrameTree.color_frames",
            "FrameTree.overlay / Frame.draw (frame.py:638-665 → 669-672) — the injected runtime's PyOverlay "
            "manager; and Reforged's Py4GWCoreLib module (Console, ConsoleLog) for its debug branch",
        )

    @property
    def overlay(self) -> Any:
        """``PyOverlay.Overlay()``, the injected runtime's overlay manager (``frame.py:667-672``).

        It is created here, in the injected runtime's own process, and every drawing member goes through it —
        `Frame.draw`, `Frame.draw_outline` and `color_frames`.  With no PyOverlay there is nothing to return,
        so the member names it instead of handing back a stand-in renderer.
        """

        raise _unported(
            "_FrameTree.overlay",
            "PyOverlay.Overlay() (frame.py:669-672) — the injected runtime's overlay manager, which this port "
            "does not carry; the source caches it in self._overlay",
        )


# --------------------------------------------------------------------------
FrameTree = _FrameTree()


# --------------------------------------------------------------------------
class Frame:
    """A handle on one native frame.  Owns every frame-scoped binding."""

    __slots__ = ("_key", "_anchor", "_tail", "_fid", "_version", "_blackboard")

    def __init__(self, key: Any, _frame_id: Optional[int] = None) -> None:
        if _frame_id is not None:          # internal: wrap a known frame id
            self._key = ""
            self._anchor: Any = ""
            self._tail: tuple[int, ...] = ()
            self._fid: Optional[int] = _frame_id
            self._version = -1
            self._blackboard: dict = {}
            return

        key = getattr(key, "KEY", key)
        if not isinstance(key, str):
            raise FrameKeyError("frame key must be a string or a FrameId node, got %r" % (key,))
        if key in DYNAMIC_KEYS:
            raise FrameKeyError(
                "%r has per-session runtime codes and cannot be resolved from the "
                "registry; locate it by walking the live tree instead" % key
            )
        self._key = key
        self._anchor, self._tail = resolve_key(key)
        self._fid = None
        self._version = -1
        self._blackboard = {}

    @classmethod
    def from_id(cls, frame_id: int) -> "Frame":
        """Wrap a frame id we already have."""
        return cls(None, _frame_id=int(frame_id))

    @classmethod
    def from_hash(cls, frame_hash: int, codes=(),
                  blackboard: Optional[dict] = None) -> "Frame":
        """Deferred handle for a runtime-computed path: anchor hash + child codes.

        Use only where the path is not knowable statically (per-bag / per-slot
        item frames).  Everything with a fixed path belongs in the registry.
        """
        f = cls.__new__(cls)
        f._key = ""
        f._anchor = int(frame_hash)
        f._tail = tuple(int(c) for c in codes)
        f._fid = None
        f._version = -1
        f._blackboard = dict(blackboard) if blackboard else {}
        return f

    @classmethod
    def from_label(cls, label: str) -> "Frame":
        """Resolve one of the legacy prose alias labels ("Xunlai Window").

        Kept for callers that select a frame by a runtime label string.  New
        code should use a FrameId constant.
        """
        for path, lab in FRAME_ALIASES.items():
            if lab == label:
                parts = path.split(",")
                h = NAME_TO_HASH.get(parts[0])
                if h is None:
                    break
                return cls.from_hash(h, [int(c) for c in parts[1:]])
        raise FrameKeyError("no frame alias labelled %r" % label)

    # -- named indexed addressing -----------------------------------------
    # The engine addresses a child by (parent, key_code).  Where those codes are
    # computed from game data - a bag number, a slot, a skill id - the
    # arithmetic belongs here, not in a script.  Each accessor takes DOMAIN
    # arguments and resolves a registered parent, so no caller ever names a code.
    @classmethod
    def _under(cls, parent_key: Any, *codes: int) -> "Frame":
        """A registered parent plus computed child codes.  Package-internal."""
        parent = cls(parent_key)
        anchor, tail = parent._anchor, parent._tail
        f = cls.__new__(cls)
        f._key = ""
        f._anchor = anchor
        f._tail = tuple(tail) + tuple(int(c) for c in codes)
        f._fid = None
        f._version = -1
        f._blackboard = {}
        return f

    @classmethod
    def skill(cls, index: int) -> "Frame":
        """Player skillbar slot, 1-based."""
        return cls("Skillbar.Skill%d" % int(index))

    @classmethod
    def hero_skill(cls, hero: int, index: int) -> "Frame":
        """Hero skillbar slot; hero and index both 1-based."""
        return cls("Hero%dWindow.SkillBar.Skill%d" % (int(hero), int(index)))

    @classmethod
    def bag_slot(cls, bag: Any, slot: int) -> "Frame":
        """Slot in the aggregate inventory bags panel.

        `bag` is a Bags enum (or its value) and `slot` is 0-based, matching how
        the game numbers them - the engine's own codes are `bag - Backpack` and
        `slot + 2`, and that arithmetic stays here.
        """
        return cls._under(FrameId.InventoryBagsWindow.Content.C0.C0,
                          cls._bag_offset(bag), 2 + int(slot))

    @staticmethod
    def _bag_offset(bag: Any) -> int:
        """Bag -> its child code.  Accepts a Bags enum or a raw bag value."""
        from ..enums_src.item_enums import Bags

        value = getattr(bag, "value", bag)
        return int(value) - int(Bags.Backpack.value)

    @classmethod
    def inventory_bag(cls, bag: Any) -> "Frame":
        """The standalone window for one bag (not the aggregate bags panel)."""
        return cls._under(FrameId.InventoryWindow, cls._bag_offset(bag))

    @classmethod
    def inventory_bag_slot(cls, bag: Any, slot: int) -> "Frame":
        """Slot inside a standalone bag window; `slot` is 0-based."""
        return cls._under(FrameId.InventoryWindow,
                          cls._bag_offset(bag), 2 + int(slot))

    @staticmethod
    def _storage_offset(bag: Any) -> int:
        """Map a storage bag to its Xunlai content-pane offset."""
        from ..enums_src.item_enums import Bags

        value = getattr(bag, "value", bag)
        if int(value) == int(Bags.MaterialStorage.value):
            return 14
        return int(value) - int(Bags.Storage1.value)

    @classmethod
    def storage_tab(cls, bag: Any, reversed_order: bool = False) -> "Frame":
        """Xunlai storage tab for `bag`.

        `reversed_order` selects the engine's descending tab codes, which the
        tab strip uses while the content panes count up.
        """
        offset = cls._storage_offset(bag)
        code = (0xFFFFFFFF - offset) if reversed_order else offset
        return cls._under(FrameId.XunlaiWindow.StorageFrame, code)

    @classmethod
    def storage_slot(cls, bag: Any, slot: int) -> "Frame":
        """Xunlai storage slot; `slot` is 0-based."""
        return cls._under(FrameId.XunlaiWindow.StorageFrame,
                          cls._storage_offset(bag), 2 + int(slot))

    @classmethod
    def material_slot(cls, slot: int, max_tabs: int = 5, raw_slot: bool = False) -> "Frame":
        """Material storage slot; it sits one tab past the last storage tab."""
        code = int(slot) if raw_slot else 2 + int(slot)
        return cls._under(FrameId.XunlaiWindow.StorageFrame, int(max_tabs), code)

    @classmethod
    def party_list(cls) -> "Frame":
        """The container holding party entries, for whichever map type we are in."""
        from ..map import Map

        return cls(
            FrameId.PartyFormation.Outpost.Members.Frame.C0.C0.Parent
            if Map.IsOutpost() else
            FrameId.PartyFormation.Explorable.C0.C0.MembersParentExplorable
        )

    @classmethod
    def party_member(cls, index: int) -> "Frame":
        """Party list entry, 1-based.

        The party window is laid out differently in an outpost than in an
        explorable area.  Deciding which is the class's job - a caller asking
        for "party member 3" should not have to know the map type.
        """
        from ..map import Map

        parent = (
            FrameId.PartyFormation.Outpost.Members.Frame.C0.C0.Parent  # codes [1,8,0,0,0,0]
            if Map.IsOutpost() else
            FrameId.PartyFormation.Explorable.C0.C0.MembersParentExplorable  # codes [0,0,0,0]
        )
        # each entry sits at <parent>,<slot>,0
        return cls._under(parent, int(index) - 1, 0)

    @classmethod
    def effect(cls, skill_id: int) -> "Frame":
        """Effect icon in the effects monitor, addressed by skill id.

        Effect children are keyed by skill id at runtime, so they can never be
        enumerated in the registry - the mapping lives here instead.
        """
        return cls._under(FrameId.EffectsMonitor, int(skill_id) + 4)

    @classmethod
    def trainer_skill(cls, skill_id: int) -> "Frame":
        """Skill entry in the skill-trainer list, keyed by skill id."""
        return cls._under(FrameId.SkillTrainerWindow, 0, 0, 0, 5, 1, int(skill_id), 0)

    @classmethod
    def capture_skill(cls, attribute: int, skill_id: int) -> "Frame":
        """Skill entry in the elite-capture dialog, keyed by attribute + skill id."""
        return cls._under(FrameId.SkillCaptureDialog, 3, 0, 0, 0,
                          int(attribute), 1, int(skill_id), 0)

    @classmethod
    def dialog_option(cls, index: int) -> "Frame":
        """NPC dialog option, 1-based."""
        return cls("Option%d" % int(index))

    # -- resolution -------------------------------------------------------
    def _resolve(self) -> Optional[int]:
        """``Frame._resolve`` (``frame.py:893-917``).

        One tick-keyed test is dropped here for the reason ``ensure``'s gate is (``FRAME_TREE_PORT.md`` §2):
        ``if self._version == FrameTree.version: return self._fid`` is a *per-tick* memo, and with no ticker
        every ``ensure()`` rebuilds and bumps ``version``, so the test never holds and the member resolves
        when it is called — which is the port's model. Everything else is as written, including the order
        that matters: the snapshot first and then the engine, so an id the sweep has not reached is not
        mistaken for a dead one.
        """

        FrameTree.ensure()
        if self._version == FrameTree.version:
            return self._fid
        self._version = FrameTree.version

        if not self._key and not self._anchor:             # wrapped id
            fid = self._fid or 0
            # snapshot first (cheap), then the engine, so an id we have not
            # swept yet is not mistaken for a dead one
            self._fid = fid if fid and (FrameTree.known(fid) or FrameTree.live(fid)) else None
            return self._fid

        fid = None
        for anchor_id in FrameTree.anchor_ids(self._anchor):
            cur: Optional[int] = anchor_id
            for code in self._tail:
                cur = FrameTree.child_of(cur, code) if cur is not None else None
                if cur is None:
                    break
            if cur is not None:
                fid = cur
                break
        self._fid = fid
        return fid

    @property
    def exists(self) -> bool:
        """The frame is present in the live tree."""
        try:
            return self._resolve() is not None
        except FrameError:
            return False

    @property
    def frame_id(self) -> int:
        fid = self._resolve()
        if fid is None:
            raise FrameNotFound(
                "%r did not resolve (anchor %r + codes %s)"
                % (self._key or "<frame id>", self._anchor, list(self._tail))
            )
        return fid

    def _target_id(self) -> int:
        """The id to read, without demanding that it resolve.

        `frame_id` is the strict accessor and raises; reads that only *describe*
        a frame must not, because a frame inspector walks ids that go stale
        mid-frame.  An unresolved id yields a zeroed snapshot here, exactly as
        constructing a UIFrame on a dead id used to.
        """
        fid = self._resolve()
        if fid is not None:
            return fid
        return self._fid or 0

    def _state(self) -> FrameState:
        return FrameTree.state(self._target_id())

    @property
    def blackboard(self) -> dict:
        """Per-handle scratch space for caller context.

        Lives on this handle object, not on the frame, so it only persists
        while the caller keeps the handle (InventoryPlus stores a handle per
        item slot and hangs the item data here).
        """
        return self._blackboard

    def refresh(self) -> None:
        """Re-read this frame from the game now, mid-tick."""
        FrameTree.invalidate(self._target_id())

    # -- identity ---------------------------------------------------------
    @property
    def key(self) -> str:
        return self._key

    @property
    def hash(self) -> int:
        """Name hash, or 0 when the frame is unnamed or gone."""
        return FrameTree.hash_of(self._target_id())

    @property
    def name(self) -> str:
        """Engine frame name, when the hash is one we can name."""
        return FRAME_NAMES.get(self.hash, "")

    @property
    def code(self) -> int:
        """Child key code under its parent, or 0 when the frame is gone."""
        return FrameTree.code_of(self._target_id())

    @property
    def label(self) -> str:
        """Native frame label; empty when the frame is gone.

        ``PyUIManager.UIManager.get_frame_label_by_frame_id`` is native ``GetFrameTitle``
        (``ui_bindings.cpp:819-821`` → ``ui_methods.cpp:1784`` and on), and it is **not a read**: it takes
        the frame's non-client word at ``+0xCC`` and binary-searches the client's **title table** through
        two client function pointers (``g_title_binary_search_func``, then the title getter), with the
        table's address coming from the client's own context.  That is a call-side work item — the same one
        ``get_frame_title_by_frame_id`` needs, since both bindings wrap this single function — and it is
        named here rather than approximated.  The source wraps the call in ``except Exception`` and returns
        `""`, so this is its own failure path: a frame whose label cannot be read reports no label.
        """

        try:
            raise _unported(
                "Frame.label",
                "PyUIManager.UIManager.get_frame_label_by_frame_id — native GetFrameTitle "
                "(ui_bindings.cpp:819-821 → ui_methods.cpp:1784), which binary-searches the client's title "
                "table through two client function pointers and reads the frame's non-client word at "
                "+0xCC; both calls, not reads (docs/TARGET_SIDE_WORK.md)",
            )
        except Exception:
            return ""

    @property
    def alias(self) -> str:
        """Prose alias for this frame, from the migrated alias table."""
        if not self.exists:
            return ""
        return alias_by_path().get(self.path(), "")

    @property
    def registry_key(self) -> str:
        """Dotted registry key that addresses this frame, if it has one.

        `key` is what this handle was built from; this is what the live frame
        turns out to be - the two differ when the handle came from a raw id.
        """
        if self._key:
            return self._key
        if not self.exists:
            return ""
        return key_by_path().get(self.path(), "")

    def describe(self) -> str:
        """Best available identity for display: engine name, key, then alias.

        This is what a frame inspector should show.  Nothing here reads a file -
        it is all resolved from the migrated name / registry / alias tables.
        """
        parts: list[str] = []
        name = self.name
        if name:
            parts.append(name)
        key = self.registry_key
        if key and key != name:
            parts.append(key)
        alias = self.alias
        if alias and alias not in parts:
            parts.append("(%s)" % alias)
        return "  ".join(parts)

    @property
    def widget_id(self) -> str:
        """A stable, unique token for this frame, for ImGui widget suffixes.

        Scripts used the raw frame id to keep `##` suffixes unique.  This is a
        string label instead: unique per frame and stable within a session, but
        not something that can be passed back in to address a frame.
        """
        return "fr%x" % (self._target_id() & 0xFFFFFFFF)

    def matches(self, *names: str) -> bool:
        """The frame resolved and its engine name is one of `names`.

        This is the identity check for paths that host different frames
        depending on context - the Merchant / Crafter / Trader buttons all sit
        at the same path and are told apart only by name.
        """
        if not self.exists:
            return False
        return self.name in names

    @property
    def is_anonymous(self) -> bool:
        """Resolved, but the frame carries no name hash."""
        return self.exists and self.hash == 0

    def path(self) -> str:
        """"hash" if the frame is named, else "ancestor_hash,code,code,..."."""
        if not self.exists:
            return ""
        fid = self.frame_id
        own = FrameTree.hash_of(fid)
        if own:
            return str(own)
        codes: list[str] = []
        cur = fid
        anchor = 0
        while cur:
            codes.append(str(FrameTree.code_of(cur)))
            pid = FrameTree.parent_of(cur)
            if not pid:
                break
            ph = FrameTree.hash_of(pid)
            if ph:
                anchor = ph
                break
            cur = pid
        if not anchor:
            return ""
        return str(anchor) + "," + ",".join(reversed(codes))

    # -- state ------------------------------------------------------------
    @property
    def is_created(self) -> bool:
        return self.exists and self._state().is_created

    @property
    def is_visible(self) -> bool:
        return self.exists and self._state().is_visible

    @property
    def is_usable(self) -> bool:
        """Present, created and visible - safe to read or act on.

        This is the one readiness question.  Callers ask it instead of
        composing their own conjunction of exists / is_created / is_visible.
        """
        if not self.exists:
            return False
        st = self._state()
        return st.is_created and st.is_visible

    @property
    def template_type(self) -> int:
        """Widget template kind (1 == the interactive dialog button template)."""
        f = self._state().frame
        return int(getattr(f, "template_type", 0) or 0) if f is not None else 0

    @property
    def type(self) -> int:
        f = self._state().frame
        return int(getattr(f, "type", 0) or 0) if f is not None else 0

    @property
    def visibility_flags(self) -> int:
        f = self._state().frame
        return int(getattr(f, "visibility_flags", 0) or 0) if f is not None else 0

    @property
    def frame_layout(self) -> int:
        f = self._state().frame
        return int(getattr(f, "frame_layout", 0) or 0) if f is not None else 0

    def siblings(self) -> list["Frame"]:
        """Frames sharing this frame's parent, per the engine's relation block.

        Returns handles, never ids - `relation.siblings` is a raw id list and
        must not leave the class.  Its scalars are still visible via `fields()`
        under the `relation.` prefix.
        """
        f = self._state().frame
        rel = getattr(f, "relation", None) if f is not None else None
        if rel is None:
            return []
        try:
            return [Frame.from_id(int(i)) for i in (getattr(rel, "siblings", ()) or ())]
        except Exception:
            return []

    @property
    def frame_callbacks(self) -> Any:
        f = self._state().frame
        return getattr(f, "frame_callbacks", None) if f is not None else None

    @property
    def frame_state(self) -> int:
        f = self._state().frame
        return int(getattr(f, "frame_state", 0) or 0) if f is not None else 0

    def fields(self) -> dict:
        """Every scalar the engine exposes for this frame, as plain data.

        This is the inspection surface for frame testers: they get the values,
        never the underlying object, so there is still no way to address or
        act on a frame except through this class.  Named fields come first,
        then the undocumented `field*_0x..` slots ordered by struct offset.
        """
        f = self._state().frame
        if f is None:
            return {}

        def scalars(obj, prefix=""):
            named: dict = {}
            offsets: list = []
            for name in dir(obj):
                if name.startswith("_"):
                    continue
                try:
                    value = getattr(obj, name)
                except Exception:
                    continue
                if callable(value):
                    continue
                key = prefix + name
                if isinstance(value, (int, float, bool)):
                    m = re.match(r"field\w*?_0x([0-9a-fA-F]+)$", name)
                    if m:
                        offsets.append((int(m.group(1), 16), key, value))
                    else:
                        named[key] = value
                elif prefix == "" and name in ("relation", "position"):
                    # one level of nesting, so testers never need the object
                    sub_named, sub_offsets = scalars(value, name + ".")
                    named.update(sub_named)
                    offsets.extend(sub_offsets)
            return named, offsets

        named, offsets = scalars(f)
        out = dict(sorted(named.items()))
        for _, name, value in sorted(offsets):
            out[name] = value
        return out

    @property
    def parameters(self) -> list:
        """The frame's parameter list (struct slot 0x84), as plain data."""
        f = self._state().frame
        if f is None:
            return []
        try:
            return list(getattr(f, "field31_0x84", ()) or ())
        except Exception:
            return []

    @property
    def parent_id(self) -> int:
        """Parent frame id from the snapshot; 0 at the root or when gone."""
        return FrameTree.parent_of(self._target_id())

    def state_bit(self, bit: int) -> bool:
        """``PyUIManager.UIManager.get_frame_state_bit_by_frame_id`` (``frame.py:1214-1215``).

        Native ``GetFrameStateBit`` (``ui_methods.cpp:1829-1831``) is ``frame && (frame->frame_state & bit)
        != 0`` — a record read, which is what this does.  The record is fetched the way the binding fetches
        it (``client.frame_array.get``, native's ``GetFrameById``) rather than through ``_state()``, because
        ``FrameState``'s held copy is Reforged's own Python-side buffer and this member reads the array.
        """

        from ..client import require_client

        f = require_client().frame_array.get(self._target_id())
        return bool(f is not None and (int(getattr(f, "frame_state", 0) or 0) & bit) != 0)

    @property
    def user_param(self) -> int:
        """``PyUIManager.UIManager.get_frame_user_param_by_frame_id`` (``frame.py:1217-1219``).

        Native ``GetFrameUserParam`` (``ui_methods.cpp:1825-1827``) is ``frame ? frame->field105_0x1c4 : 0``
        — the record's own field, which this port declares at that offset (``py4gw/ui/frame.py:248``).
        """

        from ..client import require_client

        f = require_client().frame_array.get(self._target_id())
        return int(getattr(f, "field105_0x1c4", 0) or 0) if f is not None else 0

    @property
    def context(self) -> int:
        """``PyUIManager.UIManager.get_frame_context`` (``frame.py:1221-1223``).

        Native ``GetFrameContext`` (``ui_methods.cpp:758-772``) walks the frame's callback array from the
        end and returns the last non-null ``uictl_context``, or null for a frame with no callbacks — which is
        the walk this port already performs in ``FrameArray.frame_context_address``
        (``py4gw/ui/frame.py:569-579``, documented there as the same rule).  The member is that call.
        """

        from ..client import require_client

        array = require_client().frame_array
        f = array.get(self._target_id())
        if f is None:
            return 0
        return int(array.frame_context_address(f) or 0)

    # -- presentation -----------------------------------------------------
    def set_visible(self, visible: bool) -> bool:
        """``set_frame_visible_by_frame_id`` (``frame.py:1226-1229``).

        Native enqueues on the game thread and calls ``SetFrameVisible`` (``ui_bindings.cpp:833-837`` →
        ``ui_methods.cpp:1739-1752``), which is a write into the record's ``frame_state``: shown clears
        ``0x200`` and sets ``0x2``, hidden sets ``0x200`` and clears ``0x2``.  The port's write path exists —
        ``Operation.WRITE_MEMORY`` copies bytes from the block's data region to a target address
        (``py4gw/game_thread/payload.py:1065``) — so this is buildable; it needs a live client and explicit
        user scope for the write, which is why the member names it instead of performing it unverified.
        """

        raise _unported(
            "Frame.set_visible",
            "PyUIManager.UIManager.set_frame_visible_by_frame_id — native SetFrameVisible "
            "(ui_bindings.cpp:833-837 → ui_methods.cpp:1739-1752): a frame_state write (clear 0x200/set 0x2 "
            "shown, set 0x200/clear 0x2 hidden) that needs the game-thread write path and live verification",
        )

    def set_disabled(self, disabled: bool) -> bool:
        """``set_frame_disabled_by_frame_id`` (``frame.py:1231-1234``).

        ``SetFrameDisabled`` (``ui_methods.cpp:1753-1763``) sets or clears ``frame_state`` bit ``0x10`` — the
        same write path as `set_visible`.
        """

        raise _unported(
            "Frame.set_disabled",
            "PyUIManager.UIManager.set_frame_disabled_by_frame_id — native SetFrameDisabled "
            "(ui_methods.cpp:1753-1763): sets or clears frame_state bit 0x10, through the game-thread write "
            "path",
        )

    def show(self, show: bool = True) -> bool:
        """``show_frame_by_frame_id`` (``frame.py:1236-1237``).

        ``ui::ShowFrame`` is not a second implementation: it **is** ``SetFrameVisible``
        (``ui_methods.cpp:1780-1782``), reached through a different binding (``ui_bindings.cpp:851-855``), so
        this member waits on exactly what `set_visible` waits on.
        """

        raise _unported(
            "Frame.show",
            "PyUIManager.UIManager.show_frame_by_frame_id — native ShowFrame (ui_bindings.cpp:851-855), which "
            "is SetFrameVisible itself (ui_methods.cpp:1780-1782): the same frame_state write as "
            "Frame.set_visible",
        )

    @property
    def layer(self) -> int:
        """``get_frame_layer_by_frame_id`` (``frame.py:1239-1241``).

        Native ``GetFrameLayer`` (``ui_methods.cpp:650-652``) is ``frame ? frame->field10_0x28 : 0`` — the very
        word `set_layer` writes — and this port declares it at that offset (``py4gw/ui/frame.py:173``).
        """

        from ..client import require_client

        f = require_client().frame_array.get(self._target_id())
        return int(getattr(f, "field10_0x28", 0) or 0) if f is not None else 0

    def set_layer(self, layer: int) -> bool:
        """``set_frame_layer_by_frame_id`` (``frame.py:1243-1244``).

        ``SetFrameLayer`` (``ui_methods.cpp:654-660``) writes ``frame->field10_0x28 = layer`` and returns
        true — a four-byte record write, through the same game-thread write path as `set_visible`.
        """

        raise _unported(
            "Frame.set_layer",
            "PyUIManager.UIManager.set_frame_layer_by_frame_id — native SetFrameLayer "
            "(ui_methods.cpp:654-660): writes frame->field10_0x28, through the game-thread write path",
        )

    @property
    def opacity(self) -> float:
        """``get_frame_opacity_by_frame_id`` (``frame.py:1246-1248``).

        Native ``GetFrameOpacity`` (``ui_methods.cpp:1818-1820``) returns the float at ``frame + 0x30``, or
        ``0.0f`` for a null frame, so this reinterprets the word this port declares as ``field12_0x30``
        (``py4gw/ui/frame.py:175``) exactly as native does.
        """

        from ..client import require_client

        f = require_client().frame_array.get(self._target_id())
        if f is None:
            return 0.0
        return struct.unpack("<f", struct.pack("<I", int(getattr(f, "field12_0x30", 0)) & 0xFFFFFFFF))[0]

    def set_opacity(self, opacity: float, fade_time: float = 0.0) -> bool:
        """``set_frame_opacity_by_frame_id`` (``frame.py:1250-1255``).

        ``SetFrameOpacity`` (``ui_methods.cpp:1765-1778``) clamps to ``[0.0, 1.0]`` and stores the float at
        ``frame + 0x30`` — **and discards `fade_time`**, which the source still passes through.  A four-byte
        write through the game-thread path.
        """

        raise _unported(
            "Frame.set_opacity",
            "PyUIManager.UIManager.set_frame_opacity_by_frame_id — native SetFrameOpacity "
            "(ui_methods.cpp:1765-1778): clamps to [0,1], writes the float at frame+0x30 and ignores "
            "fade_time, through the game-thread write path",
        )

    # -- interaction ------------------------------------------------------
    # Each one refuses on an unusable frame rather than firing an action at a
    # frame that is not on screen - that check used to be the caller's job.
    def click(self) -> None:
        """``button_click`` (``frame.py:1260-1263``).

        The source asks ``is_usable`` and then calls the binding, which enqueues
        ``ui::ButtonClick(GetFrameById(frame_id))`` (``ui_bindings.cpp:1080-1084`` →
        ``ui_methods.cpp:1249-1274``). That body refuses unless the frame *and its parent* are
        ``IsCreated()``, builds ``packet::MouseAction`` — ``frame_id`` and ``child_offset_id`` are **both**
        the button's own ``child_offset_id``, ``wparam`` points at a ``ButtonParam{0, field105_0x1c4, 0}``,
        and the state is ``ActionState::MouseUp`` — and sends it to the **parent** frame's callbacks as
        ``kMouseClick2``. Both structs are placed in the block's data region, because the client is handed
        pointers to them, and the send is the same five-word ``__thiscall`` call `send_message` makes —
        with the parent's ``frame_callbacks`` in ECX.
        """

        if not self.is_usable:
            return

        from ..client import require_client
        from ..context.gw_array import GWArray
        from ..ui.frame import FrameStruct

        client = require_client()
        if not client.resolves(_SEND_FRAME_UI_MESSAGE_FUNC):
            return
        array = client.frame_array
        button = array.get(self.frame_id)
        if button is None or not int(button.frame_state) & _FRAME_STATE_CREATED:
            return
        parent_relation = int(button.relation.parent or 0)
        if not parent_relation:
            return
        parent_pointer = parent_relation - FrameStruct.relation.offset
        if not array.read_u32(parent_pointer + FrameStruct.frame_state.offset) & _FRAME_STATE_CREATED:
            return
        callbacks_size = int(
            array.read_u32(
                parent_pointer
                + FrameStruct.frame_callbacks.offset
                + GWArray.m_size.offset
            )
        )
        if not callbacks_size:
            return

        button_param_address = client.bridge.write_data(
            _BUTTON_PARAM_OFFSET,
            struct.pack("<III", 0, int(button.field105_0x1c4), 0),
        )
        action_address = client.bridge.write_data(
            _MOUSE_ACTION_OFFSET,
            struct.pack(
                "<IIIII",
                int(button.child_offset_id),
                int(button.child_offset_id),
                _MOUSE_UP,
                button_param_address,
                0,
            ),
        )
        client.call_function(
            _SEND_FRAME_UI_MESSAGE_FUNC,
            CallForm.FASTCALL_U32_U32_U32,
            parent_pointer + FrameStruct.frame_callbacks.offset,
            0,
            _K_MOUSE_CLICK_2,
            action_address,
            0,
        )

    def double_click(self) -> None:
        """``button_double_click`` (``frame.py:1265-1268``) — as `click`, through
        ``ui::ButtonDoubleClick`` (``ui_bindings.cpp:1085-1089``)."""

        if not self.is_usable:
            return
        raise _unported(
            "Frame.double_click",
            "PyUIManager.UIManager.button_double_click — native ButtonDoubleClick "
            "(ui_bindings.cpp:1085-1089), the same game-thread action feature as Frame.click",
        )

    def hover(self) -> None:
        self.mouse_action(_MOUSE_HOVER_STATE)

    def mouse_action(self, state: int, wparam: int = 0, lparam: int = 0) -> None:
        """``PyUIManager.UIManager.test_mouse_action`` (``frame.py:1273-1276``).

        The binding enqueues on the **game thread** and calls ``ui::TestMouseAction(frame_id,
        current_state, wparam, lparam)`` there (``ui_bindings.cpp:1093-1097``).  That is an action into the
        client, so this member names the requirement instead of taking a second route to it: the port's
        ``py4gw/game_thread`` layer is the analogue of that enqueue, and the function it would call is a
        `ui::` catalog resolver.  The source's own guard above is kept — an unusable frame never reaches it.
        """

        if not self.is_usable:
            return
        raise _unported(
            "Frame.mouse_action",
            "PyUIManager.UIManager.test_mouse_action — native enqueues on the game thread and calls "
            "ui::TestMouseAction(frame_id, current_state, wparam, lparam) (ui_bindings.cpp:1093-1097), i.e. a "
            "game-thread call into the client's own mouse-action path",
        )

    def mouse_click_action(self, state: int, wparam: int = 0, lparam: int = 0) -> None:
        """``PyUIManager.UIManager.test_mouse_click_action`` (``frame.py:1278-1281``).

        As `mouse_action`, but native calls ``ui::TestMouseClickAction`` (``ui_bindings.cpp:1099-1103``).
        """

        if not self.is_usable:
            return
        raise _unported(
            "Frame.mouse_click_action",
            "PyUIManager.UIManager.test_mouse_click_action — native enqueues on the game thread and calls "
            "ui::TestMouseClickAction (ui_bindings.cpp:1099-1103), i.e. a game-thread call into the client",
        )

    def send_message(self, message_id: int, wparam: int = 0, lparam: int = 0) -> bool:
        """``PyUIManager.UIManager.SendFrameUIMessage`` (``frame.py:1283-1286``).

        The binding enqueues ``ui::SendFrameUIMessage(GetFrameById(frame_id), message, wparam, lparam)``
        and answers ``True`` whatever that call does (``ui_bindings.cpp:1066-1072``). The methods layer
        refuses unless it holds the client's sender and the frame's callback array is non-empty
        (``ui_methods.cpp:1332-1335``), and then calls that sender (``:1337-1345``). **That target is the
        client's ``__thiscall`` method** — Native declares it fastcall-shaped for its detour ABI,
        ``SendFrameUIMessageFn = void(__fastcall*)(GW::GWArray<UIInteractionCallback>* callbacks, void* edx,
        UIMessage message_id, void* wparam, void* lparam)`` (``ui_patterns.cpp:32``) — so the callbacks
        address is the client's ``this`` in ``ECX`` (the frame record's own address plus
        ``frame_callbacks``' offset, ``0xA8``), the second word is the dummy ``EDX`` the source passes null
        for, and only the message and the caller's two words travel on the stack. The live read is what
        settled that: the function this port resolves ends ``ret 0xc`` — three stack words, released by the
        callee (``0x85cd80`` on the 2026-09-27 client, ``live_reports/send_frame_ui_message_read.json``).
        """

        from ..client import require_client
        from ..ui.frame import FrameStruct, is_valid_frame_pointer

        client = require_client()
        if not client.resolves(_SEND_FRAME_UI_MESSAGE_FUNC):
            return True
        array = client.frame_array
        frame_id = self._target_id()
        pointer = array.read_frame_pointer(frame_id)
        if not is_valid_frame_pointer(pointer):
            return True
        frame = array.get(frame_id)
        if frame is None or not int(frame.frame_callbacks.m_size):
            return True
        client.call_function(
            _SEND_FRAME_UI_MESSAGE_FUNC,
            CallForm.FASTCALL_U32_U32_U32,
            pointer + FrameStruct.frame_callbacks.offset,
            0,
            int(message_id),
            int(wparam),
            int(lparam),
        )
        return True

    def send_message_text(self, message_id: int, text: str) -> bool:
        """``PyUIManager.UIManager.SendFrameUIMessageWString`` (``frame.py:1288-1291``).

        The same call as `send_message`, with the message's text instead of a word
        (``ui_bindings.cpp:1073-1078``), so it waits on the same game-thread call and additionally on the
        wide-string form ([`docs/TARGET_SIDE_WORK.md`](../../docs/TARGET_SIDE_WORK.md)).
        """

        raise _unported(
            "Frame.send_message_text",
            "PyUIManager.UIManager.SendFrameUIMessageWString — the same game-thread "
            "ui::SendFrameUIMessage call as Frame.send_message (ui_bindings.cpp:1073-1078), with a wide "
            "string, so it needs that call plus the wide-string form",
        )

    # -- text -------------------------------------------------------------
    def text(self) -> str:
        """``get_text_label_decoded_by_frame_id`` (``frame.py:1294-1300``): the rendered label.

        The binding is ``FrameAs<TextLabelFrame>(frame_id)`` and ``SafeWide(label->GetDecodedLabel())``
        (``ui_bindings.cpp:1443-1446``), and the port already performs that read in
        ``FrameArray.decoded_label`` (``py4gw/ui/frame.py:621``) — the client's decoded text, read out of the
        label allocation.  The source's own ``except Exception`` around the call is kept as written.
        """

        try:
            from ..client import require_client

            array = require_client().frame_array
            f = array.get(self._target_id())
            if f is None:
                return ""
            return str(array.decoded_label(f) or "")
        except Exception:
            return ""

    def encoded(self) -> str:
        """``get_text_label_encoded_by_frame_id`` (``frame.py:1302-1308``): the label as stored.

        ``TextLabelFrame::GetEncodedLabel`` is what the binding calls (``ui_bindings.cpp:1439-1442``), and it
        is the read the port already does in ``FrameArray.encoded_label`` (``py4gw/ui/frame.py:605``).
        """

        try:
            from ..client import require_client

            array = require_client().frame_array
            f = array.get(self._target_id())
            if f is None:
                return ""
            return str(array.encoded_label(f) or "")
        except Exception:
            return ""

    def set_text(self, encoded_text: str) -> None:
        """Set the frame's text.  The engine expects an *encoded* label.

        ``set_text_label_by_frame_id`` is a **write**: native enqueues on the game thread and sets the
        encoded label on the ``TextLabelFrame`` (``ui_bindings.cpp:1447-1452``).  It is named here rather
        than performed unverified — the port's write path exists (``py4gw/game_thread``'s ``WRITE_MEMORY``)
        but a label write needs the client's own label setter and a live run to confirm.
        """

        raise _unported(
            "Frame.set_text",
            "PyUIManager.UIManager.set_text_label_by_frame_id — native enqueues on the game thread and sets "
            "the encoded label on the TextLabelFrame (ui_bindings.cpp:1447-1452), i.e. a write into the "
            "client that needs the game-thread path and live verification",
        )

    def title(self) -> str:
        """Window title; empty when the frame is gone.

        ``get_frame_title_by_frame_id`` is the *same* native function as `label` —
        ``ui_bindings.cpp:817-821`` binds ``GW::ui::GetFrameTitle(GetFrameById(frame_id))`` twice — so it
        waits on the same client title-table binary search, and the source's own ``except Exception`` makes
        it report no title rather than an approximation.
        """

        try:
            raise _unported(
                "Frame.title",
                "PyUIManager.UIManager.get_frame_title_by_frame_id — native GetFrameTitle "
                "(ui_bindings.cpp:817-821 → ui_methods.cpp:1784), the client title-table binary search; the "
                "same call Frame.label needs (docs/TARGET_SIDE_WORK.md)",
            )
        except Exception:
            return ""

    # -- geometry ---------------------------------------------------------
    @property
    def position(self) -> Any:
        """Raw FramePosition: screen rect, content rect, scale, viewport."""
        return self._state().position

    @property
    def rect(self) -> tuple[int, int, int, int]:
        """(left, top, right, bottom) on screen.

        The source reads four words of the binding's position wrapper, which are filled **only when the UI
        root exists** (`ui_bindings.cpp:445-462`) — so without a root it answers zeros, and that is what this
        returns too. With one, the words are native's own arithmetic:
        ``FramePosition::GetTopLeftOnScreen(root)`` and ``GetBottomRightOnScreen(root)`` (``ui.h:504-522``)
        over the captured render viewport, each cast the way the binding casts it (``static_cast<uint32_t>``).
        """

        p = self.position
        if p is None:
            return (0, 0, 0, 0)
        from ..context.render_context import get_viewport_size

        root = FrameTree.root()
        if not root.exists:
            return (0, 0, 0, 0)
        render = get_viewport_size()
        root_record = root._state().frame
        left, top = p.top_left_on_screen(root_record, render)
        right, bottom = p.bottom_right_on_screen(root_record, render)
        return (int(left) & 0xFFFFFFFF, int(top) & 0xFFFFFFFF,
                int(right) & 0xFFFFFFFF, int(bottom) & 0xFFFFFFFF)

    @property
    def size(self) -> tuple[int, int]:
        """``(width, height)`` on screen, by the same rule as `rect` (`ui.h:544-551`)."""

        p = self.position
        if p is None:
            return (0, 0)
        from ..context.render_context import get_viewport_size

        root = FrameTree.root()
        if not root.exists:
            return (0, 0)
        width, height = p.size_on_screen(root._state().frame, get_viewport_size())
        return (int(width) & 0xFFFFFFFF, int(height) & 0xFFFFFFFF)

    def coords(self) -> tuple[int, int, int, int]:
        """(left, top, right, bottom); zeros when the frame is absent."""
        if not self.exists:
            return (0, 0, 0, 0)
        return self.rect

    def content_coords(self) -> tuple[int, int, int, int]:
        """Content-area screen coords, Y flipped into screen space.

        ``frame.py:1355-1379``, as written: the four corners scaled by `viewport_scale`, with the Y axis flipped
        against ``FrameTree.viewport_height()`` — the **root's** height, for the reason the source's own comment
        gives (a frame's own ``viewport_height`` is a different number, and using it anchors every Y coordinate
        at zero while leaving X correct).
        """
        if not self.exists:
            return (0, 0, 0, 0)
        p = self.position
        if p is None:
            return (0, 0, 0, 0)
        scale_x, scale_y = self.viewport_scale()
        # The Y flip must use the ROOT's viewport height - that is the screen
        # height the content rectangle is measured against.  A frame's own
        # viewport_height is not the same value, and using it anchors every Y
        # coordinate at zero while leaving X correct.  The root's height is
        # cached, so a tick where the root cannot be read reuses the last good
        # one rather than collapsing the rectangle.
        height = FrameTree.viewport_height()
        if not height:
            # without a viewport height the Y flip below would invert the frame
            # onto negative screen space; better to report nothing this tick
            return (0, 0, 0, 0)
        return (
            int(p.content_left * scale_x),
            int((height - p.content_top) * scale_y),
            int(p.content_right * scale_x),
            int((height - p.content_bottom) * scale_y),
        )

    def viewport_scale(self) -> tuple[float, float]:
        """Viewport scale, never zero.

        A zeroed position struct - what the engine leaves behind when its frame
        lookup misses - would otherwise report a scale of 0, and any caller
        multiplying by it collapses every coordinate onto the origin.  There is
        no meaningful zero scale, so an unreadable one falls back to identity.

        **Where the two numbers come from here.** Reforged reads the wrapper's ``viewport_scale_x`` /
        ``viewport_scale_y``, which the binding fills with ``frame->position.GetViewportScale(root)`` — and
        only when the UI root exists (`ui_bindings.cpp:445-462`).  Native's own body divides
        ``GW::render::GetViewportWidth()/Height()`` by the **root's** viewport size (``ui.h:553-561``), so the
        port computes it that way: the numerator is the render viewport its capture keeps, the denominator the
        root's own words.  With no root the binding leaves both fields at zero, and the guard below then
        answers the identity — which is exactly what Reforged answers in that case.
        """

        if not self.exists:
            return (1.0, 1.0)
        p = self.position
        if p is None:
            return (1.0, 1.0)
        from ..context.render_context import get_viewport_size

        root = FrameTree.root()
        scale_x, scale_y = (p.viewport_scale(root._state().frame, get_viewport_size())
                            if root.exists else (0.0, 0.0))
        if scale_x <= 0.0 or scale_y <= 0.0:
            return (1.0, 1.0)
        return scale_x, scale_y

    def viewport_dimensions(self) -> tuple[float, float]:
        """Viewport size for this frame.

        Deliberately NOT gated on `exists`.  This is normally asked of the UI
        root, which does not reliably appear in a frame-array sweep - gating it
        made the whole viewport read zero whenever the sweep missed it, which
        zeroed every content rectangle derived from it.  The legacy code read
        this straight off the frame with no checks at all, and never had that
        failure.
        """
        p = self._state().position
        if p is None:
            return (0.0, 0.0)
        return float(p.viewport_width), float(p.viewport_height)

    def min_size(self) -> tuple:
        """``get_frame_min_size_by_frame_id`` (``frame.py:1415-1416``).

        Native ``GetFrameMinSize`` (``ui_methods.cpp:680-690``) reads the two floats at ``frame + 0x50`` and
        ``+0x54`` — plain record words.  The header declares them as words (this port carries them as
        ``field20_0x50`` / ``field21_0x54``, ``py4gw/ui/frame.py:183-184``) and native reinterprets them as
        floats, which is the same reinterpretation here.  The binding seeds its out-parameters with zero and
        calls the function unconditionally (``ui_bindings.cpp:790-794``), so a missing frame answers
        ``(0.0, 0.0)``.
        """

        from ..client import require_client

        f = require_client().frame_array.get(self._target_id())
        if f is None:
            return (0.0, 0.0)
        return (
            struct.unpack("<f", struct.pack("<I", int(getattr(f, "field20_0x50", 0)) & 0xFFFFFFFF))[0],
            struct.unpack("<f", struct.pack("<I", int(getattr(f, "field21_0x54", 0)) & 0xFFFFFFFF))[0],
        )

    def native_size(self) -> tuple:
        """``get_frame_native_size_by_frame_id`` (``frame.py:1418-1419``).

        Native ``GetFrameNativeSize`` (``ui_methods.cpp:745-756``) is the record's screen rectangle:
        ``width = screen_right - screen_left``, ``height = screen_top - screen_bottom``.  No root frame and no
        render context are involved, which is what makes this readable where `rect`/`size` are not.
        """

        from ..client import require_client

        f = require_client().frame_array.get(self._target_id())
        if f is None:
            return (0.0, 0.0)
        p = getattr(f, "position", None)
        if p is None:
            return (0.0, 0.0)
        return (float(getattr(p, "screen_right", 0.0)) - float(getattr(p, "screen_left", 0.0)),
                float(getattr(p, "screen_top", 0.0)) - float(getattr(p, "screen_bottom", 0.0)))

    def client_border(self) -> tuple:
        """``get_frame_client_border_by_frame_id`` (``frame.py:1421-1422``).

        Native ``GetFrameClientBorder`` (``ui_methods.cpp:693-702``) reads four more float words at
        ``frame + 0x58``, ``+0x5C``, ``+0x60`` and ``+0x64`` (``field22_0x58`` … ``field24a_0x64``,
        ``py4gw/ui/frame.py:185-188``), reinterpreted here exactly as native reinterprets them.
        """

        from ..client import require_client

        f = require_client().frame_array.get(self._target_id())
        if f is None:
            return (0.0, 0.0, 0.0, 0.0)
        return tuple(
            struct.unpack("<f", struct.pack("<I", int(getattr(f, name)) & 0xFFFFFFFF))[0]
            for name in ("field22_0x58", "field23_0x5c", "field24_0x60", "field24a_0x64")
        )

    def clip_rect(self) -> tuple:
        """``get_frame_clip_rect_by_frame_id`` (``frame.py:1424-1425``).

        Native ``GetFrameClipRect`` (``ui_methods.cpp:704-718``) copies the position's four content words in
        that order — ``content_left``, ``content_top``, ``content_right``, ``content_bottom`` — and the binding
        seeds its out-parameters with zero, so a frame that is gone answers zeros.
        """

        from ..client import require_client

        f = require_client().frame_array.get(self._target_id())
        if f is None:
            return (0.0, 0.0, 0.0, 0.0)
        p = getattr(f, "position", None)
        if p is None:
            return (0.0, 0.0, 0.0, 0.0)
        return (float(getattr(p, "content_left", 0.0)), float(getattr(p, "content_top", 0.0)),
                float(getattr(p, "content_right", 0.0)), float(getattr(p, "content_bottom", 0.0)))

    def position_ex(self) -> tuple:
        """``get_frame_position_ex_by_frame_id`` (``frame.py:1427-1428``).

        Native ``GetFramePositionEx`` (``ui_methods.cpp:723-744``) reads the raw record's screen rectangle and
        its flags: ``x = position.screen_left``, ``y = position.screen_bottom``,
        ``w = screen_right - screen_left``, ``h = screen_top - screen_bottom``, ``flags = position.flags``.
        Note that ``y`` is the **bottom** and ``h`` is ``top - bottom``, both as native writes them.
        """

        from ..client import require_client

        f = require_client().frame_array.get(self._target_id())
        if f is None:
            return (0.0, 0.0, 0.0, 0.0, 0)
        p = getattr(f, "position", None)
        if p is None:
            return (0.0, 0.0, 0.0, 0.0, 0)
        left = float(getattr(p, "screen_left", 0.0))
        bottom = float(getattr(p, "screen_bottom", 0.0))
        return (left, bottom,
                float(getattr(p, "screen_right", 0.0)) - left,
                float(getattr(p, "screen_top", 0.0)) - bottom,
                int(getattr(p, "flags", 0) or 0))

    def is_mouse_over(self) -> bool:
        """``frame.py:1430-1441`` — it asks the client's own ImGui where the mouse is.

        The body reads ``PyImGui.get_io().mouse_pos_x/y`` and calls ``ImGui.is_mouse_in_rect`` with this
        frame's rectangle (``frame.py:1433-1441``), so it needs the in-client ImGui — the same item already
        recorded for ``Utils.TokenizeMarkupText``'s ``PyImGui.calc_text_size``
        ([`docs/TARGET_SIDE_WORK.md`](../../docs/TARGET_SIDE_WORK.md)).  It also consumes `rect`, whose own
        requirement is the binding-side on-screen computation.
        """

        raise _unported(
            "Frame.is_mouse_over",
            "PyImGui.get_io() and ImGui.is_mouse_in_rect (frame.py:1433-1441) — the client's in-process ImGui, "
            "the same item as PyImGui.calc_text_size in docs/TARGET_SIDE_WORK.md; plus Frame.rect's "
            "on-screen computation",
        )

    # -- drawing ----------------------------------------------------------
    def draw(self, color: int) -> None:
        """``frame.py:1444-1457`` — it draws through Reforged's overlay manager.

        The source takes ``FrameTree.overlay`` and calls ``BeginDraw()`` / ``DrawQuadFilled(...)`` /
        ``EndDraw()`` with four ``PyOverlay.Vec2f`` corners.  ``overlay`` is the injected runtime's
        ``PyOverlay`` manager, which has no port here, and the rectangle it draws is `rect` — so this member
        names both.
        """

        if not self.is_usable:
            return
        raise _unported(
            "Frame.draw",
            "FrameTree.overlay and PyOverlay.Vec2f (frame.py:1448-1457) — the injected runtime's overlay "
            "manager, which this port does not carry; plus Frame.rect's on-screen computation",
        )

    def draw_outline(self, color: int, thickness: float = 1.0) -> None:
        """``frame.py:1459-1473`` — as `draw`, through ``DrawQuad`` with a thickness."""

        if not self.is_usable:
            return
        raise _unported(
            "Frame.draw_outline",
            "FrameTree.overlay, PyOverlay.Vec2f and overlay.DrawQuad (frame.py:1463-1472) — the injected "
            "runtime's overlay manager; plus Frame.rect's on-screen computation",
        )

    # -- navigation -------------------------------------------------------
    def parent(self) -> "Frame":
        pid = FrameTree.parent_of(self.frame_id)
        if not pid:
            raise FrameNotFound("%r has no parent" % (self._key or self.frame_id))
        return Frame.from_id(pid)

    def parent_id_native(self) -> int:
        """Parent from the native walker rather than the snapshot.

        Native ``GetParentFrameId`` (``ui_methods.cpp:1813-1819``) is ``frame->relation.GetParent()->frame_id``,
        and ``FrameRelation::GetParent()`` (``ui_methods.cpp:414-416``) is the stored relation pointer minus
        ``offsetof(Frame, relation)``.  Both offsets are declared here (``FrameStruct.relation.offset``,
        ``FrameStruct.frame_id.offset``; ``py4gw/ui/frame.py:300-303``), so the read is the parent record's
        ``frame_id`` word at that address — a read, with no snapshot involved, which is the point of the
        member.
        """

        from ..client import require_client
        from ..ui.frame import FrameStruct

        array = require_client().frame_array
        record = array.get(self.frame_id)
        if record is None:
            return 0
        relation = getattr(record, "relation", None)
        parent_relation = int(getattr(relation, "parent", 0) or 0) if relation is not None else 0
        if not parent_relation:
            return 0
        return int(array.read_u32(parent_relation - FrameStruct.relation.offset
                                  + FrameStruct.frame_id.offset) or 0)

    def parent_direct(self) -> "Frame":
        """The same walker through its other binding (``frame.py:1486-1489``).

        ``get_parent_frame_id_direct`` is ``GW::ui::GetParentFrameId(GetFrameById(frame_id))``
        (``ui_bindings.cpp:730-732``) — the very function `parent_id_native` reaches through
        ``GetParentFrame`` — so this repeats that read as the source repeats the call.
        """

        from ..client import require_client
        from ..ui.frame import FrameStruct

        array = require_client().frame_array
        record = array.get(self.frame_id)
        if record is None:
            return Frame.from_id(0)
        relation = getattr(record, "relation", None)
        parent_relation = int(getattr(relation, "parent", 0) or 0) if relation is not None else 0
        if not parent_relation:
            return Frame.from_id(0)
        pid = int(array.read_u32(parent_relation - FrameStruct.relation.offset
                                 + FrameStruct.frame_id.offset) or 0)
        return Frame.from_id(pid)

    def children(self) -> list["Frame"]:
        return [Frame.from_id(c) for c in FrameTree.children_of(self.frame_id)]

    def child_codes(self) -> list[int]:
        return FrameTree.child_codes_of(self.frame_id)

    def child(self, *codes: int) -> "Frame":
        """Walk to an unregistered descendant by raw child codes."""
        cur = self.frame_id
        for code in codes:
            nxt = FrameTree.child_of(cur, code)
            if nxt is None:
                raise FrameNotFound(
                    "%r has no descendant at codes %s (stopped at frame %d, code %d)"
                    % (self._key or self.frame_id, list(codes), cur, code)
                )
            cur = nxt
        return Frame.from_id(cur)

    def find_child(self, *codes: int) -> Optional["Frame"]:
        """`child` that answers None instead of raising."""
        try:
            return self.child(*codes)
        except FrameError:
            return None





    def child_native(self, code: int) -> "Frame":
        """Child by code via the native lookup rather than the snapshot.

        ``get_child_frame_by_frame_id`` is native ``GetChildFrame(parent, child_offset)``
        (``ui_methods.cpp:435-441``), which returns null unless the client's own
        ``g_get_child_frame_id_func`` is resolved — a call into the client, not a read of the frame array.
        """

        raise _unported(
            "Frame.child_native",
            "PyUIManager.UIManager.get_child_frame_by_frame_id — native GetChildFrame (ui_methods.cpp:435-441), "
            "which calls the client's own g_get_child_frame_id_func",
        )

    def child_path_native(self, codes: list[int]) -> "Frame":
        """One client call per code, through the same function as `child_native`.

        ``get_child_frame_path_by_frame_id`` walks the codes with ``g_get_child_frame_id_func``
        (``GetChildFrameID``, ``ui_methods.cpp:589-607``), so it waits on the same client function.
        """

        raise _unported(
            "Frame.child_path_native",
            "PyUIManager.UIManager.get_child_frame_path_by_frame_id — one client call per code through "
            "g_get_child_frame_id_func (GetChildFrameID, ui_methods.cpp:589-607)",
        )

    def child_with_hash(self, name_hash: int) -> "Frame":
        """Child carrying `name_hash`.

        Native ``GetChildFromNameHash`` (``ui_methods.cpp:609-621``) scans the frame array for a valid frame
        whose parent is this one (``relation.GetParent() == parent``) and whose ``relation.frame_hash_id``
        matches — both record fields, with the parent test made on the **relation pointer**.  The port has
        that pointer: ``relation.parent`` is the parent's relation, and ``FrameArray.get`` binds the address
        each record was read from (``py4gw/ui/frame.py:518``), so this frame's own relation address is
        ``record.address + FrameStruct.relation.offset``.
        """

        from ..client import require_client
        from ..ui.frame import FrameStruct

        array = require_client().frame_array
        record = array.get(self.frame_id)
        if record is None or not name_hash:
            return Frame.from_id(0)
        address = getattr(record, "address", None)
        if address is None:
            return Frame.from_id(0)
        relation_at = int(address) + FrameStruct.relation.offset
        for frame_id, candidate in array.iter_frames():
            relation = getattr(candidate, "relation", None)
            if relation is None:
                continue
            if int(getattr(relation, "parent", 0) or 0) != relation_at:
                continue
            if int(getattr(relation, "frame_hash_id", 0) or 0) != int(name_hash):
                continue
            return Frame.from_id(int(frame_id))
        return Frame.from_id(0)

    def child_named(self, name: str) -> "Frame":
        """Child carrying the hash of `name`."""
        h = NAME_TO_HASH.get(name)
        if h is None:
            raise FrameKeyError("no known frame named %r" % name)
        return self.child_with_hash(h)

    # The five walkers below are the source's five bindings, and each binding is a thin call into **one**
    # native function: `GetRelatedFrameById` (ui_methods.cpp:465-533), whose four branches scan the frame
    # array and select by `child_offset_id`.  The port reproduces that walk in each member rather than adding
    # a helper the sources do not have — the same choice `anchor_ids`/`by_hash` made for the hash lookup.
    def first_child(self) -> "Frame":
        """``get_first_child_frame_id`` (``frame.py:1544-1547``).

        The binding is ``GetRelatedFrameById(id, FirstChild, 0)`` (``ui_bindings.cpp:738-741``); that branch
        (``ui_methods.cpp:473-500``) keeps the child with the **smallest** ``child_offset_id`` above 0.
        """

        from ..client import require_client
        from ..ui.frame import FrameStruct

        array = require_client().frame_array
        record = array.get(self.frame_id)
        address = getattr(record, "address", None) if record is not None else None
        if address is None:
            return Frame.from_id(0)
        relation_at = int(address) + FrameStruct.relation.offset
        best, best_offset, start_offset = 0, 0xFFFFFFFF, 0
        for frame_id, candidate in array.iter_frames():
            relation = getattr(candidate, "relation", None)
            if relation is None or int(getattr(relation, "parent", 0) or 0) != relation_at:
                continue
            offset = int(getattr(candidate, "child_offset_id", 0) or 0)
            if offset > start_offset and offset < best_offset:
                best, best_offset = int(frame_id), offset
        return Frame.from_id(best)

    def last_child(self) -> "Frame":
        """``get_last_child_frame_id`` (``frame.py:1549-1552``).

        ``GetRelatedFrameById(id, LastChild, 0)``: the child with the **largest** ``child_offset_id`` below
        the start offset, which for no start-after is ``0xFFFFFFFF`` (``ui_methods.cpp:473-500``).
        """

        from ..client import require_client
        from ..ui.frame import FrameStruct

        array = require_client().frame_array
        record = array.get(self.frame_id)
        address = getattr(record, "address", None) if record is not None else None
        if address is None:
            return Frame.from_id(0)
        relation_at = int(address) + FrameStruct.relation.offset
        best, best_offset, start_offset = 0, 0, 0xFFFFFFFF
        for frame_id, candidate in array.iter_frames():
            relation = getattr(candidate, "relation", None)
            if relation is None or int(getattr(relation, "parent", 0) or 0) != relation_at:
                continue
            offset = int(getattr(candidate, "child_offset_id", 0) or 0)
            if offset < start_offset and offset > best_offset:
                best, best_offset = int(frame_id), offset
        return Frame.from_id(best)

    def next_sibling(self) -> "Frame":
        """``get_next_child_frame_id`` (``frame.py:1554-1557``).

        ``GetRelatedFrameById(id, NextSibling, 0)`` (``ui_methods.cpp:501-530``): among the frames sharing
        this one's parent, the **smallest** ``child_offset_id`` above this frame's own, with this frame
        excluded from the candidates.
        """

        from ..client import require_client
        from ..ui.frame import FrameStruct

        array = require_client().frame_array
        record = array.get(self.frame_id)
        address = getattr(record, "address", None) if record is not None else None
        if address is None:
            return Frame.from_id(0)
        relation = getattr(record, "relation", None)
        parent_relation = int(getattr(relation, "parent", 0) or 0) if relation is not None else 0
        if not parent_relation:
            return Frame.from_id(0)
        my_offset = int(getattr(record, "child_offset_id", 0) or 0)
        mine_id = int(self.frame_id)
        best, best_offset = 0, 0xFFFFFFFF
        for frame_id, candidate in array.iter_frames():
            if int(frame_id) == mine_id:
                continue
            relation = getattr(candidate, "relation", None)
            if relation is None or int(getattr(relation, "parent", 0) or 0) != parent_relation:
                continue
            offset = int(getattr(candidate, "child_offset_id", 0) or 0)
            if offset > my_offset and offset < best_offset:
                best, best_offset = int(frame_id), offset
        return Frame.from_id(best)

    def prev_sibling(self) -> "Frame":
        """``get_prev_child_frame_id`` (``frame.py:1559-1562``).

        The mirror of `next_sibling`: the **largest** ``child_offset_id`` below this frame's own
        (``ui_methods.cpp:501-530``).
        """

        from ..client import require_client
        from ..ui.frame import FrameStruct

        array = require_client().frame_array
        record = array.get(self.frame_id)
        address = getattr(record, "address", None) if record is not None else None
        if address is None:
            return Frame.from_id(0)
        relation = getattr(record, "relation", None)
        parent_relation = int(getattr(relation, "parent", 0) or 0) if relation is not None else 0
        if not parent_relation:
            return Frame.from_id(0)
        my_offset = int(getattr(record, "child_offset_id", 0) or 0)
        mine_id = int(self.frame_id)
        best, best_offset = 0, 0
        for frame_id, candidate in array.iter_frames():
            if int(frame_id) == mine_id:
                continue
            relation = getattr(candidate, "relation", None)
            if relation is None or int(getattr(relation, "parent", 0) or 0) != parent_relation:
                continue
            offset = int(getattr(candidate, "child_offset_id", 0) or 0)
            if offset < my_offset and offset > best_offset:
                best, best_offset = int(frame_id), offset
        return Frame.from_id(best)

    def related(self, relation_kind: int, start_after: int = 0) -> "Frame":
        """Native relation walker.  See RELATION_* constants.

        ``get_related_frame_id`` is ``GetRelatedFrameById(frame_id, kind, start_after)``
        (``ui_bindings.cpp:733-736``), and its four branches are one walk (``ui_methods.cpp:465-533``):
        children of this frame for `RELATION_FIRST_CHILD`/`RELATION_LAST_CHILD`, and this frame's siblings —
        this frame excluded — for the two sibling kinds.  Selection is always by ``child_offset_id``, and
        "after" means above the start offset for the first/next kinds and below it for the last/previous
        ones.
        """

        from ..client import require_client
        from ..ui.frame import FrameStruct

        array = require_client().frame_array
        record = array.get(self.frame_id)
        address = getattr(record, "address", None) if record is not None else None
        if address is None:
            return Frame.from_id(0)
        ascending = relation_kind in (RELATION_FIRST_CHILD, RELATION_NEXT_SIBLING)
        if relation_kind in (RELATION_NEXT_SIBLING, RELATION_PREV_SIBLING):
            # the sibling branches compare against this frame's own offset and ignore `start_after`
            relation = getattr(record, "relation", None)
            anchor_relation = int(getattr(relation, "parent", 0) or 0) if relation is not None else 0
            if not anchor_relation:
                return Frame.from_id(0)
            mine_id = int(self.frame_id)
            start_offset = int(getattr(record, "child_offset_id", 0) or 0)
        else:
            anchor_relation = int(address) + FrameStruct.relation.offset
            mine_id = 0
            start_record = array.get(start_after) if start_after else None
            start_offset = (int(getattr(start_record, "child_offset_id", 0) or 0)
                            if start_record is not None
                            else (0 if ascending else 0xFFFFFFFF))
        best = 0
        best_offset = 0xFFFFFFFF if ascending else 0
        for frame_id, candidate in array.iter_frames():
            if mine_id and int(frame_id) == mine_id:
                continue
            relation = getattr(candidate, "relation", None)
            if relation is None or int(getattr(relation, "parent", 0) or 0) != anchor_relation:
                continue
            offset = int(getattr(candidate, "child_offset_id", 0) or 0)
            if ascending:
                if offset > start_offset and offset < best_offset:
                    best, best_offset = int(frame_id), offset
            elif offset < start_offset and offset > best_offset:
                best, best_offset = int(frame_id), offset
        return Frame.from_id(best)

    def item(self, index: int) -> "Frame":
        """The binding is ``&GetOrderedChildFrameId`` (``ui_bindings.cpp:758``).

        Its ordered-child walk has not been read yet, so this member names it rather than reproducing a
        guess.
        """

        raise _unported(
            "Frame.item",
            "PyUIManager.UIManager.get_item_frame_id — native GetOrderedChildFrameId "
            "(ui_bindings.cpp:758), whose walk has not been read",
        )

    def tab(self, index: int) -> "Frame":
        """``get_tab_frame_id`` is a method on the client's own frame type.

        ``FrameAs<TabsFrame>(frame_id)->GetTabFrameId(index, &tab_frame_id)``
        (``ui_bindings.cpp:1523-1527``) — the lookup is the client's, not a field of the record.
        """

        raise _unported(
            "Frame.tab",
            "PyUIManager.UIManager.get_tab_frame_id — native FrameAs<TabsFrame>(frame_id)->GetTabFrameId("
            "index, &id) (ui_bindings.cpp:1523-1527), a method on the client's TabsFrame",
        )

    def is_ancestor_of(self, other: "Frame") -> bool:
        """``is_ancestor_of_by_frame_id`` (``frame.py:1585-1588``).

        Native ``IsAncestorOf`` (``ui_methods.cpp:662-675``) walks *other*'s parent chain and compares each
        parent pointer with this frame.  With ``relation.GetParent()`` being the relation pointer minus
        ``offsetof(Frame, relation)`` (``:414-416``), one step is a single word read at the current relation
        pointer, and the comparison is against this frame's own relation address.
        """

        from ..client import require_client
        from ..ui.frame import FrameStruct

        array = require_client().frame_array
        mine = array.get(self.frame_id)
        theirs = array.get(other.frame_id)
        if mine is None or theirs is None:
            return False
        my_address = getattr(mine, "address", None)
        if my_address is None:
            return False
        my_relation = int(my_address) + FrameStruct.relation.offset
        relation = getattr(theirs, "relation", None)
        current = int(getattr(relation, "parent", 0) or 0) if relation is not None else 0
        while current:
            if current == my_relation:
                return True
            current = int(array.read_u32(current) or 0)
        return False

    # -- io events --------------------------------------------------------
    def io_events(self) -> list:
        """``UIManager.GetIOEventsForFrame`` — Reforged's other UI module.

        The source imports it at the call site (``frame.py:1591-1596``): ``from ..UIManager import UIManager``.
        That module has no port here yet, so the member names it instead of returning an empty list that
        would look like "no events".
        """

        raise _unported(
            "Frame.io_events",
            "UIManager.GetIOEventsForFrame — Reforged's Py4GWCoreLib/UIManager.py (imported at frame.py:1594), "
            "a module this port has not ported",
        )

    def __iter__(self) -> Iterator["Frame"]:
        return iter(self.children())

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Frame):
            return NotImplemented
        return self._resolve() == other._resolve()

    def __hash__(self) -> int:
        return hash(self._resolve())

    def __bool__(self) -> bool:
        return self.exists

    def __str__(self) -> str:
        """Human-readable identity, for logs and labels."""
        return self.describe() or self.widget_id

    def __repr__(self) -> str:
        fid = self._resolve()
        if self._key:
            return "<Frame %s -> %s>" % (self._key, fid if fid else "unresolved")
        return "<Frame #%s>" % fid
