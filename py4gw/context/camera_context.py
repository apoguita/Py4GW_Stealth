"""External read-only layout and reader for the Guild Wars camera."""

from __future__ import annotations

from ..helpers.target_struct import TargetStruct

import ctypes
import math
from ctypes import Structure, c_float, c_uint32
from typing import NoReturn, Protocol

from ..scanner import PatternCatalog, RemoteScanner
from .acc_agent_context import Vec3fStruct
from .gw_array import RemoteMemoryReader


class _memory_reader(RemoteMemoryReader, Protocol):
    """The byte-reading operation needed by the camera reader."""


class CameraStruct(TargetStruct):
    """The fixed-width x86 portion of the native ``Camera`` record.

    The native header documents fields through ``camera_mode`` at ``0x11C``.
    The external reader copies that maintained portion only; it does not
    invoke camera methods or write any camera state.
    """

    _pack_ = 1
    _fields_ = [
        ("look_at_agent_id", c_uint32),
        ("h0004", c_uint32),
        ("h0008", c_float),
        ("h000C", c_float),
        ("max_distance", c_float),
        ("h0014", c_float),
        ("yaw", c_float),
        ("pitch", c_float),
        ("distance", c_float),
        ("h0024", c_uint32 * 4),
        ("yaw_right_click", c_float),
        ("yaw_right_click2", c_float),
        ("pitch_right_click", c_float),
        ("distance2", c_float),
        ("acceleration_constant", c_float),
        ("time_since_last_keyboard_rotation", c_float),
        ("time_since_last_mouse_rotation", c_float),
        ("time_since_last_mouse_move", c_float),
        ("time_since_last_agent_selection", c_float),
        ("time_in_the_map", c_float),
        ("time_in_the_district", c_float),
        ("yaw_to_go", c_float),
        ("pitch_to_go", c_float),
        ("dist_to_go", c_float),
        ("max_distance2", c_float),
        ("h0070", c_float * 2),
        ("position", Vec3fStruct),
        ("camera_pos_to_go", Vec3fStruct),
        ("cam_pos_inverted", Vec3fStruct),
        ("cam_pos_inverted_to_go", Vec3fStruct),
        ("look_at_target", Vec3fStruct),
        ("look_at_to_go", Vec3fStruct),
        ("field_of_view", c_float),
        ("field_of_view2", c_float),
        ("h00C8", c_uint32),
        ("h00CC", c_uint32),
        ("h00D0", c_uint32),
        ("h00D4", c_uint32),
        ("h00D8", c_uint32),
        ("h00DC", c_uint32),
        ("h00E0", c_uint32),
        ("h00E4", c_uint32),
        ("h00E8", c_uint32),
        ("h00EC", c_uint32),
        ("h00F0", c_uint32),
        ("h00F4", c_uint32),
        ("h00F8", c_uint32),
        ("h00FC", c_uint32),
        ("h0100", c_uint32),
        ("h0104", c_uint32),
        ("h0108", c_uint32),
        ("h010C", c_uint32),
        ("h0110", c_uint32),
        ("h0114", c_uint32),
        ("h0118", c_uint32),
        ("camera_mode", c_uint32),
    ]

    @property
    def is_unlocked(self) -> bool:
        """Return whether the native camera mode is the unlocked mode."""

        return int(self.camera_mode) == 3

    def GetYaw(self) -> float:
        """Return the native yaw field using its source method name."""

        return float(self.yaw)

    def GetPitch(self) -> float:
        """Return the native pitch field using its source method name."""

        return float(self.pitch)

    def GetFieldOfView(self) -> float:
        """Return the camera field-of-view field (not the render FOV)."""

        return float(self.field_of_view)

    def IsCameraUnlocked(self) -> bool:
        """Return whether the native camera mode is the unlocked mode."""

        return self.is_unlocked

    def SetYaw(self, yaw: float) -> None:
        """Declare the native setter without writing to the remote process."""

        raise NotImplementedError(
            "Camera.SetYaw changes live client memory and is not enabled."
        )

    def SetPitch(self, pitch: float) -> None:
        """Declare the native setter without writing to the remote process."""

        raise NotImplementedError(
            "Camera.SetPitch changes live client memory and is not enabled."
        )

    @property
    def current_yaw(self) -> float:
        """Return the native angle calculated from position and target."""

        x = float(self.position.x) - float(self.look_at_target.x)
        y = float(self.position.y) - float(self.look_at_target.y)
        current = ctypes.c_float(math.atan2(y, x)).value
        pi = ctypes.c_float(3.141592741).value
        result = current - pi if current >= 0 else current + pi
        return ctypes.c_float(result).value

    def GetCurrentYaw(self) -> float:
        """Return the source's current-yaw calculation."""

        return self.current_yaw

    def GetCameraZoom(self) -> float:
        """Return the camera distance using the native method name."""

        return float(self.distance)

    def GetLookAtTarget(self) -> Vec3fStruct:
        """Return a detached copy of the native look-at target vector."""

        return Vec3fStruct.from_buffer_copy(bytes(self.look_at_target))

    def GetCameraPosition(self) -> Vec3fStruct:
        """Return a detached copy of the native camera position vector."""

        return Vec3fStruct.from_buffer_copy(bytes(self.position))

    def SetCameraPos(self, new_position: Vec3fStruct) -> None:
        """Declare the native setter without writing to the remote process."""

        raise NotImplementedError(
            "Camera.SetCameraPos changes live client memory and is not enabled."
        )

    def SetLookAtTarget(self, new_position: Vec3fStruct) -> None:
        """Declare the native setter without writing to the remote process."""

        raise NotImplementedError(
            "Camera.SetLookAtTarget changes live client memory and is not enabled."
        )

    @property
    def camera_zoom(self) -> float:
        """Return the Reforged camera-zoom alias for ``distance``."""

        return float(self.distance)

    @staticmethod
    def _vector_tuple(vector: Vec3fStruct) -> tuple[float, float, float]:
        """Convert one fixed-width vector to the source tuple form."""

        return (float(vector.x), float(vector.y), float(vector.z))

    @property
    def camera_position(self) -> tuple[float, float, float]:
        """Return the source ``GetPosition`` tuple."""

        return self._vector_tuple(self.position)

    @property
    def camera_position_to_go_value(self) -> tuple[float, float, float]:
        """Return the source camera-position-to-go tuple."""

        return self._vector_tuple(self.camera_pos_to_go)

    @property
    def camera_position_inverted_value(self) -> tuple[float, float, float]:
        """Return the source inverted-camera-position tuple."""

        return self._vector_tuple(self.cam_pos_inverted)

    @property
    def camera_position_inverted_to_go_value(self) -> tuple[float, float, float]:
        """Return the source inverted-position-to-go tuple."""

        return self._vector_tuple(self.cam_pos_inverted_to_go)

    @property
    def look_at_target_value(self) -> tuple[float, float, float]:
        """Return the source ``GetLookAtTarget`` tuple."""

        return self._vector_tuple(self.look_at_target)

    @property
    def look_at_to_go_value(self) -> tuple[float, float, float]:
        """Return the source look-at-to-go tuple."""

        return self._vector_tuple(self.look_at_to_go)


assert ctypes.sizeof(CameraStruct) == 0x120
assert CameraStruct.position.offset == 0x78
assert CameraStruct.look_at_target.offset == 0xA8
assert CameraStruct.camera_mode.offset == 0x11C


class Camera:
    """Resolve and read the current camera through the JSON signature catalog."""

    _RESOLVER = "camera.camera_ptr"

    def __init__(
        self,
        reader: _memory_reader,
        scanner: RemoteScanner,
        patterns: PatternCatalog,
    ) -> None:
        """Create a read-only camera reader for one connected process."""

        self._reader = reader
        self._scanner = scanner
        self._patterns = patterns
        self._context_address: int | None = None

    def resolve_address(self) -> int | None:
        """Return the cached native camera object address, if available."""

        if self._context_address is None:
            return self.initialize()
        return self._context_address

    def initialize(self) -> int | None:
        """Resolve and cache the camera object address once for this connection."""

        if self._context_address is None:
            result = self._patterns.resolve(self._RESOLVER, self._scanner)
            if not result.ok:
                detail = result.message or "the resolver returned no address"
                raise RuntimeError(f"{self._RESOLVER} failed: {detail}")
            self._context_address = result.value
        return self._context_address or None

    @property
    def cached_context_address(self) -> int | None:
        """Return the cached native camera object address."""

        return self._context_address

    def read(self) -> CameraStruct | None:
        """Read the maintained camera structure without modifying the client."""

        address = self.resolve_address()
        if address is None:
            return None
        raw_context = self._reader.read(address, ctypes.sizeof(CameraStruct))
        return CameraStruct.from_buffer_copy(raw_context)

    def camera_instance(self) -> CameraStruct:
        """Return one fresh camera snapshot for source-compatible getters."""

        camera = self.read()
        if camera is None:
            raise RuntimeError("The camera context is currently unavailable.")
        return camera

    def GetLookAtAgentID(self) -> int:
        return int(self.camera_instance().look_at_agent_id)

    def GetMaxDistance(self) -> float:
        return float(self.camera_instance().max_distance)

    def GetYaw(self) -> float:
        return self.camera_instance().GetYaw()

    def GetCurrentYaw(self) -> float:
        return self.camera_instance().GetCurrentYaw()

    def GetPitch(self) -> float:
        return self.camera_instance().GetPitch()

    def GetCameraZoom(self) -> float:
        return self.camera_instance().GetCameraZoom()

    def GetYawRightClick(self) -> float:
        return float(self.camera_instance().yaw_right_click)

    def GetYawRightClick2(self) -> float:
        return float(self.camera_instance().yaw_right_click2)

    def GetPitchRightClick(self) -> float:
        return float(self.camera_instance().pitch_right_click)

    def GetDistance2(self) -> float:
        return float(self.camera_instance().distance2)

    def GetAccelerationConstant(self) -> float:
        return float(self.camera_instance().acceleration_constant)

    def GetTimeSinceLastKeyboardRotation(self) -> float:
        return float(self.camera_instance().time_since_last_keyboard_rotation)

    def GetTimeSinceLastMouseRotation(self) -> float:
        return float(self.camera_instance().time_since_last_mouse_rotation)

    def GetTimeSinceLastMouseMove(self) -> float:
        return float(self.camera_instance().time_since_last_mouse_move)

    def GetTimeSinceLastAgentSelection(self) -> float:
        return float(self.camera_instance().time_since_last_agent_selection)

    def GetTimeInTheMap(self) -> float:
        return float(self.camera_instance().time_in_the_map)

    def GetTimeInTheDistrict(self) -> float:
        return float(self.camera_instance().time_in_the_district)

    def GetYawToGo(self) -> float:
        return float(self.camera_instance().yaw_to_go)

    def GetPitchToGo(self) -> float:
        return float(self.camera_instance().pitch_to_go)

    def GetDistanceToGo(self) -> float:
        return float(self.camera_instance().dist_to_go)

    def GetMaxDistance2(self) -> float:
        return float(self.camera_instance().max_distance2)

    def GetPosition(self) -> tuple[float, float, float]:
        return self.camera_instance().camera_position

    def GetCameraPositionToGo(self) -> tuple[float, float, float]:
        return self.camera_instance().camera_position_to_go_value

    def GetCameraPositionInverted(self) -> tuple[float, float, float]:
        return self.camera_instance().camera_position_inverted_value

    def GetCameraPositionInvertedToGo(self) -> tuple[float, float, float]:
        return self.camera_instance().camera_position_inverted_to_go_value

    def GetLookAtTarget(self) -> tuple[float, float, float]:
        return self.camera_instance().look_at_target_value

    def GetAtTargetToGo(self) -> tuple[float, float, float]:
        return self.camera_instance().look_at_to_go_value

    def GetFieldOfView(self) -> float:
        return self.camera_instance().GetFieldOfView()

    def GetFielsOfView2(self) -> float:
        """Keep the misspelled source API name for compatibility."""

        return float(self.camera_instance().field_of_view2)

    def GetCameraUnlock(self) -> bool:
        return self.camera_instance().IsCameraUnlocked()

    def IsPointInFOV(self, target_x: float, target_y: float) -> bool:
        """Apply the source 2D camera-field-of-view check to one point."""

        camera = self.camera_instance()
        yaw = camera.GetYaw()
        if yaw == float("inf") or yaw == float("-inf"):
            return False
        delta_x = target_x - float(camera.position.x)
        delta_y = target_y - float(camera.position.y)
        if math.hypot(delta_x, delta_y) == 0:
            return True
        angle_to_target = math.atan2(delta_y, delta_x)
        angle_diff = angle_to_target - yaw
        while angle_diff > math.pi:
            angle_diff -= 2 * math.pi
        while angle_diff < -math.pi:
            angle_diff += 2 * math.pi
        half_fov = (float(camera.field_of_view) / 2) + 0.2
        return abs(angle_diff) < half_fov

    def SetYaw(self, yaw: float) -> None:
        self.camera_instance().SetYaw(yaw)

    def SetPitch(self, pitch: float) -> None:
        self.camera_instance().SetPitch(pitch)

    def SetMaxDistance(self, distance: float) -> None:
        self._raise_action_unavailable("SetMaxDistance")

    def SetFieldOfView(self, field_of_view: float) -> None:
        self._raise_action_unavailable("SetFieldOfView")

    def SetCameraUnlock(self, unlock: bool) -> None:
        self._raise_action_unavailable("SetCameraUnlock")

    def ForwardMovement(self, amount: float, true_forward: bool) -> None:
        self._raise_action_unavailable("ForwardMovement")

    def VerticalMovement(self, amount: float) -> None:
        self._raise_action_unavailable("VerticalMovement")

    def SideMovement(self, amount: float) -> None:
        self._raise_action_unavailable("SideMovement")

    def RotateMovement(self, angle: float) -> None:
        self._raise_action_unavailable("RotateMovement")

    def ComputeCameraPos(self) -> tuple[float, float, float]:
        self._raise_action_unavailable("ComputeCameraPos")

    def UpdateCameraPos(self) -> None:
        self._raise_action_unavailable("UpdateCameraPos")

    def SetCameraPosition(self, x: float, y: float, z: float) -> None:
        self._raise_action_unavailable("SetCameraPosition")

    def SetLookAtTarget(self, x: float, y: float, z: float) -> None:
        self._raise_action_unavailable("SetLookAtTarget")

    def SetFog(self, fog: bool) -> None:
        self._raise_action_unavailable("SetFog")

    @staticmethod
    def _raise_action_unavailable(operation: str) -> NoReturn:
        """Refuse source actions that require the in-client camera runtime."""

        raise NotImplementedError(
            f"Camera.{operation} requires in-client execution and is unavailable."
        )


def get() -> CameraStruct | None:
    """Read the camera for the current selected client, if connected."""

    from ..client import current_client

    client = current_client()
    return client.read_camera_context() if client is not None else None
