"""Live read-only checks for the external GadgetContext root."""

from __future__ import annotations

import unittest

from py4gw import GadgetContext, GameContext, PatternCatalog, ProcessMemoryReader, RemoteScanner, Win32


class LiveGadgetContextTests(unittest.TestCase):
    """Verify the direct GameContext pointer and the complete gadget array."""

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
            cls.reader, int(module["base_address"]), int(module["size"])
        )
        cls.scanner.initialize()
        cls.game_context = GameContext(
            cls.reader, cls.scanner, PatternCatalog.from_directory("offsets")
        )
        cls.game_context.initialize()
        cls.context = GadgetContext(cls.reader, cls.game_context)

    @classmethod
    def tearDownClass(cls) -> None:
        """Close the selected process handle."""

        if hasattr(cls, "reader"):
            cls.reader.close()

    def test_reads_gadget_root(self) -> None:
        """Read every advertised GadgetInfo record from the live client."""

        address = self.context.resolve_address()
        if address is None:
            self.skipTest("The client has no active GadgetContext.")
        snapshot = self.context.read()
        self.assertIsNotNone(snapshot)
        if snapshot is None:
            return
        records = snapshot.gadget_infos()
        self.assertEqual(len(records), snapshot.array_size)
        print(
            "Live GadgetContext: "
            f"0x{address:08X}, advertised={snapshot.array_size}, "
            f"read={len(records)}"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
