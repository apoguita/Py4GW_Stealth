"""Offline layout and bounded-read checks for ``MapContext``."""

from __future__ import annotations

import ctypes
import unittest

from py4gw import (
    GWArray,
    MapContextStruct,
    MapStaticDataStruct,
    MapVec2fStruct,
    PathContextStruct,
    PathingMapStruct,
    SpawnEntryStruct,
    SpawnPoint,
)


class _FakeReader:
    """Small addressable byte store for bounded remote-array tests."""

    def __init__(self, memory: dict[int, bytes]) -> None:
        self._memory = memory

    def read(self, address: int, size: int) -> bytes:
        for start, value in self._memory.items():
            end = start + len(value)
            if start <= address and address + size <= end:
                offset = address - start
                return value[offset : offset + size]
        raise OSError(f"unmapped fake address 0x{address:08X}")


class MapContextOfflineTests(unittest.TestCase):
    """Keep the root layout and spawn traversal fixed without a live client."""

    def test_native_offsets_and_sizes(self) -> None:
        """The root and direct child records match the source layout."""

        self.assertEqual(ctypes.sizeof(MapVec2fStruct), 0x08)
        self.assertEqual(ctypes.sizeof(SpawnEntryStruct), 0x10)
        self.assertEqual(ctypes.sizeof(PathingMapStruct), 0x54)
        self.assertEqual(ctypes.sizeof(MapStaticDataStruct), 0xA0)
        self.assertEqual(ctypes.sizeof(PathContextStruct), 0x94)
        self.assertEqual(ctypes.sizeof(MapContextStruct), 0x138)
        self.assertEqual(MapContextStruct.spawns1_array.offset, 0x2C)
        self.assertEqual(MapContextStruct.path_ptr.offset, 0x74)
        self.assertEqual(MapContextStruct.props_ptr.offset, 0x7C)
        self.assertEqual(MapContextStruct.map_id.offset, 0x8C)
        self.assertEqual(MapContextStruct.zones.offset, 0x130)

    def test_spawn_entry_decodes_source_tag(self) -> None:
        """Spawn FourCCs and numeric map tags retain source helper behavior."""

        entry = SpawnEntryStruct()
        entry.x = 12.5
        entry.y = -4.0
        entry.angle = 1.25
        entry.tag_raw = int.from_bytes(b"0558", "big")

        point = entry.snapshot()

        self.assertIsInstance(point, SpawnPoint)
        self.assertEqual(point.tag, "0558")
        self.assertEqual(point.map_id, 558)
        self.assertFalse(point.is_default)
        self.assertEqual((point.x, point.y, point.angle), (12.5, -4.0, 1.25))

    def test_spawn_reads_are_bounded_and_lazy(self) -> None:
        """Only the requested bounded array entries are materialized."""

        address = 0x22000
        entries = []
        for tag in (b"0000", b"0558"):
            entry = SpawnEntryStruct()
            entry.tag_raw = int.from_bytes(tag, "big")
            entries.append(bytes(entry))

        root = MapContextStruct()
        root.map_id = 42
        root.path_ptr = 0x30000
        root.props_ptr = 0x31000
        root.spawns1_array = GWArray(address, 2, 2, 0)
        reader = _FakeReader({address: b"".join(entries)})
        root.bind_reader(reader, 0x20000, max_spawn_entries=1)

        self.assertEqual(root.spawn_array_sizes["spawns1"], 2)
        self.assertEqual(len(root.spawns1), 1)
        self.assertEqual(root.spawns1[0].tag, "0000")
        self.assertTrue(root.spawns1[0].is_default)
        self.assertEqual(root.path_address, 0x30000)
        self.assertEqual(root.props_address, 0x31000)
        self.assertEqual(root.map_id, 42)
        self.assertEqual(len(root.map_boundaries), 5)

    def test_reads_pathing_context_roots_without_materializing_graph(self) -> None:
        """Read PathContext/MapStaticData/PathingMap roots only."""

        path_address = 0x30000
        static_address = 0x31000
        maps_address = 0x32000

        path = PathContextStruct()
        path.static_data_ptr = static_address

        static_data = MapStaticDataStruct()
        static_data.map_id = 42
        static_data.pmaps_array = GWArray(maps_address, 1, 1, 0)

        pathing_map = PathingMapStruct()
        pathing_map.zplane = 0xFFFFFFFF
        pathing_map.trapezoid_count = 120
        pathing_map.trapezoids_ptr = 0x50000
        pathing_map.portal_count = 3
        pathing_map.portals_ptr = 0x51000

        reader = _FakeReader(
            {
                path_address: bytes(path),
                static_address: bytes(static_data),
                maps_address: bytes(pathing_map),
            }
        )
        root = MapContextStruct()
        root.path_ptr = path_address
        root.bind_reader(reader, 0x20000, max_pathing_maps=4)

        path_view = root.path_context
        self.assertIsNotNone(path_view)
        assert path_view is not None
        self.assertEqual(path_view.static_data_address, static_address)

        static_view = path_view.static_data
        self.assertIsNotNone(static_view)
        assert static_view is not None
        self.assertEqual(static_view.map_id, 42)
        self.assertEqual(static_view.pathing_map_sizes, (1, 1))

        maps = static_view.pathing_maps
        self.assertEqual(len(maps), 1)
        self.assertEqual(maps[0].trapezoid_count, 120)
        self.assertEqual(maps[0].portals_address, 0x51000)


if __name__ == "__main__":
    unittest.main(verbosity=2)
