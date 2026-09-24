"""Offline field and layout checks for WorldMapContext."""

from __future__ import annotations

import ctypes
import unittest
from typing import Any, cast

from py4gw import ConnectedClient, WorldMapContext, WorldMapContextStruct


class _MemoryReader:
    """Addressable test memory for a supplied callback-owned context address."""

    def __init__(self, regions: dict[int, bytes]) -> None:
        self._regions = regions

    def read(self, address: int, size: int) -> bytes:
        for base, contents in self._regions.items():
            if base <= address < base + len(contents):
                start = address - base
                return contents[start : start + size]
        raise OSError(f"unmapped test address 0x{address:08X}")


class WorldMapContextOfflineTests(unittest.TestCase):
    """Verify every source field and the fixed x86 layout."""

    def test_root_can_be_read_when_a_caller_supplies_the_context_address(self) -> None:
        source = WorldMapContextStruct()
        source.frame_id = 0x1234
        source.zoom = 1.25
        source.top_left.x = -10.0
        source.top_left.y = 20.0
        source.bottom_right.x = 30.0
        source.bottom_right.y = 40.0
        address = 0x160000

        context = WorldMapContextStruct.read_at(
            _MemoryReader({address: bytes(source)}), address
        )

        self.assertEqual(context.frame_id, 0x1234)
        self.assertEqual(context.zoom, 1.25)
        self.assertEqual(context.top_left.x, -10.0)
        self.assertEqual(context.top_left.y, 20.0)
        self.assertEqual(context.bottom_right.x, 30.0)
        self.assertEqual(context.bottom_right.y, 40.0)

    def test_connected_client_exposes_the_supplied_address_reader(self) -> None:
        source = WorldMapContextStruct()
        source.frame_id = 0x4321
        address = 0x160000
        client = object.__new__(ConnectedClient)
        setattr(client, "_reader", _MemoryReader({address: bytes(source)}))
        context = client.read_world_map_context(address)

        self.assertIsNotNone(context)
        assert context is not None
        self.assertEqual(context.frame_id, 0x4321)

    def test_root_read_rejects_invalid_address_and_short_data(self) -> None:
        with self.assertRaisesRegex(ValueError, "outside x86"):
            WorldMapContextStruct.read_at(_MemoryReader({}), 0xFFFF)

        with self.assertRaisesRegex(ValueError, "expected 548"):
            WorldMapContextStruct.read_at(_MemoryReader({0x160000: b"short"}), 0x160000)

    def test_size_and_source_offsets(self) -> None:
        self.assertEqual(ctypes.sizeof(WorldMapContextStruct), 0x224)
        structure = cast(Any, WorldMapContextStruct)
        self.assertEqual(structure.zoom.offset, 0x38)
        self.assertEqual(structure.top_left.offset, 0x3C)
        self.assertEqual(structure.bottom_right.offset, 0x44)
        self.assertEqual(structure.params.offset, 0x70)

    def test_source_field_names_and_order(self) -> None:
        self.assertEqual(
            [name for name, _ in cast(Any, WorldMapContextStruct)._fields_],
            [
                "frame_id", "h0004", "h0008", "h000c", "h0010", "h0014",
                "h0018", "h001c", "h0020", "h0024", "h0028", "h002c",
                "h0030", "h0034", "zoom", "top_left", "bottom_right",
                "h004c", "h0068", "h006c", "params",
            ],
        )

    def test_source_facade_members_and_external_callback_limit(self) -> None:
        WorldMapContext.disable()
        self.assertEqual(WorldMapContext.get_ptr(), 0)
        self.assertIsNone(WorldMapContext.get_context())
        with self.assertRaisesRegex(NotImplementedError, "callback"):
            WorldMapContext.enable()
        with self.assertRaisesRegex(NotImplementedError, "callback"):
            WorldMapContext._update_ptr()


if __name__ == "__main__":
    unittest.main(verbosity=2)
