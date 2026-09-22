"""Offline parity checks for the external ``InstanceInfo`` reader."""

from __future__ import annotations

import unittest

import ctypes

from py4gw import AreaInfoStruct, InstanceInfo, InstanceInfoStruct, MapDimensionsStruct


class InstanceInfoParityTests(unittest.TestCase):
    """Check every source-defined layout, property, and facade member."""

    def test_source_layouts_and_offsets(self) -> None:
        map_fields = {
            "unk": 0x00,
            "start_x": 0x04,
            "start_y": 0x08,
            "end_x": 0x0C,
            "end_y": 0x10,
            "unk1": 0x14,
        }
        area_fields = {
            "campaign": 0x00,
            "continent": 0x04,
            "region": 0x08,
            "type": 0x0C,
            "flags": 0x10,
            "thumbnail_id": 0x14,
            "min_party_size": 0x18,
            "max_party_size": 0x1C,
            "min_player_size": 0x20,
            "max_player_size": 0x24,
            "controlled_outpost_id": 0x28,
            "fraction_mission": 0x2C,
            "min_level": 0x30,
            "max_level": 0x34,
            "needed_pq": 0x38,
            "mission_maps_to": 0x3C,
            "x": 0x40,
            "y": 0x44,
            "icon_start_x": 0x48,
            "icon_start_y": 0x4C,
            "icon_end_x": 0x50,
            "icon_end_y": 0x54,
            "icon_start_x_dupe": 0x58,
            "icon_start_y_dupe": 0x5C,
            "icon_end_x_dupe": 0x60,
            "icon_end_y_dupe": 0x64,
            "file_id": 0x68,
            "mission_chronology": 0x6C,
            "ha_map_chronology": 0x70,
            "name_id": 0x74,
            "description_id": 0x78,
        }
        instance_fields = {
            "terrain_info1_ptr": 0x00,
            "instance_type": 0x04,
            "current_map_info_ptr": 0x08,
            "terrain_count": 0x0C,
            "terrain_info2_ptr": 0x10,
        }
        self.assertEqual(ctypes.sizeof(MapDimensionsStruct), 0x18)
        self.assertEqual(ctypes.sizeof(AreaInfoStruct), 0x7C)
        self.assertEqual(ctypes.sizeof(InstanceInfoStruct), 0x14)
        for structure, expected in (
            (MapDimensionsStruct, map_fields),
            (AreaInfoStruct, area_fields),
            (InstanceInfoStruct, instance_fields),
        ):
            self.assertEqual(
                [field[0] for field in structure._fields_], list(expected)
            )
            for name, offset in expected.items():
                self.assertEqual(getattr(structure, name).offset, offset, name)

    def test_file_id_aliases_match_reforged_names(self) -> None:
        """Both public spellings must return the same derived identifiers."""

        area = AreaInfoStruct()
        area.file_id = 0x12345

        self.assertEqual(area.file_id1, area.file_id_1)
        self.assertEqual(area.file_id2, area.file_id_2)

    def test_area_flag_properties_match_native_masks(self) -> None:
        area = AreaInfoStruct()
        area.flags = 0x100 | 0x20 | 0x40001 | 0x800000 | 0x10000000 | 0x10000 | 0x8000000
        self.assertTrue(area.has_enter_button)
        self.assertFalse(area.is_on_world_map)
        self.assertTrue(area.is_pvp)
        self.assertTrue(area.is_guild_hall)
        self.assertTrue(area.is_vanquishable_area)
        self.assertTrue(area.is_unlockable)
        self.assertTrue(area.has_mission_maps_to)

    def test_nested_pointer_properties_are_declared(self) -> None:
        for name in ("terrain_info1", "current_map_info", "terrain_info2"):
            self.assertTrue(hasattr(InstanceInfoStruct, name), name)
        snapshot = InstanceInfoStruct()
        self.assertIsNone(snapshot.terrain_info1)
        self.assertIsNone(snapshot.current_map_info)
        self.assertIsNone(snapshot.terrain_info2)

    def test_source_facade_members_are_declared(self) -> None:
        for name in ("get_ptr", "_update_ptr", "enable", "disable", "get_context"):
            self.assertTrue(hasattr(InstanceInfo, name), name)

    def test_callback_enable_is_explicitly_external_unavailable(self) -> None:
        with self.assertRaises(NotImplementedError):
            InstanceInfo.enable()

    def test_static_facade_refresh_has_source_state_semantics_without_client(self) -> None:
        InstanceInfo.disable()
        InstanceInfo._update_ptr()
        self.assertEqual(InstanceInfo.get_ptr(), 0)
        self.assertIsNone(InstanceInfo.get_context())


if __name__ == "__main__":
    unittest.main(verbosity=2)
