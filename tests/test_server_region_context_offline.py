"""Offline declaration and layout checks for the ServerRegion port."""

from __future__ import annotations

import ctypes
import unittest

from py4gw.context.server_region_context import ServerRegion, ServerRegionStruct


class ServerRegionParityTests(unittest.TestCase):
    """Check the complete source declaration and facade surface."""

    def test_layout_matches_source(self) -> None:
        self.assertEqual(ctypes.sizeof(ServerRegionStruct), 0x04)
        self.assertEqual(
            [field[0] for field in ServerRegionStruct._fields_], ["region_id"]
        )
        self.assertEqual(getattr(ServerRegionStruct, "region_id").offset, 0x00)

    def test_source_facade_members_are_declared(self) -> None:
        for name in ("get_ptr", "_update_ptr", "enable", "disable", "get_context"):
            self.assertTrue(hasattr(ServerRegion, name), name)

    def test_callback_enable_is_explicitly_external_unavailable(self) -> None:
        with self.assertRaises(NotImplementedError):
            ServerRegion.enable()

    def test_static_facade_refresh_has_source_state_semantics_without_client(self) -> None:
        ServerRegion.disable()
        ServerRegion._update_ptr()
        self.assertEqual(ServerRegion.get_ptr(), 0)
        self.assertIsNone(ServerRegion.get_context())


if __name__ == "__main__":
    unittest.main(verbosity=2)
