"""Live Guild Wars tests for the external InstanceInfo reader."""

from __future__ import annotations

import ctypes
import unittest

from py4gw import (
    AreaInfoStruct,
    InstanceInfo,
    InstanceInfoStruct,
    MapDimensionsStruct,
    PatternCatalog,
    ProcessMemoryReader,
    RemoteScanner,
    Win32,
)


class LiveInstanceInfoTests(unittest.TestCase):
    """Verify InstanceInfo and its nested records against Guild Wars."""

    @classmethod
    def setUpClass(cls) -> None:
        """Open the first discovered client with read-only access."""

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
        cls.context = InstanceInfo(
            cls.reader,
            cls.scanner,
            PatternCatalog.from_directory("offsets"),
        )

    @classmethod
    def tearDownClass(cls) -> None:
        """Close the selected process handle after the live checks."""

        if hasattr(cls, "reader"):
            cls.reader.close()

    def test_layout_matches_native_instance_info(self) -> None:
        """Keep the root and nested layouts aligned with native source."""

        self.assertEqual(ctypes.sizeof(MapDimensionsStruct), 0x18)
        self.assertEqual(ctypes.sizeof(AreaInfoStruct), 0x7C)
        self.assertEqual(ctypes.sizeof(InstanceInfoStruct), 0x14)
        self.assertEqual(InstanceInfoStruct.current_map_info_ptr.offset, 0x08)

    def test_resolves_live_instance_info(self) -> None:
        """Resolve and cache the JSON InstanceInfo address."""

        address = self.context.resolve_address()
        cached_address = self.context.cached_context_address or 0
        self.assertGreater(cached_address, 0)
        self.assertEqual(address, cached_address)
        print(f"Live InstanceInfo address: 0x{cached_address:08X}")

    def test_reads_live_instance_info_and_nested_map(self) -> None:
        """Read the root structure and its current area metadata."""

        snapshot = self.context.read()
        self.assertIsNotNone(snapshot)
        assert snapshot is not None
        self.assertEqual(len(bytes(snapshot)), 0x14)
        print(f"Live instance type: {snapshot.instance_type}")

        area = snapshot.current_map_info
        if area is None:
            print("Live current map metadata is not available")
            return

        self.assertEqual(len(bytes(area)), 0x7C)
        self.assertEqual(
            area.file_id_1,
            ((int(area.file_id) - 1) % 0xFF00) + 0x100,
        )
        self.assertEqual(
            area.file_id_2,
            ((int(area.file_id) - 1) // 0xFF00) + 0x100,
        )
        print(
            "Live map info: "
            f"campaign={area.campaign}, region={area.region}, file_id={area.file_id}"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
