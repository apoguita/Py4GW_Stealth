"""Offline source-parity checks for the available-character roster."""

from __future__ import annotations

import ctypes
import unittest

from py4gw import (
    AvailableCharacterArray,
    AvailableCharacterArrayStruct,
    AvailableCharacterInfoStruct,
    AvailableCharacterStruct,
)


class AvailableCharacterParityTests(unittest.TestCase):
    """Keep the external record source-compatible with Reforged."""

    def test_source_record_alias_and_layout(self) -> None:
        """The source record name must refer to the same fixed-width layout."""

        self.assertIs(AvailableCharacterStruct, AvailableCharacterInfoStruct)
        self.assertEqual(ctypes.sizeof(AvailableCharacterStruct), 0x84)
        self.assertEqual(ctypes.sizeof(AvailableCharacterArrayStruct), 0x10)
        self.assertEqual(
            [field[0] for field in AvailableCharacterStruct._fields_],
            ["h0000", "uuid_ptr", "player_name_enc", "props"],
        )
        self.assertEqual(
            getattr(AvailableCharacterStruct, "h0000").offset, 0x00
        )
        self.assertEqual(
            getattr(AvailableCharacterStruct, "uuid_ptr").offset, 0x08
        )
        self.assertEqual(
            getattr(AvailableCharacterStruct, "player_name_enc").offset, 0x18
        )
        self.assertEqual(getattr(AvailableCharacterStruct, "props").offset, 0x40)
        self.assertEqual(
            [field[0] for field in AvailableCharacterArrayStruct._fields_],
            ["available_characters_array"],
        )

    def test_source_property_names(self) -> None:
        """UUID and encoded-name aliases expose the source-facing values."""

        character = AvailableCharacterStruct()
        character.uuid_ptr[:] = (1, 2, 3, 4)
        character.player_name_enc[:5] = (ord("A"), ord("p"), ord("o"), 0, 0)

        self.assertEqual(character.uuid, (1, 2, 3, 4))
        self.assertEqual(character.player_name_encoded_string, "Apo")
        self.assertEqual(character.player_name, character.player_name_str)

    def test_packed_properties_match_native_bit_rules(self) -> None:
        character = AvailableCharacterStruct()
        character.props[0] = 449 << 16
        character.props[2] = 3 << 20
        character.props[7] = 5 | (20 << 4) | (7 << 10)
        self.assertEqual(character.map_id, 449)
        self.assertEqual(character.primary, 3)
        self.assertEqual(character.secondary, 7)
        self.assertEqual(character.campaign, 5)
        self.assertEqual(character.level, 20)
        self.assertFalse(character.is_pvp)
        character.props[7] |= 1 << 9
        self.assertEqual(character.level, (int(character.props[7]) >> 4) & 0x3F)
        self.assertTrue(character.is_pvp)

    def test_source_array_and_facade_members_are_declared(self) -> None:
        for name in ("available_characters_list", "characters"):
            self.assertTrue(hasattr(AvailableCharacterArrayStruct, name), name)
        for name in ("get_ptr", "_update_ptr", "enable", "disable", "get_context"):
            self.assertTrue(hasattr(AvailableCharacterArray, name), name)

    def test_callback_enable_is_explicitly_external_unavailable(self) -> None:
        with self.assertRaises(NotImplementedError):
            AvailableCharacterArray.enable()

    def test_static_facade_refresh_has_source_state_semantics_without_client(self) -> None:
        AvailableCharacterArray.disable()
        AvailableCharacterArray._update_ptr()
        self.assertEqual(AvailableCharacterArray.get_ptr(), 0)
        self.assertIsNone(AvailableCharacterArray.get_context())


if __name__ == "__main__":
    unittest.main(verbosity=2)
