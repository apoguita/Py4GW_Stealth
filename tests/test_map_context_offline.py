"""Offline layout and bounded-read checks for ``MapContext``."""

from __future__ import annotations

import ctypes
import struct
import unittest
from typing import Any, cast
from unittest.mock import patch

from py4gw import (
    BlockingPropStruct,
    GWArray,
    GWLinkStruct,
    GWListStruct,
    MapPropStruct,
    MapContext,
    MapContextStruct,
    MapStaticDataStruct,
    MapVec2fStruct,
    MapVec3fStruct,
    NativeMapContextPrefixStruct,
    NativeMapContextSub1Struct,
    NativeMapContextSub2Struct,
    NativeMapPropStruct,
    NativePathingMapStruct,
    NativePathingTrapezoidStruct,
    NativePortalStruct,
    NativePropsContextStruct,
    NativeSinkNodeStruct,
    NativeXNodeStruct,
    NativeYNodeStruct,
    NodeStruct,
    PathingTrapezoidStruct,
    PathContextStruct,
    PathingMapStruct,
    PortalStruct,
    PropByTypeStruct,
    PropModelInfoStruct,
    PropsContextStruct,
    RecObjectStruct,
    SinkNodeStruct,
    SpawnEntryStruct,
    SpawnPoint,
    XNodeStruct,
    YNodeStruct,
)


def _field_names(structure: type[ctypes.Structure]) -> list[str]:
    """Return ctypes field names, including optional source bit widths."""

    return [name for name, *_ in cast(Any, structure)._fields_]


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
        self.assertEqual(ctypes.sizeof(MapVec3fStruct), 0x0C)
        self.assertEqual(ctypes.sizeof(SpawnEntryStruct), 0x10)
        self.assertEqual(ctypes.sizeof(PathingTrapezoidStruct), 0x30)
        self.assertEqual(ctypes.sizeof(NodeStruct), 0x08)
        self.assertEqual(ctypes.sizeof(SinkNodeStruct), 0x0C)
        self.assertEqual(ctypes.sizeof(XNodeStruct), 0x20)
        self.assertEqual(ctypes.sizeof(YNodeStruct), 0x18)
        self.assertEqual(ctypes.sizeof(PortalStruct), 0x14)
        self.assertEqual(ctypes.sizeof(PathingMapStruct), 0x54)
        self.assertEqual(ctypes.sizeof(PropModelInfoStruct), 0x18)
        self.assertEqual(ctypes.sizeof(RecObjectStruct), 0x0C)
        self.assertEqual(ctypes.sizeof(PropByTypeStruct), 0x08)
        self.assertEqual(ctypes.sizeof(MapPropStruct), 0x90)
        self.assertEqual(ctypes.sizeof(PropsContextStruct), 0x1A4)
        self.assertEqual(ctypes.sizeof(BlockingPropStruct), 0x0C)
        self.assertEqual(ctypes.sizeof(NativePathingTrapezoidStruct), 0x30)
        self.assertEqual(ctypes.sizeof(NativeSinkNodeStruct), 0x0C)
        self.assertEqual(ctypes.sizeof(NativeXNodeStruct), 0x20)
        self.assertEqual(ctypes.sizeof(NativeYNodeStruct), 0x18)
        self.assertEqual(ctypes.sizeof(NativePortalStruct), 0x14)
        self.assertEqual(ctypes.sizeof(NativePathingMapStruct), 0x54)
        self.assertEqual(ctypes.sizeof(NativeMapPropStruct), 0x90)
        self.assertEqual(ctypes.sizeof(NativePropsContextStruct), 0x1A4)
        self.assertEqual(ctypes.sizeof(NativeMapContextSub2Struct), 0x28)
        self.assertEqual(ctypes.sizeof(NativeMapContextSub1Struct), 0x70)
        self.assertEqual(ctypes.sizeof(NativeMapContextPrefixStruct), 0x134)
        self.assertEqual(ctypes.sizeof(MapStaticDataStruct), 0xA0)
        self.assertEqual(ctypes.sizeof(PathContextStruct), 0x94)
        self.assertEqual(ctypes.sizeof(MapContextStruct), 0x138)
        self.assertEqual(MapContextStruct.spawns1_array.offset, 0x2C)
        self.assertEqual(MapContextStruct.path_ptr.offset, 0x74)
        self.assertEqual(MapContextStruct.props_ptr.offset, 0x7C)
        self.assertEqual(MapContextStruct.map_id.offset, 0x8C)
        self.assertEqual(MapContextStruct.zones.offset, 0x130)
        self.assertEqual(NativeMapContextPrefixStruct.spawns1.offset, 0x2C)
        self.assertEqual(NativeMapContextPrefixStruct.sub1.offset, 0x74)
        self.assertEqual(NativeMapContextPrefixStruct.props.offset, 0x7C)
        self.assertEqual(NativeMapContextPrefixStruct.h0088.offset, 0x88)
        self.assertEqual(NativeMapContextPrefixStruct.zones.offset, 0x130)
        self.assertEqual(NativeMapContextSub1Struct.pathing_map_block.offset, 0x04)
        # C++ member order places total_trapezoid_count at 0x14; its comment
        # says 0x18, so retain the sequential layout and flag the mismatch.
        self.assertEqual(NativeMapContextSub1Struct.total_trapezoid_count.offset, 0x14)

    def test_pathing_and_prop_source_fields(self) -> None:
        """New declarations preserve native/Reforged field names and order."""

        expected_fields = {
            SpawnEntryStruct: ["x", "y", "angle", "tag_raw"],
            NodeStruct: ["type", "id"],
            SinkNodeStruct: ["trapezoid_ptr_ptr"],
            XNodeStruct: ["pos", "dir", "left_ptr", "right_ptr"],
            YNodeStruct: ["pos", "left_ptr", "right_ptr"],
            PortalStruct: [
                "left_layer_id", "right_layer_id", "flags", "pair_ptr",
                "count", "trapezoids_ptr_ptr",
            ],
            PathingMapStruct: [
                "zplane", "h0004", "h0008", "h000C", "h0010",
                "trapezoid_count", "trapezoids_ptr", "sink_node_count",
                "sink_nodes_ptr", "x_node_count", "x_nodes_ptr",
                "y_node_count", "y_nodes_ptr", "h0034", "h0038",
                "portal_count", "portals_ptr", "root_node_ptr", "h0048_ptr",
                "h004C_ptr", "h0050_ptr",
            ],
            PropModelInfoStruct: ["h0000", "h0004", "h0008", "h000C", "h0010", "h0014"],
            RecObjectStruct: ["h0000", "h0004", "accessKey"],
            PropByTypeStruct: ["object_id", "prop_index"],
            BlockingPropStruct: ["pos", "radius"],
            MapStaticDataStruct: [
                "h0000", "pmaps_array", "h0028", "blocking_props", "h0044",
                "trapezoid_count", "h0088", "map_id", "h0090",
            ],
            PathContextStruct: [
                "static_data_ptr", "blocked_planes", "path_nodes", "node_cache",
                "open_list", "free_ipath_node", "allocated_path_nodes", "h005C",
                "h0060", "waypoints", "node_stack", "h0084",
            ],
            MapContextStruct: [
                "map_type", "start_pos", "end_pos", "h0014", "spawns1_array",
                "spawns2_array", "spawns3_array", "h005C", "path_ptr",
                "path_engine_ptr", "props_ptr", "h0080", "terrain", "h0088",
                "map_id", "h0090", "zones", "h0134",
            ],
        }
        for structure, expected in expected_fields.items():
            with self.subTest(structure=structure.__name__):
                self.assertEqual([name for name, _ in structure._fields_], expected)

        self.assertEqual(
            _field_names(PathingTrapezoidStruct),
            [
                "id",
                "adjacent_ptr",
                "portal_left",
                "portal_right",
                "XTL",
                "XTR",
                "YT",
                "XBL",
                "XBR",
                "YB",
            ],
        )
        self.assertEqual(
            _field_names(MapPropStruct),
            [
                "h0000",
                "uptime_seconds",
                "h0018",
                "prop_index",
                "position",
                "model_file_id",
                "h0030",
                "rotation_angle",
                "rotation_cos",
                "rotation_sin",
                "h0034",
                "interactive_model_ptr",
                "h005C",
                "appearance_bitmap",
                "animation_bits",
                "h0064",
                "prop_object_info_ptr",
                "h008C",
            ],
        )
        self.assertEqual(
            _field_names(PropsContextStruct),
            ["pad1", "propsByType_array", "h007C", "propModels_array", "h00B4", "propArray_array"],
        )
        self.assertEqual(
            _field_names(NativePathingMapStruct),
            [
                "zplane", "h0004", "h0008", "h000C", "h0010",
                "trapezoid_count", "trapezoids", "sink_node_count", "sink_nodes",
                "x_node_count", "x_nodes", "y_node_count", "y_nodes",
                "h0034", "h0038", "portal_count", "portals", "root_node",
                "h0048", "h004C", "h0050",
            ],
        )
        self.assertEqual(NativeMapPropStruct.interactive_model.offset, 0x58)
        self.assertEqual(NativeMapPropStruct.prop_object_info.offset, 0x88)
        self.assertEqual(NativePropsContextStruct.propsByType.offset, 0x6C)
        self.assertEqual(NativePropsContextStruct.propModels.offset, 0xA4)
        self.assertEqual(NativePropsContextStruct.propArray.offset, 0x194)

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

    def test_spawn_reads_raise_instead_of_returning_a_partial_array(self) -> None:
        """Configured bounds never silently hide advertised source entries."""

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
        with self.assertRaisesRegex(ValueError, "exceeds max_spawn_entries"):
            _ = root.spawns1
        root.bind_reader(reader, 0x20000, max_spawn_entries=2)
        self.assertEqual(len(root.spawns1), 2)
        self.assertEqual(root.spawns1[0].tag, "0000")
        self.assertTrue(root.spawns1[0].is_default)
        self.assertEqual(root.path_address, 0x30000)
        self.assertEqual(root.props_address, 0x31000)
        self.assertEqual(root.map_id, 42)
        self.assertEqual(len(root.map_boundaries), 5)

    def test_facade_reports_empty_results_without_a_selected_client(self) -> None:
        """Source-named convenience methods are safe before connect()."""

        with patch("py4gw.client.current_client", return_value=None):
            self.assertEqual(MapContext.GetPathingMaps(), [])
            self.assertEqual(MapContext.GetPathingMapsRaw(), [])
            self.assertEqual(MapContext.GetTravelPortals(), [])
            self.assertEqual(MapContext.GetSpawns(), ([], [], []))

    def test_callback_facade_is_declared_but_not_enabled_externally(self) -> None:
        """The original callback entry point stays explicit and unavailable."""

        MapContext._ptr = 0x1234
        MapContext._cached_ctx = MapContextStruct()

        self.assertEqual(MapContext.get_ptr(), 0x1234)
        self.assertIsNotNone(MapContext.get_context())
        with self.assertRaisesRegex(NotImplementedError, "callback runtime"):
            MapContext.enable()

        MapContext.disable()

        self.assertEqual(MapContext.get_ptr(), 0)
        self.assertIsNone(MapContext.get_context())

    def test_pathing_cache_can_be_cleared_by_map_or_process(self) -> None:
        """Cache keys isolate clients and support explicit lifecycle cleanup."""

        MapContext._pathing_maps_cache[(101, 42)] = []
        MapContext._pathing_maps_cache[(202, 42)] = []
        MapContext._pathing_maps_cache_raw[(101, 42)] = []
        MapContext._pathing_maps_cache_raw[(101, 43)] = []

        MapContext.ClearPathingCache(42)
        self.assertNotIn((101, 42), MapContext._pathing_maps_cache)
        self.assertNotIn((202, 42), MapContext._pathing_maps_cache)
        self.assertNotIn((101, 42), MapContext._pathing_maps_cache_raw)

        MapContext._clear_pathing_cache_for_pid(101)
        self.assertNotIn((101, 43), MapContext._pathing_maps_cache_raw)

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
        self.assertEqual(root.path.address, path_address)  # type: ignore[union-attr]
        self.assertEqual(root.sub1.address, path_address)  # type: ignore[union-attr]
        self.assertEqual(path_view.static_data_address, static_address)

        static_view = path_view.static_data
        self.assertIsNotNone(static_view)
        assert static_view is not None
        self.assertEqual(path_view.sub2.address, static_address)  # type: ignore[union-attr]
        self.assertEqual(static_view.map_id, 42)
        self.assertEqual(static_view.pathing_map_sizes, (1, 1))

        maps = static_view.pathing_maps
        self.assertEqual(len(maps), 1)
        self.assertEqual(maps[0].trapezoid_count, 120)
        self.assertEqual(maps[0].portals_address, 0x51000)

    def test_pathing_map_reads_bounded_child_arrays(self) -> None:
        """Read each fixed PathingMap child array through its remote address."""

        traps_address = 0x40000
        sinks_address = 0x41000
        x_nodes_address = 0x42000
        y_nodes_address = 0x43000
        portals_address = 0x44000

        trap_records = []
        for trap_id in (10, 20):
            trap = PathingTrapezoidStruct()
            trap.id = trap_id
            trap_records.append(bytes(trap))

        sink = SinkNodeStruct()
        sink.type = 2
        sink.id = 30
        x_node = XNodeStruct()
        x_node.type = 0
        x_node.id = 31
        y_node = YNodeStruct()
        y_node.type = 1
        y_node.id = 32
        portal = PortalStruct()
        portal.left_layer_id = 2
        portal.right_layer_id = 3

        reader = _FakeReader(
            {
                traps_address: b"".join(trap_records),
                sinks_address: bytes(sink),
                x_nodes_address: bytes(x_node),
                y_nodes_address: bytes(y_node),
                portals_address: bytes(portal),
            }
        )
        pathing_map = PathingMapStruct()
        pathing_map.trapezoids_ptr = traps_address
        pathing_map.trapezoid_count = 2
        pathing_map.sink_nodes_ptr = sinks_address
        pathing_map.sink_node_count = 1
        pathing_map.x_nodes_ptr = x_nodes_address
        pathing_map.x_node_count = 1
        pathing_map.y_nodes_ptr = y_nodes_address
        pathing_map.y_node_count = 1
        pathing_map.portals_ptr = portals_address
        pathing_map.portal_count = 1
        pathing_map.bind_reader(reader, max_pathing_entries=2)

        self.assertEqual([entry.id for entry in pathing_map.trapezoids], [10, 20])
        self.assertEqual([entry.id for entry in pathing_map.sink_nodes], [30])
        self.assertEqual([entry.id for entry in pathing_map.x_nodes], [31])
        self.assertEqual([entry.id for entry in pathing_map.y_nodes], [32])
        self.assertEqual(
            [(entry.left_layer_id, entry.right_layer_id) for entry in pathing_map.portals],
            [(2, 3)],
        )

        pathing_map.bind_reader(reader, max_pathing_entries=1)
        with self.assertRaises(ValueError):
            _ = pathing_map.trapezoids

    def test_pathing_records_follow_source_pointer_links(self) -> None:
        """Neighbor, node, sink, and portal links are read as remote records."""

        trap_a_address = 0x50000
        trap_b_address = 0x50030
        sink_address = 0x51000
        x_node_address = 0x52000
        y_node_address = 0x52020
        portal_address = 0x53000
        portal_pair_address = 0x53014
        sink_trapezoid_array_address = 0x54000
        portal_array_address = 0x55000
        unterminated_sink_array_address = 0x56000

        trap_a = PathingTrapezoidStruct()
        trap_a.id = 101
        trap_a.adjacent_ptr[0] = trap_b_address
        trap_b = PathingTrapezoidStruct()
        trap_b.id = 202

        sink = SinkNodeStruct()
        sink.id = 2
        sink.trapezoid_ptr_ptr = sink_trapezoid_array_address
        x_node = XNodeStruct()
        x_node.left_ptr = sink_address
        x_node.right_ptr = 0
        y_node = YNodeStruct()
        y_node.left_ptr = sink_address
        y_node.right_ptr = 0
        portal = PortalStruct()
        portal.pair_ptr = portal_pair_address
        portal.count = 2
        portal.trapezoids_ptr_ptr = portal_array_address
        portal_pair = PortalStruct()

        reader = _FakeReader(
            {
                trap_a_address: bytes(trap_a),
                trap_b_address: bytes(trap_b),
                sink_address: bytes(sink),
                x_node_address: bytes(x_node),
                y_node_address: bytes(y_node),
                portal_address: bytes(portal),
                portal_pair_address: bytes(portal_pair),
                sink_trapezoid_array_address: (
                    trap_a_address.to_bytes(4, "little")
                    + trap_b_address.to_bytes(4, "little")
                    + bytes(4)
                ),
                portal_array_address: (
                    trap_b_address.to_bytes(4, "little")
                    + bytes(4)
                ),
                unterminated_sink_array_address: (
                    trap_a_address.to_bytes(4, "little")
                    + trap_b_address.to_bytes(4, "little")
                    + trap_a_address.to_bytes(4, "little")
                ),
            }
        )

        trap_view = PathingTrapezoidStruct.from_buffer_copy(bytes(trap_a)).bind_reader(reader)
        sink_view = SinkNodeStruct.from_buffer_copy(bytes(sink)).bind_reader(reader, 4)
        x_node_view = XNodeStruct.from_buffer_copy(bytes(x_node)).bind_reader(reader)
        y_node_view = YNodeStruct.from_buffer_copy(bytes(y_node)).bind_reader(reader)
        portal_view = PortalStruct.from_buffer_copy(bytes(portal)).bind_reader(reader, 4)

        self.assertEqual([item.id if item else None for item in trap_view.adjacent], [202, None, None, None])
        self.assertEqual(trap_view.neighbor_ids, [202])
        self.assertEqual(trap_view.snapshot().neighbor_ids, [202])
        self.assertEqual(sink_view.trapezoid.id, 101)  # type: ignore[union-attr]
        self.assertEqual(sink_view.trapezoid_ids, [101, 202])
        self.assertEqual(sink_view.snapshot_sinknode().trapezoid_ids, [101, 202])
        self.assertEqual(x_node_view.left.id, 2)  # type: ignore[union-attr]
        self.assertIsNone(x_node_view.right)
        self.assertEqual(x_node_view.snapshot_xnode().left_id, 2)
        self.assertEqual(y_node_view.snapshot_ynode().left_id, 2)
        self.assertIsNotNone(portal_view.pair)
        self.assertEqual(portal_view.trapezoids.id, 202)  # type: ignore[union-attr]
        self.assertEqual(portal_view.trapezoid_indices, [202])
        self.assertEqual(portal_view.snapshot().trapezoid_indices, [202])

        sink_view.trapezoid_ptr_ptr = unterminated_sink_array_address
        sink_view.bind_reader(reader, 2)
        with self.assertRaisesRegex(ValueError, "no null terminator"):
            _ = sink_view.trapezoid_ids

    def test_props_context_reads_source_arrays_and_pointer_records(self) -> None:
        """Read prop values, pointer entries, and PropByType intrusive lists."""

        props_address = 0x60000
        groups_address = 0x61000
        models_address = 0x62000
        prop_pointers_address = 0x63000
        prop_address = 0x64000
        model_pointer_address = 0x65000
        object_info_address = 0x66000
        list_item_address = 0x67000

        group = GWListStruct()
        group.offset = ctypes.sizeof(PropByTypeStruct)
        group.link.next_node = list_item_address
        model = PropModelInfoStruct()
        model.h0008 = 88
        info = PropByTypeStruct()
        info.object_id = 1234
        info.prop_index = 7
        prop = MapPropStruct()
        prop.interactive_model_ptr = model_pointer_address
        prop.prop_object_info_ptr = object_info_address
        resource = RecObjectStruct()
        resource.accessKey = 0xABC
        linked_item_and_link = bytes(info) + bytes(GWLinkStruct())

        context = PropsContextStruct()
        context.propsByType_array = GWArray(groups_address, 1, 1, 0)
        context.propModels_array = GWArray(models_address, 1, 1, 0)
        context.propArray_array = GWArray(prop_pointers_address, 1, 1, 0)

        reader = _FakeReader(
            {
                props_address: bytes(context),
                groups_address: bytes(group),
                models_address: bytes(model),
                prop_pointers_address: prop_address.to_bytes(4, "little"),
                prop_address: bytes(prop),
                model_pointer_address: bytes(resource),
                object_info_address: bytes(info),
                list_item_address: linked_item_and_link,
            }
        )
        props = PropsContextStruct.from_buffer_copy(bytes(context)).bind_reader(
            reader, props_address, max_prop_entries=4, max_prop_list_entries=4
        )

        self.assertEqual(len(props.props_by_type), 1)
        self.assertEqual(
            [(entry.object_id, entry.prop_index) for entry in props.props_by_type[0]],
            [(1234, 7)],
        )
        self.assertEqual(props.prop_models[0].h0008, 88)
        self.assertEqual(props.props[0].interactive_model.accessKey, 0xABC)  # type: ignore[union-attr]
        self.assertEqual(props.props[0].prop_object_info.object_id, 1234)  # type: ignore[union-attr]

    def test_map_static_data_reads_bounded_blocking_props(self) -> None:
        """Read the source BaseArray of collision-only blocking props."""

        array_address = 0x68000
        first = BlockingPropStruct()
        first.pos.x = 12.5
        first.pos.y = -8.0
        first.radius = 4.0
        second = BlockingPropStruct()
        second.pos.x = 2.0
        second.radius = 3.0
        static_data = MapStaticDataStruct()
        static_data.blocking_props = (array_address, 2, 2)
        reader = _FakeReader({array_address: bytes(first) + bytes(second)})
        static_view = MapStaticDataStruct.from_buffer_copy(bytes(static_data)).bind_reader(
            reader, max_blocking_props=2
        )

        self.assertEqual(
            [(prop.pos.x, prop.pos.y, prop.radius) for prop in static_view.blocking_props_list],
            [(12.5, -8.0, 4.0), (2.0, 0.0, 3.0)],
        )

    def test_pathing_map_snapshot_resolves_portal_pair_index(self) -> None:
        """Source snapshots resolve paired portals to their array index."""

        path_maps_address = 0x71000
        node_address = 0x72000
        portals_address = 0x73000

        root_node = NodeStruct()
        root_node.type = 0
        root_node.id = 99
        first_portal = PortalStruct()
        first_portal.left_layer_id = 1
        first_portal.right_layer_id = 2
        first_portal.pair_ptr = portals_address + ctypes.sizeof(PortalStruct)
        second_portal = PortalStruct()
        second_portal.left_layer_id = 2
        second_portal.right_layer_id = 1

        pathing_map = PathingMapStruct()
        pathing_map.root_node_ptr = node_address
        pathing_map.portals_ptr = portals_address
        pathing_map.portal_count = 2
        static_data = MapStaticDataStruct()
        static_data.pmaps_array = GWArray(path_maps_address, 1, 1, 0)

        reader = _FakeReader(
            {
                path_maps_address: bytes(pathing_map),
                node_address: bytes(root_node),
                portals_address: bytes(first_portal) + bytes(second_portal),
            }
        )
        static_view = MapStaticDataStruct.from_buffer_copy(bytes(static_data)).bind_reader(
            reader
        )

        snapshots = static_view.pathing_maps_snapshot

        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0].root_node_id, 99)
        self.assertEqual(snapshots[0].portals[0].pair_index, 1)
        self.assertEqual(snapshots[0].portals[1].pair_index, 0xFFFFFFFF)

    def test_map_context_finds_source_travel_portal_models(self) -> None:
        """The source file-hash chain resolves a known portal model ID."""

        props_address = 0x74000
        prop_array_address = 0x75000
        prop_address = 0x76000
        sub_address = 0x77000
        hash_address = 0x78000
        file_hash = struct.pack("<3H", 0xEBB1, 0x0104, 0)

        prop = MapPropStruct()
        prop.position.x = 10.5
        prop.position.y = -2.0
        prop.position.z = 7.25
        prop.h0034[4] = sub_address

        props_context = PropsContextStruct()
        props_context.propArray_array = GWArray(prop_array_address, 1, 1, 0)
        map_context = MapContextStruct()
        map_context.props_ptr = props_address

        reader = _FakeReader(
            {
                props_address: bytes(props_context),
                prop_array_address: prop_address.to_bytes(4, "little"),
                prop_address: bytes(prop),
                sub_address: bytes(4) + hash_address.to_bytes(4, "little"),
                hash_address: file_hash,
            }
        )
        map_view = MapContextStruct.from_buffer_copy(bytes(map_context)).bind_reader(reader)

        portals = map_view.travel_portals

        self.assertEqual(len(portals), 1)
        self.assertEqual(
            (portals[0].x, portals[0].y, portals[0].z, portals[0].model_file_id),
            (10.5, -2.0, 7.25, 0x4E6B2),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
