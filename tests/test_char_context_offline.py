"""Offline declaration and behavior checks for the CharContext port."""

from __future__ import annotations

import ctypes
import unittest

from py4gw.context.char_context import (
    CharContext,
    CharContextStruct,
    ObserverMatch,
    ObserverMatchFlags,
    ProgressBar,
)


class CharContextParityTests(unittest.TestCase):
    """Check the source layout and source-visible property surface."""

    def test_structure_sizes_and_offsets_match_source(self) -> None:
        self.assertEqual(ctypes.sizeof(ObserverMatchFlags), 0x38)
        self.assertEqual(ctypes.sizeof(ObserverMatch), 0x78)
        self.assertEqual(ctypes.sizeof(ProgressBar), 0x2C)
        self.assertEqual(ctypes.sizeof(CharContextStruct), 0x448)
        expected_offsets = {
            "h0000_array": 0x0000,
            "h0010": 0x0010,
            "h0014_array": 0x0014,
            "h0024": 0x0024,
            "h0034_array": 0x0034,
            "h0044_array": 0x0044,
            "h0054": 0x0054,
            "player_uuid_ptr": 0x0064,
            "player_name_enc": 0x0074,
            "h009C": 0x009C,
            "h00EC_array": 0x00EC,
            "h00FC": 0x00FC,
            "world_flags": 0x0190,
            "token1": 0x0194,
            "map_id": 0x0198,
            "is_explorable": 0x019C,
            "host": 0x01A0,
            "token2": 0x01B8,
            "h01BC": 0x01BC,
            "district_number": 0x0228,
            "language": 0x022C,
            "observe_map_id": 0x0230,
            "current_map_id": 0x0234,
            "observe_map_type": 0x0238,
            "current_map_type": 0x023C,
            "h0240": 0x0240,
            "observer_matches_array": 0x0254,
            "h0264": 0x0264,
            "player_flags": 0x02A8,
            "player_number": 0x02AC,
            "h02B0": 0x02B0,
            "progress_bar_ptr": 0x0350,
            "h0354": 0x0354,
            "player_email_ptr": 0x03C8,
        }
        self.assertEqual(
            [field[0] for field in CharContextStruct._fields_],
            list(expected_offsets),
        )
        for name, offset in expected_offsets.items():
            self.assertEqual(getattr(CharContextStruct, name).offset, offset, name)

    def test_source_facade_members_are_declared(self) -> None:
        for name in ("get_ptr", "_update_ptr", "enable", "disable", "get_context"):
            self.assertTrue(hasattr(CharContext, name), name)

    def test_encoded_and_display_properties_preserve_source_order(self) -> None:
        snapshot = CharContextStruct()
        encoded = "A\x01B\x00".encode("utf-16-le")
        ctypes.memmove(
            ctypes.addressof(snapshot)
            + getattr(CharContextStruct, "player_name_enc").offset,
            encoded,
            len(encoded),
        )
        self.assertEqual(snapshot.player_name_encoded_str, "A\x01B")
        self.assertEqual(snapshot.player_name_str, "A\\x0001B")

    def test_callback_enable_is_explicitly_external_unavailable(self) -> None:
        with self.assertRaises(NotImplementedError):
            CharContext.enable()

    def test_static_facade_refresh_has_source_state_semantics_without_client(self) -> None:
        CharContext.disable()
        CharContext._update_ptr()
        self.assertEqual(CharContext.get_ptr(), 0)
        self.assertIsNone(CharContext.get_context())


if __name__ == "__main__":
    unittest.main(verbosity=2)
