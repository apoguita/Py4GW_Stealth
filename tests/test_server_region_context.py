"""Live Guild Wars tests for the external ServerRegion reader."""

from __future__ import annotations

import ctypes
import unittest

from py4gw import (
    PatternCatalog,
    ProcessMemoryReader,
    RemoteScanner,
    ServerRegion,
    ServerRegionStruct,
    Win32,
)


class LiveServerRegionTests(unittest.TestCase):
    """Verify ServerRegion against a running Guild Wars client."""

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
        cls.context = ServerRegion(
            cls.reader,
            cls.scanner,
            PatternCatalog.from_directory("offsets"),
        )

    @classmethod
    def tearDownClass(cls) -> None:
        """Close the selected process handle after the live checks."""

        if hasattr(cls, "reader"):
            cls.reader.close()

    def test_layout_matches_native_server_region(self) -> None:
        """Keep the fixed-width layout aligned with the native source."""

        self.assertEqual(ctypes.sizeof(ServerRegionStruct), 0x04)
        self.assertEqual(ServerRegionStruct.region_id.offset, 0x00)

    def test_resolves_live_server_region_pointer(self) -> None:
        """Resolve and cache the JSON region-value address."""

        address = self.context.resolve_address()
        pointer_address = self.context.cached_pointer_address or 0
        self.assertGreater(pointer_address, 0)
        if address is not None:
            self.assertEqual(address, pointer_address)
            print(f"Live ServerRegion address: 0x{address:08X}")

    def test_reads_live_server_region(self) -> None:
        """Read the current signed server-region enum value."""

        snapshot = self.context.read()
        if snapshot is None:
            print("ServerRegion is not active")
            return

        self.assertEqual(len(bytes(snapshot)), 0x04)
        self.assertGreaterEqual(snapshot.region_id, -2)
        print(f"Live server region id: {snapshot.region_id}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
