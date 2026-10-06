"""Offline tests for the ported first section of ``py4gw/frame_tree/frame.py``.

What the source module provides up to ``_FrameTree`` — the three exception classes, ``resolve_key``, the two
reverse-identity lookups, ``_position_unusable`` and ``FrameState`` — driven over the **ported** tables
(``REGISTRY``, ``FRAME_ALIASES``, ``FRAME_NAMES``/``NAME_TO_HASH``), which are themselves compared against
the sources by ``tests/test_frame_tree_tables_offline.py``.

The two things this file cannot do are named rather than implied: the source module cannot be loaded for a
comparison (it imports the injected ``PyOverlay``/``PyUIManager``), so the *structure* of the lookups is
checked against those tables instead; and ``_FrameTree``/``Frame`` are not ported yet, which a test asserts
so the gap stays visible.
"""

from __future__ import annotations

import struct
import unittest
from typing import Any
from unittest import mock

from py4gw.context.gw_array import GWArray
from py4gw.frame_tree import frame as frame_module
from py4gw.frame_tree.frame import (
    RELATION_FIRST_CHILD,
    RELATION_LAST_CHILD,
    RELATION_NEXT_SIBLING,
    RELATION_PREV_SIBLING,
    FrameError,
    FrameKeyError,
    FrameNotFound,
    FrameState,
    _FrameTree,
    alias_by_path,
    key_by_path,
    resolve_key,
)
from py4gw.frame_tree.frame_aliases import FRAME_ALIASES
from py4gw.frame_tree.frame_names import FRAME_NAMES, NAME_TO_HASH
from py4gw.frame_tree.frame_registry import REGISTRY
from py4gw.game_thread.shared_block import CallForm
from py4gw.ui.frame import FrameStruct


class _Position:
    """The engine's position struct, in the shape `_position_unusable` reads."""

    def __init__(self, scale: float = 1.0, left: float = 1.0) -> None:
        self.viewport_scale_x = scale
        self.viewport_scale_y = scale
        self.left_on_screen = left
        self.top_on_screen = left
        self.right_on_screen = left + 1.0
        self.bottom_on_screen = left + 1.0


class _Frame:
    """What the port's frame read answers: `is_created`/`is_visible` and a `position`."""

    def __init__(self, created: bool = True, visible: bool = True, position: Any = None) -> None:
        self.is_created = created
        self.is_visible = visible
        self.position = position if position is not None else _Position()


class _FrameArray:
    """The port's frame-array read: `get(frame_id)`, and `iter_frames()` for `rebuild`."""

    def __init__(self, frames: Any) -> None:
        if isinstance(frames, dict):
            self._frames: Any = frames
            self._ordered: list[tuple[int, Any]] = list(frames.items())
        else:
            self._ordered = list(frames)
            self._frames = dict(self._ordered)

    def get(self, frame_id: int) -> Any:
        return self._frames.get(int(frame_id))

    def iter_frames(self) -> Any:
        return iter(self._ordered)


class _Client:
    def __init__(self, frames: Any) -> None:
        self.frame_array = _FrameArray(frames)


class ErrorTests(unittest.TestCase):
    """The three exception classes, and their nesting."""

    def test_the_hierarchy_is_the_sources(self) -> None:
        self.assertTrue(issubclass(FrameKeyError, FrameError))
        self.assertTrue(issubclass(FrameNotFound, FrameError))
        self.assertTrue(issubclass(FrameError, Exception))

    def test_the_relation_constants_are_the_native_values(self) -> None:
        """`frame.py:71-75`: the native `relation_kind` values `get_related_frame_id` takes."""

        self.assertEqual(
            (RELATION_FIRST_CHILD, RELATION_LAST_CHILD, RELATION_NEXT_SIBLING, RELATION_PREV_SIBLING),
            (0, 1, 2, 3),
        )


class ResolveKeyTests(unittest.TestCase):
    """`resolve_key` over the ported registry."""

    def test_an_unknown_top_level_key_raises(self) -> None:
        """The source's own message shape, and the class the dialog catches."""

        with self.assertRaises(FrameKeyError) as caught:
            resolve_key("NotARegistryKey")
        self.assertIn("unknown registry key", str(caught.exception))

    def test_a_top_level_key_resolves_to_its_anchor(self) -> None:
        """A string entry is its own anchor and has no child codes."""

        top = next(name for name, entry in REGISTRY.items() if isinstance(entry, str))
        anchor, codes = resolve_key(top)
        self.assertEqual(anchor, REGISTRY[top])
        self.assertEqual(codes, ())

    def test_a_nested_key_resolves_to_codes_in_order(self) -> None:
        """A key whose segments walk into the registry's child maps."""

        for name, entry in REGISTRY.items():
            if isinstance(entry, str) or not entry[1]:
                continue
            child = next(iter(entry[1]))
            node = entry[1][child]
            expected = (node,) if isinstance(node, int) else (node[0],)
            with self.subTest(key=f"{name}.{child}"):
                anchor, codes = resolve_key(f"{name}.{child}")
                self.assertEqual(anchor, entry[0])
                self.assertEqual(codes, expected)
                return
        self.skipTest("the registry has no nested entry to drive this with")

    def test_a_missing_child_segment_raises(self) -> None:
        """The second `FrameKeyError` path, which names the path that had no such child."""

        for name, entry in REGISTRY.items():
            if isinstance(entry, str) or not entry[1]:
                continue
            with self.subTest(key=name):
                with self.assertRaises(FrameKeyError) as caught:
                    resolve_key(f"{name}.NotAChildSegment")
                self.assertIn("has no child", str(caught.exception))
                return
        self.skipTest("the registry has no nested entry to drive this with")


class ReverseIdentityTests(unittest.TestCase):
    """The two inversions: every path they produce names something real."""

    def test_alias_by_path_names_aliases(self) -> None:
        """`alias_by_path()` values are the source's own alias labels, and its keys are paths."""

        mapping = alias_by_path()
        self.assertEqual(mapping, alias_by_path(), "the table is built once and kept")
        self.assertGreater(len(mapping), 0)
        for path, label in mapping.items():
            with self.subTest(path=path):
                self.assertIn(label, set(FRAME_ALIASES.values()))
                self.assertEqual(len(path.split(",")), path.count(",") + 1)

    def test_key_by_path_names_registry_keys(self) -> None:
        """`key_by_path()` values are keys the registry actually resolves."""

        mapping = key_by_path()
        self.assertEqual(mapping, key_by_path(), "the table is built once and kept")
        self.assertGreater(len(mapping), 0)
        for path, key in mapping.items():
            with self.subTest(path=path):
                self.assertIn(key.split(".")[0], REGISTRY)
                anchor = key.split(".")[0]
                entry = REGISTRY[anchor]
                self.assertEqual(path.split(",")[0], str(NAME_TO_HASH.get(entry if isinstance(entry, str) else entry[0])))

    def test_a_path_is_the_hash_and_codes_that_the_name_table_knows(self) -> None:
        """Every path's first field is one of `NAME_TO_HASH`'s values."""

        hashes = set(NAME_TO_HASH.values())
        for mapping in (alias_by_path(), key_by_path()):
            for path in mapping:
                with self.subTest(path=path):
                    self.assertIn(int(path.split(",")[0]), hashes)

    def test_frame_names_are_the_hash_table_the_lookups_use(self) -> None:
        """`NAME_TO_HASH` is the reverse of `FRAME_NAMES`, which is how `_path_of` resolves an anchor."""

        self.assertEqual(len(FRAME_NAMES), len(NAME_TO_HASH))


class FrameStateTests(unittest.TestCase):
    """`FrameState` over the port's frame read, including the inheritance rule."""

    def _use(self, frames: dict[int, Any]) -> None:
        """Point the port's frame read at this fixture — `FrameState.__init__`'s one injected read."""

        patcher = mock.patch("py4gw.client.require_client", lambda: _Client(frames))
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_no_frame_read_means_blank(self) -> None:
        """The source's `except Exception: self.frame = None`, and `landed` false for it."""

        self._use({})
        state = FrameState(7)
        self.assertIsNone(state.frame)
        self.assertFalse(state.landed)
        self.assertTrue(state.blank)
        self.assertIsNone(state.position)

    def test_a_created_frame_with_geometry_lands(self) -> None:
        """`is_created` and a positive viewport scale are what the verdict reads."""

        self._use({7: _Frame()})
        state = FrameState(7)
        self.assertTrue(state.landed)
        self.assertFalse(state.blank)
        self.assertIsInstance(state.position, _Position)

    def test_a_zeroed_position_does_not_land(self) -> None:
        """A missed lookup zeroes the whole struct, and `_position_unusable` says so."""

        self._use({7: _Frame(position=_Position(scale=0.0, left=0.0))})
        state = FrameState(7)
        self.assertFalse(state.landed)

    def test_an_unusable_read_inherits_the_previous_position(self) -> None:
        """`position` reuses the last good geometry rather than handing back zeros."""

        self._use({})
        previous = FrameState(1)
        previous._position = _Position(scale=1.0, left=42.0)
        fresh = FrameState(7, previous=previous)
        self.assertIsNone(fresh.frame)
        self.assertIs(fresh.position, previous._position)
        self.assertEqual(fresh.position.left_on_screen, 42.0)

    def test_a_usable_read_is_not_replaced_by_the_previous_one(self) -> None:
        """With a landed read the fresh geometry is the answer."""

        self._use({7: _Frame()})
        previous = FrameState(1)
        previous._position = _Position(scale=1.0, left=42.0)
        fresh = FrameState(7, previous=previous)
        self.assertIsNot(fresh.position, previous._position)
        self.assertEqual(fresh.position.left_on_screen, 1.0)

    def test_the_slot_table_is_the_sources(self) -> None:
        """`__slots__` is the source's own list, so an attribute cannot be added by accident."""

        self.assertEqual(
            FrameState.__slots__,
            ("frame_id", "frame", "is_created", "is_visible", "tick",
             "_position", "_previous", "_landed", "served"),
        )


class FrameTreeSnapshotTests(unittest.TestCase):
    """`_FrameTree`'s lifecycle and snapshot, over the port's frame-array read."""

    def _use(self, frames: list[tuple[int, Any]]) -> None:
        patcher = mock.patch("py4gw.client.require_client", lambda: _Client(frames))
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_the_initial_state_is_the_sources(self) -> None:
        """`__init__`'s fields, including the two the source's own comments explain."""

        tree = _FrameTree()
        self.assertEqual(tree.version, 0)
        self.assertEqual(tree.tick, 0)
        self.assertEqual(tree._built_tick, -1)
        self.assertFalse(tree.stale)
        self.assertFalse(tree._registered)
        self.assertEqual(tree._order, [])
        self.assertEqual((tree._parent, tree._code, tree._hash), ({}, {}, {}))
        self.assertEqual(tree._children, {})
        self.assertEqual(tree._by_hash, {})
        self.assertEqual(tree._state, {})

    def test_the_class_constants_are_the_sources(self) -> None:
        """`_CALLBACK` and `BUFFER_TICKS`, as the source declares them (`frame.py:282-286`)."""

        self.assertEqual(_FrameTree._CALLBACK, "FrameTree.Tick")
        self.assertEqual(_FrameTree.BUFFER_TICKS, 5)

    def test_rebuild_snapshots_the_array(self) -> None:
        """Every id in order, and each record's parent, code and hash keyed by id."""

        class _Record:
            def __init__(self, parent: int, code: int, h: int) -> None:
                self.parent_id = parent
                self.child_offset_id = code
                self.frame_hash = h

        self._use([(1, _Record(0, 0, 0)), (2, _Record(1, 6, 0x1234)), (3, _Record(1, 6, 0x5678))])
        tree = _FrameTree()
        tree.rebuild()
        self.assertEqual(tree._order, [1, 2, 3])
        self.assertEqual(tree._parent, {1: 0, 2: 1, 3: 1})
        self.assertEqual(tree._code, {1: 0, 2: 6, 3: 6})
        self.assertEqual(tree._hash, {1: 0, 2: 0x1234, 3: 0x5678})
        # a colliding code keeps both siblings, which the source comments on (frame.py:350-352)
        self.assertEqual(tree._children[1][6], [2, 3])
        self.assertEqual(tree._by_hash[0x1234], [2])
        self.assertEqual(tree.version, 1)
        self.assertFalse(tree.stale)

    def test_an_empty_array_keeps_the_last_good_tree(self) -> None:
        """The source's own rule (`frame.py:356-369`): an unreadable array is not an empty UI."""

        class _Record:
            def __init__(self) -> None:
                self.parent_id = 0
                self.child_offset_id = 0
                self.frame_hash = 0

        self._use([(1, _Record())])
        tree = _FrameTree()
        tree.rebuild()
        version = tree.version
        self._use([])
        tree.rebuild()
        self.assertTrue(tree.stale)
        self.assertEqual(tree._order, [1], "the last good tree is kept")
        self.assertEqual(tree.version, version, "and the version did not bump")

    def test_an_empty_first_rebuild_is_not_stale(self) -> None:
        """With no previous tree there is nothing to keep, so the empty one is taken."""

        self._use([])
        tree = _FrameTree()
        tree.rebuild()
        self.assertFalse(tree.stale)
        self.assertEqual(tree._order, [])
        self.assertEqual(tree.version, 1)

    def test_ensure_rebuilds_on_the_call(self) -> None:
        """The port's adaptation: with no ticker, the call is the gate (`FRAME_TREE_PORT.md` §2)."""

        class _Record:
            def __init__(self) -> None:
                self.parent_id = 0
                self.child_offset_id = 0
                self.frame_hash = 0

        self._use([(1, _Record())])
        tree = _FrameTree()
        tree.ensure()
        self.assertEqual(tree.version, 1)
        tree.ensure()
        self.assertEqual(tree.version, 2, "a second call rebuilds again rather than pinning the first")

    def test_the_frame_loop_halves_name_what_they_need(self) -> None:
        """`enable`/`disable` are the tick's registration, which this port has no loop for."""

        tree = _FrameTree()
        for member in (tree.enable, tree.disable):
            with self.subTest(member=member.__name__):
                with self.assertRaises(NotImplementedError) as caught:
                    member()
                self.assertIn(member.__name__, str(caught.exception).replace("FrameTree.", ""))
                self.assertIn("PyCallback", str(caught.exception))

    def test_on_tick_only_bumps_the_counter(self) -> None:
        """`_on_tick`'s docstring says so, and the body is one line."""

        tree = _FrameTree()
        tree._on_tick()
        tree._on_tick()
        self.assertEqual(tree.tick, 2)
        self.assertEqual(tree.version, 0, "no work beyond the counter")

    def test_the_singleton_exists(self) -> None:
        """`FrameTree = _FrameTree()` (`frame.py:675`)."""

        self.assertIsInstance(frame_module.FrameTree, _FrameTree)


class StructureQueryTests(unittest.TestCase):
    """The tree's structure queries over a rebuilt snapshot (`frame.py:462-526`)."""

    def _tree(self, frames: Any) -> Any:
        patcher = mock.patch("py4gw.client.require_client", lambda: _Client(frames))
        patcher.start()
        self.addCleanup(patcher.stop)
        tree = _FrameTree()
        tree.rebuild()
        return tree

    def _frames(self) -> list[tuple[int, Any]]:
        class _Record:
            def __init__(self, parent: int, code: int, h: int, created: bool = True) -> None:
                self.parent_id = parent
                self.child_offset_id = code
                self.frame_hash = h
                self.is_created = created
                self.is_visible = created

        return [
            (1, _Record(0, 0, 0)),
            (2, _Record(1, 6, 0x1234)),
            (3, _Record(1, 6, 0x5678)),
            (4, _Record(2, 9, 0x9ABC)),
        ]

    def test_the_single_child_lookup_takes_the_first_of_a_collision(self) -> None:
        """`child_of` answers `got[0]`, and `None` when the code has no child."""

        tree = self._tree(self._frames())
        self.assertEqual(tree.child_of(1, 6), 2)
        self.assertIsNone(tree.child_of(1, 7))
        self.assertIsNone(tree.child_of(99, 0))

    def test_the_multi_child_lookup_keeps_every_sibling(self) -> None:
        """`children_at` is the list the collision note in `rebuild` exists for."""

        tree = self._tree(self._frames())
        self.assertEqual(tree.children_at(1, 6), [2, 3])
        self.assertEqual(tree.children_at(1, 7), [])

    def test_children_of_is_sorted_and_flattened(self) -> None:
        """Every code under one frame, in id order rather than code order."""

        tree = self._tree(self._frames())
        self.assertEqual(tree.children_of(1), [2, 3])
        self.assertEqual(tree.children_of(2), [4])
        self.assertEqual(tree.children_of(4), [])
        self.assertEqual(tree.child_codes_of(1), [6])

    def test_the_single_value_lookups_answer_the_snapshot(self) -> None:
        """`parent_of`, `hash_of`, `code_of` and `known`, including their zero defaults."""

        tree = self._tree(self._frames())
        self.assertEqual(tree.parent_of(4), 2)
        self.assertEqual(tree.hash_of(3), 0x5678)
        self.assertEqual(tree.code_of(2), 6)
        self.assertTrue(tree.known(4))
        self.assertFalse(tree.known(99))
        self.assertEqual(tree.parent_of(99), 0)
        self.assertEqual(tree.hash_of(99), 0)
        self.assertEqual(tree.code_of(99), 0)

    def test_all_ids_is_the_array_order(self) -> None:
        """`all_ids` rebuilds when called and answers the snapshot in native order."""

        tree = self._tree(self._frames())
        self.assertEqual(tree.all_ids(), [1, 2, 3, 4])

    def test_children_map_groups_by_parent(self) -> None:
        """`children_map` is the parent-to-children view the dialog walks."""

        tree = self._tree(self._frames())
        self.assertEqual(tree.children_map(), {0: [1], 1: [2, 3], 2: [4]})

    def test_live_asks_the_engine_rather_than_the_snapshot(self) -> None:
        """`live` is the raw read: an id the snapshot never saw still answers."""

        frames = self._frames()
        tree = self._tree(frames)

        class _Extra:
            is_created = True
            is_visible = False

        tree._state.clear()
        with mock.patch("py4gw.client.require_client", lambda: _Client(frames + [(77, _Extra())])):
            self.assertTrue(tree.live(77), "not in the snapshot, but the engine has it")
            self.assertTrue(tree.live(1))
        self.assertFalse(tree.live(0))
        self.assertFalse(tree.live(404), "the engine does not have it")


class PerFrameStateTests(unittest.TestCase):
    """`state`, `_prune` and `invalidate` (`frame.py:378-423`) — the port's adaptation included."""

    def _use(self, frames: Any) -> Any:
        patcher = mock.patch("py4gw.client.require_client", lambda: _Client(frames))
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_a_landed_read_is_stored_and_answered(self) -> None:
        """A frame the engine has, with usable geometry."""

        self._use({7: _Frame()})
        tree = _FrameTree()
        state = tree.state(7)
        self.assertIsInstance(state, FrameState)
        self.assertTrue(state.landed)
        self.assertIs(tree._state[7], state)

    def test_the_member_reads_again_on_the_next_call(self) -> None:
        """The adaptation: no per-tick memo, so a second call is a second read.

        The source's own memo (`:387-389`) would answer the first copy forever here, since nothing advances
        `tick`; this port reads when it is called.
        """

        self._use({7: _Frame()})
        tree = _FrameTree()
        first = tree.state(7)
        second = tree.state(7)
        self.assertIsNot(first, second, "a fresh copy per call")
        self.assertIs(tree._state[7], second)

    def test_a_blank_read_inherits_the_last_good_copy(self) -> None:
        """The buffer rule the source keeps, driven to its bound."""

        self._use({7: _Frame()})
        tree = _FrameTree()
        good = tree.state(7)
        self.assertTrue(good.landed)

        self._use({7: _Frame(position=_Position(scale=0.0, left=0.0))})
        for expected_served in range(1, _FrameTree.BUFFER_TICKS + 1):
            with self.subTest(served=expected_served):
                self.assertIs(tree.state(7), good, "the good copy stands in")
                self.assertEqual(good.served, expected_served)

        blank = tree.state(7)
        self.assertIsNot(blank, good, "past the bound the truth is told")
        self.assertFalse(blank.landed)
        self.assertIs(tree._state[7], blank)

    def test_a_frame_that_was_never_good_gets_the_blank_read(self) -> None:
        """With no previous good copy there is nothing to serve, so the blank one is stored."""

        self._use({7: _Frame(created=False, visible=False)})
        tree = _FrameTree()
        state = tree.state(7)
        self.assertFalse(state.landed)
        self.assertIs(tree._state[7], state)

    def test_invalidate_drops_one_or_every_copy(self) -> None:
        """`invalidate(frame_id)` pops that one; `invalidate()` clears the cache."""

        self._use({7: _Frame(), 8: _Frame()})
        tree = _FrameTree()
        tree.state(7)
        tree.state(8)
        tree.invalidate(7)
        self.assertNotIn(7, tree._state)
        self.assertIn(8, tree._state)
        tree.invalidate()
        self.assertEqual(tree._state, {})
        tree.invalidate(404)  # an id with nothing cached is not an error

    def test_the_prune_keeps_the_sources_cutoff_rule(self) -> None:
        """`st.tick < self.tick - 240` — ported as written, and it cannot fire without a ticker."""

        self._use({7: _Frame()})
        tree = _FrameTree()
        aged = tree.state(7)
        aged.tick = -1000
        tree._prune()
        self.assertNotIn(7, tree._state, "a copy older than the cutoff goes")
        tree.tick = 1000
        fresh = tree.state(7)
        fresh.tick = 900
        tree._prune()
        self.assertIn(7, tree._state, "1000 - 240 = 760, and 900 is newer than that")
        fresh.tick = 700
        tree._prune()
        self.assertNotIn(7, tree._state, "700 is older than 760")


class RemainingSectionsTests(unittest.TestCase):
    """What is not ported yet, stated rather than skipped: `_FrameTree`'s Frame-backed queries, and
    `Frame`'s members past its first slice."""

    def test_the_tree_is_here_and_its_queries_are_not(self) -> None:
        """The class's lifecycle, snapshot and structure queries are ported; the rest is the next section."""

        self.assertTrue(hasattr(frame_module, "_FrameTree"))
        self.assertTrue(hasattr(frame_module, "FrameTree"))
        for member in ("ensure", "all_ids", "children_map", "child_of", "live", "state", "invalidate"):
            with self.subTest(present=member):
                self.assertTrue(hasattr(frame_module._FrameTree, member))
        for member in ("all_frames", "_as_id", "descendants", "descendants_of", "frames_at_path",
                       "frames_under", "_frames_at", "sort_by_vertical", "root", "viewport_height",
                       "hierarchy", "overlay_frames", "popup_frames", "coords_for_hash",
                       "child_by_parent_hash", "color_frames", "overlay"):
            with self.subTest(present=member):
                self.assertTrue(hasattr(frame_module._FrameTree, member))
    def test_frame_is_here_in_its_first_slice(self) -> None:
        """`Frame`'s handles, accessors and its resolution are ported (`frame.py:678-925`); the reads are not."""

        self.assertTrue(hasattr(frame_module, "Frame"))
        for member in ("from_id", "from_hash", "from_label", "_under", "skill", "hero_skill",
                       "bag_slot", "_bag_offset", "inventory_bag", "inventory_bag_slot",
                       "_storage_offset", "storage_tab", "storage_slot", "material_slot",
                       "party_list", "party_member", "effect", "trainer_skill", "capture_skill",
                       "dialog_option", "_resolve", "exists", "frame_id", "_target_id", "_state",
                       "blackboard", "refresh", "key", "hash", "name", "code", "label", "alias",
                       "registry_key", "describe", "widget_id", "matches", "is_anonymous", "path",
                       "is_created", "is_visible", "is_usable", "template_type", "type",
                       "visibility_flags", "frame_layout", "siblings", "frame_callbacks",
                       "frame_state", "fields", "parameters", "parent_id", "state_bit", "user_param",
                       "context", "mouse_action", "mouse_click_action", "send_message",
                       "send_message_text", "text", "encoded", "set_text", "title", "position",
                       "rect", "size", "coords", "viewport_scale", "viewport_dimensions",
                       "min_size", "native_size", "client_border", "position_ex", "parent",
                       "children", "child_codes", "child", "find_child", "parent_id_native",
                       "parent_direct", "child_native", "child_path_native", "child_with_hash",
                       "child_named", "first_child", "last_child", "next_sibling", "prev_sibling",
                       "related", "item", "tab", "is_ancestor_of", "io_events", "__iter__", "__eq__",
                       "__hash__", "__bool__", "__str__", "__repr__", "set_visible", "set_disabled",
                       "show", "layer", "set_layer", "opacity", "set_opacity", "click", "double_click",
                       "hover", "draw", "draw_outline", "is_mouse_over", "content_coords", "clip_rect"):
            with self.subTest(present=member):
                self.assertTrue(hasattr(frame_module.Frame, member))

    def test_the_anchor_lookups_are_here(self) -> None:
        """The four lookups are declared, and all four answer (`frame.py:426-460`, `579-588`).

        `hash_for_label` and `by_label` were the two that named the client's own hash function as
        missing work until round 90; both are built, so the set of members here that raise is smaller
        than it was and the assertions below say which.
        """

        for member in ("anchor_ids", "by_hash", "by_label", "hash_for_label"):
            with self.subTest(present=member):
                self.assertTrue(hasattr(frame_module._FrameTree, member))

        with mock.patch("py4gw.client._current_client", _AnchorClient({})):
            self.assertIsInstance(frame_module.FrameTree.by_label("DlgRedirect"), frame_module.Frame)
            self.assertEqual(frame_module.FrameTree.hash_for_label("DlgRedirect"), 0)
    def test_all_is_the_sources_list_minus_those_two(self) -> None:
        """`__all__` names only what this file defines, so `import *` cannot fail."""

        for name in frame_module.__all__:
            with self.subTest(name=name):
                self.assertTrue(hasattr(frame_module, name))

    def test_the_injected_imports_are_not_carried(self) -> None:
        """`PyOverlay`/`PyUIManager` are the injected runtime's modules; the port reaches the reads."""

        self.assertFalse(hasattr(frame_module, "PyUIManager"))
        self.assertFalse(hasattr(frame_module, "PyOverlay"))


class TestFrameHandlesOffline(unittest.TestCase):
    """`Frame`'s constructor and handle builders — `frame.py:678-793`, the first slice ported."""

    SOURCE_SLOTS = ("_key", "_anchor", "_tail", "_fid", "_version", "_blackboard")

    def test_the_slots_are_the_sources_six(self) -> None:
        """`__slots__` is the source's own tuple (`frame.py:682`)."""

        self.assertEqual(frame_module.Frame.__slots__, self.SOURCE_SLOTS)

    def test_wrapping_a_known_id_sets_the_internal_shape(self) -> None:
        """`from_id` is the internal path: no key, no path, the id it was given (`:684-692`)."""

        f = frame_module.Frame.from_id(0x1234)
        self.assertEqual(f._key, "")
        self.assertEqual(f._anchor, "")
        self.assertEqual(f._tail, ())
        self.assertEqual(f._fid, 0x1234)
        self.assertEqual(f._version, -1)
        self.assertEqual(f._blackboard, {})

    def test_from_hash_defers_the_path(self) -> None:
        """A runtime-computed path is anchor hash plus child codes, resolved later (`:713-728`)."""

        f = frame_module.Frame.from_hash(0xABCD, [3, 4])
        self.assertEqual(f._key, "")
        self.assertEqual(f._anchor, 0xABCD)
        self.assertEqual(f._tail, (3, 4))
        self.assertIsNone(f._fid)

    def test_from_hash_copies_the_blackboard_it_is_given(self) -> None:
        """`dict(blackboard) if blackboard else {}` — the caller's dict is not adopted (`:727`)."""

        board = {"a": 1}
        f = frame_module.Frame.from_hash(1, (), board)
        self.assertEqual(f._blackboard, {"a": 1})
        self.assertIsNot(f._blackboard, board)

    def test_a_key_is_resolved_through_the_registry(self) -> None:
        """A static key becomes (anchor, tail) at construction (`:702-704`)."""

        f = frame_module.Frame("Skillbar.Skill1")
        anchor, tail = frame_module.resolve_key("Skillbar.Skill1")
        self.assertEqual(f._key, "Skillbar.Skill1")
        self.assertEqual((f._anchor, f._tail), (anchor, tail))
        self.assertIsNone(f._fid)
        self.assertEqual(f._version, -1)

    def test_a_non_string_key_raises_frame_key_error(self) -> None:
        """`frame key must be a string or a FrameId node` (`:694-696`)."""

        with self.assertRaises(frame_module.FrameKeyError):
            frame_module.Frame(5)

    def test_a_dynamic_key_raises_rather_than_resolving(self) -> None:
        """`DYNAMIC_KEYS` has per-session codes and must not be resolved (`:697-701`)."""

        self.assertTrue(frame_module.DYNAMIC_KEYS, "the dynamic-key table is empty")
        dynamic = sorted(frame_module.DYNAMIC_KEYS)[0]
        with self.assertRaises(frame_module.FrameKeyError):
            frame_module.Frame(dynamic)

    def test_a_frame_id_node_is_accepted_by_its_key(self) -> None:
        """`getattr(key, "KEY", key)` — a FrameId node stands in for its key (`:694`)."""

        node = frame_module.FrameId.InventoryBagsWindow.Content.C0.C0
        f = frame_module.Frame(node)
        anchor, tail = frame_module.resolve_key(node.KEY)
        self.assertEqual(f._key, node.KEY)
        self.assertEqual((f._anchor, f._tail), (anchor, tail))

    def test_from_label_walks_the_alias_table(self) -> None:
        """The first alias whose path head is a known name resolves to that path (`:736-744`)."""

        for path, label in frame_module.FRAME_ALIASES.items():
            parts = path.split(",")
            head = frame_module.NAME_TO_HASH.get(parts[0])
            if head is None:
                continue
            f = frame_module.Frame.from_label(label)
            self.assertEqual(f._anchor, head)
            self.assertEqual(f._tail, tuple(int(c) for c in parts[1:]))
            self.assertEqual(f._key, "")
            return
        self.skipTest("no alias in FRAME_ALIASES has a path head present in NAME_TO_HASH")

    def test_an_unknown_label_raises_frame_key_error(self) -> None:
        """`no frame alias labelled %r` (`:744`)."""

        with self.assertRaises(frame_module.FrameKeyError):
            frame_module.Frame.from_label("\x00 no such frame alias")

    def test_under_appends_the_computed_codes_to_the_parent(self) -> None:
        """`_under` keeps the parent's anchor and extends its tail (`:751-763`)."""

        parent = frame_module.Frame("Skillbar.Skill1")
        f = frame_module.Frame._under("Skillbar.Skill1", 7, 9)
        self.assertEqual(f._key, "")
        self.assertEqual(f._anchor, parent._anchor)
        self.assertEqual(f._tail, tuple(parent._tail) + (7, 9))
        self.assertIsNone(f._fid)

    def test_the_named_slots_build_their_registry_keys(self) -> None:
        """`skill` and `hero_skill` are 1-based and named in the key (`:765-773`)."""

        self.assertEqual(frame_module.Frame.skill(2)._key, "Skillbar.Skill2")
        self.assertEqual(frame_module.Frame.hero_skill(1, 3)._key,
                         "Hero1Window.SkillBar.Skill3")

    def test_bag_offset_is_measured_from_the_backpack(self) -> None:
        """`bag - Bags.Backpack`, accepting the enum or its raw value (`:786-792`)."""

        from py4gw.enums_src.item_enums import Bags

        self.assertEqual(frame_module.Frame._bag_offset(Bags.Backpack), 0)
        self.assertEqual(frame_module.Frame._bag_offset(Bags.Backpack.value), 0)

    def test_bag_slot_uses_the_engines_own_arithmetic(self) -> None:
        """The panel's codes are `bag - Backpack` and `slot + 2` (`:775-784`)."""

        from py4gw.enums_src.item_enums import Bags

        panel = frame_module.Frame(frame_module.FrameId.InventoryBagsWindow.Content.C0.C0)
        f = frame_module.Frame.bag_slot(Bags.Backpack, 0)
        self.assertEqual(f._key, "")
        self.assertEqual(f._tail, tuple(panel._tail) + (0, 2))
        self.assertEqual(f._anchor, panel._anchor)


class TestFrameIndexedAccessorsOffline(unittest.TestCase):
    """`Frame`'s named indexed addressing — the codes the engine addresses a child by (`frame.py:794-890`)."""

    def test_inventory_bag_wraps_the_standalone_window(self) -> None:
        """The standalone bag window, keyed by `bag - Backpack` (`:794-797`)."""

        from py4gw.enums_src.item_enums import Bags

        window = frame_module.Frame(frame_module.FrameId.InventoryWindow)
        f = frame_module.Frame.inventory_bag(Bags.Backpack)
        self.assertEqual(f._key, "")
        self.assertEqual(f._anchor, window._anchor)
        self.assertEqual(f._tail, tuple(window._tail) + (0,))

    def test_inventory_bag_slot_adds_the_engines_two(self) -> None:
        """`slot + 2` inside that window (`:799-803`)."""

        from py4gw.enums_src.item_enums import Bags

        window = frame_module.Frame(frame_module.FrameId.InventoryWindow)
        f = frame_module.Frame.inventory_bag_slot(Bags.Backpack, 3)
        self.assertEqual(f._tail, tuple(window._tail) + (0, 5))

    def test_storage_offset_maps_the_material_bag_to_fourteen(self) -> None:
        """Materials sit one tab past the storage tabs; anything else is `bag - Storage1` (`:805-813`)."""

        from py4gw.enums_src.item_enums import Bags

        self.assertEqual(frame_module.Frame._storage_offset(Bags.MaterialStorage), 14)
        self.assertEqual(frame_module.Frame._storage_offset(Bags.MaterialStorage.value), 14)
        self.assertEqual(frame_module.Frame._storage_offset(Bags.Storage1), 0)

    def test_storage_tab_and_its_reversed_order(self) -> None:
        """The tab strip counts down while the panes count up (`:815-824`)."""

        from py4gw.enums_src.item_enums import Bags

        frame = frame_module.Frame(frame_module.FrameId.XunlaiWindow.StorageFrame)
        plain = frame_module.Frame.storage_tab(Bags.Storage1)
        self.assertEqual(plain._tail, tuple(frame._tail) + (0,))
        self.assertEqual(plain._anchor, frame._anchor)
        reversed_order = frame_module.Frame.storage_tab(Bags.Storage1, True)
        self.assertEqual(reversed_order._tail, tuple(frame._tail) + (0xFFFFFFFF,))

    def test_storage_slot_adds_the_engines_two(self) -> None:
        """`slot + 2` in the storage pane (`:826-830`)."""

        from py4gw.enums_src.item_enums import Bags

        frame = frame_module.Frame(frame_module.FrameId.XunlaiWindow.StorageFrame)
        f = frame_module.Frame.storage_slot(Bags.Storage1, 3)
        self.assertEqual(f._tail, tuple(frame._tail) + (0, 5))

    def test_material_slot_sits_one_tab_past_the_last(self) -> None:
        """`max_tabs` is the tab code; the slot code is `slot + 2` unless raw (`:832-836`)."""

        frame = frame_module.Frame(frame_module.FrameId.XunlaiWindow.StorageFrame)
        tail = tuple(frame._tail)
        self.assertEqual(frame_module.Frame.material_slot(4)._tail, tail + (5, 6))
        self.assertEqual(frame_module.Frame.material_slot(4, raw_slot=True)._tail, tail + (5, 4))
        self.assertEqual(frame_module.Frame.material_slot(4, max_tabs=6)._tail, tail + (6, 6))

    def test_effect_is_keyed_by_skill_id_plus_four(self) -> None:
        """Effect children are runtime-keyed, so the mapping lives here (`:867-874`)."""

        monitor = frame_module.Frame(frame_module.FrameId.EffectsMonitor)
        f = frame_module.Frame.effect(1234)
        self.assertEqual(f._tail, tuple(monitor._tail) + (1238,))
        self.assertEqual(f._anchor, monitor._anchor)

    def test_trainer_skill_names_the_whole_code_path(self) -> None:
        """The trainer's list path, ending in the skill id (`:876-879`)."""

        window = frame_module.Frame(frame_module.FrameId.SkillTrainerWindow)
        f = frame_module.Frame.trainer_skill(77)
        self.assertEqual(f._tail, tuple(window._tail) + (0, 0, 0, 5, 1, 77, 0))

    def test_capture_skill_names_the_whole_code_path(self) -> None:
        """The capture dialog's path, keyed by attribute and skill id (`:881-885`)."""

        dialog = frame_module.Frame(frame_module.FrameId.SkillCaptureDialog)
        f = frame_module.Frame.capture_skill(2, 77)
        self.assertEqual(f._tail, tuple(dialog._tail) + (3, 0, 0, 0, 2, 1, 77, 0))

    def test_dialog_option_builds_its_registry_key(self) -> None:
        """`Option%d`, 1-based (`:887-890`) — the key is built whether or not the registry has it."""

        try:
            f = frame_module.Frame.dialog_option(3)
        except frame_module.FrameKeyError as caught:
            self.assertIn("Option3", str(caught))
        else:
            self.assertEqual(f._key, "Option3")
            self.assertIsNone(f._fid)

    def test_the_party_accessors_follow_the_map_type(self) -> None:
        """`party_list`/`party_member` ask `Map.IsOutpost()` which layout to use (`:838-865`).

        `Map.IsOutpost()` is `False` when no map data is loaded (`py4gw/map.py:96-101`), so a call with no
        client reaches the explorable layout.  The test takes the source's own condition rather than
        assuming a map type, so it states the choice in either case.

        The two parents also show why the source writes `getattr(key, "KEY", key)` (`:694`): a `FrameId`
        leaf is a key string, while an interior node carries its key as `KEY`, and both are accepted.
        """

        from py4gw.map import Map

        outpost = frame_module.FrameId.PartyFormation.Outpost.Members.Frame.C0.C0.Parent
        explorable = frame_module.FrameId.PartyFormation.Explorable.C0.C0.MembersParentExplorable
        expected = outpost if Map.IsOutpost() else explorable
        expected_key = getattr(expected, "KEY", expected)

        party = frame_module.Frame.party_list()
        self.assertEqual(party._key, expected_key)
        self.assertIsNone(party._fid)

        parent = frame_module.Frame(expected)
        member = frame_module.Frame.party_member(3)
        self.assertEqual(member._key, "")
        self.assertEqual(member._anchor, parent._anchor)
        self.assertEqual(member._tail, tuple(parent._tail) + (2, 0))


class _Relation:
    """The engine's relation block, as far as the port reads it (`py4gw/ui/frame.py:90-101`)."""

    def __init__(self, parent: int = 0, siblings=()) -> None:
        self.parent = parent
        self.siblings = list(siblings)


class _ScreenPosition:
    """`FramePositionStruct`'s fields, as the geometry members read them (`py4gw/ui/frame.py:65-88`)."""

    def __init__(self, left: int = 0, top: int = 0, right: int = 0, bottom: int = 0,
                 width: int = 0, height: int = 0, content=(0, 0, 0, 0),
                 scale=(1.0, 1.0), viewport=(0.0, 0.0)) -> None:
        self.left_on_screen = left
        self.top_on_screen = top
        self.right_on_screen = right
        self.bottom_on_screen = bottom
        self.width_on_screen = width
        self.height_on_screen = height
        self.content_left, self.content_top, self.content_right, self.content_bottom = content
        self.viewport_scale_x, self.viewport_scale_y = scale
        self.viewport_width, self.viewport_height = viewport


class _AnchorRecord:
    """A frame record with the fields the tree reads (`parent_id`, `child_offset_id`, `frame_hash`)."""

    def __init__(self, frame_hash: int = 0, parent_id: int = 0, child_offset_id: int = 0,
                 is_created: bool = True, is_visible: bool = True, template_type: int = 0,
                 type: int = 0, visibility_flags: int = 0, frame_layout: int = 0,
                 frame_state: int = 0, user_param: int = 0, parameters=(),
                 relation: "_Relation | None" = None, frame_callbacks=None, position=None,
                 field3_0x20: int = 0, field12_0x40: int = 0) -> None:
        self.frame_hash = frame_hash
        self.parent_id = parent_id
        self.child_offset_id = child_offset_id
        self.is_created = is_created
        self.is_visible = is_visible
        self.template_type = template_type
        self.type = type
        self.visibility_flags = visibility_flags
        self.frame_layout = frame_layout
        self.frame_state = frame_state
        self.field105_0x1c4 = user_param
        self.field31_0x84 = parameters
        self.relation = relation
        self.frame_callbacks = frame_callbacks
        self.position = position
        # the record's own undocumented slot names, which `fields()` orders by offset
        self.field3_0x20 = field3_0x20
        self.field12_0x40 = field12_0x40


class _AnchorFrameArray:
    """`client.frame_array`, in the shapes the port reads it: `iter_frames()`, `get()`, context walk."""

    def __init__(self, records: dict) -> None:
        self.records = dict(records)
        self.context_address = 0
        self.encoded = ""
        self.decoded = ""
        self.words: dict = {}

    def read_u32(self, address: int) -> int:
        """The array's own word read (`py4gw/ui/frame.py:506`), answered from this fixture's map."""

        return int(self.words.get(int(address), 0))

    def iter_frames(self):
        for frame_id in sorted(self.records):
            yield frame_id, self.records[frame_id]

    def get(self, frame_id: int):
        return self.records.get(int(frame_id))

    def frame_context_address(self, frame):
        """`FrameArray`'s own callback walk (`py4gw/ui/frame.py:569-579`), answered from this fixture."""

        return self.context_address

    def encoded_label(self, frame):
        """`FrameArray`'s own encoded-label read (`py4gw/ui/frame.py:605`), answered from this fixture."""

        return self.encoded

    def decoded_label(self, frame):
        """`FrameArray`'s own decoded-label read (`py4gw/ui/frame.py:621`), answered from this fixture."""

        return self.decoded


class _AnchorBridge:
    """`client._bridge`, as far as the render capture's reader needs it."""

    def __init__(self) -> None:
        self.context_address = 0

    def render_context_address(self) -> int:
        return self.context_address


class _AnchorReader:
    """`client.reader`, answering a prepared address with a prepared image."""

    def __init__(self) -> None:
        self.images: dict = {}

    def read(self, address: int, size: int) -> bytes:
        return self.images.get(int(address), bytes(size))


class _CallRecord:
    """The `CommandRecord` a call answers with, as far as this fixture needs it.

    `client.call_function` returns the record of the **completed** command: the callee's return
    register is `value`, and `result` is the command's own status code (`py4gw/game_thread/payload.py`,
    `_capture_return`: *"Store the callee's `eax` in the command's `value` word"*). The fixture models
    both words, because a member that reads the wrong one resolves to nothing and — with only one word
    in the fixture — a test cannot tell the two apart. Round 90 is where that was found: `_FrameTree.root`
    read `result`, i.e. the status, and this fixture agreed with it.
    """

    def __init__(self, value: int, result: int = 0) -> None:
        self.value = int(value)
        self.result = int(result)


class _AnchorClient:
    """A connected-client stand-in carrying a frame array and the port's call path."""

    def __init__(self, records: dict) -> None:
        self.frame_array = _AnchorFrameArray(records)
        self.root_pointer = 0
        self.root_status = 0
        self.child_id = 0
        self.resolvable = True
        self.calls: list = []
        self._bridge = _AnchorBridge()
        self.bridge = _ClickBridge()
        self.reader = _AnchorReader()

    def resolves(self, name: str) -> bool:
        """The resolver question, answered from `self.resolvable` (`client.resolves`)."""

        return self.resolvable

    def call_function(self, name, form, *args):
        """`client.call_function`, answered from this fixture.

        ``ui.get_root_frame_func`` is the one the port calls to read the UI root, and native's
        ``GetRootFrame`` is exactly that pointer's call (`ui_methods.cpp:415-417`). The record carries
        the pointer as its `value` and the caller's status as its `result`, which are the two words the
        real command fills in.
        """

        self.calls.append((name, form, *args))
        if name == "ui.get_root_frame_func":
            return _CallRecord(self.root_pointer, self.root_status)
        if name == frame_module._GET_CHILD_FRAME_ID_FUNC:
            return _CallRecord(self.child_id)
        return _CallRecord(0)


class TestFrameTreeAnchorsOffline(unittest.TestCase):
    """`anchor_ids`, `by_hash`, `by_label`, `hash_for_label` and `Frame`'s resolution through them.

    These are the members the two injected `PyUIManager.UIManager` frame lookups live in.  Each is resolved
    to the native function it wraps — `GetFrameIDByHash` is an array read (`ui_methods.cpp:575-588`) and
    `GetHashByLabel` is the client's `CreateHashFromWChar` over a wide string (`:542-546`) — so the first
    answers here and the second names what it still needs.
    """

    def test_anchor_ids_returns_the_snapshots_ids_for_a_hash(self) -> None:
        """The snapshot branch: `rebuild` files every frame under its hash (`frame.py:435-437`)."""

        from unittest import mock

        records = {5: _AnchorRecord(frame_hash=0xABC),
                   9: _AnchorRecord(frame_hash=0xABC),
                   12: _AnchorRecord(frame_hash=0xDEF)}
        with mock.patch("py4gw.client._current_client", _AnchorClient(records)):
            tree = frame_module._FrameTree()
            tree.rebuild()
            self.assertEqual(tree.anchor_ids(0xABC), [5, 9])
            self.assertEqual(tree.anchor_ids(0xDEF), [12])

    def test_anchor_ids_resolves_a_label_through_the_name_table(self) -> None:
        """A registry anchor is a name; `NAME_TO_HASH` is the source's own first step (`:430-434`)."""

        from unittest import mock

        label = next(iter(frame_module.NAME_TO_HASH))
        h = frame_module.NAME_TO_HASH[label]
        with mock.patch("py4gw.client._current_client", _AnchorClient({3: _AnchorRecord(frame_hash=h)})):
            tree = frame_module._FrameTree()
            tree.rebuild()
            self.assertEqual(tree.anchor_ids(label), [3])

    def test_anchor_ids_raises_for_a_name_it_cannot_know(self) -> None:
        """`no known frame named %r` — before any lookup (`:432-434`)."""

        with self.assertRaises(frame_module.FrameKeyError):
            frame_module.FrameTree.anchor_ids("no.such.frame.at.all")

    def test_anchor_ids_asks_the_engine_for_a_hash_the_snapshot_has_not_seen(self) -> None:
        """The direct read: the snapshot can be a tick behind a frame that already exists (`:449-459`)."""

        from unittest import mock

        client = _AnchorClient({1: _AnchorRecord(frame_hash=0xAA)})
        with mock.patch("py4gw.client._current_client", client):
            tree = frame_module._FrameTree()
            tree.rebuild()
            # the array gains a frame after the sweep, exactly the case the source's fallback is for
            client.frame_array.records[2] = _AnchorRecord(frame_hash=0xBB)
            self.assertEqual(tree.anchor_ids(0xBB), [2])

    def test_anchor_ids_answers_nothing_for_hash_zero(self) -> None:
        """Native opens with `if (!(hash && frame_array)) return 0;` (`ui_methods.cpp:576-578`)."""

        from unittest import mock

        with mock.patch("py4gw.client._current_client", _AnchorClient({1: _AnchorRecord(frame_hash=0)})):
            tree = frame_module._FrameTree()
            tree.rebuild()
            self.assertEqual(tree.anchor_ids(0), [])

    def test_the_label_fallback_takes_the_sources_own_failure_path(self) -> None:
        """A label the snapshot has not seen falls to the client's hash (`frame.py:449-459`).

        The source wraps that lookup in ``except Exception`` and uses 0, so a client that cannot hash
        the label is its own failure path: the hash lookup underneath then answers, and with no frame
        carrying the hash the member returns an empty list rather than a plausible id. The client here
        is `_AnchorClient`, whose call path answers the root pointer and 0 for everything else — so the
        label hash comes back 0, which is the unresolvable case.
        """

        from unittest import mock

        label = next(iter(frame_module.NAME_TO_HASH))
        h = frame_module.NAME_TO_HASH[label]
        self.assertNotIn(h, {0x1234: object()})
        with mock.patch("py4gw.client._current_client", _AnchorClient({1: _AnchorRecord(frame_hash=0x1234)})):
            tree = frame_module._FrameTree()
            tree.rebuild()
            self.assertEqual(tree.anchor_ids(label), [])

    def test_by_hash_answers_from_the_array(self) -> None:
        """`by_hash` is the same read, wrapped as a handle (`frame.py:579-581`)."""

        from unittest import mock

        client = _AnchorClient({1: _AnchorRecord(frame_hash=0xAA)})
        with mock.patch("py4gw.client._current_client", client):
            tree = frame_module._FrameTree()
            tree.rebuild()
            client.frame_array.records[2] = _AnchorRecord(frame_hash=0xBB)
            f = tree.by_hash(0xBB)
            self.assertIsInstance(f, frame_module.Frame)
            self.assertEqual(f._fid, 2)

    def test_hash_for_label_hands_the_client_the_wide_label_and_its_length(self) -> None:
        """`GetHashByLabel` is `g_create_hash_from_wchar_func(label, -1)` (`ui_methods.cpp:542-546`).

        The label goes into the block's data region — the port has no frame in the client to build it
        in — as UTF-16 code units with the terminator `std::wstring::c_str()` adds, and the client's
        answer is the call's **return register** (the record's `value`).
        """

        from unittest import mock

        from py4gw.game_thread.shared_block import CallForm

        class _LabelClient:
            def __init__(self) -> None:
                self.bridge = _ClickBridge()
                self.calls: list = []

            def resolves(self, name: str) -> bool:
                return True

            def call_function(self, name, form, *args):
                self.calls.append((name, form, *args))
                return _CallRecord(0xABCD1234)

        client = _LabelClient()
        with mock.patch("py4gw.client._current_client", client):
            self.assertEqual(frame_module.FrameTree.hash_for_label("DlgRedirect"), 0xABCD1234)

        self.assertEqual(
            client.bridge.writes,
            [
                (
                    frame_module._LABEL_OFFSET,
                    "DlgRedirect".encode("utf-16-le") + b"\x00\x00",
                    0x00D00E40,
                )
            ],
        )
        self.assertEqual(
            client.calls,
            [
                (
                    frame_module._CREATE_HASH_FROM_WCHAR_FUNC,
                    int(CallForm.U32_U32),
                    0x00D00E40,
                    frame_module._HASH_LABEL_LENGTH,
                )
            ],
        )

    def test_a_client_that_cannot_hash_answers_zero(self) -> None:
        """Native's own guard: `g_create_hash_from_wchar_func && frame_label` (`:543-545`)."""

        from unittest import mock

        class _NoHashClient(_AnchorClient):
            def resolves(self, name: str) -> bool:
                return False

        client = _NoHashClient({})
        with mock.patch("py4gw.client._current_client", client):
            self.assertEqual(frame_module.FrameTree.hash_for_label("DlgRedirect"), 0)
        self.assertEqual(client.bridge.writes, [], "nothing is placed when the call cannot be made")
    def test_by_label_is_the_hash_then_the_arrays_scan(self) -> None:
        """`GetFrameIDByLabel` → `GetFrameByLabel`: hash, then the first frame carrying it (`:556-573`)."""

        from unittest import mock

        class _LabelClient(_AnchorClient):
            def call_function(self, name, form, *args):
                self.calls.append((name, form, *args))
                return _CallRecord(0xABCD)

        client = _LabelClient({4: _AnchorRecord(frame_hash=0xABCD)})
        with mock.patch("py4gw.client._current_client", client):
            found = frame_module.FrameTree.by_label("DlgRedirect")

        self.assertIsInstance(found, frame_module.Frame)
        self.assertEqual(found._fid, 4)

    def test_a_label_no_frame_carries_is_a_handle_that_resolves_to_nothing(self) -> None:
        """The binding's `or 0` — a hash with no frame is `Frame.from_id(0)` (`frame.py:583-585`)."""

        from unittest import mock

        class _LabelClient(_AnchorClient):
            def call_function(self, name, form, *args):
                self.calls.append((name, form, *args))
                return _CallRecord(0xABCD)

        client = _LabelClient({4: _AnchorRecord(frame_hash=0x1234)})
        with mock.patch("py4gw.client._current_client", client):
            found = frame_module.FrameTree.by_label("DlgRedirect")
            self.assertEqual(found._fid, 0)
            self.assertFalse(found.exists)

    def test_resolve_walks_the_anchor_and_its_codes(self) -> None:
        """`_resolve` is the funnel: snapshot anchor, then one `child_of` per code (`frame.py:893-917`)."""

        from unittest import mock

        h = 0xABCD
        records = {1: _AnchorRecord(frame_hash=h),
                   2: _AnchorRecord(parent_id=1, child_offset_id=7),
                   3: _AnchorRecord(parent_id=2, child_offset_id=9)}
        with mock.patch("py4gw.client._current_client", _AnchorClient(records)):
            f = frame_module.Frame.from_hash(h, [7, 9])
            self.assertIsNone(f._fid)
            self.assertTrue(f.exists)
            self.assertEqual(f._fid, 3)

    def test_resolve_reports_a_missing_step_as_not_existing(self) -> None:
        """A code with no child breaks the walk and leaves the handle unresolved (`:906-917`)."""

        from unittest import mock

        h = 0xABCD
        records = {1: _AnchorRecord(frame_hash=h), 2: _AnchorRecord(parent_id=1, child_offset_id=7)}
        with mock.patch("py4gw.client._current_client", _AnchorClient(records)):
            f = frame_module.Frame.from_hash(h, [7, 99])
            self.assertFalse(f.exists)
            self.assertIsNone(f._fid)

    def test_a_wrapped_id_resolves_from_the_snapshot(self) -> None:
        """The wrapped-id branch: the snapshot first, then the engine (`:899-904`)."""

        from unittest import mock

        with mock.patch("py4gw.client._current_client", _AnchorClient({1: _AnchorRecord()})):
            f = frame_module.Frame.from_id(1)
            self.assertTrue(f.exists)
            self.assertEqual(f._fid, 1)
            gone = frame_module.Frame.from_id(999)
            self.assertFalse(gone.exists)
            self.assertIsNone(gone._fid)

    def test_exists_with_no_client_states_that_a_read_needs_one(self) -> None:
        """Every read in this port needs the connection; the source's in-process tree never did."""

        self.assertRaises(RuntimeError, lambda: frame_module.Frame.from_id(1).exists)


class TestFrameReadsOffline(unittest.TestCase):
    """`Frame`'s read surface — `frame.py:927-1126`, the members that read through `_resolve` and the tree.

    Every one of these is composition over `_resolve`, the tree's snapshot and the migrated tables.  The two
    members that would need the injected runtime are stated where they are: `label` (native `GetFrameTitle`
    binary-searches the client's title table through two client function pointers) and `title` (the same call).
    """

    def _named(self) -> tuple[int, str]:
        """A real (hash, engine name) pair from the ported name table."""

        h, name = next(iter(frame_module.FRAME_NAMES.items()))
        return int(h), name

    def _chain(self, parts: list[int]) -> dict:
        """Frame records forming one registry path: a named anchor, then a child per code."""

        records = {1: _AnchorRecord(frame_hash=parts[0])}
        parent = 1
        for index, code in enumerate(parts[1:], start=2):
            records[index] = _AnchorRecord(parent_id=parent, child_offset_id=code)
            parent = index
        return records

    def test_frame_id_raises_when_it_cannot_resolve(self) -> None:
        """`frame_id` is the strict accessor; `_target_id` is the lenient one (`frame.py:927-948`)."""

        from unittest import mock

        h, _ = self._named()
        with mock.patch("py4gw.client._current_client", _AnchorClient({1: _AnchorRecord(frame_hash=h)})):
            self.assertEqual(frame_module.Frame.from_hash(h, []).frame_id, 1)
            gone = frame_module.Frame.from_hash(0xDEADBEEF, [])
            with self.assertRaises(frame_module.FrameNotFound) as caught:
                gone.frame_id
            self.assertIn("did not resolve", str(caught.exception))
            self.assertEqual(gone._target_id(), 0)

    def test_the_identity_reads_come_from_the_snapshot(self) -> None:
        """`hash`, `name` and `code` are the tree's own answers for the resolved id (`:968-985`)."""

        from unittest import mock

        h, name = self._named()
        with mock.patch("py4gw.client._current_client",
                        _AnchorClient({1: _AnchorRecord(frame_hash=h, child_offset_id=7)})):
            f = frame_module.Frame.from_id(1)
            self.assertEqual(f.hash, h)
            self.assertEqual(f.name, name)
            self.assertEqual(f.code, 7)
            self.assertEqual(f.key, "")
            self.assertFalse(f.is_anonymous)

    def test_key_is_what_the_handle_was_built_from(self) -> None:
        """No read: `key` is the string this handle was constructed with (`:968-970`)."""

        self.assertEqual(frame_module.Frame("Skillbar.Skill1").key, "Skillbar.Skill1")

    def test_label_reports_no_label_and_names_what_it_needs(self) -> None:
        """`GetFrameTitle` is a call, so the source's own `except Exception` answers `""` (`:987-995`).

        The requirement is named in the member and in `docs/TARGET_SIDE_WORK.md`; this pins the source's
        failure path — a frame whose label cannot be read reports no label, rather than a stand-in.
        """

        from unittest import mock

        with mock.patch("py4gw.client._current_client", _AnchorClient({1: _AnchorRecord()})):
            self.assertEqual(frame_module.Frame.from_id(1).label, "")

    def test_path_is_the_hash_for_a_named_frame(self) -> None:
        """A named frame is addressed by its hash alone (`:1061-1084`)."""

        from unittest import mock

        h, _ = self._named()
        with mock.patch("py4gw.client._current_client", _AnchorClient({1: _AnchorRecord(frame_hash=h)})):
            self.assertEqual(frame_module.Frame.from_id(1).path(), str(h))

    def test_path_walks_to_the_nearest_named_ancestor(self) -> None:
        """An unnamed frame is `ancestor_hash,code,code,...`, innermost code last (`:1069-1084`)."""

        from unittest import mock

        h, _ = self._named()
        records = {1: _AnchorRecord(frame_hash=h),
                   2: _AnchorRecord(parent_id=1, child_offset_id=7),
                   3: _AnchorRecord(parent_id=2, child_offset_id=9)}
        with mock.patch("py4gw.client._current_client", _AnchorClient(records)):
            self.assertEqual(frame_module.Frame.from_id(3).path(), "%d,7,9" % h)

    def test_path_is_empty_for_a_frame_that_is_not_there(self) -> None:
        """No resolution, no path (`:1063-1064`)."""

        from unittest import mock

        with mock.patch("py4gw.client._current_client", _AnchorClient({1: _AnchorRecord()})):
            self.assertEqual(frame_module.Frame.from_id(999).path(), "")

    def test_the_registry_inversion_names_an_unnamed_frame(self) -> None:
        """A real registry path, rebuilt as a frame chain, must answer its own dotted key.

        `key_by_path()` is the registry inverted onto the `"<anchor_hash>,<codes>"` form `path()` produces;
        this walks the tables against each other, one entry end to end.
        """

        from unittest import mock

        candidate = next(((p, k) for p, k in frame_module.key_by_path().items()
                          if len(p.split(",")) > 1), None)
        if candidate is None:
            self.skipTest("the registry has no entry with child codes")
        path_string, dotted = candidate
        parts = [int(part) for part in path_string.split(",")]
        records = self._chain(parts)
        with mock.patch("py4gw.client._current_client", _AnchorClient(records)):
            f = frame_module.Frame.from_id(len(records))
            self.assertEqual(f.path(), path_string)
            self.assertEqual(f.registry_key, dotted)
            self.assertIn(dotted, f.describe())

    def test_the_alias_table_names_a_frame_by_its_path(self) -> None:
        """Same walk, against the alias inversion (`:997-1002`)."""

        from unittest import mock

        candidate = next(iter(frame_module.alias_by_path().items()), None)
        if candidate is None:
            self.skipTest("the alias table is empty")
        path_string, label = candidate
        parts = [int(part) for part in path_string.split(",")]
        records = self._chain(parts)
        with mock.patch("py4gw.client._current_client", _AnchorClient(records)):
            f = frame_module.Frame.from_id(len(records))
            self.assertEqual(f.path(), path_string)
            self.assertEqual(f.alias, label)
            self.assertIn("(%s)" % label, f.describe())

    def test_registry_key_prefers_the_handles_own_key(self) -> None:
        """`key` is what the handle was built from; `registry_key` is what the frame turns out to be."""

        from unittest import mock

        h, _ = self._named()
        with mock.patch("py4gw.client._current_client", _AnchorClient({1: _AnchorRecord(frame_hash=h)})):
            f = frame_module.Frame("Skillbar.Skill1")
            self.assertEqual(f.registry_key, "Skillbar.Skill1")

    def test_widget_id_is_the_frame_id_in_hex(self) -> None:
        """`fr%x` over the target id, which is lenient about resolution (`:1035-1043`)."""

        from unittest import mock

        with mock.patch("py4gw.client._current_client", _AnchorClient({0x1A2B: _AnchorRecord()})):
            f = frame_module.Frame.from_id(0x1A2B)
            self.assertEqual(f.widget_id, "fr1a2b")
            self.assertEqual(frame_module.Frame.from_hash(0xDEADBEEF, []).widget_id, "fr0")

    def test_matches_is_the_engine_name(self) -> None:
        """The identity check for paths that host different frames (`:1045-1054`)."""

        from unittest import mock

        h, name = self._named()
        with mock.patch("py4gw.client._current_client", _AnchorClient({1: _AnchorRecord(frame_hash=h)})):
            f = frame_module.Frame.from_id(1)
            self.assertTrue(f.matches(name))
            self.assertTrue(f.matches("something else", name))
            self.assertFalse(f.matches("something else"))
            self.assertFalse(frame_module.Frame.from_id(999).matches(name))

    def test_is_anonymous_is_resolved_but_unnamed(self) -> None:
        """`exists and hash == 0` (`:1056-1059`)."""

        from unittest import mock

        with mock.patch("py4gw.client._current_client",
                        _AnchorClient({1: _AnchorRecord(frame_hash=0)})):
            self.assertTrue(frame_module.Frame.from_id(1).is_anonymous)

    def test_the_state_reads_follow_the_record(self) -> None:
        """`is_created` / `is_visible` / `is_usable` are the one live read (`:1087-1105`)."""

        from unittest import mock

        hidden = _AnchorRecord(is_created=True, is_visible=False)
        with mock.patch("py4gw.client._current_client", _AnchorClient({1: hidden})):
            f = frame_module.Frame.from_id(1)
            self.assertTrue(f.is_created)
            self.assertFalse(f.is_visible)
            self.assertFalse(f.is_usable)

        shown = _AnchorRecord(is_created=True, is_visible=True)
        with mock.patch("py4gw.client._current_client", _AnchorClient({1: shown})):
            f = frame_module.Frame.from_id(1)
            self.assertTrue(f.is_usable)

    def test_the_record_describes_the_widget(self) -> None:
        """`template_type`, `type`, `visibility_flags` and `frame_layout` are record fields (`:1107-1126`)."""

        from unittest import mock

        record = _AnchorRecord(template_type=1, type=5, visibility_flags=0x21, frame_layout=3)
        with mock.patch("py4gw.client._current_client", _AnchorClient({1: record})):
            f = frame_module.Frame.from_id(1)
            self.assertEqual(f.template_type, 1)
            self.assertEqual(f.type, 5)
            self.assertEqual(f.visibility_flags, 0x21)
            self.assertEqual(f.frame_layout, 3)

    def test_blackboard_is_the_handles_own_space(self) -> None:
        """It lives on the handle, not the frame (`:953-961`)."""

        board = {"slot": 3}
        f = frame_module.Frame.from_hash(0xABCD, (), board)
        self.assertIs(f.blackboard, f._blackboard)
        self.assertEqual(f.blackboard, {"slot": 3})
        f.blackboard["extra"] = 1
        self.assertEqual(board, {"slot": 3}, "the caller's dict was adopted, not copied")

    def test_refresh_drops_the_cached_copy(self) -> None:
        """Mid-tick re-read: the tree forgets this frame's copy (`:963-965`)."""

        from unittest import mock

        with mock.patch("py4gw.client._current_client", _AnchorClient({1: _AnchorRecord()})):
            f = frame_module.Frame.from_id(1)
            f._state()
            self.assertIn(1, frame_module.FrameTree._state)
            f.refresh()
            self.assertNotIn(1, frame_module.FrameTree._state)


class TestFrameRelationAndInspectionOffline(unittest.TestCase):
    """`Frame`'s relation block, its inspection surfaces, and the three native record reads.

    Source `frame.py:1128-1223`.  `state_bit`, `user_param` and `context` are the three that go through the
    injected UI manager in the source, and each was resolved to the native function it wraps — all three turn
    out to be reads of one frame record, so all three answer here.
    """

    def test_siblings_returns_handles_never_ids(self) -> None:
        """`relation.siblings` is a raw id list and must not leave the class (`:1128-1142`)."""

        from unittest import mock

        record = _AnchorRecord(relation=_Relation(parent=1, siblings=[4, 5]))
        with mock.patch("py4gw.client._current_client", _AnchorClient({1: record})):
            siblings = frame_module.Frame.from_id(1).siblings()
            self.assertTrue(all(isinstance(s, frame_module.Frame) for s in siblings))
            self.assertEqual([s._fid for s in siblings], [4, 5])

    def test_siblings_is_empty_without_a_relation_block(self) -> None:
        """No relation, no handles (`:1136-1138`)."""

        from unittest import mock

        with mock.patch("py4gw.client._current_client", _AnchorClient({1: _AnchorRecord()})):
            self.assertEqual(frame_module.Frame.from_id(1).siblings(), [])

    def test_frame_callbacks_and_frame_state_are_record_fields(self) -> None:
        """Handed back as they are, or zeroed when the frame is gone (`:1144-1152`)."""

        from unittest import mock

        callbacks = object()
        record = _AnchorRecord(frame_state=0x200, frame_callbacks=callbacks)
        with mock.patch("py4gw.client._current_client", _AnchorClient({1: record})):
            f = frame_module.Frame.from_id(1)
            self.assertIs(f.frame_callbacks, callbacks)
            self.assertEqual(f.frame_state, 0x200)

    def test_fields_lists_named_scalars_then_slots_by_offset(self) -> None:
        """Named fields sorted, then `field*_0x..` by struct offset, one level of nesting (`:1154-1196`)."""

        from unittest import mock

        record = _AnchorRecord(frame_state=0x200, is_created=False,
                               field3_0x20=1, field12_0x40=7)
        record.relation = _Relation(parent=9, siblings=[1])
        with mock.patch("py4gw.client._current_client", _AnchorClient({1: record})):
            out = frame_module.Frame.from_id(1).fields()
        self.assertEqual(out["frame_state"], 0x200)
        self.assertEqual(out["relation.parent"], 9, "one level of nesting is flattened with a prefix")
        self.assertNotIn("relation.siblings", out, "a list is not a scalar")
        keys = list(out)
        self.assertLess(keys.index("field3_0x20"), keys.index("field12_0x40"),
                        "the undocumented slots are ordered by offset, not by name")

    def test_fields_is_empty_for_a_frame_that_is_not_there(self) -> None:
        """A dead id yields no fields rather than an error (`:1162-1164`)."""

        from unittest import mock

        with mock.patch("py4gw.client._current_client", _AnchorClient({1: _AnchorRecord()})):
            self.assertEqual(frame_module.Frame.from_id(999).fields(), {})

    def test_parameters_is_the_frames_parameter_slot(self) -> None:
        """Struct slot 0x84, as plain data (`:1198-1207`)."""

        from unittest import mock

        with mock.patch("py4gw.client._current_client",
                        _AnchorClient({1: _AnchorRecord(parameters=(1, 2, 3))})):
            self.assertEqual(frame_module.Frame.from_id(1).parameters, [1, 2, 3])
        with mock.patch("py4gw.client._current_client", _AnchorClient({1: _AnchorRecord()})):
            self.assertEqual(frame_module.Frame.from_id(1).parameters, [])
            self.assertEqual(frame_module.Frame.from_id(999).parameters, [])

    def test_parent_id_comes_from_the_snapshot(self) -> None:
        """0 at the root or when gone (`:1209-1212`)."""

        from unittest import mock

        records = {1: _AnchorRecord(frame_hash=0xAA), 2: _AnchorRecord(parent_id=1, child_offset_id=5)}
        with mock.patch("py4gw.client._current_client", _AnchorClient(records)):
            self.assertEqual(frame_module.Frame.from_id(2).parent_id, 1)
            self.assertEqual(frame_module.Frame.from_id(1).parent_id, 0)
            self.assertEqual(frame_module.Frame.from_id(999).parent_id, 0)

    def test_state_bit_is_the_records_own_mask(self) -> None:
        """Native `GetFrameStateBit` is `frame && (frame->frame_state & bit) != 0` (`ui_methods.cpp:1829`)."""

        from unittest import mock

        record = _AnchorRecord(frame_state=0x200)
        with mock.patch("py4gw.client._current_client", _AnchorClient({1: record})):
            f = frame_module.Frame.from_id(1)
            self.assertTrue(f.state_bit(0x200))
            self.assertFalse(f.state_bit(0x10))
            self.assertFalse(frame_module.Frame.from_id(999).state_bit(0x200))

    def test_user_param_is_the_records_0x1c4_word(self) -> None:
        """Native `GetFrameUserParam` is `frame ? frame->field105_0x1c4 : 0` (`ui_methods.cpp:1825`)."""

        from unittest import mock

        with mock.patch("py4gw.client._current_client",
                        _AnchorClient({1: _AnchorRecord(user_param=42)})):
            self.assertEqual(frame_module.Frame.from_id(1).user_param, 42)
            self.assertEqual(frame_module.Frame.from_id(999).user_param, 0)

    def test_context_is_the_frames_registered_context(self) -> None:
        """Native `GetFrameContext` (`ui_methods.cpp:758-772`) is the port's own callback walk."""

        from unittest import mock

        client = _AnchorClient({1: _AnchorRecord()})
        client.frame_array.context_address = 0x1234
        with mock.patch("py4gw.client._current_client", client):
            self.assertEqual(frame_module.Frame.from_id(1).context, 0x1234)

        with mock.patch("py4gw.client._current_client", _AnchorClient({1: _AnchorRecord()})):
            self.assertEqual(frame_module.Frame.from_id(1).context, 0)
            self.assertEqual(frame_module.Frame.from_id(999).context, 0)


class TestFramePresentationAndGeometryOffline(unittest.TestCase):
    """`Frame`'s text, geometry and the action members — `frame.py:1273-1413`.

    The eight that read answer here: `text`/`encoded` are the port's own label readers (native
    `TextLabelFrame::GetDecodedLabel` / `GetEncodedLabel`) and the geometry is the position struct.  The
    action and write members are declared and name their requirement: native runs every one of them through a
    **game-thread enqueue** (`ui_bindings.cpp:1066-1103`, `1447`), which is the model this port's
    `py4gw/game_thread` layer implements, and each needs a call into the client and a live run.
    """

    POSITION = _ScreenPosition(left=10, top=20, right=110, bottom=70, width=100, height=50,
                               content=(1, 2, 3, 4), scale=(2.0, 3.0), viewport=(1280.0, 720.0))

    def setUp(self) -> None:
        """Start from no held copy.

        The tree is a module singleton and it keeps a frame's last good read across calls (the source's
        buffer rule), so without this a test would read the record a previous test left behind.
        """

        frame_module.FrameTree.invalidate()

    def _client(self, record=None, **array_attrs):
        client = _AnchorClient({1: record if record is not None else _AnchorRecord()})
        for name, value in array_attrs.items():
            setattr(client.frame_array, name, value)
        return client

    def test_text_and_encoded_are_the_frames_own_labels(self) -> None:
        """Decoded and stored label, both from the port's own reads (`:1294-1308`)."""

        from unittest import mock

        client = self._client(encoded="\x01encoded", decoded="Rendered")
        with mock.patch("py4gw.client._current_client", client):
            f = frame_module.Frame.from_id(1)
            self.assertEqual(f.encoded(), "\x01encoded")
            self.assertEqual(f.text(), "Rendered")
            self.assertEqual(frame_module.Frame.from_id(999).text(), "")
            self.assertEqual(frame_module.Frame.from_id(999).encoded(), "")

    def test_the_geometry_is_natives_own_methods_on_the_position_record(self) -> None:
        """The computations live on `FramePositionStruct`, where native puts them (`ui.h:504-551`)."""

        from py4gw.ui.frame import FramePositionStruct

        for name in ("viewport_scale", "top_left_on_screen", "bottom_right_on_screen", "size_on_screen"):
            with self.subTest(method=name):
                self.assertTrue(hasattr(FramePositionStruct, name))

    def test_rect_is_zeroed_without_a_position(self) -> None:
        """A frame that is not there answers zeros before any computation is reached (`:1349-1353`)."""

        from unittest import mock

        with mock.patch("py4gw.client._current_client", self._client()):
            self.assertEqual(frame_module.Frame.from_id(999).coords(), (0, 0, 0, 0))

    def test_coords_requires_the_frame_to_be_there(self) -> None:
        """`coords` checks existence first, then defers to `rect` (`:1349-1353`)."""

        from unittest import mock

        with mock.patch("py4gw.client._current_client", self._client(_AnchorRecord(position=self.POSITION))):
            self.assertEqual(frame_module.Frame.from_id(1).coords(), (0, 0, 0, 0),
                             "no root here, and the wrapper's words are only filled with one")
        with mock.patch("py4gw.client._current_client", self._client()):
            self.assertEqual(frame_module.Frame.from_id(999).coords(), (0, 0, 0, 0))

    def test_viewport_scale_names_the_render_viewport_it_needs(self) -> None:
        """No root and no capture is the identity, which is what Reforged answers without a root (`:1381-1398`)."""

        from unittest import mock

        with mock.patch("py4gw.client._current_client", self._client(_AnchorRecord(position=self.POSITION))):
            self.assertEqual(frame_module.Frame.from_id(1).viewport_scale(), (1.0, 1.0))

    def test_viewport_dimensions_come_from_the_position_struct(self) -> None:
        """Read straight off the frame, with no existence gate (`:1400-1413`)."""

        from unittest import mock

        with mock.patch("py4gw.client._current_client", self._client(_AnchorRecord(position=self.POSITION))):
            self.assertEqual(frame_module.Frame.from_id(1).viewport_dimensions(), (1280.0, 720.0))
        frame_module.FrameTree.invalidate()
        with mock.patch("py4gw.client._current_client", self._client()):
            self.assertEqual(frame_module.Frame.from_id(1).viewport_dimensions(), (0.0, 0.0))

    def test_navigation_is_the_snapshot_walk(self) -> None:
        """`parent`, `children`, `child_codes`, `child`, `find_child` (`:1476-1515`)."""

        from unittest import mock

        records = {1: _AnchorRecord(frame_hash=0xAA),
                   2: _AnchorRecord(parent_id=1, child_offset_id=7),
                   3: _AnchorRecord(parent_id=2, child_offset_id=9)}
        with mock.patch("py4gw.client._current_client", _AnchorClient(records)):
            root = frame_module.Frame.from_id(1)
            self.assertEqual([c._fid for c in root.children()], [2])
            self.assertEqual(root.child_codes(), [7])
            self.assertEqual(root.child(7)._fid, 2)
            found = root.find_child(7, 9)
            if found is None:
                self.fail("find_child(7, 9) should resolve")
            self.assertEqual(found._fid, 3)
            self.assertIsNone(root.find_child(7, 99))
            self.assertEqual(frame_module.Frame.from_id(3).parent()._fid, 2)
            with self.assertRaises(frame_module.FrameNotFound):
                root.parent()
            with self.assertRaises(frame_module.FrameNotFound):
                root.child(99)

    def test_send_message_text_names_the_client_call_it_needs(self) -> None:
        """The wide-string member waits on that game-thread call plus the wide-string form (`:1288-1291`).

        `send_message` itself answers since round 58 — the five-word call is built and tested in
        `TestFrameSendMessageOffline`; this member still needs the string form on top of it.
        """

        from unittest import mock

        with mock.patch("py4gw.client._current_client", self._client()):
            with self.assertRaises(NotImplementedError) as caught:
                frame_module.Frame.from_id(1).send_message_text(
                    frame_module._MOUSE_HOVER_STATE, "text"
                )
        text = str(caught.exception)
        self.assertIn("SendFrameUIMessage", text)
        self.assertIn("game-thread", text)

    def test_set_text_names_the_label_write_it_needs(self) -> None:
        """A write into the client's label, enqueued on the game thread (`:1310-1312`)."""

        from unittest import mock

        with mock.patch("py4gw.client._current_client", self._client()):
            with self.assertRaises(NotImplementedError) as caught:
                frame_module.Frame.from_id(1).set_text("\x01text")
            self.assertIn("set_text_label_by_frame_id", str(caught.exception))

    def test_title_reports_no_title_and_names_what_it_needs(self) -> None:
        """The same client title-table call as `label`, behind the source's own `except` (`:1314-1321`)."""

        from unittest import mock

        with mock.patch("py4gw.client._current_client", self._client()):
            self.assertEqual(frame_module.Frame.from_id(1).title(), "")

    def test_the_mouse_actions_refuse_on_an_unusable_frame(self) -> None:
        """The source's guard runs before the action; only a usable frame reaches the call (`:1273-1281`)."""

        from unittest import mock

        unusable = _AnchorRecord(is_created=False, is_visible=False)
        with mock.patch("py4gw.client._current_client", self._client(unusable)):
            f = frame_module.Frame.from_id(1)
            self.assertFalse(f.is_usable)
            self.assertIsNone(f.mouse_action(frame_module._MOUSE_HOVER_STATE))
            self.assertIsNone(f.mouse_click_action(frame_module._MOUSE_HOVER_STATE))

    def test_the_mouse_actions_name_the_client_calls_they_need(self) -> None:
        """Native enqueues `ui::TestMouseAction` / `ui::TestMouseClickAction` (`ui_bindings.cpp:1093-1103`)."""

        from unittest import mock

        with mock.patch("py4gw.client._current_client", self._client()):
            for member, call, named in (
                    ("mouse_action", lambda: frame_module.Frame.from_id(1).mouse_action(
                        frame_module._MOUSE_HOVER_STATE), "TestMouseAction"),
                    ("mouse_click_action", lambda: frame_module.Frame.from_id(1).mouse_click_action(
                        frame_module._MOUSE_HOVER_STATE), "TestMouseClickAction")):
                with self.subTest(member=member):
                    with self.assertRaises(NotImplementedError) as caught:
                        call()
                    self.assertIn(named, str(caught.exception))


def _nav_record(address: int, parent_relation: int = 0, code: int = 0, frame_hash: int = 0):
    """A real `FrameStruct` bound to an address, so a relation walk has the pointer it compares.

    `FrameArray.get` binds the address each record was read from (`py4gw/ui/frame.py:518`), and native's
    parent test is `relation.GetParent() == frame` — a comparison of relation pointers — so a stand-in
    without an address could not exercise these members at all.
    """

    from py4gw.ui.frame import FrameStruct

    record = FrameStruct()
    record.bind_address(address)
    setattr(record, "frame_state", 0x4)          # native `IsCreated`
    setattr(record, "child_offset_id", code)
    relation = getattr(record, "relation")
    setattr(relation, "parent", parent_relation)
    setattr(relation, "frame_hash_id", frame_hash)
    return record


class TestFrameNativeNavigationOffline(unittest.TestCase):
    """The native walkers — `frame.py:1482-1588`: parent pointers, child scans and the relation walker.

    These read the client's frame array rather than the tree snapshot.  Native compares **relation pointers**
    (`candidate->relation.GetParent() == frame`, `ui_methods.cpp:485`) and selects by `child_offset_id`, so the
    fixture carries real records with addresses and a word map for the parent-id read.
    """

    RELATION_AT = 0x128        # FrameStruct.relation.offset
    FRAME_ID_AT = 0xBC         # FrameStruct.frame_id.offset

    def _client(self, records: dict, words: dict | None = None):
        client = _AnchorClient(records)
        client.frame_array.words = dict(words or {})
        return client

    def test_parent_id_native_reads_the_parents_id_word(self) -> None:
        """`relation.GetParent()->frame_id` (`ui_methods.cpp:1813-1819`, `:414-416`)."""

        from unittest import mock

        # this frame sits at 0x1000; its stored relation pointer is the parent's relation at 0x2128, so the
        # parent record starts at 0x2000 and its frame_id word is at 0x20BC
        records = {1: _nav_record(0x1000, parent_relation=0x2000 + self.RELATION_AT)}
        with mock.patch("py4gw.client._current_client",
                        self._client(records, {0x2000 + self.FRAME_ID_AT: 7})):
            f = frame_module.Frame.from_id(1)
            self.assertEqual(f.parent_id_native(), 7)
            self.assertEqual(f.parent_direct()._fid, 7)

    def test_a_frame_with_no_parent_answers_zero(self) -> None:
        """A null relation pointer is native's `parent ? ... : 0` (`:1813-1819`)."""

        from unittest import mock

        with mock.patch("py4gw.client._current_client", self._client({1: _nav_record(0x1000)})):
            f = frame_module.Frame.from_id(1)
            self.assertEqual(f.parent_id_native(), 0)
            self.assertEqual(f.parent_direct()._fid, 0)

    def test_a_child_is_found_by_parent_pointer_and_hash(self) -> None:
        """`GetChildFromNameHash` (`ui_methods.cpp:609-621`), and `child_named` over the name table."""

        from unittest import mock

        h, name = next(iter(frame_module.FRAME_NAMES.items()))
        mine = 0x1000 + self.RELATION_AT
        records = {1: _nav_record(0x1000),
                   2: _nav_record(0x2000, parent_relation=mine, frame_hash=h),
                   3: _nav_record(0x3000, parent_relation=0x9999, frame_hash=h)}
        with mock.patch("py4gw.client._current_client", self._client(records)):
            f = frame_module.Frame.from_id(1)
            self.assertEqual(f.child_with_hash(h)._fid, 2, "frame 3 has the hash but another parent")
            self.assertEqual(f.child_named(name)._fid, 2)
            self.assertEqual(f.child_with_hash(h + 1)._fid, 0)
            with self.assertRaises(frame_module.FrameKeyError):
                f.child_named("no.such.frame.at.all")

    def test_the_related_walkers_select_by_child_offset(self) -> None:
        """All four branches of `GetRelatedFrameById` (`ui_methods.cpp:465-533`) in one fixture."""

        from unittest import mock

        mine = 0x1000 + self.RELATION_AT
        records = {1: _nav_record(0x1000),
                   2: _nav_record(0x2000, parent_relation=mine, code=5),
                   3: _nav_record(0x3000, parent_relation=mine, code=9),
                   4: _nav_record(0x4000, parent_relation=mine, code=1)}
        with mock.patch("py4gw.client._current_client", self._client(records)):
            parent = frame_module.Frame.from_id(1)
            second = frame_module.Frame.from_id(2)
            third = frame_module.Frame.from_id(3)
            self.assertEqual(parent.first_child()._fid, 4, "smallest offset")
            self.assertEqual(parent.last_child()._fid, 3, "largest offset")
            self.assertEqual(second.next_sibling()._fid, 3)
            self.assertEqual(third.prev_sibling()._fid, 2)
            self.assertEqual(parent.related(frame_module.RELATION_FIRST_CHILD)._fid, 4)
            self.assertEqual(parent.related(frame_module.RELATION_LAST_CHILD)._fid, 3)
            self.assertEqual(second.related(frame_module.RELATION_NEXT_SIBLING)._fid, 3)
            self.assertEqual(second.related(frame_module.RELATION_PREV_SIBLING)._fid, 4)
            # `start_after` is a frame id: from frame 2 (offset 5) take the next one above and below
            self.assertEqual(parent.related(frame_module.RELATION_FIRST_CHILD, start_after=2)._fid, 3)
            self.assertEqual(parent.related(frame_module.RELATION_LAST_CHILD, start_after=2)._fid, 4)

    def test_a_frame_that_is_not_there_raises(self) -> None:
        """These members take the strict `self.frame_id`, so an unresolved frame raises (`:1476-1515`).

        The source calls `self.frame_id` (not `_target_id`) in every one of them, so a handle that cannot
        resolve raises `FrameNotFound` before any walk happens — that is the source's behaviour, not a guard
        added here.
        """

        from unittest import mock

        with mock.patch("py4gw.client._current_client", self._client({1: _nav_record(0x1000)})):
            gone = frame_module.Frame.from_id(999)
            for member, call in (("first_child", gone.first_child),
                                 ("last_child", gone.last_child),
                                 ("next_sibling", gone.next_sibling),
                                 ("prev_sibling", gone.prev_sibling),
                                 ("parent_id_native", gone.parent_id_native),
                                 ("child_with_hash", lambda: gone.child_with_hash(0x1234)),
                                 ("related", lambda: gone.related(frame_module.RELATION_FIRST_CHILD)),
                                 ("is_ancestor_of", lambda: gone.is_ancestor_of(gone))):
                with self.subTest(member=member):
                    with self.assertRaises(frame_module.FrameNotFound):
                        call()

    def test_is_ancestor_walks_the_parent_chain(self) -> None:
        """`IsAncestorOf` (`ui_methods.cpp:662-675`): one word read per step up the chain."""

        from unittest import mock

        records = {1: _nav_record(0x1000),
                   2: _nav_record(0x2000, parent_relation=0x1000 + self.RELATION_AT),
                   3: _nav_record(0x3000, parent_relation=0x2000 + self.RELATION_AT)}
        words = {0x2000 + self.RELATION_AT: 0x1000 + self.RELATION_AT}
        with mock.patch("py4gw.client._current_client", self._client(records, words)):
            one = frame_module.Frame.from_id(1)
            two = frame_module.Frame.from_id(2)
            three = frame_module.Frame.from_id(3)
            self.assertTrue(one.is_ancestor_of(two))
            self.assertTrue(one.is_ancestor_of(three))
            self.assertTrue(two.is_ancestor_of(three))
            self.assertFalse(three.is_ancestor_of(one))
            self.assertFalse(two.is_ancestor_of(one))

    def test_the_client_call_walkers_name_what_they_need(self) -> None:
        """`child_path_native`/`item`/`tab`/`io_events` (`ui_methods.cpp:435-441`, `:589-607`)."""

        from unittest import mock

        with mock.patch("py4gw.client._current_client", self._client({1: _nav_record(0x1000)})):
            f = frame_module.Frame.from_id(1)
            for member, call, named in (
                    ("child_path_native", lambda: f.child_path_native([1, 2]),
                     "g_get_child_frame_id_func"),
                    ("item", lambda: f.item(0), "GetOrderedChildFrameId"),
                    ("tab", lambda: f.tab(0), "TabsFrame"),
                    ("io_events", lambda: f.io_events(), "UIManager.py")):
                with self.subTest(member=member):
                    with self.assertRaises(NotImplementedError) as caught:
                        call()
                    self.assertIn(named, str(caught.exception))

    def test_child_native_is_the_bindings_two_steps(self) -> None:
        """`get_child_frame_by_frame_id` (`ui_bindings.cpp:707-710`) = `GetFrameById` + one call.

        The binding is ``GetChildFrame(GetFrameById(parent_frame_id), child_offset)``: the port reads
        the array slot for validity first — with no call made when it is empty, which is native's
        ``GetChildFrame(nullptr, ...)`` — and otherwise calls the client's own
        ``g_get_child_frame_id_func(parent_frame_id, child_offset)``, whose return register is the
        child's id.
        """

        from unittest import mock

        client = self._client({1: _nav_record(0x1000)})
        client.child_id = 9
        with mock.patch("py4gw.client._current_client", client):
            child = frame_module.Frame.from_id(1).child_native(6)

        self.assertIsInstance(child, frame_module.Frame)
        self.assertEqual(child._fid, 9)
        self.assertEqual(
            client.calls,
            [
                (
                    frame_module._GET_CHILD_FRAME_ID_FUNC,
                    CallForm.U32_U32,
                    1,
                    6,
                )
            ],
        )

    def test_child_native_refuses_a_slot_the_array_does_not_hold(self) -> None:
        """`GetFrameById` answers null (`ui_methods.cpp:421-428`), so `GetChildFrame` never calls.

        The id is handed in as the binding's own plain word — Reforged passes ``self.frame_id``, which
        is the strict accessor, so this stands in for a handle whose slot has gone stale between the
        resolution and the call, which is exactly the case native's second read exists for.
        """

        from unittest import mock

        client = self._client({})
        with mock.patch("py4gw.client._current_client", client), mock.patch.object(
            frame_module.Frame, "frame_id", property(lambda self: 7)
        ):
            child = frame_module.Frame.from_id(7).child_native(0)

        self.assertEqual(child._fid, 0)
        self.assertEqual(client.calls, [], "native's own `if (!(func && parent)) return nullptr`")

    def test_child_native_refuses_without_the_client_function(self) -> None:
        """`g_get_child_frame_id_func` is the whole body: unresolved means null (`:445-447`)."""

        from unittest import mock

        client = self._client({1: _nav_record(0x1000)})
        client.resolvable = False
        with mock.patch("py4gw.client._current_client", client):
            self.assertEqual(frame_module.Frame.from_id(1).child_native(0)._fid, 0)
        self.assertEqual(client.calls, [])


class TestFrameRecordReadsOffline(unittest.TestCase):
    """The geometry the **raw record** answers — built from this port's own ctypes structs.

    These fixtures are the real `FrameStruct` / `FramePositionStruct` (`py4gw/ui/frame.py`), not hand-written
    stand-ins, and that is deliberate: the first version of the geometry tests used a fake whose attribute
    names came from the *source's* wrapper (`left_on_screen`, `viewport_scale_x`), which hid the fact that the
    record this port reads has no such field.  A fixture built from the record itself cannot hide it again.

    Fields are set through `setattr` because a `ctypes.Structure`'s declared fields are not visible to a type
    checker; the names are the record's own.
    """

    def _record(self, **fields):
        from py4gw.ui.frame import FrameStruct

        record = FrameStruct()
        setattr(record, "frame_state", 0x4)          # native `IsCreated`; 0x200 (`IsHidden`) stays clear
        position = getattr(record, "position")
        for name, value in (("screen_left", 10.0), ("screen_bottom", 70.0),
                            ("screen_right", 110.0), ("screen_top", 20.0),
                            ("content_left", 1.0), ("content_top", 2.0),
                            ("content_right", 3.0), ("content_bottom", 4.0),
                            ("viewport_width", 1280.0), ("viewport_height", 720.0),
                            ("flags", 0x40)):
            setattr(position, name, value)
        for name, value in fields.items():
            setattr(record, name, value)
        return record

    def test_the_record_carries_no_wrapper_fields(self) -> None:
        """The finding, asserted against the record: no `*_on_screen`, no `viewport_scale_*`."""

        from py4gw.ui.frame import FramePositionStruct

        for absent in ("left_on_screen", "top_on_screen", "right_on_screen", "bottom_on_screen",
                       "width_on_screen", "height_on_screen", "viewport_scale_x", "viewport_scale_y"):
            with self.subTest(absent=absent):
                self.assertFalse(hasattr(FramePositionStruct, absent))
        for present in ("screen_left", "screen_bottom", "screen_right", "screen_top",
                        "content_left", "viewport_width", "viewport_height", "flags"):
            with self.subTest(present=present):
                self.assertTrue(hasattr(FramePositionStruct, present))

    def test_the_screen_rectangle_reads_are_natives_own_arithmetic(self) -> None:
        """`position_ex`, `native_size` and `viewport_dimensions` off the real record (`ui_methods.cpp:723-756`)."""

        from unittest import mock

        with mock.patch("py4gw.client._current_client", _AnchorClient({1: self._record()})):
            f = frame_module.Frame.from_id(1)
            self.assertEqual(f.position_ex(), (10.0, 70.0, 100.0, -50.0, 0x40))
            self.assertEqual(f.native_size(), (100.0, -50.0))
            self.assertEqual(f.viewport_dimensions(), (1280.0, 720.0))

    def test_min_size_and_client_border_reinterpret_record_words(self) -> None:
        """Native reads floats at 0x50-0x64 by reinterpretation (`ui_methods.cpp:680-702`)."""

        import struct as struct_module
        from unittest import mock

        record = self._record()
        for name, value in (("field20_0x50", 64.0), ("field21_0x54", 48.0),
                            ("field22_0x58", 1.5), ("field23_0x5c", 2.5),
                            ("field24_0x60", 3.5), ("field24a_0x64", 4.5)):
            setattr(record, name, struct_module.unpack("<I", struct_module.pack("<f", value))[0])
        with mock.patch("py4gw.client._current_client", _AnchorClient({1: record})):
            f = frame_module.Frame.from_id(1)
            self.assertEqual(f.min_size(), (64.0, 48.0))
            self.assertEqual(f.client_border(), (1.5, 2.5, 3.5, 4.5))

    def test_a_missing_frame_answers_the_bindings_zeros(self) -> None:
        """Each of these bindings seeds its out-parameters with zero and still calls (`ui_bindings.cpp:790-810`)."""

        from unittest import mock

        with mock.patch("py4gw.client._current_client", _AnchorClient({1: self._record()})):
            gone = frame_module.Frame.from_id(999)
            self.assertEqual(gone.coords(), (0, 0, 0, 0))
            self.assertEqual(gone.position_ex(), (0.0, 0.0, 0.0, 0.0, 0))
            self.assertEqual(gone.native_size(), (0.0, 0.0))
            self.assertEqual(gone.min_size(), (0.0, 0.0))
            self.assertEqual(gone.client_border(), (0.0, 0.0, 0.0, 0.0))


class TestFramePresentationOffline(unittest.TestCase):
    """The last members: `layer`, `opacity`, `clip_rect`, `hover` — and the ones that name their need.

    Together with the geometry, this is the whole of `frame.py:1225-1473`: the record words `GetFrameLayer`
    and `GetFrameOpacity` read, the position's content rectangle, `hover` delegating as the source writes it,
    and the write/draw/imGui members naming the one feature each waits on.
    """

    def _client(self, record):
        return _AnchorClient({1: record})

    def test_layer_and_opacity_are_record_words(self) -> None:
        """`GetFrameLayer` is `frame->field10_0x28` (`ui_methods.cpp:650`) and `GetFrameOpacity` the float at
        `frame + 0x30` (`:1818`)."""

        import struct as struct_module
        from unittest import mock

        record = _nav_record(0x1000)
        setattr(record, "field10_0x28", 3)
        setattr(record, "field12_0x30", struct_module.unpack("<I", struct_module.pack("<f", 0.25))[0])
        with mock.patch("py4gw.client._current_client", self._client(record)):
            f = frame_module.Frame.from_id(1)
            self.assertEqual(f.layer, 3)
            self.assertAlmostEqual(f.opacity, 0.25)
        with mock.patch("py4gw.client._current_client", self._client(_nav_record(0x1000))):
            gone = frame_module.Frame.from_id(999)
            self.assertEqual(gone.layer, 0)
            self.assertEqual(gone.opacity, 0.0)

    def test_clip_rect_is_the_content_rectangle(self) -> None:
        """`GetFrameClipRect` copies four position words in its own order (`ui_methods.cpp:704-718`)."""

        from unittest import mock

        record = _nav_record(0x1000)
        position = getattr(record, "position")
        for name, value in (("content_left", 1.0), ("content_top", 2.0),
                            ("content_right", 3.0), ("content_bottom", 4.0)):
            setattr(position, name, value)
        with mock.patch("py4gw.client._current_client", self._client(record)):
            self.assertEqual(frame_module.Frame.from_id(1).clip_rect(), (1.0, 2.0, 3.0, 4.0))
            self.assertEqual(frame_module.Frame.from_id(999).clip_rect(), (0.0, 0.0, 0.0, 0.0))

    def test_hover_delegates_to_the_mouse_action(self) -> None:
        """`hover` is `mouse_action(_MOUSE_HOVER_STATE)`, guard included (`frame.py:1270-1276`)."""

        from unittest import mock

        _reset_tree()
        record = _nav_record(0x1000)
        with mock.patch("py4gw.client._current_client", self._client(record)):
            f = frame_module.Frame.from_id(1)
            self.assertTrue(f.is_usable)
            with self.assertRaises(NotImplementedError) as caught:
                f.hover()
            self.assertIn("TestMouseAction", str(caught.exception))

        hidden = _nav_record(0x1000)
        setattr(hidden, "frame_state", 0x200)          # native `IsHidden`
        _reset_tree()
        with mock.patch("py4gw.client._current_client", self._client(hidden)):
            f = frame_module.Frame.from_id(1)
            self.assertFalse(f.is_usable)
            self.assertIsNone(f.hover(), "an unusable frame never reaches the action")

    def test_the_write_draw_and_imGui_members_name_what_they_need(self) -> None:
        """Each of these waits on one named feature; none of them is stubbed."""

        from unittest import mock

        with mock.patch("py4gw.client._current_client", self._client(_nav_record(0x1000))):
            f = frame_module.Frame.from_id(1)
            for member, call, named in (
                    ("set_visible", lambda: f.set_visible(True), "SetFrameVisible"),
                    ("set_disabled", lambda: f.set_disabled(True), "SetFrameDisabled"),
                    ("show", lambda: f.show(), "ShowFrame"),
                    ("set_layer", lambda: f.set_layer(1), "SetFrameLayer"),
                    ("set_opacity", lambda: f.set_opacity(0.5), "SetFrameOpacity"),
                    ("double_click", lambda: f.double_click(), "ButtonDoubleClick"),
                    ("draw", lambda: f.draw(0), "PyOverlay"),
                    ("draw_outline", lambda: f.draw_outline(0), "DrawQuad"),
                    ("is_mouse_over", lambda: f.is_mouse_over(), "PyImGui")):
                with self.subTest(member=member):
                    with self.assertRaises(NotImplementedError) as caught:
                        call()
                    self.assertIn(named, str(caught.exception))


class TestFrameTreeQueriesOffline(unittest.TestCase):
    """The tree's Frame-backed queries — `frame.py:517-636`, the members that waited on `Frame` existing.

    `all_frames`, `_as_id`, `descendants`/`descendants_of`, `frames_at_path`, `frames_under` and `_frames_at`
    are snapshot walks, so they answer now that `Frame` does.  `sort_by_vertical` sorts by `Frame.rect`, so it
    raises exactly where `rect` does — the dependency names itself rather than the member failing obscurely.
    """

    def _records(self) -> dict:
        """One anchor (hash 0xAA) with two branches that share the code path [7, 9]."""

        return {1: _AnchorRecord(frame_hash=0xAA),
                2: _AnchorRecord(parent_id=1, child_offset_id=7),
                3: _AnchorRecord(parent_id=2, child_offset_id=9),
                4: _AnchorRecord(parent_id=1, child_offset_id=7),
                5: _AnchorRecord(parent_id=4, child_offset_id=9)}

    def test_all_frames_returns_handles(self) -> None:
        """`[Frame.from_id(f) for f in self.all_ids()]` (`frame.py:517-518`)."""

        from unittest import mock

        with mock.patch("py4gw.client._current_client", _AnchorClient(self._records())):
            frames = frame_module._FrameTree().all_frames()
            self.assertEqual([f._fid for f in frames], [1, 2, 3, 4, 5])
            self.assertTrue(all(isinstance(f, frame_module.Frame) for f in frames))

    def test_as_id_accepts_a_frame_or_a_raw_id(self) -> None:
        """The source's own unwrapper (`frame.py:529-533`)."""

        from unittest import mock

        with mock.patch("py4gw.client._current_client", _AnchorClient(self._records())):
            self.assertEqual(frame_module._FrameTree._as_id(7), 7)
            self.assertEqual(frame_module._FrameTree._as_id(None), 0)
            self.assertEqual(frame_module._FrameTree._as_id(frame_module.Frame.from_id(1)), 1)

    def test_descendants_are_breadth_first(self) -> None:
        """Levels in native order, walking the children map (`frame.py:535-552`)."""

        from unittest import mock

        with mock.patch("py4gw.client._current_client", _AnchorClient(self._records())):
            tree = frame_module._FrameTree()
            self.assertEqual(tree.descendants_of(1), [2, 4, 3, 5])
            self.assertEqual([f._fid for f in tree.descendants(frame_module.Frame.from_id(1))],
                             [2, 4, 3, 5])
            self.assertEqual(tree.descendants_of(0), [1, 2, 4, 3, 5])

    def test_frames_at_path_matches_the_whole_code_path(self) -> None:
        """All frames whose path from the anchor is exactly the codes (`frame.py:598-632`)."""

        from unittest import mock

        with mock.patch("py4gw.client._current_client", _AnchorClient(self._records())):
            tree = frame_module._FrameTree()
            self.assertEqual([f._fid for f in tree.frames_at_path(0xAA, [7, 9])], [3, 5])
            self.assertEqual([f._fid for f in tree.frames_at_path(0xAA, [7])], [2, 4])
            self.assertEqual(tree.frames_at_path(0xAA, [9]), [], "the path must match in full")
            self.assertEqual([f._fid for f in tree.frames_under(1, [7, 9])], [3, 5])
            self.assertEqual(tree.frames_under(0, [7]), [], "no anchor, no answer")

    def test_sort_by_vertical_is_the_rects_top_first(self) -> None:
        """`sorted(frames, key=lambda f: f.rect[1])` (`frame.py:634-636`) — it needs the geometry, and it
        takes whatever `rect` gives it."""

        from unittest import mock

        with mock.patch("py4gw.client._current_client", _AnchorClient(self._records())):
            tree = frame_module._FrameTree()
            frames = tree.all_frames()
            self.assertEqual(tree.sort_by_vertical(frames), frames,
                             "without a root every rect is zero, so the order is kept")


class TestFrameTreeClientWalkersOffline(unittest.TestCase):
    """The tree's last members — `frame.py:554-672`: three array scans, one hash-coordinate read, and four
    that name a client-side input.

    `hierarchy`, `overlay_frames`, `popup_frames` and `coords_for_hash` are array scans; `root` needs the
    client's `g_get_root_frame_func`, `child_by_parent_hash` the client's `g_get_child_frame_id_func`, and
    `overlay`/`color_frames` the injected `PyOverlay` manager.  `viewport_height` delegates to `root`, so it
    names that same requirement rather than failing obscurely.
    """

    def _records(self) -> dict:
        return {1: _nav_record(0x1000, frame_hash=0xAA),
                2: _nav_record(0x2000, parent_relation=0x1000 + 0x128, frame_hash=0xBB),
                3: _nav_record(0x3000, parent_relation=0x2000 + 0x128, frame_hash=0xCC)}

    def _client(self, records: dict, words: dict | None = None):
        client = _AnchorClient(records)
        client.frame_array.words = dict(words or {})
        return client

    def test_overlay_and_popup_frames_are_the_created_frames(self) -> None:
        """`GetOverlayFrames` and `GetPopupFrames` are the same scan, written twice (`ui_methods.cpp:622-648`)."""

        from unittest import mock

        records = self._records()
        setattr(records[2], "frame_state", 0x200)            # hidden and not created -> not in the scan
        with mock.patch("py4gw.client._current_client", self._client(records)):
            tree = frame_module._FrameTree()
            self.assertEqual([f._fid for f in tree.overlay_frames()], [1, 3])
            self.assertEqual([f._fid for f in tree.popup_frames()], [1, 3])

    def test_hierarchy_rows_are_natives_order_not_the_docstrings(self) -> None:
        """`GetFrameHierarchy` pushes parent hash, own hash, parent id, own id (`ui_methods.cpp:1866-1884`)."""

        from unittest import mock

        records = self._records()
        setattr(records[3], "frame_state", 0x4 | 0x200)      # hidden frames are skipped
        words = {0x1000 + 0x128 + 0xC: 0xAA,                 # frame 2's parent hash word
                 0x1000 + 0xBC: 1}                           # frame 2's parent id word
        with mock.patch("py4gw.client._current_client", self._client(records, words)):
            rows = frame_module._FrameTree().hierarchy()
            self.assertEqual(rows, [(0, 0xAA, 0, 1), (0xAA, 0xBB, 1, 2)])

    def test_coords_for_hash_returns_the_two_corners(self) -> None:
        """`GetFrameCoordsByHash` (`ui_methods.cpp:1886-1900`): a hash lookup then two corner pairs."""

        from unittest import mock

        records = self._records()
        position = getattr(records[1], "position")
        for name, value in (("screen_left", 10.0), ("screen_top", 20.0),
                            ("screen_right", 110.0), ("screen_bottom", 70.0)):
            setattr(position, name, value)
        with mock.patch("py4gw.client._current_client", self._client(records)):
            tree = frame_module._FrameTree()
            self.assertEqual(tree.coords_for_hash(0xAA), [(10, 20), (110, 70)])
            self.assertEqual(tree.coords_for_hash(0xDEAD), [], "no frame for that hash")
            self.assertEqual(tree.coords_for_hash(0), [], "hash 0 answers nothing, as in native")

    def test_root_calls_the_clients_own_function_and_reads_the_id(self) -> None:
        """`GetRootFrame` is the client's pointer; the id is the word at `+0xBC` (`ui_methods.cpp:415-417`).

        The pointer comes from the call's **return register** — the record's `value`, not its `result`
        status — which is the defect round 90 fixed in this member; the fixture now carries both words
        so a member reading the wrong one cannot pass.
        """

        from unittest import mock

        from py4gw.game_thread.shared_block import CallForm

        pointer, root_id = 0x00A00000, 0x1234
        client = _AnchorClient({root_id: _nav_record(0x1000)})
        client.root_pointer = pointer
        client.frame_array.words = {pointer + 0xBC: root_id}
        with mock.patch("py4gw.client._current_client", client):
            tree = frame_module._FrameTree()
            self.assertEqual(tree.root()._fid, root_id)
            self.assertEqual(client.calls, [("ui.get_root_frame_func", CallForm.NO_ARGS)])

            # the source's cache: a transient zero from the engine keeps the last good id
            client.root_pointer = 0
            self.assertEqual(tree.root()._fid, root_id, "the last good root id is held")

    def test_a_nonzero_status_does_not_replace_the_return_it_carries(self) -> None:
        """The status word is not the pointer: a refused command still carries its own return.

        `payload` writes the completion's status into the record's `result` and the callee's `eax` into
        its `value`, so a member that resolves the root out of `result` would answer the status — here
        `RESULT_BAD_ARGUMENTS` — as if it were an address.
        """

        from unittest import mock

        from py4gw.game_thread.shared_block import RESULT_BAD_ARGUMENTS

        pointer, root_id = 0x00A00000, 0x1234
        client = _AnchorClient({root_id: _nav_record(0x1000)})
        client.root_pointer = pointer
        client.root_status = RESULT_BAD_ARGUMENTS
        client.frame_array.words = {pointer + 0xBC: root_id}
        with mock.patch("py4gw.client._current_client", client):
            self.assertEqual(frame_module._FrameTree().root()._fid, root_id)

    def test_a_null_root_pointer_answers_the_cached_zero(self) -> None:
        """No root pointer and no cache is `Frame.from_id(0)`, not an exception."""

        from unittest import mock

        with mock.patch("py4gw.client._current_client", _AnchorClient({})):
            tree = frame_module._FrameTree()
            self.assertEqual(tree.root()._fid, 0)

    def test_viewport_height_is_the_roots_own_viewport(self) -> None:
        """`self.root().viewport_dimensions()` plus the held copy (`frame.py:562-567`)."""

        from unittest import mock

        pointer, root_id = 0x00A00000, 0x1234
        record = _nav_record(0x1000)
        setattr(getattr(record, "position"), "viewport_height", 720.0)
        client = _AnchorClient({root_id: record})
        client.root_pointer = pointer
        client.frame_array.words = {pointer + 0xBC: root_id}
        with mock.patch("py4gw.client._current_client", client):
            tree = frame_module._FrameTree()
            self.assertEqual(tree.viewport_height(), 720.0)

            # a frame whose root cannot be read keeps the height it last had
            client.root_pointer = 0
            client.calls.clear()
            self.assertEqual(tree.viewport_height(), 720.0, "the height is held across a miss")

    def test_the_client_side_members_name_what_they_need(self) -> None:
        """`child_by_parent_hash`, `color_frames` and `overlay` are what is left on the tree."""

        from unittest import mock

        with mock.patch("py4gw.client._current_client", self._client(self._records())):
            tree = frame_module._FrameTree()
            for member, call, named in (
                    ("child_by_parent_hash", lambda: tree.child_by_parent_hash(0xAA, [1]),
                     "g_get_child_frame_id_func"),
                    ("color_frames", lambda: tree.color_frames(0xAA, [1]), "PyOverlay"),
                    ("overlay", lambda: tree.overlay, "PyOverlay")):
                with self.subTest(member=member):
                    with self.assertRaises(NotImplementedError) as caught:
                        call()
                    self.assertIn(named, str(caught.exception))


def _reset_tree() -> None:
    """Clear the tree singleton's own caches.

    They are the source's own — the per-frame live copy, the last good root id and the held viewport height —
    and they outlive a test, which is exactly what makes them worth keeping in the port and worth clearing
    here.
    """

    frame_module.FrameTree.invalidate()
    frame_module.FrameTree._root_id = 0
    frame_module.FrameTree._viewport_height = 0.0


class TestFrameGeometryOffline(unittest.TestCase):
    """The on-screen geometry: native's arithmetic over the root and the captured render viewport.

    Three inputs meet here, and the fixture supplies all three: the frame's own `FramePosition` record, the
    **root's** viewport size (the divisor, `ui.h:553-561`), and the render viewport the capture keeps.  The
    numbers are chosen so the flip is visible — the client's own space has `screen_top` larger than
    `screen_bottom`, so a frame's `rect` top ends up above its bottom.
    """

    RENDER = (1920.0, 1080.0)
    ROOT_ID = 0x1234

    def _client(self, frame_screen, root_viewport, render=(1920.0, 1080.0), pointer=0x00A00000):
        from py4gw.context.render_context import GwDxContextStruct

        root = _nav_record(0x1000, frame_hash=0xAA)
        setattr(getattr(root, "position"), "viewport_width", float(root_viewport[0]))
        setattr(getattr(root, "position"), "viewport_height", float(root_viewport[1]))
        child = _nav_record(0x2000, parent_relation=0x1000 + 0x128)
        position = getattr(child, "position")
        for name, value in zip(("screen_left", "screen_top", "screen_right", "screen_bottom"),
                               frame_screen):
            setattr(position, name, float(value))

        client = _AnchorClient({self.ROOT_ID: root, 2: child})
        client.root_pointer = pointer
        client.frame_array.words = {pointer + 0xBC: self.ROOT_ID} if pointer else {}
        if render:
            context = 0x0B000000
            record = GwDxContextStruct()
            setattr(record, "viewport_width", int(render[0]))
            setattr(record, "viewport_height", int(render[1]))
            client._bridge.context_address = context
            client.reader.images[context] = bytes(record)
        return client

    def test_rect_and_size_are_natives_arithmetic(self) -> None:
        """`GetTopLeftOnScreen(root)` / `GetBottomRightOnScreen(root)` / `GetSizeOnScreen(root)` (`ui.h:504-551`)."""

        from unittest import mock

        client = self._client((100, 900, 300, 800), (1920, 1080))
        with mock.patch("py4gw.client._current_client", client):
            f = frame_module.Frame.from_id(2)
            self.assertEqual(f.viewport_scale(), (1.0, 1.0), "render and root viewport agree")
            self.assertEqual(f.rect, (100, 180, 300, 280))
            self.assertEqual(f.size, (200, 100))

    def test_the_scale_is_the_render_viewport_over_the_roots_own(self) -> None:
        """A root half the render size doubles every coordinate (`ui.h:553-561`)."""

        from unittest import mock

        client = self._client((100, 900, 300, 800), (960, 540))
        with mock.patch("py4gw.client._current_client", client):
            self.assertEqual(frame_module.Frame.from_id(2).viewport_scale(), (2.0, 2.0))

    def test_without_a_root_the_geometry_is_zero_and_the_scale_identity(self) -> None:
        """The binding fills the wrapper's words only `if (root)` (`ui_bindings.cpp:445-462`)."""

        from unittest import mock

        _reset_tree()
        client = self._client((100, 900, 300, 800), (1920, 1080), pointer=0)
        with mock.patch("py4gw.client._current_client", client):
            f = frame_module.Frame.from_id(2)
            self.assertEqual(f.rect, (0, 0, 0, 0))
            self.assertEqual(f.size, (0, 0))
            self.assertEqual(f.viewport_scale(), (1.0, 1.0))

    def test_content_coords_flip_y_against_the_roots_height(self) -> None:
        """The source's own body, over `FrameTree.viewport_height()` (`:1355-1379`)."""

        from unittest import mock

        client = self._client((0, 0, 0, 0), (1920, 1080))
        position = getattr(client.frame_array.get(2), "position")
        for name, value in (("content_left", 10.0), ("content_top", 20.0),
                            ("content_right", 30.0), ("content_bottom", 40.0)):
            setattr(position, name, value)
        with mock.patch("py4gw.client._current_client", client):
            self.assertEqual(frame_module.Frame.from_id(2).content_coords(), (10, 1060, 30, 1040))

    def test_a_capture_that_has_not_happened_is_no_scale(self) -> None:
        """`GW::render::GetViewportWidth` answers 0 without a context (`render_methods.cpp:56-63`)."""

        from unittest import mock

        client = self._client((100, 900, 300, 800), (1920, 1080), render=None)
        with mock.patch("py4gw.client._current_client", client):
            self.assertEqual(frame_module.Frame.from_id(2).viewport_scale(), (1.0, 1.0),
                             "a zero render viewport is not a usable scale")


class _MessageFrameArray:
    """`client.frame_array`, in the two reads `Frame.send_message` makes."""

    def __init__(self, pointer: int, callbacks_size: int) -> None:
        self.pointer = pointer
        self.callbacks_size = callbacks_size

    def read_frame_pointer(self, frame_id: int) -> int:
        return self.pointer if int(frame_id) == 1 else 0

    def iter_frames(self) -> Any:
        """The array walk `Frame._resolve` performs; this fixture resolves by id alone."""

        return iter(())

    def get(self, frame_id: int) -> Any:
        if int(frame_id) != 1 or not self.pointer:
            return None
        record = FrameStruct()
        record.frame_callbacks = GWArray(0x00300000, self.callbacks_size, self.callbacks_size, 0)
        return record


class TestFrameSendMessageOffline(unittest.TestCase):
    """`Frame.send_message` — native's `ui::SendFrameUIMessage` over the port's five-word call.

    The member is the port of `ui_bindings.cpp:1066-1072` → `ui_methods.cpp:1332-1345`: the binding answers
    `true` whatever happens, and the methods layer refuses unless it holds the client's sender and the
    frame's callback array is non-empty, then calls that sender with `&frame->frame_callbacks`, a null
    second word and the two caller words.
    """

    def _client(self, pointer: int, callbacks_size: int, resolvable: bool = True) -> Any:
        class _Client:
            def __init__(self) -> None:
                self.calls: list = []
                self.frame_array = _MessageFrameArray(pointer, callbacks_size)

            def resolves(self, name: str) -> bool:
                return resolvable

            def call_function(self, name: str, form: Any, *args: Any) -> Any:
                self.calls.append((name, int(form), *args))
                return _CallRecord(1)

        return _Client()

    def test_it_calls_the_client_sender_with_the_thiscall_shape(self) -> None:
        """``arg1`` is the client's ``this`` in ECX — ``&frame->frame_callbacks`` — and three stack words.

        Native declares the target fastcall-shaped because its detour ABI requires it
        (``SendFrameUIMessageFn``, ``ui_patterns.cpp:32``); the client's own convention is ``__thiscall``,
        which the live read confirmed: the resolved function ends ``ret 0xc``
        (``tests/live_reports/send_frame_ui_message_read.json``).
        """

        client = self._client(0x00200000, 2)
        with mock.patch("py4gw.client._current_client", client):
            self.assertTrue(frame_module.Frame.from_id(1).send_message(0x10000001, 7, 9))
        self.assertEqual(
            client.calls,
            [
                (
                    frame_module._SEND_FRAME_UI_MESSAGE_FUNC,
                    int(CallForm.FASTCALL_U32_U32_U32),
                    0x00200000 + FrameStruct.frame_callbacks.offset,
                    0,
                    0x10000001,
                    7,
                    9,
                )
            ],
        )

    def test_a_frame_with_no_callbacks_is_not_sent(self) -> None:
        """`frame->frame_callbacks.size()` (`ui_methods.cpp:1333`)."""

        client = self._client(0x00200000, 0)
        with mock.patch("py4gw.client._current_client", client):
            self.assertTrue(frame_module.Frame.from_id(1).send_message(0x10000001))
        self.assertEqual(client.calls, [])

    def test_a_missing_frame_is_not_sent(self) -> None:
        """`GetFrameById` answers null for an empty slot, and the binding still answers `true`."""

        client = self._client(0, 2)
        with mock.patch("py4gw.client._current_client", client):
            self.assertTrue(frame_module.Frame.from_id(1).send_message(0x10000001))
        self.assertEqual(client.calls, [])

    def test_a_missing_sender_means_no_call(self) -> None:
        """`!(g_send_frame_ui_message_original && ...)` — nothing is called, and the answer is `true`."""

        client = self._client(0x00200000, 2, resolvable=False)
        with mock.patch("py4gw.client._current_client", client):
            self.assertTrue(frame_module.Frame.from_id(1).send_message(0x10000001))
        self.assertEqual(client.calls, [])


def _click_record(
    address: int,
    *,
    parent_relation: int = 0,
    state: int = 0x4,
    code: int = 0,
    user_param: int = 0,
) -> Any:
    """A real ``FrameStruct`` bound to an address, in the shape ``ui::ButtonClick`` reads.

    ``0x4`` is native's ``IsCreated`` bit and ``0x200`` is ``IsHidden`` — a frame without it is visible
    (``py4gw/ui/frame.py:320-336``), which is what ``is_usable`` needs.
    """

    record = FrameStruct()
    record.bind_address(address)
    setattr(record, "frame_state", state)
    setattr(record, "child_offset_id", code)
    setattr(record, "field105_0x1c4", user_param)
    setattr(getattr(record, "relation"), "parent", parent_relation)
    return record


class _ClickBridge:
    """`client.bridge`, recording where the two structs are placed."""

    def __init__(self) -> None:
        self.writes: list = []

    def write_data(self, offset: int, payload: bytes) -> int:
        address = 0x00D00000 + int(offset)
        self.writes.append((int(offset), bytes(payload), address))
        return address


class _ClickClient:
    """A connected-client stand-in for `Frame.click`: the frame array, the block and the call path."""

    def __init__(self, records: dict, words: dict | None = None, resolvable: bool = True) -> None:
        self.frame_array = _AnchorFrameArray(records)
        self.frame_array.words = dict(words or {})
        self.bridge = _ClickBridge()
        self.calls: list = []
        self.resolvable = resolvable

    def resolves(self, name: str) -> bool:
        return self.resolvable

    def call_function(self, name: str, form: Any, *args: Any) -> Any:
        self.calls.append((name, int(form), *args))
        return _CallRecord(1)


class TestFrameClickOffline(unittest.TestCase):
    """`Frame.click` — native's `ui::ButtonClick` (`ui_methods.cpp:1249-1274`) over real records.

    The button is frame 1 at `BUTTON`; its `relation.parent` points into frame 2's record at `PARENT`, which
    is how native reaches the parent (`GetParentFrame` is `frame->relation.GetParent()`). The parent's
    `frame_state` and `frame_callbacks` header are read as words, which is what the fixture's map answers.
    """

    BUTTON = 0x00100000
    PARENT = 0x00200000

    def _client(
        self,
        *,
        parent_state: int = 0x4,
        callbacks_size: int = 1,
        with_parent: bool = True,
        resolvable: bool = True,
    ) -> Any:
        parent_relation = (self.PARENT + FrameStruct.relation.offset) if with_parent else 0
        records = {
            1: _click_record(self.BUTTON, parent_relation=parent_relation, code=0x62, user_param=0x1234),
            2: _click_record(self.PARENT, state=parent_state),
        }
        words = {
            self.PARENT + FrameStruct.frame_state.offset: parent_state,
            self.PARENT
            + FrameStruct.frame_callbacks.offset
            + GWArray.m_size.offset: callbacks_size,
        }
        return _ClickClient(records, words, resolvable)

    def test_it_places_the_two_structs_and_sends_the_click(self) -> None:
        """`MouseAction{offset, offset, MouseUp, &ButtonParam, 0}` to the **parent**, as `kMouseClick2`."""

        client = self._client()
        with mock.patch("py4gw.client._current_client", client):
            answered = frame_module.Frame.from_id(1).click()

        self.assertIs(answered, True, "native's `ButtonClick` answers `SendFrameUIMessage`'s true")

        self.assertEqual(
            client.bridge.writes,
            [
                (frame_module._BUTTON_PARAM_OFFSET, struct.pack("<III", 0, 0x1234, 0), 0x00D00320),
                (
                    frame_module._MOUSE_ACTION_OFFSET,
                    struct.pack(
                        "<IIIII",
                        0x62,
                        0x62,
                        frame_module._MOUSE_UP,
                        0x00D00320,
                        0,
                    ),
                    0x00D00300,
                ),
            ],
        )
        self.assertEqual(
            client.calls,
            [
                (
                    frame_module._SEND_FRAME_UI_MESSAGE_FUNC,
                    int(CallForm.FASTCALL_U32_U32_U32),
                    self.PARENT + FrameStruct.frame_callbacks.offset,
                    0,
                    frame_module._K_MOUSE_CLICK_2,
                    0x00D00300,
                    0,
                )
            ],
        )

    def test_a_parent_with_no_callbacks_is_not_sent_to(self) -> None:
        """`SendFrameUIMessage` requires `frame->frame_callbacks.size()` (`ui_methods.cpp:1333`)."""

        client = self._client(callbacks_size=0)
        with mock.patch("py4gw.client._current_client", client):
            answered = frame_module.Frame.from_id(1).click()
        self.assertIs(answered, False, "the source's other answer for this guard")
        self.assertEqual(client.calls, [])
        self.assertEqual(client.bridge.writes, [])

    def test_a_parent_that_is_not_created_is_refused(self) -> None:
        """`parent_frame->IsCreated()` (`:1255`)."""

        client = self._client(parent_state=0x0)
        with mock.patch("py4gw.client._current_client", client):
            self.assertIs(frame_module.Frame.from_id(1).click(), False)
        self.assertEqual(client.calls, [])

    def test_a_button_without_a_parent_is_refused(self) -> None:
        """`GetParentFrame` answers null and the body returns false (`:1254-1257`)."""

        client = self._client(with_parent=False)
        with mock.patch("py4gw.client._current_client", client):
            self.assertIs(frame_module.Frame.from_id(1).click(), False)
        self.assertEqual(client.calls, [])

    def test_a_missing_sender_means_no_call(self) -> None:
        """`!(g_send_frame_ui_message_original && ...)` — nothing is placed and nothing is called."""

        client = self._client(resolvable=False)
        with mock.patch("py4gw.client._current_client", client):
            self.assertIs(frame_module.Frame.from_id(1).click(), False)
        self.assertEqual(client.calls, [])
        self.assertEqual(client.bridge.writes, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
