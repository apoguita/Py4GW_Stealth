"""Live Guild Wars tests for the external Camera reader."""

from __future__ import annotations

import math
import unittest

from py4gw import (
    Camera,
    CameraStruct,
    PatternCatalog,
    ProcessMemoryReader,
    RemoteScanner,
    Win32,
)


class LiveCameraTests(unittest.TestCase):
    """Verify Camera resolution and read-only snapshots against a client."""

    @classmethod
    def setUpClass(cls) -> None:
        """Open the first discovered client with read-only access."""

        cls.win32 = Win32()
        clients = cls.win32.find_guild_wars()
        if not clients:
            raise unittest.SkipTest("Start Guild Wars before running this test.")

        cls.pid = int(clients[0]["pid"])
        module = cls.win32.get_main_module(cls.pid)
        cls.reader = ProcessMemoryReader(cls.win32, cls.pid)
        cls.scanner = RemoteScanner(
            cls.reader,
            int(module["base_address"]),
            int(module["size"]),
        )
        cls.scanner.initialize()
        cls.camera = Camera(
            cls.reader,
            cls.scanner,
            PatternCatalog.from_directory("offsets"),
        )

    @classmethod
    def tearDownClass(cls) -> None:
        """Close the selected process handle after the live checks."""

        if hasattr(cls, "reader"):
            cls.reader.close()

    def test_resolves_live_camera(self) -> None:
        """The maintained JSON resolver locates the native camera object."""

        address = self.camera.resolve_address()
        self.assertIsNotNone(address)
        self.assertGreater(address or 0, 0)
        self.assertEqual(address, self.camera.cached_context_address)
        print(f"Live Camera: 0x{address or 0:08X}")

    def test_reads_live_camera_snapshot(self) -> None:
        """A live snapshot exposes the maintained camera values."""

        snapshot = self.camera.read()
        self.assertIsNotNone(snapshot)
        assert snapshot is not None
        self.assertIsInstance(snapshot, CameraStruct)
        self.assertGreaterEqual(int(snapshot.look_at_agent_id), 0)
        self.assertTrue(math.isfinite(float(snapshot.distance)))
        self.assertTrue(math.isfinite(float(snapshot.yaw)))
        self.assertTrue(math.isfinite(float(snapshot.pitch)))
        print(
            "Live camera: "
            f"agent={snapshot.look_at_agent_id}, "
            f"yaw={snapshot.yaw:.3f}, pitch={snapshot.pitch:.3f}, "
            f"distance={snapshot.distance:.3f}"
        )

    def test_source_facade_getters_and_disabled_actions(self) -> None:
        """Source facade getters read remotely; action wrappers never write."""

        snapshot = self.camera.camera_instance()
        self.assertEqual(self.camera.GetLookAtAgentID(), snapshot.look_at_agent_id)
        self.assertEqual(self.camera.GetYaw(), snapshot.yaw)
        self.assertEqual(self.camera.GetPitch(), snapshot.pitch)
        self.assertEqual(self.camera.GetDistance2(), snapshot.distance2)
        self.assertEqual(self.camera.GetPosition(), snapshot.camera_position)
        self.assertEqual(
            self.camera.GetCameraPositionToGo(),
            snapshot.camera_position_to_go_value,
        )
        self.assertEqual(self.camera.GetCameraUnlock(), snapshot.IsCameraUnlocked())
        with self.assertRaises(NotImplementedError):
            self.camera.SetYaw(0.25)
        with self.assertRaises(NotImplementedError):
            self.camera.SetCameraUnlock(True)
        with self.assertRaises(NotImplementedError):
            self.camera.ForwardMovement(1.0, True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
