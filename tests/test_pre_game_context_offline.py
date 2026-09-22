"""Offline declaration and behavior checks for the PreGameContext port."""

from __future__ import annotations

import ctypes
import unittest

from py4gw.context.pre_game_context import (
    LoginCharacter,
    PreGameContext,
    PreGameContextStruct,
)


class PreGameContextParityTests(unittest.TestCase):
    """Check every source-defined field and source-visible member."""

    def test_login_character_layout_matches_source(self) -> None:
        expected_offsets = {
            "appearance_packed": 0x00,
            "pvp_flag": 0x04,
            "guild_guid_0": 0x08,
            "guild_guid_1": 0x0C,
            "guild_guid_2": 0x10,
            "guild_guid_3": 0x14,
            "items_data": 0x18,
            "items_capacity": 0x1C,
            "items_count": 0x20,
            "items_param": 0x24,
            "level": 0x28,
            "current_map_id": 0x2C,
            "field_0x30": 0x30,
            "primary_profession": 0x34,
            "profession_enum": 0x38,
            "field_0x3C": 0x3C,
            "field_0x40": 0x40,
            "field_0x44": 0x44,
            "field_0x48": 0x48,
            "char_model_ptr": 0x4C,
            "character_name_enc": 0x50,
        }
        self.assertEqual(ctypes.sizeof(LoginCharacter), 0x78)
        self.assertEqual(
            [field[0] for field in LoginCharacter._fields_],
            list(expected_offsets),
        )
        for name, offset in expected_offsets.items():
            self.assertEqual(getattr(LoginCharacter, name).offset, offset, name)

    def test_pre_game_layout_matches_source(self) -> None:
        expected_offsets = {
            "frame_id": 0x00,
            "scene_type": 0x04,
            "scene_controller_iface": 0x08,
            "camera_pitch_frequency": 0x0C,
            "camera_pitch_current": 0x10,
            "camera_pitch_target": 0x14,
            "camera_pitch_velocity": 0x18,
            "RESERVED_0x1C": 0x1C,
            "camera_mode": 0x4C,
            "RESERVED_0x50": 0x50,
            "RESERVED_0x64": 0x64,
            "camera_limits_frequency": 0x68,
            "camera_limits_min_current": 0x6C,
            "camera_limits_max_current": 0x70,
            "camera_limits_min_target": 0x74,
            "camera_limits_max_target": 0x78,
            "camera_limits_min_velocity": 0x7C,
            "camera_limits_max_velocity": 0x80,
            "scroll_offset_frequency": 0x84,
            "scroll_offset_current": 0x88,
            "scroll_offset_target": 0x8C,
            "scroll_offset_velocity": 0x90,
            "scroll_speed_frequency": 0x94,
            "scroll_speed_current": 0x98,
            "scroll_speed_target": 0x9C,
            "scroll_speed_velocity": 0xA0,
            "camera_height": 0xA4,
            "camera_height_min": 0xA8,
            "camera_height_max": 0xAC,
            "camera_rotation_frequency": 0xB0,
            "camera_rotation_current": 0xB4,
            "camera_rotation_target": 0xB8,
            "camera_rotation_velocity": 0xBC,
            "RESERVED_0xC0": 0xC0,
            "max_characters": 0xD0,
            "chosen_character_index": 0xD4,
            "preview_character_index": 0xD8,
            "pending_character_index": 0xDC,
            "chars_array": 0xE0,
            "char_creation_flag": 0xEC,
            "create_slot_index": 0xF0,
            "sentinel_guard": 0xF4,
            "self_link": 0xF8,
            "list_head": 0xFC,
        }
        self.assertEqual(ctypes.sizeof(PreGameContextStruct), 0x100)
        self.assertEqual(
            [field[0] for field in PreGameContextStruct._fields_],
            list(expected_offsets),
        )
        for name, offset in expected_offsets.items():
            self.assertEqual(getattr(PreGameContextStruct, name).offset, offset, name)

    def test_login_character_properties_match_source_semantics(self) -> None:
        character = LoginCharacter()
        character.guild_guid_0 = 0x11223344
        character.guild_guid_1 = 0x55667788
        character.guild_guid_2 = 0x99AABBCC
        character.guild_guid_3 = 0xDDEEFF00
        encoded = "A\x01B\x00".encode("utf-16-le")
        ctypes.memmove(
            ctypes.addressof(character)
            + LoginCharacter.character_name_enc.offset,
            encoded,
            len(encoded),
        )
        self.assertEqual(
            character.guild_guid,
            bytes.fromhex("4433221188776655ccbbaa9900ffeedd"),
        )
        self.assertEqual(character.character_name_str, "A\x01B")
        self.assertEqual(character.character_name, "A\\x0001B")

    def test_source_facade_members_are_declared(self) -> None:
        for name in ("get_ptr", "_update_ptr", "enable", "disable", "get_context"):
            self.assertTrue(hasattr(PreGameContext, name), name)

    def test_callback_enable_is_explicitly_external_unavailable(self) -> None:
        with self.assertRaises(NotImplementedError):
            PreGameContext.enable()

    def test_static_facade_refresh_has_source_state_semantics_without_client(self) -> None:
        PreGameContext.disable()
        PreGameContext._update_ptr()
        self.assertEqual(PreGameContext.get_ptr(), 0)
        self.assertIsNone(PreGameContext.get_context())


if __name__ == "__main__":
    unittest.main(verbosity=2)
