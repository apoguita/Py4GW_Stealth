"""Offline declaration and layout checks for the Cinematic port."""

from __future__ import annotations

import ctypes
import unittest

from py4gw.context.cinematic_context import Cinematic, CinematicStruct


class CinematicParityTests(unittest.TestCase):
    """Check the complete source declaration and facade surface."""

    def test_layout_matches_source(self) -> None:
        expected_offsets = {"h0000": 0x00, "h0004": 0x04}
        self.assertEqual(ctypes.sizeof(CinematicStruct), 0x08)
        self.assertEqual(
            [field[0] for field in CinematicStruct._fields_],
            list(expected_offsets),
        )
        for name, offset in expected_offsets.items():
            self.assertEqual(getattr(CinematicStruct, name).offset, offset, name)

    def test_source_facade_members_are_declared(self) -> None:
        for name in ("get_ptr", "_update_ptr", "enable", "disable", "get_context"):
            self.assertTrue(hasattr(Cinematic, name), name)

    def test_callback_enable_is_explicitly_external_unavailable(self) -> None:
        with self.assertRaises(NotImplementedError):
            Cinematic.enable()

    def test_static_facade_refresh_has_source_state_semantics_without_client(self) -> None:
        Cinematic.disable()
        Cinematic._update_ptr()
        self.assertEqual(Cinematic.get_ptr(), 0)
        self.assertIsNone(Cinematic.get_context())


if __name__ == "__main__":
    unittest.main(verbosity=2)
