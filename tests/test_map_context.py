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

        snapshot = self.context.read(max_pathing_maps=32)
        if snapshot is None or snapshot.path_address is None:
            self.skipTest("The client has no active pathing context.")
        path_context = snapshot.path_context
        if path_context is None:
            self.skipTest("The client path pointer is currently unreadable.")
        static_data = path_context.static_data
        if static_data is None:
            self.skipTest("The client has no active map static-data root.")
        maps = static_data.pathing_maps
        self.assertLessEqual(len(maps), 32)
        print(
            f"Live pathing roots: path=0x{path_context.address or 0:08X}, "
            f"static=0x{static_data.address or 0:08X}, "
            f"maps={len(maps)}, map_id={static_data.map_id}"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
