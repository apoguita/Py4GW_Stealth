"""External read-only layout and reader for the Guild Wars camera."""

from __future__ import annotations

import ctypes
import math
from ctypes import Structure, c_float, c_uint32
from typing import Protocol

from ..scanner import PatternCatalog, RemoteScanner
from .acc_agent_context import Vec3fStruct
from .gw_array import RemoteMemoryReader


class _memory_reader(RemoteMemoryReader, Protocol):
    """The byte-reading operation needed by the camera reader."""


class CameraStruct(Structure):
    """The fixed-width x86 portion of the native ``Camera`` record.

    The native header documents fields through ``camera_mode`` at ``0x11C``.
    The external reader copies that maintained portion only; it does not
    invoke camera methods or write any camera state.
    """

    _pack_ = 1
    _fields_ = [
        ("look_at_agent_id", c_uint32),
        ("unknown_0004", c_uint32),
        ("unknown_0008", c_float),
        ("unknown_000c", c_float),
        ("max_distance", c_float),
        ("unknown_0014", c_float),
        ("yaw", c_float),
        ("pitch", c_float),
        ("distance", c_float),
        ("unknown_0024", c_uint32 * 4),
        ("yaw_right_click", c_float),
        ("yaw_right_click_2", c_float),
        ("pitch_right_click", c_float),
        ("distance_2", c_float),
        ("acceleration_constant", c_float),
        ("time_since_last_keyboard_rotation", c_float),
        ("time_since_last_mouse_rotation", c_float),
        ("time_since_last_mouse_move", c_float),
        ("time_since_last_agent_selection", c_float),
        ("time_in_map", c_float),
        ("time_in_district", c_float),
        ("yaw_to_go", c_float),
        ("pitch_to_go", c_float),
        ("distance_to_go", c_float),
        ("max_distance_2", c_float),
        ("unknown_0070", c_uint32 * 2),
        ("position", Vec3fStruct),
        ("camera_position_to_go", Vec3fStruct),
        ("camera_position_inverted", Vec3fStruct),
        ("camera_position_inverted_to_go", Vec3fStruct),
        ("look_at_target", Vec3fStruct),
        ("look_at_to_go", Vec3fStruct),
        ("field_of_view", c_float),
        ("field_of_view_2", c_float),
        ("unknown_00c8", c_uint32 * 4),
        ("camera_controller_ptr", c_uint32),
        ("unknown_00dc", c_uint32 * 16),
        ("camera_mode", c_uint32),
    ]

    @property
    def is_unlocked(self) -> bool:
        """Return whether the native camera mode is the unlocked mode."""

        return int(self.camera_mode) == 3

    @property
    def current_yaw(self) -> float:
        """Return the native angle calculated from position and target."""

        x = float(self.position.x) - float(self.look_at_target.x)
        y = float(self.position.y) - float(self.look_at_target.y)
        current = math.atan2(y, x)
        return current - math.pi if current >= 0 else current + math.pi

    @property
    def camera_zoom(self) -> float:
        """Return the Reforged camera-zoom alias for ``distance``."""

        return float(self.distance)

    @property
    def distance2(self) -> float:
        """Return the Reforged spelling of ``distance_2``."""

        return float(self.distance_2)

    @property
    def field_of_view2(self) -> float:
        """Return the Reforged spelling of ``field_of_view_2``."""

        return float(self.field_of_view_2)

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

        return self._vector_tuple(self.camera_position_to_go)

    @property
    def camera_position_inverted_value(self) -> tuple[float, float, float]:
        """Return the source inverted-camera-position tuple."""

        return self._vector_tuple(self.camera_position_inverted)

    @property
    def camera_position_inverted_to_go_value(self) -> tuple[float, float, float]:
        """Return the source inverted-position-to-go tuple."""

        return self._vector_tuple(self.camera_position_inverted_to_go)

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


def get() -> CameraStruct | None:
    """Read the camera for the current selected client, if connected."""

    from ..client import current_client

    client = current_client()
    return client.read_camera_context() if client is not None else None
