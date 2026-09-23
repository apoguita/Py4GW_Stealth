"""Offline layout checks for the external Camera reader."""

from __future__ import annotations

import ctypes
import unittest

from py4gw import CameraStruct


class CameraLayoutTests(unittest.TestCase):
    """Check the fixed-width camera layout and read-only helpers."""

    def test_layout_matches_native_offsets(self) -> None:
        """The maintained native fields retain their x86 offsets."""

        self.assertEqual(ctypes.sizeof(CameraStruct), 0x120)
        self.assertEqual(CameraStruct.position.offset, 0x78)
        self.assertEqual(CameraStruct.look_at_target.offset, 0xA8)
        self.assertEqual(CameraStruct.field_of_view.offset, 0xC0)
        self.assertEqual(CameraStruct.camera_mode.offset, 0x11C)
        self.assertEqual(CameraStruct.yaw_right_click2.offset, 0x38)
        self.assertEqual(CameraStruct.distance2.offset, 0x40)
        self.assertEqual(CameraStruct.camera_pos_to_go.offset, 0x84)
        self.assertEqual(CameraStruct.h00D8.offset, 0xD8)
        self.assertEqual(CameraStruct.h0118.offset, 0x118)
        self.assertEqual(
            [field[0] for field in CameraStruct._fields_],
            [
                "look_at_agent_id", "h0004", "h0008", "h000C", "max_distance",
                "h0014", "yaw", "pitch", "distance", "h0024",
                "yaw_right_click", "yaw_right_click2", "pitch_right_click",
                "distance2", "acceleration_constant",
                "time_since_last_keyboard_rotation",
                "time_since_last_mouse_rotation", "time_since_last_mouse_move",
                "time_since_last_agent_selection", "time_in_the_map",
                "time_in_the_district", "yaw_to_go", "pitch_to_go", "dist_to_go",
                "max_distance2", "h0070", "position", "camera_pos_to_go",
                "cam_pos_inverted", "cam_pos_inverted_to_go", "look_at_target",
                "look_at_to_go", "field_of_view", "field_of_view2", "h00C8",
                "h00CC", "h00D0", "h00D4", "h00D8", "h00DC", "h00E0",
                "h00E4", "h00E8", "h00EC", "h00F0", "h00F4", "h00F8",
                "h00FC", "h0100", "h0104", "h0108", "h010C", "h0110",
                "h0114", "h0118", "camera_mode",
            ],
        )

    def test_unlocked_mode_property(self) -> None:
        """Camera mode three is reported as the native unlocked mode."""

        camera = CameraStruct()
        camera.camera_mode = 3
        self.assertTrue(camera.is_unlocked)
        camera.camera_mode = 2
        self.assertFalse(camera.is_unlocked)

    def test_read_only_source_helpers(self) -> None:
        """Computed camera values match the native/Reforged formulas."""

        camera = CameraStruct()
        camera.position.x = 1.0
        camera.position.y = 0.0
        camera.position.z = 3.0
        camera.look_at_target.x = 0.0
        camera.look_at_target.y = 0.0
        camera.look_at_target.z = 0.0
        camera.distance = 42.0
        camera.distance2 = 7.0
        camera.field_of_view2 = 1.5

        self.assertAlmostEqual(camera.current_yaw, -3.141592741)
        self.assertAlmostEqual(camera.GetCurrentYaw(), camera.current_yaw)
        self.assertEqual(camera.GetYaw(), 0.0)
        self.assertEqual(camera.GetPitch(), 0.0)
        self.assertEqual(camera.GetFieldOfView(), 0.0)
        self.assertTrue(camera.GetLookAtTarget() is not camera.look_at_target)
        self.assertEqual(camera.camera_zoom, 42.0)
        self.assertEqual(camera.GetCameraZoom(), 42.0)
        self.assertEqual(camera.distance2, 7.0)
        self.assertEqual(camera.field_of_view2, 1.5)
        self.assertEqual(camera.camera_position, (1.0, 0.0, 3.0))
        self.assertEqual(camera.look_at_target_value, (0.0, 0.0, 0.0))

    def test_native_mutators_are_declared_but_not_enabled(self) -> None:
        """Source setter names cannot write to the external client process."""

        camera = CameraStruct()
        with self.assertRaises(NotImplementedError):
            camera.SetYaw(1.0)
        with self.assertRaises(NotImplementedError):
            camera.SetPitch(1.0)
        with self.assertRaises(NotImplementedError):
            camera.SetCameraPos(camera.position)
        with self.assertRaises(NotImplementedError):
            camera.SetLookAtTarget(camera.look_at_target)


if __name__ == "__main__":
    unittest.main(verbosity=2)
