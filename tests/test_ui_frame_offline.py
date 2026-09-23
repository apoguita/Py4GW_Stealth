"""Offline layout and logic checks for the UI frame primitives.

These tests build a synthetic x86 target memory image and exercise the frame
array, the frame tree, and the frame-published context locator. They do not
require, contact, or modify a Guild Wars client.
"""

from __future__ import annotations

import ctypes
import unittest
from collections.abc import Sequence
from typing import Any, cast

from py4gw import ResolutionResult
from py4gw.context.gw_array import GWArray
from py4gw.ui import (
    FrameArray,
    FrameContextCandidate,
    FrameStruct,
    FrameTree,
    is_valid_frame_pointer,
    locate_frame_published_context,
)
from py4gw.ui.frame import (
    FrameInteractionCallbackStruct,
    FramePositionStruct,
    FrameRelationStruct,
    InteractionMessageStruct,
    TooltipInfoStruct,
)

_BASE = 0x00100000
_SIZE = 0x100000

_ARRAY_HEADER = _BASE + 0x1000
_FRAME_BUFFER = _BASE + 0x2000
_CALLBACK_BUFFER = _BASE + 0x3000
_FRAME_BASE = _BASE + 0x10000
_CONTEXT = _BASE + 0x80000

_FRAME_STRIDE = ctypes.sizeof(FrameStruct)
_CALLBACK_STRIDE = ctypes.sizeof(FrameInteractionCallbackStruct)


class _Memory:
    """One contiguous synthetic target region with sparse-backed reads."""

    def __init__(self, base: int = _BASE, size: int = _SIZE) -> None:
        self._base = base
        self._data = bytearray(size)

    def read(self, address: int, size: int) -> bytes:
        offset = address - self._base
        if offset < 0 or offset + size > len(self._data):
            raise OSError(f"unmapped test address 0x{address:08X}")
        return bytes(self._data[offset : offset + size])

    def write(self, address: int, payload: bytes) -> None:
        offset = address - self._base
        self._data[offset : offset + len(payload)] = payload

    def write_u32(self, address: int, value: int) -> None:
        self.write(address, value.to_bytes(4, "little"))


class _Catalog:
    """A resolver stand-in that returns one fixed callback address."""

    def __init__(self, callback_address: int) -> None:
        self._callback_address = callback_address
        self.calls = 0

    def resolve(self, name: str, scanner: Any) -> ResolutionResult:
        self.calls += 1
        return ResolutionResult(
            name=name,
            module="test",
            ok=True,
            value=self._callback_address,
        )


def _write_array_header(
    memory: _Memory,
    address: int,
    buffer: int,
    capacity: int,
    size: int,
) -> None:
    header = GWArray()
    header.m_buffer = buffer
    header.m_capacity = capacity
    header.m_size = size
    memory.write(address, bytes(header))


def _write_frame(
    memory: _Memory,
    frame_id: int,
    frame_address: int,
    parent_relation: int = 0,
    callbacks: tuple[tuple[int, int, int], ...] = (),
    callbacks_buffer: int = _CALLBACK_BUFFER,
    frame_state: int = 0,
) -> None:
    """Write one frame record and its callback entries."""

    _write_array_header(
        memory,
        frame_address + FrameStruct.frame_callbacks.offset,
        callbacks_buffer if callbacks else 0,
        len(callbacks),
        len(callbacks),
    )
    memory.write_u32(frame_address + FrameStruct.child_offset_id.offset, 0xFF)
    memory.write_u32(frame_address + FrameStruct.frame_id.offset, frame_id)
    memory.write_u32(frame_address + FrameStruct.frame_state.offset, frame_state)
    memory.write_u32(frame_address + FrameStruct.relation.offset, parent_relation)

    for index, (callback, context, extra) in enumerate(callbacks):
        entry = callbacks_buffer + index * _CALLBACK_STRIDE
        memory.write_u32(entry, callback)
        memory.write_u32(entry + 4, context)
        memory.write_u32(entry + 8, extra)


def _frames_for(
    memory: _Memory,
    slots: Sequence[int | None],
    frames: dict[int, dict[str, Any]],
    callbacks_buffer: int = _CALLBACK_BUFFER,
) -> FrameArray:
    """Build a frame array whose slots and records match the supplied layout."""

    _write_array_header(
        memory, _ARRAY_HEADER, _FRAME_BUFFER, len(slots), len(slots)
    )
    for slot_index, slot in enumerate(slots):
        memory.write_u32(_FRAME_BUFFER + slot_index * 4, slot or 0)

    cursor = callbacks_buffer
    for frame_id, spec in frames.items():
        frame_address = _FRAME_BASE + frame_id * _FRAME_STRIDE
        callbacks = spec.get("callbacks", ())
        _write_frame(
            memory,
            frame_id,
            frame_address,
            parent_relation=spec.get("parent_relation", 0),
            callbacks=callbacks,
            callbacks_buffer=cursor,
            frame_state=spec.get("frame_state", 0x4),
        )
        cursor += max(len(callbacks), 0) * _CALLBACK_STRIDE

    frames_reader = FrameArray(cast(Any, memory), cast(Any, None), cast(Any, None))
    cast(Any, frames_reader)._array_address = _ARRAY_HEADER
    return frames_reader


class UiFrameLayoutTests(unittest.TestCase):
    """Verify the native layout port and the source field list."""

    def test_sizes_match_the_native_records(self) -> None:
        self.assertEqual(ctypes.sizeof(FramePositionStruct), 0x44)
        self.assertEqual(ctypes.sizeof(FrameRelationStruct), 0x1C)
        self.assertEqual(ctypes.sizeof(FrameInteractionCallbackStruct), 0x0C)
        self.assertEqual(ctypes.sizeof(TooltipInfoStruct), 0x20)
        self.assertEqual(ctypes.sizeof(InteractionMessageStruct), 0x0C)
        self.assertEqual(ctypes.sizeof(FrameStruct), 0x1C8)

    def test_key_frame_offsets(self) -> None:
        structure = cast(Any, FrameStruct)
        self.assertEqual(structure.frame_callbacks.offset, 0xA8)
        self.assertEqual(structure.child_offset_id.offset, 0xB8)
        self.assertEqual(structure.frame_id.offset, 0xBC)
        self.assertEqual(structure.position.offset, 0xD8)
        self.assertEqual(structure.relation.offset, 0x128)
        self.assertEqual(structure.frame_state.offset, 0x18C)
        self.assertEqual(structure.tooltip_info.offset, 0x1AC)

    def test_frame_field_names_match_the_source(self) -> None:
        names = [name for name, _ in cast(Any, FrameStruct)._fields_]
        self.assertEqual(names[0], "field1_0x0")
        self.assertEqual(names[32], "field30_0x80")
        self.assertEqual(names[33], "field31_0x84")
        self.assertEqual(names[39], "frame_callbacks")
        self.assertEqual(names[40], "child_offset_id")
        self.assertEqual(names[41], "frame_id")
        self.assertEqual(names[-1], "field105_0x1c4")
        self.assertEqual(len(names), 86)

    def test_native_frame_state_helpers(self) -> None:
        frame = FrameStruct()
        self.assertFalse(frame.is_created)
        frame.frame_state = 0x4
        self.assertTrue(frame.is_created)
        self.assertTrue(frame.is_visible)
        frame.frame_state = 0x204
        self.assertTrue(frame.is_hidden)
        self.assertFalse(frame.is_visible)
        frame.frame_state = 0x10
        self.assertTrue(frame.is_disabled)

    def test_frame_pointer_validation_rejects_the_sentinel(self) -> None:
        self.assertFalse(is_valid_frame_pointer(0))
        self.assertFalse(is_valid_frame_pointer(0xFFFFFFFF))
        self.assertFalse(is_valid_frame_pointer(0xFFFF))
        self.assertTrue(is_valid_frame_pointer(0x10000))


class FrameArrayTests(unittest.TestCase):
    """Verify array validation, indexing, and callback selection order."""

    def test_reads_a_frame_by_its_array_index(self) -> None:
        memory = _Memory()
        slots = [_FRAME_BASE + index * _FRAME_STRIDE for index in range(3)]
        frames_reader = _frames_for(
            memory,
            slots,
            {index: {} for index in range(3)},
        )

        self.assertEqual(frames_reader.size(), 3)
        frame = frames_reader.get(2)
        self.assertIsNotNone(frame)
        assert frame is not None
        self.assertEqual(frame.frame_id, 2)
        self.assertEqual(frame.address, slots[2])

    def test_null_sentinel_and_out_of_range_slots_are_absent(self) -> None:
        memory = _Memory()
        slots: list[int | None] = [
            _FRAME_BASE,
            None,
            0xFFFFFFFF,
        ]
        frames_reader = _frames_for(memory, slots, {0: {}})

        self.assertIsNotNone(frames_reader.get(0))
        self.assertIsNone(frames_reader.get(1))
        self.assertIsNone(frames_reader.get(2))
        self.assertIsNone(frames_reader.get(3))
        self.assertEqual(frames_reader.read_frame_pointer(2), 0xFFFFFFFF)
        self.assertEqual(len(list(frames_reader.iter_frames())), 1)

    def test_header_must_describe_a_bounded_array(self) -> None:
        memory = _Memory()
        _write_array_header(memory, _ARRAY_HEADER, _FRAME_BUFFER, 2, 5)
        frames_reader = FrameArray(cast(Any, memory), cast(Any, None), cast(Any, None))
        cast(Any, frames_reader)._array_address = _ARRAY_HEADER
        with self.assertRaisesRegex(ValueError, "exceeds"):
            frames_reader.read_header()

        _write_array_header(memory, _ARRAY_HEADER, 0, 4, 4)
        with self.assertRaisesRegex(ValueError, "no usable buffer"):
            frames_reader.read_header()

        _write_array_header(memory, _ARRAY_HEADER, _FRAME_BUFFER, 200_000, 200_000)
        with self.assertRaisesRegex(ValueError, "cap"):
            frames_reader.read_header()

    def test_frame_context_uses_the_last_non_null_entry(self) -> None:
        memory = _Memory()
        slots = [_FRAME_BASE]
        frames_reader = _frames_for(
            memory,
            slots,
            {
                0: {
                    "callbacks": (
                        (0x00AABBCC, _CONTEXT + 0x100, 0),
                        (0x00AABBDD, 0, 0),
                        (0x00AABBEE, _CONTEXT + 0x200, 0),
                    )
                }
            },
        )
        frame = frames_reader.get(0)
        assert frame is not None
        self.assertEqual(frames_reader.frame_context_address(frame), _CONTEXT + 0x200)

    def test_frame_context_is_zero_when_no_entry_registers_one(self) -> None:
        memory = _Memory()
        slots = [_FRAME_BASE]
        frames_reader = _frames_for(
            memory,
            slots,
            {0: {"callbacks": ((0x00AABBCC, 0, 0),)}},
        )
        frame = frames_reader.get(0)
        assert frame is not None
        self.assertEqual(frames_reader.frame_context_address(frame), 0)

    def test_frame_without_callbacks_has_no_context(self) -> None:
        memory = _Memory()
        slots = [_FRAME_BASE]
        frames_reader = _frames_for(memory, slots, {0: {}})
        frame = frames_reader.get(0)
        assert frame is not None
        self.assertEqual(frames_reader.read_callbacks(frame), [])
        self.assertEqual(frames_reader.frame_context_address(frame), 0)


class FrameTreeTests(unittest.TestCase):
    """Verify parent, child, and callback-based lookups."""

    def _tree(self) -> tuple[_Memory, FrameTree]:
        memory = _Memory()
        root_address = _FRAME_BASE + 0 * _FRAME_STRIDE
        child_address = _FRAME_BASE + 1 * _FRAME_STRIDE
        slots = [root_address, child_address]
        frames_reader = _frames_for(
            memory,
            slots,
            {
                0: {"callbacks": ((0x00AABBCC, 0, 0),)},
                1: {
                    "parent_relation": root_address + FrameStruct.relation.offset,
                    "callbacks": ((0x00AABBDD, _CONTEXT, 0),),
                },
            },
        )
        return memory, FrameTree(frames_reader)

    def test_root_is_the_first_parentless_frame(self) -> None:
        _, tree = self._tree()
        root = tree.root()
        self.assertIsNotNone(root)
        assert root is not None
        self.assertEqual(root.frame_id, 0)

    def test_parent_is_recovered_from_the_relation_pointer(self) -> None:
        _, tree = self._tree()
        child = tree.by_id(1)
        assert child is not None
        parent = tree.parent_of(child)
        self.assertIsNotNone(parent)
        assert parent is not None
        self.assertEqual(parent.frame_id, 0)
        self.assertIsNone(tree.parent_of(parent))

    def test_children_are_found_by_scanning_for_the_parent(self) -> None:
        _, tree = self._tree()
        root = tree.by_id(0)
        assert root is not None
        children = tree.children_of(root)
        self.assertEqual([child.frame_id for child in children], [1])
        child = tree.by_id(1)
        assert child is not None
        self.assertEqual(tree.children_of(child), [])

    def test_frames_are_found_by_their_registered_callback(self) -> None:
        _, tree = self._tree()
        matches = tree.frames_using_callback(0x00AABBDD)
        self.assertEqual([frame_id for frame_id, _ in matches], [1])
        self.assertEqual(tree.frames_using_callback(0x00AABBCC)[0][0], 0)
        self.assertEqual(tree.frames_using_callback(0x00AABBFF), [])

    def test_children_of_needs_an_address_bound_frame(self) -> None:
        _, tree = self._tree()
        detached = FrameStruct()
        with self.assertRaisesRegex(ValueError, "target address"):
            tree.children_of(detached)


class FramePublishedContextTests(unittest.TestCase):
    """Verify the frame-id cross-check that confirms a published context."""

    _CALLBACK = 0x0110B5A0

    def _array_with_context(
        self,
        memory: _Memory,
        frame_index: int,
        context_address: int,
        context_frame_id: int,
        context_offset: int = 0x0,
    ) -> FrameArray:
        slots: list[int | None] = [None] * (frame_index + 1)
        slots[frame_index] = _FRAME_BASE + frame_index * _FRAME_STRIDE
        frames = {frame_index: {"callbacks": ((self._CALLBACK, context_address, 0),)}}
        frames_reader = _frames_for(memory, slots, frames)
        memory.write_u32(context_address + context_offset, context_frame_id)
        return frames_reader

    def test_matching_frame_id_confirms_the_candidate(self) -> None:
        memory = _Memory()
        frames_reader = self._array_with_context(memory, 5, _CONTEXT, 5)
        tree = FrameTree(frames_reader)

        candidates = locate_frame_published_context(tree, self._CALLBACK)

        self.assertEqual(len(candidates), 1)
        self.assertTrue(candidates[0].is_confirmed)
        self.assertEqual(candidates[0].context_address, _CONTEXT)
        self.assertEqual(candidates[0].frame_id, 5)

    def test_frame_id_mismatch_is_rejected_with_a_reason(self) -> None:
        memory = _Memory()
        frames_reader = self._array_with_context(memory, 5, _CONTEXT, 9)
        tree = FrameTree(frames_reader)

        candidates = locate_frame_published_context(tree, self._CALLBACK)

        self.assertEqual(len(candidates), 1)
        self.assertFalse(candidates[0].is_confirmed)
        self.assertIn("cross-check failed", candidates[0].rejection)

    def test_unreadable_context_address_is_rejected(self) -> None:
        memory = _Memory()
        frames_reader = self._array_with_context(memory, 0, 0x7FFF0000, 0)
        tree = FrameTree(frames_reader)

        candidates = locate_frame_published_context(tree, self._CALLBACK)

        self.assertEqual(len(candidates), 1)
        self.assertFalse(candidates[0].is_confirmed)
        self.assertIn("unreadable", candidates[0].rejection)

    def test_frame_without_a_context_is_reported(self) -> None:
        memory = _Memory()
        slots = [_FRAME_BASE]
        frames_reader = _frames_for(
            memory, slots, {0: {"callbacks": ((self._CALLBACK, 0, 0),)}}
        )
        tree = FrameTree(frames_reader)

        candidates = locate_frame_published_context(tree, self._CALLBACK)

        self.assertEqual(len(candidates), 1)
        self.assertFalse(candidates[0].is_confirmed)
        self.assertEqual(candidates[0].context_address, 0)
        self.assertIn("no context pointer", candidates[0].rejection)

    def test_no_frame_uses_the_callback(self) -> None:
        memory = _Memory()
        slots = [_FRAME_BASE]
        frames_reader = _frames_for(memory, slots, {0: {}})
        tree = FrameTree(frames_reader)

        self.assertEqual(locate_frame_published_context(tree, self._CALLBACK), ())

    def test_offset_selects_a_frame_id_away_from_the_root(self) -> None:
        memory = _Memory()
        frames_reader = self._array_with_context(
            memory, 3, _CONTEXT, 3, context_offset=0x14
        )
        tree = FrameTree(frames_reader)

        candidates = locate_frame_published_context(tree, self._CALLBACK, 0x14)

        self.assertTrue(candidates[0].is_confirmed)
        self.assertEqual(candidates[0].context_frame_id, 3)


class WorldMapFrameAcquisitionTests(unittest.TestCase):
    """Verify the WorldMapContext acquisition over the synthetic frame array."""

    _CALLBACK = 0x0110B5A0
    _FRAME_ID = 42

    def _reader(self) -> tuple[_Memory, FrameArray, FrameTree]:
        memory = _Memory()
        slots: list[int | None] = [None] * (self._FRAME_ID + 1)
        slots[self._FRAME_ID] = _FRAME_BASE + self._FRAME_ID * _FRAME_STRIDE
        frames_reader = _frames_for(
            memory,
            slots,
            {
                self._FRAME_ID: {
                    "callbacks": ((self._CALLBACK, _CONTEXT, 0),)
                }
            },
        )
        return memory, frames_reader, FrameTree(frames_reader)

    def test_resolve_address_returns_the_confirmed_context(self) -> None:
        from py4gw import WorldMapContext

        memory, frames_reader, tree = self._reader()
        memory.write_u32(_CONTEXT, self._FRAME_ID)
        context = WorldMapContext(
            cast(Any, memory),
            cast(Any, None),
            cast(Any, _Catalog(self._CALLBACK)),
            tree,
        )

        self.assertEqual(context.resolve_address(), _CONTEXT)
        self.assertEqual(context.callback_address, self._CALLBACK)
        snapshot = context.read()
        self.assertIsNotNone(snapshot)
        assert snapshot is not None
        self.assertEqual(snapshot.frame_id, self._FRAME_ID)

    def test_resolve_address_returns_none_without_a_confirmed_candidate(self) -> None:
        from py4gw import WorldMapContext

        memory, _, tree = self._reader()
        memory.write_u32(_CONTEXT, self._FRAME_ID + 1)
        context = WorldMapContext(
            cast(Any, memory),
            cast(Any, None),
            cast(Any, _Catalog(self._CALLBACK)),
            tree,
        )

        self.assertIsNone(context.resolve_address())
        self.assertIsNone(context.read())
        candidates = context.candidates()
        self.assertEqual(len(candidates), 1)
        self.assertFalse(candidates[0].is_confirmed)

    def test_missing_callback_resolution_raises_with_the_resolver_name(self) -> None:
        from py4gw import WorldMapContext

        class _Failing:
            def resolve(self, name: str, scanner: Any) -> ResolutionResult:
                return ResolutionResult(
                    name=name,
                    module="map",
                    ok=False,
                    message="no match",
                )

        memory, _, tree = self._reader()
        context = WorldMapContext(
            cast(Any, memory), cast(Any, None), cast(Any, _Failing()), tree
        )
        with self.assertRaisesRegex(RuntimeError, "world_map_ui_callback_func"):
            context.initialize()


_CONTEXT_MISSION = _BASE + 0x81000
_CONTEXT_SALVAGE = _BASE + 0x82000


def _published_context_tree(
    memory: _Memory,
    publishers: list[tuple[int, int, int]],
) -> FrameTree:
    """Build a frame tree where each publisher frame registers a callback.

    ``publishers`` holds ``(frame_index, callback_address, context_address)``.
    """

    if not publishers:
        return FrameTree(_frames_for(memory, [], {}))

    highest = max(index for index, _, _ in publishers)
    slots: list[int | None] = [None] * (highest + 1)
    frames: dict[int, dict[str, Any]] = {}
    for index, callback, context in publishers:
        slots[index] = _FRAME_BASE + index * _FRAME_STRIDE
        frames[index] = {"callbacks": ((callback, context, 0),)}
    return FrameTree(_frames_for(memory, slots, frames))


class FrameArrayBatchTests(unittest.TestCase):
    """Verify the batched read paths used by the acquisition walk."""

    def _array(self) -> tuple[_Memory, FrameArray]:
        memory = _Memory()
        slots: list[int | None] = [
            _FRAME_BASE,
            None,
            0xFFFFFFFF,
            _FRAME_BASE + 3 * _FRAME_STRIDE,
        ]
        frames_reader = _frames_for(
            memory,
            slots,
            {
                0: {"callbacks": ((0x00AABBCC, _CONTEXT, 0),)},
                3: {"callbacks": ((0x00AABBDD, _CONTEXT, 0), (0x00AABBEE, 0, 0))},
            },
        )
        return memory, frames_reader

    def test_bulk_slot_read_matches_per_slot_reads(self) -> None:
        _, frames_reader = self._array()
        bulk = frames_reader.read_slot_pointers()
        per_slot = [
            frames_reader.read_frame_pointer(index)
            for index in range(frames_reader.size())
        ]
        self.assertEqual(bulk, per_slot)
        self.assertEqual([slot for slot, _ in frames_reader.iter_slots()], [0, 3])

    def test_frame_id_for_address_finds_and_rejects(self) -> None:
        _, frames_reader = self._array()
        self.assertEqual(frames_reader.frame_id_for_address(_FRAME_BASE), 0)
        self.assertEqual(
            frames_reader.frame_id_for_address(_FRAME_BASE + 3 * _FRAME_STRIDE), 3
        )
        self.assertIsNone(frames_reader.frame_id_for_address(0x00FFFFFF))
        self.assertIsNone(frames_reader.frame_id_for_address(0xFFFFFFFF))

    def test_callbacks_read_by_address_match_the_frame_record(self) -> None:
        _, frames_reader = self._array()
        for frame_id, pointer in frames_reader.iter_slots():
            frame = frames_reader.get(frame_id)
            assert frame is not None
            self.assertEqual(
                [int(c.callback) for c in frames_reader.read_callbacks_at(pointer)],
                [int(c.callback) for c in frames_reader.read_callbacks(frame)],
            )

    def test_callback_search_uses_the_address_path(self) -> None:
        _, frames_reader = self._array()
        tree = FrameTree(frames_reader)
        matches = tree.frames_using_callback(0x00AABBEE)
        self.assertEqual([frame_id for frame_id, _ in matches], [3])


class ThunkCallbackTests(unittest.TestCase):
    """Verify that a registered jmp thunk is matched to its handler.

    Some frames register a short x86 ``jmp`` thunk while the signature resolver
    yields the real handler; this was observed live on the world-map frame.
    """

    _HANDLER = 0x0110B5A0
    _THUNK = 0x0110C340
    _FRAME_ID = 9

    def _tree(self, thunk_target: Any = None) -> FrameTree:
        memory = _Memory()
        tree = _published_context_tree(
            memory, [(self._FRAME_ID, self._THUNK, _CONTEXT)]
        )
        memory.write_u32(_CONTEXT, self._FRAME_ID)
        if thunk_target is not None:
            return FrameTree(tree.frames, thunk_target)
        return tree

    def test_thunk_is_matched_to_its_handler(self) -> None:
        def thunk_target(address: int) -> int | None:
            return self._HANDLER if address == self._THUNK else None

        tree = self._tree(thunk_target)

        matches = tree.frames_using_callback(self._HANDLER)
        self.assertEqual([frame_id for frame_id, _ in matches], [self._FRAME_ID])
        self.assertEqual(tree.frames_using_callback(self._THUNK)[0][0], self._FRAME_ID)

    def test_without_a_thunk_resolver_only_direct_matches_are_found(self) -> None:
        tree = self._tree()

        self.assertEqual(tree.frames_using_callback(self._HANDLER), [])
        self.assertEqual(tree.frames_using_callback(self._THUNK)[0][0], self._FRAME_ID)

    def test_a_failing_thunk_resolver_is_not_fatal(self) -> None:
        def thunk_target(address: int) -> int | None:
            raise OSError("unreadable")

        tree = self._tree(thunk_target)

        self.assertEqual(tree.frames_using_callback(self._HANDLER), [])
        self.assertEqual(tree.frames_using_callback(self._THUNK)[0][0], self._FRAME_ID)

    def test_thunk_route_resolves_the_context_end_to_end(self) -> None:
        from py4gw import WorldMapContext

        memory = _Memory()
        tree = _published_context_tree(
            memory, [(self._FRAME_ID, self._THUNK, _CONTEXT)]
        )
        memory.write_u32(_CONTEXT, self._FRAME_ID)
        thunked = FrameTree(
            tree.frames,
            lambda address: self._HANDLER if address == self._THUNK else None,
        )
        context = WorldMapContext(
            cast(Any, memory),
            cast(Any, None),
            cast(Any, _Catalog(self._HANDLER)),
            thunked,
        )

        self.assertEqual(context.resolve_address(), _CONTEXT)
        self.assertTrue(context.candidates()[0].is_confirmed)


class FramePublishedContextSourceTests(unittest.TestCase):
    """Verify the shared acquisition primitive directly."""

    _CALLBACK = 0x0110B5A0

    def test_source_resolves_and_caches_the_callback(self) -> None:
        from py4gw import FramePublishedContextSource

        memory = _Memory()
        tree = _published_context_tree(memory, [(4, self._CALLBACK, _CONTEXT)])
        memory.write_u32(_CONTEXT, 4)
        catalog = _Catalog(self._CALLBACK)
        source = FramePublishedContextSource(
            cast(Any, None), cast(Any, catalog), tree, "test.callback", 0x0
        )

        self.assertIsNone(source.callback_address)
        self.assertEqual(source.resolve_address(), _CONTEXT)
        self.assertEqual(source.resolve_address(), _CONTEXT)
        self.assertEqual(catalog.calls, 1)
        self.assertEqual(source.callback_address, self._CALLBACK)
        self.assertEqual(source.callback_resolver, "test.callback")
        self.assertEqual(source.frame_id_offset, 0x0)

    def test_source_rejects_a_negative_frame_id_offset(self) -> None:
        from py4gw import FramePublishedContextSource

        with self.assertRaisesRegex(ValueError, "must not be negative"):
            FramePublishedContextSource(
                cast(Any, None),
                cast(Any, _Catalog(self._CALLBACK)),
                cast(Any, None),
                "test.callback",
                -1,
            )

    def test_unusable_callback_address_is_rejected(self) -> None:
        from py4gw import FramePublishedContextSource

        source = FramePublishedContextSource(
            cast(Any, None),
            cast(Any, _Catalog(0x40)),
            cast(Any, None),
            "test.callback",
            0x0,
        )
        with self.assertRaisesRegex(ValueError, "unusable address"):
            source.resolve_callback_address()


class MissionMapFrameAcquisitionTests(unittest.TestCase):
    """Verify the mission-map route, whose frame id sits at 0x14."""

    _CALLBACK = 0x0110B6A0
    _FRAME_ID = 7

    def _context(self) -> tuple[_Memory, FrameTree, _Catalog]:
        memory = _Memory()
        tree = _published_context_tree(
            memory, [(self._FRAME_ID, self._CALLBACK, _CONTEXT_MISSION)]
        )
        catalog = _Catalog(self._CALLBACK)
        return memory, tree, catalog

    def test_frame_id_offset_matches_the_source(self) -> None:
        from py4gw.context.mission_map_context import MissionMapContextStruct

        self.assertEqual(
            cast(Any, MissionMapContextStruct).frame_id.offset, 0x14
        )
        self.assertEqual(ctypes.sizeof(MissionMapContextStruct), 0x48)

    def test_resolve_address_returns_the_confirmed_context(self) -> None:
        from py4gw import MissionMapContext
        from py4gw.context.mission_map_context import MissionMapContextStruct

        memory, tree, catalog = self._context()
        snapshot = MissionMapContextStruct()
        snapshot.frame_id = self._FRAME_ID
        memory.write(_CONTEXT_MISSION, bytes(snapshot))
        context = MissionMapContext(
            cast(Any, memory), cast(Any, None), cast(Any, catalog), tree
        )

        self.assertEqual(context.resolve_address(), _CONTEXT_MISSION)
        read_back = context.read()
        self.assertIsNotNone(read_back)
        assert read_back is not None
        self.assertEqual(read_back.frame_id, self._FRAME_ID)

    def test_frame_id_mismatch_is_rejected(self) -> None:
        from py4gw import MissionMapContext

        memory, tree, catalog = self._context()
        memory.write_u32(_CONTEXT_MISSION + 0x14, self._FRAME_ID + 1)
        context = MissionMapContext(
            cast(Any, memory), cast(Any, None), cast(Any, catalog), tree
        )

        self.assertIsNone(context.resolve_address())
        self.assertIsNone(context.read())
        self.assertIn("cross-check failed", context.candidates()[0].rejection)

    def test_supplied_address_still_reads_the_struct(self) -> None:
        from py4gw.context.mission_map_context import MissionMapContextStruct

        memory, _, _ = self._context()
        snapshot = MissionMapContextStruct()
        snapshot.frame_id = 0x99
        memory.write(_CONTEXT_MISSION, bytes(snapshot))

        read_back = MissionMapContextStruct.read_at(
            cast(Any, memory), _CONTEXT_MISSION
        )
        self.assertEqual(read_back.frame_id, 0x99)


class SalvageFrameAcquisitionTests(unittest.TestCase):
    """Verify the salvage route, whose frame id sits at 0x4."""

    _CALLBACK = 0x0110B7A0
    _FRAME_ID = 11

    def test_layout_matches_the_native_record(self) -> None:
        from py4gw import SalvageSessionInfoStruct

        structure = cast(Any, SalvageSessionInfoStruct)
        self.assertEqual(ctypes.sizeof(SalvageSessionInfoStruct), 0x24)
        self.assertEqual(structure.vtable.offset, 0x0)
        self.assertEqual(structure.frame_id.offset, 0x4)
        self.assertEqual(structure.item_id.offset, 0x8)
        self.assertEqual(structure.salvagable_1.offset, 0xC)
        self.assertEqual(structure.salvagable_2.offset, 0x10)
        self.assertEqual(structure.salvagable_3.offset, 0x14)
        self.assertEqual(structure.chosen_salvagable.offset, 0x18)
        self.assertEqual(structure.h001c.offset, 0x1C)
        self.assertEqual(structure.kit_id.offset, 0x20)
        self.assertEqual(
            [name for name, _ in structure._fields_],
            [
                "vtable",
                "frame_id",
                "item_id",
                "salvagable_1",
                "salvagable_2",
                "salvagable_3",
                "chosen_salvagable",
                "h001c",
                "kit_id",
            ],
        )

    def test_resolve_address_returns_the_confirmed_session(self) -> None:
        from py4gw import SalvageSessionInfo, SalvageSessionInfoStruct

        memory = _Memory()
        tree = _published_context_tree(
            memory, [(self._FRAME_ID, self._CALLBACK, _CONTEXT_SALVAGE)]
        )
        snapshot = SalvageSessionInfoStruct()
        snapshot.vtable = 0x00AABBCC
        snapshot.frame_id = self._FRAME_ID
        snapshot.item_id = 0x1234
        snapshot.chosen_salvagable = 3
        snapshot.kit_id = 0x5678
        memory.write(_CONTEXT_SALVAGE, bytes(snapshot))

        session = SalvageSessionInfo(
            cast(Any, memory),
            cast(Any, None),
            cast(Any, _Catalog(self._CALLBACK)),
            tree,
        )

        self.assertEqual(session.resolve_address(), _CONTEXT_SALVAGE)
        read_back = session.read()
        self.assertIsNotNone(read_back)
        assert read_back is not None
        self.assertEqual(read_back.frame_id, self._FRAME_ID)
        self.assertEqual(read_back.item_id, 0x1234)
        self.assertEqual(read_back.chosen_salvagable, 3)
        self.assertEqual(read_back.kit_id, 0x5678)

    def test_no_popup_means_no_session(self) -> None:
        from py4gw import SalvageSessionInfo

        memory = _Memory()
        tree = _published_context_tree(memory, [])
        session = SalvageSessionInfo(
            cast(Any, memory),
            cast(Any, None),
            cast(Any, _Catalog(self._CALLBACK)),
            tree,
        )

        self.assertIsNone(session.resolve_address())
        self.assertIsNone(session.read())

    def test_struct_read_rejects_bad_address_and_short_data(self) -> None:
        from py4gw import SalvageSessionInfoStruct

        class _ShortReader:
            def read(self, address: int, size: int) -> bytes:
                return b"short"

        with self.assertRaisesRegex(ValueError, "outside x86"):
            SalvageSessionInfoStruct.read_at(_Memory(), 0xFFFF)
        with self.assertRaisesRegex(ValueError, "expected 36"):
            SalvageSessionInfoStruct.read_at(_ShortReader(), _CONTEXT_SALVAGE)

    def test_facade_members_report_the_callback_limit(self) -> None:
        from py4gw import SalvageSessionInfo

        SalvageSessionInfo.disable()
        self.assertEqual(SalvageSessionInfo.get_ptr(), 0)
        self.assertIsNone(SalvageSessionInfo.get_context())
        with self.assertRaisesRegex(NotImplementedError, "callback"):
            SalvageSessionInfo.enable()
        with self.assertRaisesRegex(NotImplementedError, "callback"):
            SalvageSessionInfo._update_ptr()


class CrossRouteIsolationTests(unittest.TestCase):
    """Verify three routes coexisting in one frame array stay independent."""

    _WORLD = 0x0110B5A0
    _MISSION = 0x0110B6A0
    _SALVAGE = 0x0110B7A0

    def test_each_route_finds_only_its_own_frame(self) -> None:
        from py4gw import (
            MissionMapContext,
            SalvageSessionInfo,
            WorldMapContext,
        )

        memory = _Memory()
        tree = _published_context_tree(
            memory,
            [
                (2, self._WORLD, _CONTEXT),
                (7, self._MISSION, _CONTEXT_MISSION),
                (11, self._SALVAGE, _CONTEXT_SALVAGE),
            ],
        )
        memory.write_u32(_CONTEXT, 2)
        memory.write_u32(_CONTEXT_MISSION + 0x14, 7)
        memory.write_u32(_CONTEXT_SALVAGE + 0x4, 11)

        world = WorldMapContext(
            cast(Any, memory),
            cast(Any, None),
            cast(Any, _Catalog(self._WORLD)),
            tree,
        )
        mission = MissionMapContext(
            cast(Any, memory),
            cast(Any, None),
            cast(Any, _Catalog(self._MISSION)),
            tree,
        )
        salvage = SalvageSessionInfo(
            cast(Any, memory),
            cast(Any, None),
            cast(Any, _Catalog(self._SALVAGE)),
            tree,
        )

        self.assertEqual(world.resolve_address(), _CONTEXT)
        self.assertEqual(mission.resolve_address(), _CONTEXT_MISSION)
        self.assertEqual(salvage.resolve_address(), _CONTEXT_SALVAGE)


if __name__ == "__main__":
    unittest.main(verbosity=2)
