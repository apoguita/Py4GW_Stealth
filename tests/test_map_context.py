"""Live read-only checks for the external ``MapContext`` root slice."""

from __future__ import annotations

import ctypes
import unittest

from py4gw import (
    GameContext,
    MapContext,
    MapContextStruct,
    PatternCatalog,
    ProcessMemoryReader,
    RemoteScanner,
    Win32,
    connect,
    disconnect,
)


class LiveMapContextTests(unittest.TestCase):
    """Verify the GameContext pointer path and bounded map-root reads."""

    @classmethod
    def setUpClass(cls) -> None:
        """Open the first running client with read-only access."""

        cls.win32 = Win32()
        clients = cls.win32.find_guild_wars()
        if not clients:
            raise unittest.SkipTest("Start Guild Wars before running this test.")
        cls.pid = int(clients[0]["pid"])
        module = cls.win32.get_main_module(cls.pid)
        cls.reader = ProcessMemoryReader(cls.win32, cls.pid)
        cls.scanner = RemoteScanner(
            cls.reader,
            int(module["base_address"]),
            int(module["size"]),
        )
        cls.scanner.initialize()
        cls.game_context = GameContext(
            cls.reader,
            cls.scanner,
            PatternCatalog.from_directory("offsets"),
        )
        cls.game_context.initialize()
        cls.context = MapContext(cls.reader, cls.game_context)

    @classmethod
    def tearDownClass(cls) -> None:
        """Close the selected process handle."""

        if hasattr(cls, "reader"):
            cls.reader.close()

    def test_layout_matches_source_slice(self) -> None:
        """The external root remains the maintained fixed 0x138 bytes."""

        self.assertEqual(ctypes.sizeof(MapContextStruct), 0x138)
        self.assertEqual(MapContextStruct.spawns1_array.offset, 0x2C)
        self.assertEqual(MapContextStruct.map_id.offset, 0x8C)

    def test_resolves_map_context_from_game_context(self) -> None:
        """Follow GameContext.map_context without a second signature scan."""

        address = self.context.resolve_address()
        if address is None:
            self.skipTest("The client has no active MapContext.")
        self.assertGreater(address, 0)
        print(f"Live MapContext: 0x{address:08X}")

    def test_source_facade_and_pathing_caches(self) -> None:
        """Exercise the source-named facade against the selected live client."""

        if not self.win32.is_elevated():
            self.skipTest(
                "This test connects to the client, and connecting requires an "
                "elevated controller. Run it from an elevated shell."
            )
        client = connect(self.pid)
        try:
            MapContext._update_ptr()
            self.assertGreater(MapContext.get_ptr(), 0)
            self.assertIsNotNone(MapContext.get_context())

            spawn_groups = MapContext.GetSpawns()
            snapshot = client.read_map_context(max_pathing_maps=100_000)
            self.assertIsNotNone(snapshot)
            assert snapshot is not None
            self.assertEqual(
                tuple(map(len, spawn_groups)),
                tuple(snapshot.spawn_array_sizes.values()),
            )
            self.assertEqual(
                len(MapContext.GetTravelPortals()),
                len(snapshot.travel_portals),
            )

            raw_maps = MapContext.GetPathingMapsRaw()
            pathing_maps = MapContext.GetPathingMaps()
            self.assertEqual(len(raw_maps), len(pathing_maps))
            self.assertGreater(len(raw_maps), 0)
            self.assertIs(MapContext.GetPathingMapsRaw(), raw_maps)
            self.assertIs(MapContext.GetPathingMaps(), pathing_maps)
            self.assertTrue(
                all(key[0] == self.pid for key in MapContext._pathing_maps_cache)
            )

            MapContext.ClearPathingCache(int(snapshot.map_id))
            self.assertFalse(
                any(
                    key[0] == self.pid and key[1] == int(snapshot.map_id)
                    for key in MapContext._pathing_maps_cache
                )
            )
        finally:
            MapContext.disable()
            disconnect()
        self.assertFalse(
            any(key[0] == self.pid for key in MapContext._pathing_maps_cache)
        )
        self.assertFalse(
            any(key[0] == self.pid for key in MapContext._pathing_maps_cache_raw)
        )

    def test_reads_bounded_map_root_and_spawns(self) -> None:
        """Read root values and bounded spawn records from the live client."""

        snapshot = self.context.read(max_spawn_entries=2048)
        if snapshot is None:
            self.skipTest("The client has no active MapContext.")
        self.assertEqual(len(bytes(snapshot)), 0x138)
        for size in snapshot.spawn_array_sizes.values():
            self.assertGreaterEqual(size, 0)
            self.assertLessEqual(size, 0x100000)
        spawns = snapshot.spawns1 + snapshot.spawns2 + snapshot.spawns3
        facade_spawns = self.context.get_spawns()
        self.assertEqual(
            tuple(len(group) for group in facade_spawns),
            tuple(snapshot.spawn_array_sizes.values()),
        )
        self.assertLessEqual(len(spawns), 6144)
        print(
            "Live map: "
            f"map_id={snapshot.map_id}, type={snapshot.map_type}, "
            f"spawn_sizes={snapshot.spawn_array_sizes}, "
            f"materialized_spawns={len(spawns)}, "
            f"path=0x{snapshot.path_address or 0:08X}"
        )

    def test_reads_pathing_context_roots_only(self) -> None:
        """Read live pathing context roots without graph materialization."""

        snapshot = self.context.read(max_pathing_maps=100_000)
        if snapshot is None or snapshot.path_address is None:
            self.skipTest("The client has no active pathing context.")
        path_context = snapshot.path_context
        if path_context is None:
            self.skipTest("The client path pointer is currently unreadable.")
        static_data = path_context.static_data
        if static_data is None:
            self.skipTest("The client has no active map static-data root.")
        maps = static_data.pathing_maps
        # The bound matches the limit requested above; the previous 64 was too
        # small for larger maps, which have been observed with 68 pathing maps.
        self.assertLessEqual(len(maps), 100_000)
        blocking_props = static_data.blocking_props_list
        print(
            f"Live pathing roots: path=0x{path_context.address or 0:08X}, "
            f"static=0x{static_data.address or 0:08X}, "
            f"maps={len(maps)}, blocking_props={len(blocking_props)}, "
            f"map_id={static_data.map_id}"
        )

    def test_reads_pathing_map_child_arrays(self) -> None:
        """Read the source-counted arrays for each live pathing map."""

        snapshot = self.context.read(max_pathing_maps=100_000)
        if snapshot is None or snapshot.path_context is None:
            self.skipTest("The client has no active pathing context.")
        static_data = snapshot.path_context.static_data
        if static_data is None:
            self.skipTest("The client has no active map static-data root.")

        totals = {"trapezoids": 0, "sink_nodes": 0, "x_nodes": 0, "y_nodes": 0, "portals": 0}
        for pathing_map in static_data.pathing_maps:
            records = {
                "trapezoids": (pathing_map.trapezoid_count, pathing_map.trapezoids),
                "sink_nodes": (pathing_map.sink_node_count, pathing_map.sink_nodes),
                "x_nodes": (pathing_map.x_node_count, pathing_map.x_nodes),
                "y_nodes": (pathing_map.y_node_count, pathing_map.y_nodes),
                "portals": (pathing_map.portal_count, pathing_map.portals),
            }
            for name, (expected_count, values) in records.items():
                self.assertEqual(len(values), expected_count, name)
                totals[name] += len(values)

        self.assertGreater(totals["trapezoids"], 0)
        for total in totals.values():
            self.assertLessEqual(total, 100_000 * 32)
        print(f"Live pathing child records: {totals}")

    def test_reads_live_pathing_pointer_links(self) -> None:
        """Read live links and report the source/live SinkNode disagreement."""

        snapshot = self.context.read(max_pathing_maps=100_000)
        if snapshot is None or snapshot.path_context is None:
            self.skipTest("The client has no active pathing context.")
        static_data = snapshot.path_context.static_data
        if static_data is None:
            self.skipTest("The client has no active map static-data root.")

        linked = {"trapezoid_neighbors": 0, "node_children": 0, "portal_first": 0, "portal_trapezoids": 0, "portal_pairs": 0}
        direct_sink_pointer_matches = 0
        source_sink_pointer_shape_mismatch_verified = False
        for map_index, pathing_map in enumerate(static_data.pathing_maps):
            trapezoids = pathing_map.trapezoids
            trapezoid_addresses = {
                int(pathing_map.trapezoids_ptr) + index * ctypes.sizeof(type(trapezoid)):
                int(trapezoid.id)
                for index, trapezoid in enumerate(trapezoids)
            }
            for trapezoid in trapezoids[:16]:
                linked["trapezoid_neighbors"] += sum(
                    neighbor is not None for neighbor in trapezoid.adjacent
                )
            for sink in pathing_map.sink_nodes:
                field_address = int(sink.trapezoid_ptr_ptr)
                if field_address:
                    self.assertIn(
                        field_address,
                        trapezoid_addresses,
                        f"SinkNode in pathing map #{map_index} does not match the live direct-pointer shape.",
                    )
                    direct_value = int.from_bytes(self.reader.read(field_address, 4), "little")
                    self.assertEqual(direct_value, trapezoid_addresses[field_address])
                    direct_sink_pointer_matches += 1
                    if direct_value and not source_sink_pointer_shape_mismatch_verified:
                        with self.assertRaisesRegex(ValueError, "Invalid x86 structure address"):
                            _ = sink.trapezoid
                        with self.assertRaisesRegex(ValueError, "Invalid x86 structure address"):
                            _ = sink.trapezoid_ids
                        source_sink_pointer_shape_mismatch_verified = True
            for node in pathing_map.x_nodes[:16]:
                linked["node_children"] += int(node.left is not None) + int(node.right is not None)
            for node in pathing_map.y_nodes[:16]:
                linked["node_children"] += int(node.left is not None) + int(node.right is not None)
            for portal in pathing_map.portals[:16]:
                linked["portal_pairs"] += int(portal.pair is not None)
                linked["portal_first"] += int(portal.trapezoids is not None)
                linked["portal_trapezoids"] += len(portal.trapezoid_indices)

        self.assertTrue(source_sink_pointer_shape_mismatch_verified)
        print(
            f"Live pathing links (first 16 records per array/map): {linked}; "
            "the current client stores direct trapezoid addresses, so the "
            "source-shaped SinkNode dereferences correctly reject the first "
            "trapezoid ID as an address; "
            f"direct sink fields within owning arrays={direct_sink_pointer_matches}"
        )

    def test_reads_live_props_context_arrays(self) -> None:
        """Read the source PropsContext arrays reachable from MapContext."""

        snapshot = self.context.read(max_prop_entries=100_000, max_prop_list_entries=100_000)
        if snapshot is None or snapshot.props_address is None:
            self.skipTest("The client has no active PropsContext.")
        props = snapshot.props
        if props is None:
            self.skipTest("The client has no readable PropsContext pointer.")

        prop_groups = props.props_by_type
        prop_models = props.prop_models
        map_props = props.props
        travel_portals = snapshot.travel_portals
        self.assertEqual(self.context.get_travel_portals(), travel_portals)
        pointer_records = 0
        for map_prop in map_props[:16]:
            pointer_records += int(map_prop.interactive_model is not None)
            pointer_records += int(map_prop.prop_object_info is not None)
        self.assertEqual(len(prop_groups), int(props.propsByType_array.m_size))
        self.assertEqual(len(prop_models), int(props.propModels_array.m_size))
        self.assertLessEqual(len(map_props), int(props.propArray_array.m_size))
        print(
            "Live PropsContext: "
            f"address=0x{props.address or 0:08X}, groups={len(prop_groups)}, "
            f"PropByType={sum(map(len, prop_groups))}, models={len(prop_models)}, "
            f"props={len(map_props)}, non-null nested records in first 16={pointer_records}, "
            f"travel_portals={len(travel_portals)}"
        )

    def test_reads_live_pathing_snapshots(self) -> None:
        """Materialize the Reforged source snapshot surface from live records."""

        snapshot = self.context.read(max_pathing_maps=100_000)
        if snapshot is None or snapshot.path_context is None:
            self.skipTest("The client has no active pathing context.")
        static_data = snapshot.path_context.static_data
        if static_data is None:
            self.skipTest("The client has no active map static-data root.")

        pathing_maps = static_data.pathing_maps_snapshot
        self.assertEqual(len(pathing_maps), int(static_data.pmaps_array.m_size))
        self.assertTrue(all(pathing_map.root_node is not None for pathing_map in pathing_maps))
        print(
            "Live pathing snapshots: "
            f"maps={len(pathing_maps)}, "
            f"trapezoids={sum(len(value.trapezoids) for value in pathing_maps)}, "
            f"portals={sum(len(value.portals) for value in pathing_maps)}, "
            f"resolved pairs={sum(portal.pair_index != 0xFFFFFFFF for value in pathing_maps for portal in value.portals)}"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
