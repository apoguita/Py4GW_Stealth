"""Offline declaration and layout checks for the GameplayContext port."""

from __future__ import annotations

import ctypes
import unittest

from py4gw.context.gameplay_context import GameplayContext, GameplayContextStruct


class GameplayContextParityTests(unittest.TestCase):
    """Check the complete source declaration and facade surface."""

    def test_layout_matches_source(self) -> None:
        expected_offsets = {
            "h0000": 0x00,
            "mission_map_zoom": 0x4C,
            "unk": 0x50,
        }
        self.assertEqual(ctypes.sizeof(GameplayContextStruct), 0x78)
        self.assertEqual(
            [field[0] for field in GameplayContextStruct._fields_],
            list(expected_offsets),
        )
        for name, offset in expected_offsets.items():
            self.assertEqual(getattr(GameplayContextStruct, name).offset, offset, name)

    def test_source_facade_members_are_declared(self) -> None:
        for name in ("get_ptr", "_update_ptr", "enable", "disable", "get_context"):
            self.assertTrue(hasattr(GameplayContext, name), name)

    def test_callback_enable_is_explicitly_external_unavailable(self) -> None:
        with self.assertRaises(NotImplementedError):
            GameplayContext.enable()

    def test_static_facade_refresh_has_source_state_semantics_without_client(self) -> None:
        GameplayContext.disable()
        GameplayContext._update_ptr()
        self.assertEqual(GameplayContext.get_ptr(), 0)
        self.assertIsNone(GameplayContext.get_context())


if __name__ == "__main__":
    unittest.main(verbosity=2)
