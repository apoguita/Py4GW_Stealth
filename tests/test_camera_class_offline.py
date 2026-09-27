"""``Camera``, the class: the whole surface, and where each member's work lands.

The class is the port of Reforged's ``Py4GWCoreLib/Camera.py`` (46 members) over Native's
``GW::Context::Camera``. A client is needed only for the *value* of the record and the two patch
addresses, so a fixture supplies both: a real ``CameraStruct`` with its fields set, and a stand-in client
whose bridge records what a write asked the payload to do.

The checks are the source's own claims: every member present with no raising body (from the module's
``ast``, as every class here is checked), each getter answering its field, ``GetCurrentYaw`` and
``IsPointInFOV`` following ``Camera.py``'s arithmetic term for term, and each action naming **the field
the source writes** — ``SetYaw`` writes ``yaw`` *and* ``yaw_to_go``, ``SetPitch`` writes ``pitch_to_go``
only, ``SetMaxDist`` writes ``max_distance2`` (``camera.h:80-117``, ``camera_methods.cpp:78-94``).

The context struct's own layout and helpers are covered beside this file, in ``test_camera_offline.py``.
"""

from __future__ import annotations

import ast
import math
import pathlib
import struct
import unittest
from unittest import mock

from py4gw import camera as camera_module
from py4gw.camera import Camera
from py4gw.context.camera_context import CameraStruct
from py4gw.game_thread.shared_block import Operation

MODULE_PATH = pathlib.Path(__file__).resolve().parent.parent / "py4gw" / "camera.py"


def _camera_struct() -> CameraStruct:
    """A camera record with every field a member reads set to something recognisable."""

    camera = CameraStruct()
    camera.look_at_agent_id = 25
    camera.max_distance = 1100.0
    camera.yaw = 0.5
    camera.pitch = 0.25
    camera.distance = 900.0
    camera.yaw_right_click = 0.75
    camera.yaw_right_click2 = 0.875
    camera.pitch_right_click = -0.125
    camera.distance2 = 810000.0
    camera.acceleration_constant = 12.5
    camera.time_since_last_keyboard_rotation = 1.5
    camera.time_since_last_mouse_rotation = 2.5
    camera.time_since_last_mouse_move = 3.5
    camera.time_since_last_agent_selection = 4.5
    camera.time_in_the_map = 60.0
    camera.time_in_the_district = 30.0
    camera.yaw_to_go = 0.625
    camera.pitch_to_go = 0.375
    camera.dist_to_go = 850.0
    camera.max_distance2 = 1200.0
    camera.position.x, camera.position.y, camera.position.z = 10.0, 20.0, 30.0
    camera.camera_pos_to_go.x, camera.camera_pos_to_go.y, camera.camera_pos_to_go.z = 1.0, 2.0, 3.0
    camera.cam_pos_inverted.x, camera.cam_pos_inverted.y, camera.cam_pos_inverted.z = -1.0, -2.0, -3.0
    camera.cam_pos_inverted_to_go.x = -4.0
    camera.cam_pos_inverted_to_go.y = -5.0
    camera.cam_pos_inverted_to_go.z = -6.0
    camera.look_at_target.x, camera.look_at_target.y, camera.look_at_target.z = 40.0, 50.0, 60.0
    camera.look_at_to_go.x, camera.look_at_to_go.y, camera.look_at_to_go.z = 7.0, 8.0, 9.0
    camera.field_of_view = 1.5
    camera.field_of_view2 = 2.25
    camera.camera_mode = 3
    return camera


class _FakeBridge:
    """The bridge surface a camera write uses: the data region, and one published command."""

    def __init__(self) -> None:
        self.writes: list[tuple[int, bytes]] = []
        self.commands: list[tuple[Operation, int, int, int]] = []

    def write_data(self, offset: int, payload: bytes) -> int:
        self.writes.append((offset, bytes(payload)))
        return 0x70000000 + offset

    def submit(self, operation, arg0=0, arg1=0, arg2=0, arg3=0, arg4=0, arg5=0, timeout_ms=None):
        self.commands.append((Operation(operation), arg0, arg1, arg2))
        return None


class _FakeAccess:
    """The write transport the patch path reads the client's own bytes through."""

    def __init__(self, contents: bytes) -> None:
        self.contents = contents

    def read(self, address: int, size: int) -> bytes:
        return self.contents[:size]


class _FakeCameraReader:
    """The ported context's own two calls, which is all ``Camera`` asks of it."""

    def __init__(self, camera: CameraStruct) -> None:
        self._camera = camera
        self.address = 0x00A00000

    def resolve_address(self) -> int:
        return self.address

    def camera_instance(self) -> CameraStruct:
        return self._camera


class _FakeResolution:
    """One resolver answer, with the attempt name native reads for the patch bytes."""

    def __init__(self, value: int, attempt: str) -> None:
        self.ok = True
        self.value = value
        self.selected_attempt = attempt
        self.message = ""


class _FakeCatalog:
    """The two patch addresses, as the catalog answers them."""

    def __init__(self) -> None:
        self.addresses = {
            "camera.fog_patch_addr": 0x00512000,
            "camera.camera_update_patch_addr": 0x00513000,
        }

    def resolve(self, name: str, scanner: object) -> _FakeResolution:
        attempt = "vs2017" if name.endswith("camera_update_patch_addr") else "default"
        return _FakeResolution(self.addresses[name], attempt)


class _FakeClient:
    """A client stand-in: the camera facade, the bridge, the transport, and the catalog."""

    def __init__(self, camera: CameraStruct, contents: bytes = b"\x55\x8B") -> None:
        self.camera = _FakeCameraReader(camera)
        self.bridge = _FakeBridge()
        self.access = _FakeAccess(contents)
        self.pid = 4242
        self._patterns = _FakeCatalog()
        self._scanner = object()


class CameraSurfaceTests(unittest.TestCase):
    """The class is whole, and nothing in it raises."""

    def test_every_source_member_is_present(self) -> None:
        source = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
        members = {
            node.name
            for node in ast.walk(source)
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("_")
        }
        self.assertEqual(len(members), 46, f"the source declares 46: {sorted(members)}")
        for name in ("camera_instance", "GetCurrentYaw", "IsPointInFOV", "SetFog", "UpdateCameraPos"):
            self.assertIn(name, members)

    def test_no_member_raises_not_implemented(self) -> None:
        """Zero raisers, from this module's own body — the check every class here carries."""

        source = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
        raisers = []
        for node in ast.walk(source):
            if not isinstance(node, ast.FunctionDef) or node.name.startswith("_"):
                continue
            for inner in ast.walk(node):
                if isinstance(inner, ast.Name) and inner.id in ("NotImplementedError", "_unported"):
                    raisers.append(node.name)
        self.assertEqual(raisers, [])


class CameraReadTests(unittest.TestCase):
    """Every getter answers the field the source names."""

    def setUp(self) -> None:
        self.camera = _camera_struct()
        self.client = _FakeClient(self.camera)
        patcher = mock.patch("py4gw.camera.require_client", return_value=self.client)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_the_scalar_getters_are_their_fields(self) -> None:
        self.assertEqual(Camera.GetLookAtAgentID(), 25)
        self.assertEqual(Camera.GetMaxDistance(), 1100.0)
        self.assertEqual(Camera.GetYaw(), 0.5)
        self.assertEqual(Camera.GetPitch(), 0.25)
        self.assertEqual(Camera.GetCameraZoom(), 900.0, "camera.h:103: the zoom is ``distance``")
        self.assertEqual(Camera.GetYawRightClick(), 0.75)
        self.assertEqual(Camera.GetYawRightClick2(), 0.875)
        self.assertEqual(Camera.GetPitchRightClick(), -0.125)
        self.assertEqual(Camera.GetDistance2(), 810000.0)
        self.assertEqual(Camera.GetAccelerationConstant(), 12.5)
        self.assertEqual(Camera.GetTimeSinceLastKeyboardRotation(), 1.5)
        self.assertEqual(Camera.GetTimeSinceLastMouseRotation(), 2.5)
        self.assertEqual(Camera.GetTimeSinceLastMouseMove(), 3.5)
        self.assertEqual(Camera.GetTimeSinceLastAgentSelection(), 4.5)
        self.assertEqual(Camera.GetTimeInTheMap(), 60.0)
        self.assertEqual(Camera.GetTimeInTheDistrict(), 30.0)
        self.assertEqual(Camera.GetYawToGo(), 0.625)
        self.assertEqual(Camera.GetPitchToGo(), 0.375)
        self.assertEqual(Camera.GetDistanceToGo(), 850.0)
        self.assertEqual(Camera.GetMaxDistance2(), 1200.0)
        self.assertEqual(Camera.GetFieldOfView(), 1.5)
        self.assertEqual(Camera.GetFielsOfView2(), 2.25)

    def test_the_vector_getters_are_three_tuples(self) -> None:
        self.assertEqual(Camera.GetPosition(), (10.0, 20.0, 30.0))
        self.assertEqual(Camera.GetCameraPositionToGo(), (1.0, 2.0, 3.0))
        self.assertEqual(Camera.GetCameraPositionInverted(), (-1.0, -2.0, -3.0))
        self.assertEqual(Camera.GetCameraPositionInvertedToGo(), (-4.0, -5.0, -6.0))
        self.assertEqual(Camera.GetLookAtTarget(), (40.0, 50.0, 60.0))
        self.assertEqual(Camera.GetAtTargetToGo(), (7.0, 8.0, 9.0))

    def test_the_current_yaw_is_the_sources_arithmetic(self) -> None:
        """``Camera.py:33-49``: the sign of the tangent decides which way pi is applied."""

        curtan = math.atan2(20.0 - 50.0, 10.0 - 40.0)
        expected = curtan - math.pi if curtan >= 0 else curtan + math.pi
        self.assertAlmostEqual(Camera.GetCurrentYaw(), expected, places=6)

    def test_a_point_inside_the_field_of_view_is_inside_it(self) -> None:
        cam_x, cam_y, _ = Camera.GetPosition()
        ahead = (cam_x + 100.0 * math.cos(0.5), cam_y + 100.0 * math.sin(0.5))
        behind = (cam_x - 100.0 * math.cos(0.5), cam_y - 100.0 * math.sin(0.5))
        self.assertTrue(Camera.IsPointInFOV(*ahead))
        self.assertFalse(Camera.IsPointInFOV(*behind))

    def test_a_point_at_the_camera_is_inside_it(self) -> None:
        """``Camera.py:355-356``: ``dist == 0`` answers before any angle is computed."""

        cam_x, cam_y, _ = Camera.GetPosition()
        self.assertTrue(Camera.IsPointInFOV(cam_x, cam_y))

    def test_an_infinite_yaw_is_never_in_the_field_of_view(self) -> None:
        """``Camera.py:346-347``."""

        self.camera.yaw = float("inf")
        self.assertFalse(Camera.IsPointInFOV(0.0, 0.0))


class CameraWriteTests(unittest.TestCase):
    """Each action names the field the source writes, and publishes it as one command."""

    def setUp(self) -> None:
        self.camera = _camera_struct()
        self.client = _FakeClient(self.camera)
        patcher = mock.patch("py4gw.camera.require_client", return_value=self.client)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _last_command(self) -> tuple[Operation, int, int, int]:
        self.assertTrue(self.client.bridge.commands, "no command was published")
        return self.client.bridge.commands[-1]

    def _assert_field_write(self, field: str, payload: bytes) -> None:
        operation, address, offset, size = self._last_command()
        self.assertIs(operation, Operation.WRITE_MEMORY)
        self.assertEqual(offset, 0x200, "the write travels through the module's own data offset")
        self.assertEqual(size, len(payload))
        expected = self.client.camera.address + int(getattr(CameraStruct, field).offset)
        self.assertEqual(address, expected, f"the write did not land on {field}")
        self.assertEqual(self.client.bridge.writes[-1][1], payload)

    def test_set_yaw_writes_both_fields_the_source_writes(self) -> None:
        """``camera.h:80-83``: ``yaw_to_go`` first, then ``yaw``."""

        Camera.SetYaw(1.25)
        self._assert_field_write("yaw", struct.pack("<f", 1.25))
        self.assertEqual(len(self.client.bridge.commands), 2, "two fields, two writes")
        operation, address, _, _ = self.client.bridge.commands[0]
        self.assertIs(operation, Operation.WRITE_MEMORY)
        self.assertEqual(address, self.client.camera.address + int(CameraStruct.yaw_to_go.offset))

    def test_set_pitch_writes_only_pitch_to_go(self) -> None:
        """``camera.h:99-101``."""

        Camera.SetPitch(-0.375)
        self._assert_field_write("pitch_to_go", struct.pack("<f", -0.375))
        self.assertEqual(len(self.client.bridge.commands), 1)

    def test_set_max_distance_writes_max_distance2(self) -> None:
        """``camera_methods.cpp:78-85``: not ``max_distance``."""

        Camera.SetMaxDistance(1500.0)
        self._assert_field_write("max_distance2", struct.pack("<f", 1500.0))

    def test_set_field_of_view_writes_field_of_view(self) -> None:
        """``camera_methods.cpp:87-94``."""

        Camera.SetFieldOfView(1.75)
        self._assert_field_write("field_of_view", struct.pack("<f", 1.75))

    def test_forward_movement_adds_the_yaw_projection_to_the_target(self) -> None:
        """``camera_methods.cpp:13-30``, the ``true_forward`` branch."""

        Camera.ForwardMovement(10.0, True)
        pitch_x = math.sqrt(1.0 - 0.25 * 0.25)
        expected = (
            40.0 + 10.0 * pitch_x * math.cos(0.5),
            50.0 + 10.0 * pitch_x * math.sin(0.5),
            60.0 + 10.0 * 0.25,
        )
        self._assert_field_write("look_at_target", struct.pack("<3f", *expected))

    def test_a_zero_amount_writes_nothing(self) -> None:
        """``camera_methods.cpp:15-17`` and ``:69-71`` refuse a zero amount."""

        Camera.ForwardMovement(0.0, True)
        Camera.SideMovement(0.0)
        Camera.RotateMovement(0.0)
        self.assertEqual(self.client.bridge.commands, [])

    def test_update_camera_pos_writes_the_computed_position(self) -> None:
        """``camera_methods.cpp:116-124``: the computed vector goes into ``position``."""

        x, y, z = Camera.ComputeCameraPos()
        Camera.UpdateCameraPos()
        self._assert_field_write("position", struct.pack("<3f", x, y, z))

    def test_set_camera_position_writes_position(self) -> None:
        """``camera.h:107-111``."""

        Camera.SetCameraPosition(1.0, -2.0, 3.5)
        self._assert_field_write("position", struct.pack("<3f", 1.0, -2.0, 3.5))

    def test_set_look_at_target_writes_the_target(self) -> None:
        """``camera.h:113-117``."""

        Camera.SetLookAtTarget(-1.0, 2.0, -3.0)
        self._assert_field_write("look_at_target", struct.pack("<3f", -1.0, 2.0, -3.0))


class CameraPatchTests(unittest.TestCase):
    """The unlock and the fog are patches, and the toggle keeps the bytes to put back."""

    def setUp(self) -> None:
        self.camera = _camera_struct()
        self.client = _FakeClient(self.camera, contents=b"\x55\x8B\xEC\x83")
        patcher = mock.patch("py4gw.camera.require_client", return_value=self.client)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.patch = mock.patch("py4gw.game_thread.patcher.Patcher")
        self.patcher = self.patch.start()
        self.addCleanup(self.patch.stop)
        # The two patches are module state, as native's are process state: each test starts from a
        # connection that has never toggled one.
        camera_module._reset_patch_state()
        self.addCleanup(camera_module._reset_patch_state)

    def test_enabling_the_unlock_patches_the_vs2017_bytes_the_attempt_names(self) -> None:
        """``camera_patterns.cpp:43-46``: the vs2017 attempt is ``EB 0C``."""

        Camera.SetCameraUnlock(True)
        self.assertTrue(Camera.GetCameraUnlock())
        address, expected, replacement = self.patcher.return_value.patch.call_args.args
        self.assertEqual(address, 0x00513000)
        self.assertEqual(expected, b"\x55\x8B")
        self.assertEqual(replacement, b"\xEB\x0C")

    def test_disabling_restores_through_the_same_patcher(self) -> None:
        """Native's ``TogglePatch(false)`` puts the client's own bytes back."""

        Camera.SetCameraUnlock(True)
        Camera.SetCameraUnlock(False)
        self.assertFalse(Camera.GetCameraUnlock())
        self.patcher.return_value.restore.assert_called_once_with(0x00513000)

    def test_enabling_twice_and_disabling_once_restores_the_clients_own_bytes(self) -> None:
        """``TogglePatch`` does nothing when the state already matches, and that is load-bearing.

        A second enable would read the backup from the *patched* bytes, so the disable after it would put
        the patch back instead of the client's own bytes -- measured live on 2026-09-27, where that left
        the camera update patched in the client.
        """

        Camera.SetCameraUnlock(True)
        Camera.SetCameraUnlock(True)
        calls = self.patcher.return_value.patch.call_count
        self.assertEqual(calls, 1, "the second enable must not re-patch")
        Camera.SetCameraUnlock(False)
        self.assertEqual(self.patcher.return_value.patch.call_args.args[2], b"\xEB\x0C")
        self.patcher.return_value.restore.assert_called_once_with(0x00513000)

    def test_a_disable_that_was_never_enabled_does_nothing(self) -> None:
        """``TogglePatch`` is a no-op when the state already matches, and so is this."""

        Camera.SetFog(False)
        self.patcher.return_value.patch.assert_not_called()
        self.patcher.return_value.restore.assert_not_called()

    def test_the_fog_patch_writes_the_one_byte_the_source_sets(self) -> None:
        """``camera_patterns.cpp:31-32``: ``{0x00}``."""

        Camera.SetFog(True)
        address, _expected, replacement = self.patcher.return_value.patch.call_args.args
        self.assertEqual(address, 0x00512000)
        self.assertEqual(replacement, b"\x00")


if __name__ == "__main__":
    unittest.main(verbosity=2)
