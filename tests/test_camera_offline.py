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
        camera.distance_2 = 7.0
        camera.field_of_view_2 = 1.5

        self.assertAlmostEqual(camera.current_yaw, -3.141592653589793)
        self.assertEqual(camera.camera_zoom, 42.0)
        self.assertEqual(camera.distance2, 7.0)
        self.assertEqual(camera.field_of_view2, 1.5)
        self.assertEqual(camera.camera_position, (1.0, 0.0, 3.0))
        self.assertEqual(camera.look_at_target_value, (0.0, 0.0, 0.0))


if __name__ == "__main__":
    unittest.main(verbosity=2)
