"""External port of Reforged's ``Py4GWCoreLib/Camera.py``.

Every member of that class is here with the same name, the same signature and the same return value.

**Where each body comes from.** Reforged's members are one-liners over its in-process camera object
(`Camera.camera_instance().yaw`), which is native's ``GW::Context::Camera``
(``include/GW/context/camera.h``). The port's ``camera_instance()`` is that same record, read through
the ported context (``py4gw/context/camera_context.py``), so **the reads are the source's own lines** —
the same field, the same tuple, the same `GetCurrentYaw` arithmetic (``camera.h:84-97`` and
``Camera.py:33-49`` agree term for term).

**The actions are Native's**, because Reforged's bodies are calls on an object this controller does not
have. Two mechanisms, and both are the source's own choice of *where* the work happens:

* **field writes** — ``GW::camera`` writes the record and says so on the game thread
  (``camera_bindings.cpp:100-103`` → ``GW::game_thread::Enqueue``), because the client is reading the
  same struct. The port does the same thing in the same place: the new value is computed here from a
  fresh read and placed on the client's own thread with the payload's ``WRITE_MEMORY`` operation
  (``py4gw/game_thread/``), which runs inside the function this project hooked. The arithmetic is
  ``camera_methods.cpp:13-124`` line for line — ``ForwardMovement``/``VerticalMovement``/``SideMovement``/
  ``RotateMovement``/``ComputeCamPos``/``UpdateCameraPos``, and the setters
  (``SetYaw`` writes ``yaw`` **and** ``yaw_to_go``, ``SetPitch`` writes ``pitch_to_go``,
  ``SetMaxDist`` writes ``max_distance2``, ``SetFieldOfView`` writes ``field_of_view`` —
  ``camera.h:80-117``, ``camera_methods.cpp:78-94``).
* **patches** — the camera unlock and the fog are not fields at all: native toggles a
  ``MemoryPatcher`` (``camera_methods.cpp:137-147``) whose bytes are set from the two catalog addresses
  (``camera_patterns.cpp:24-52``: fog ``00``; camera update ``EB 0C`` on the vs2017 attempt and
  ``EB 0F`` on the vs2022 one). The port toggles the same bytes at the same addresses with its own
  ``Patcher``, remembering each patch's original bytes as the backup it restores.

**A read-only connection still reads.** Every getter works from the ported context alone; the actions
need the capability layer and a write transport, which is what ``py4gw.connect()`` installs, and a
connection opened with ``game_thread=False`` says so by refusing the write the way the rest of the port
does rather than returning a value it did not produce.
"""

from __future__ import annotations

import math
import struct

from .client import require_client
from .context.camera_context import CameraStruct
from .game_thread.shared_block import Operation

#: The offset in the block's data region a camera write travels through: the value is placed there by
#: the host and named to the payload as ``WRITE_MEMORY``'s second word. Nothing else uses this offset.
_WRITE_REGION_OFFSET = 0x200

#: The three catalog names this module resolves (``offsets/camera.json``), spelled as native spells
#: them (``camera_patterns.cpp:19-52``).
CAMERA_POINTER = "camera.camera_ptr"
FOG_PATCH_ADDR = "camera.fog_patch_addr"
CAMERA_UPDATE_PATCH_ADDR = "camera.camera_update_patch_addr"

#: The bytes each patch writes, and the attempt each belongs to (``camera_patterns.cpp:24-52``).
_FOG_PATCH = bytes((0x00,))
_CAMERA_UPDATE_PATCH = {"vs2017": bytes((0xEB, 0x0C)), "vs2022": bytes((0xEB, 0x0F))}
_CAMERA_UPDATE_PATCH_DEFAULT = bytes((0xEB, 0x0F))

#: The two patches' state: their resolved address, the client's own bytes at that address (the backup a
#: disable puts back) and whether the patch is in place. Native keeps exactly this in its two
#: ``MemoryPatcher`` globals (``camera.cpp:24-25``), and it keeps **the patcher object**, not just its
#: bytes -- the port's ``Patcher`` remembers what it wrote so a restore can put the same bytes back on
#: the same instance, which is why these are module state rather than a fresh patcher per call.
_fog_patch_address = 0
_fog_patch_active = False
_fog_patcher = None
_fog_patch_bytes = b""
_camera_update_address = 0
_camera_update_active = False
_camera_update_patcher = None
_camera_update_patch_bytes = b""


def _reset_patch_state() -> None:
    """Forget both patches, which is what native's ``Exit`` does (``camera.cpp:28-33``).

    A patch's address and bytes belong to one client and one build, and a connection is the boundary for
    both: the connection calls this where it resets the other modules' state. It deliberately does not
    *undo* anything -- a connection that is closing has already restored what it toggled, and one that
    died could not have.
    """

    global _fog_patch_address, _fog_patch_active, _fog_patcher, _fog_patch_bytes
    global _camera_update_address, _camera_update_active, _camera_update_patcher
    global _camera_update_patch_bytes

    _fog_patch_address, _fog_patch_active, _fog_patcher, _fog_patch_bytes = 0, False, None, b""
    _camera_update_address, _camera_update_active = 0, False
    _camera_update_patcher, _camera_update_patch_bytes = None, b""


def _camera_reader():
    """The ported camera context of the connected client."""

    return require_client().camera


def _catalog():
    """The connected client's catalog and scanner, which is what resolved its own startup addresses."""

    client = require_client()
    return client._patterns, client._scanner


class Camera:
    """Reforged's ``Camera``: the source's 46 members over native's camera record."""

    @staticmethod
    def _camera_address() -> int:
        """The client address of the camera record, which every write is relative to.

        The port's own helper, and the read/write split is the only reason it exists: the getters ask the
        context for a *snapshot* (as the source's do), while a write has to name the live record. Native
        reads the same pointer once into ``Context::g_camera`` and writes through it
        (``camera_patterns.cpp:19-22``).
        """

        address = _camera_reader().resolve_address()
        if not address:
            raise RuntimeError("The camera context is currently unavailable.")
        return int(address)

    @staticmethod
    def _write_field(field: str, value: bytes) -> None:
        """Place one field of the camera record on the client's own thread.

        ``WRITE_MEMORY`` copies the bytes from the block's data region to
        ``camera + CameraStruct.<field>.offset``, inside the hooked function — the same thread and the
        same place Native's ``GW::game_thread::Enqueue`` runs ``camera->yaw = …``.
        """

        client = require_client()
        bridge = client.bridge
        bridge.write_data(_WRITE_REGION_OFFSET, value)
        bridge.submit(
            Operation.WRITE_MEMORY,
            Camera._camera_address() + int(getattr(CameraStruct, field).offset),
            _WRITE_REGION_OFFSET,
            len(value),
            0,
            0,
            0,
        )

    @staticmethod
    def _write_vec3(field: str, x: float, y: float, z: float) -> None:
        """Write one ``Vec3f`` field of the camera record (three little-endian floats)."""

        Camera._write_field(
            field,
            b"".join(struct.pack("<f", float(value)) for value in (x, y, z)),
        )

    @staticmethod
    def _write_float(field: str, value: float) -> None:
        """Write one ``float`` field of the camera record."""

        Camera._write_field(field, struct.pack("<f", float(value)))

    @staticmethod
    def _toggle_patch(which: str, enabled: bool) -> bool:
        """Toggle one of the two camera patches, the way native's ``MemoryPatcher`` does.

        ``MemoryPatcher::TogglePatch`` writes the patch bytes when it is asked to enable and puts the
        client's own bytes back when it is asked to disable, remembering which state it is in
        (``base/memory_patcher.h:27-34``). This is that, through the port's ``Patcher``: the client's
        bytes at the address are read first, so the backup is the client's own rather than a copy of a
        constant; **the patcher instance is kept** because the restore has to be the same one that wrote
        the patch; and **the address is resolved once and then remembered**, because a patch rewrites the
        very bytes its own pattern matches -- the camera update's pattern wants ``89 0E`` / ``8B 45`` and
        the patch turns those two bytes into ``EB 0C`` / ``EB 0F`` (``offsets/camera.json``,
        ``camera_patterns.cpp:43-51``) -- so a second resolve after enabling finds nothing. Native's
        ``MemoryPatcher`` holds the address it was built with for exactly that reason
        (``base/memory_patcher.h:42``). Measured live on 2026-09-27: the first version re-resolved on the
        way out, the disable raised "did not resolve", and the camera unlock stayed applied in the client.
        """

        global _fog_patch_address, _fog_patch_active, _fog_patcher
        global _camera_update_address, _camera_update_active, _camera_update_patcher

        client = require_client()
        from .game_thread.patcher import Patcher

        global _fog_patch_bytes, _camera_update_patch_bytes

        is_fog = which == "fog"
        state = _fog_patch_active if is_fog else _camera_update_active

        # **Asked for the state it is already in, nothing happens.** ``TogglePatch`` is exactly this
        # (``base/memory_patcher.h:27-34``), and it is not a shortcut: enabling a patch that is already
        # on would read the backup *from the patched bytes* and forget the client's own, so the disable
        # after it would write the patch back instead of the original. Measured live on 2026-09-27: a
        # sweep that enabled the unlock a second time left the client's camera update patched, and the
        # bytes had to be put back by hand (``tools/recover_camera_patch.py``).
        if enabled == state:
            return True

        address = _fog_patch_address if is_fog else _camera_update_address
        patch = _fog_patch_bytes if is_fog else _camera_update_patch_bytes

        if enabled:
            if not address or not patch:
                patterns, scanner = _catalog()
                name = FOG_PATCH_ADDR if is_fog else CAMERA_UPDATE_PATCH_ADDR
                result = patterns.resolve(name, scanner)
                if not result.ok or not result.value:
                    raise RuntimeError(
                        f"{name} did not resolve: {result.message or 'no address'}"
                    )
                address = int(result.value)
                patch = _FOG_PATCH if is_fog else _CAMERA_UPDATE_PATCH.get(
                    # Which patch belongs to this build is what the resolver's selected attempt says,
                    # exactly as native reads it (``camera_patterns.cpp:43-51``); an attempt it does not
                    # name takes the vs2022 bytes, which is native's own fallthrough. The bytes are kept
                    # with the address, as native's ``SetPatch`` keeps them
                    # (``base/memory_patcher.h:19``), because a re-enable has no pattern left to read
                    # the attempt from.
                    getattr(result, "selected_attempt", "") or "",
                    _CAMERA_UPDATE_PATCH_DEFAULT,
                )
                if is_fog:
                    _fog_patch_address, _fog_patch_bytes = address, patch
                else:
                    _camera_update_address, _camera_update_patch_bytes = address, patch

            backup = bytes(client.access.read(address, len(patch)))
            patcher = Patcher(client.access, client.pid)
            patcher.patch(address, backup, patch)
            if is_fog:
                _fog_patcher, _fog_patch_active = patcher, True
            else:
                _camera_update_patcher, _camera_update_active = patcher, True
            return True

        # The state is on, so the enable above is the only thing that can have set it: the patcher and
        # the address it wrote are the ones kept beside it (``MemoryPatcher`` holds the same pair).
        patcher = _fog_patcher if is_fog else _camera_update_patcher
        assert patcher is not None and address
        patcher.restore(address)
        if is_fog:
            _fog_patch_active = False
        else:
            _camera_update_active = False
        return True

    # -- the source's surface, in its own order (``Camera.py:5-367``) --------------------------

    @staticmethod
    def camera_instance() -> CameraStruct:
        """Returns the camera instance. (``Camera.py:5-10``)"""

        return _camera_reader().camera_instance()

    @staticmethod
    def GetLookAtAgentID() -> int:
        """Returns the agent ID of the camera's look-at target. (``Camera.py:12-17``)"""

        return int(Camera.camera_instance().look_at_agent_id)

    @staticmethod
    def GetMaxDistance() -> float:
        """Returns the maximum distance of the camera. (``Camera.py:19-24``)"""

        return float(Camera.camera_instance().max_distance)

    @staticmethod
    def GetYaw() -> float:
        """Returns the yaw of the camera. (``Camera.py:26-31``)"""

        return float(Camera.camera_instance().yaw)

    @staticmethod
    def GetCurrentYaw() -> float:
        """Returns the current yaw of the camera. (``Camera.py:33-49``)"""

        pos = Camera.GetPosition()
        lat = Camera.GetLookAtTarget()

        x = pos[0] - lat[0]
        y = pos[1] - lat[1]

        curtan = math.atan2(y, x)

        if curtan >= 0:
            return curtan - math.pi
        return curtan + math.pi

    @staticmethod
    def GetPitch() -> float:
        """Returns the pitch of the camera. (``Camera.py:51-56``)"""

        return float(Camera.camera_instance().pitch)

    @staticmethod
    def GetCameraZoom() -> float:
        """Returns the camera zoom. (``Camera.py:58-63``, ``camera.h:103``)"""

        return float(Camera.camera_instance().distance)

    @staticmethod
    def GetYawRightClick() -> float:
        """Returns the yaw right-click. (``Camera.py:65-70``)"""

        return float(Camera.camera_instance().yaw_right_click)

    @staticmethod
    def GetYawRightClick2() -> float:
        """Returns the yaw right-click. (``Camera.py:72-77``)"""

        return float(Camera.camera_instance().yaw_right_click2)

    @staticmethod
    def GetPitchRightClick() -> float:
        """Returns the pitch right-click. (``Camera.py:79-84``)"""

        return float(Camera.camera_instance().pitch_right_click)

    @staticmethod
    def GetDistance2() -> float:
        """Returns the distance squared. (``Camera.py:86-91``)"""

        return float(Camera.camera_instance().distance2)

    @staticmethod
    def GetAccelerationConstant() -> float:
        """Returns the acceleration constant. (``Camera.py:93-98``)"""

        return float(Camera.camera_instance().acceleration_constant)

    @staticmethod
    def GetTimeSinceLastKeyboardRotation() -> float:
        """Returns the time since the last keyboard rotation. (``Camera.py:100-105``)"""

        return float(Camera.camera_instance().time_since_last_keyboard_rotation)

    @staticmethod
    def GetTimeSinceLastMouseRotation() -> float:
        """Returns the time since the last mouse rotation. (``Camera.py:107-112``)"""

        return float(Camera.camera_instance().time_since_last_mouse_rotation)

    @staticmethod
    def GetTimeSinceLastMouseMove() -> float:
        """Returns the time since the last mouse move. (``Camera.py:114-119``)"""

        return float(Camera.camera_instance().time_since_last_mouse_move)

    @staticmethod
    def GetTimeSinceLastAgentSelection() -> float:
        """Returns the time since the last agent selection. (``Camera.py:121-126``)"""

        return float(Camera.camera_instance().time_since_last_agent_selection)

    @staticmethod
    def GetTimeInTheMap() -> float:
        """Returns the time in the map. (``Camera.py:128-133``)"""

        return float(Camera.camera_instance().time_in_the_map)

    @staticmethod
    def GetTimeInTheDistrict() -> float:
        """Returns the time in the district. (``Camera.py:135-140``)"""

        return float(Camera.camera_instance().time_in_the_district)

    @staticmethod
    def GetYawToGo() -> float:
        """Returns the yaw to go. (``Camera.py:142-147``)"""

        return float(Camera.camera_instance().yaw_to_go)

    @staticmethod
    def GetPitchToGo() -> float:
        """Returns the pitch to go. (``Camera.py:149-154``)"""

        return float(Camera.camera_instance().pitch_to_go)

    @staticmethod
    def GetDistanceToGo() -> float:
        """Returns the distance to go. (``Camera.py:156-161``)"""

        return float(Camera.camera_instance().dist_to_go)

    @staticmethod
    def GetMaxDistance2() -> float:
        """Returns the maximum distance squared. (``Camera.py:163-168``)"""

        return float(Camera.camera_instance().max_distance2)

    @staticmethod
    def GetPosition() -> tuple[float, float, float]:
        """Returns the position of the camera. (``Camera.py:170-176``)"""

        position = Camera.camera_instance().position
        return float(position.x), float(position.y), float(position.z)

    @staticmethod
    def GetCameraPositionToGo() -> tuple[float, float, float]:
        """Returns the camera position to go. (``Camera.py:178-184``)"""

        position = Camera.camera_instance().camera_pos_to_go
        return float(position.x), float(position.y), float(position.z)

    @staticmethod
    def GetCameraPositionInverted() -> tuple[float, float, float]:
        """Returns the inverted camera position. (``Camera.py:186-192``)"""

        position = Camera.camera_instance().cam_pos_inverted
        return float(position.x), float(position.y), float(position.z)

    @staticmethod
    def GetCameraPositionInvertedToGo() -> tuple[float, float, float]:
        """Returns the inverted camera position to go. (``Camera.py:194-200``)"""

        position = Camera.camera_instance().cam_pos_inverted_to_go
        return float(position.x), float(position.y), float(position.z)

    @staticmethod
    def GetLookAtTarget() -> tuple[float, float, float]:
        """Returns the look-at target of the camera. (``Camera.py:202-208``)"""

        target = Camera.camera_instance().look_at_target
        return float(target.x), float(target.y), float(target.z)

    @staticmethod
    def GetAtTargetToGo() -> tuple[float, float, float]:
        """Returns the look-at target to go. (``Camera.py:210-216``)"""

        target = Camera.camera_instance().look_at_to_go
        return float(target.x), float(target.y), float(target.z)

    @staticmethod
    def GetFieldOfView() -> float:
        """Returns the field of view of the camera. (``Camera.py:218-223``)"""

        return float(Camera.camera_instance().field_of_view)

    @staticmethod
    def GetFielsOfView2() -> float:
        """Returns the field of view squared. (``Camera.py:225-230``)"""

        return float(Camera.camera_instance().field_of_view2)

    @staticmethod
    def SetYaw(yaw: float) -> None:
        """Sets the yaw of the camera. (``Camera.py:232-237``, ``camera.h:80-83``)

        Native's setter writes **both** fields, and this is native's body (``camera.h:80-83``): the
        client steers toward ``yaw_to_go``, so a yaw set without the target would be undone by the next
        camera update.
        """

        Camera._write_float("yaw_to_go", float(yaw))
        Camera._write_float("yaw", float(yaw))

    @staticmethod
    def SetPitch(pitch: float) -> None:
        """Sets the pitch of the camera. (``Camera.py:239-244``, ``camera.h:99-101``)

        Native's setter writes ``pitch_to_go`` only — the client interpolates the current pitch toward
        it — and this is that body.
        """

        Camera._write_float("pitch_to_go", float(pitch))

    @staticmethod
    def SetMaxDistance(dist: float) -> None:
        """Sets the maximum distance of the camera. (``Camera.py:246-251``, ``camera_methods.cpp:78-85``)"""

        Camera._write_float("max_distance2", float(dist))

    @staticmethod
    def SetFieldOfView(fov: float) -> None:
        """Sets the field of view of the camera. (``Camera.py:253-258``, ``camera_methods.cpp:87-94``)"""

        Camera._write_float("field_of_view", float(fov))

    @staticmethod
    def SetCameraUnlock(unlock: bool) -> None:
        """Sets the camera unlock state. (``Camera.py:260-265``, ``camera_methods.cpp:137-139``)"""

        Camera._toggle_patch("update", bool(unlock))

    @staticmethod
    def GetCameraUnlock() -> bool:
        """Returns the camera unlock state. (``Camera.py:267-272``, ``camera_methods.cpp:141-143``)"""

        return bool(_camera_update_active)

    @staticmethod
    def ForwardMovement(amount: float, true_forward: bool) -> None:
        """Moves the camera forward. (``Camera.py:274-279``, ``camera_methods.cpp:13-30``)"""

        camera = Camera.camera_instance()
        value = float(amount)
        if value == 0.0:
            return

        target = camera.look_at_target
        x, y, z = float(target.x), float(target.y), float(target.z)
        if true_forward:
            pitch_x = math.sqrt(1.0 - float(camera.pitch) * float(camera.pitch))
            x += value * pitch_x * math.cos(float(camera.yaw))
            y += value * pitch_x * math.sin(float(camera.yaw))
            z += value * float(camera.pitch)
        else:
            x += value * math.cos(float(camera.yaw))
            y += value * math.sin(float(camera.yaw))
        Camera._write_vec3("look_at_target", x, y, z)

    @staticmethod
    def VerticalMovement(amount: float) -> None:
        """Moves the camera vertically. (``Camera.py:281-286``, ``camera_methods.cpp:32-40``)"""

        target = Camera.camera_instance().look_at_target
        Camera._write_vec3(
            "look_at_target",
            float(target.x),
            float(target.y),
            float(target.z) + float(amount),
        )

    @staticmethod
    def SideMovement(amount: float) -> None:
        """Moves the camera sideways. (``Camera.py:288-293``, ``camera_methods.cpp:67-76``)"""

        camera = Camera.camera_instance()
        value = float(amount)
        if value == 0.0:
            return

        target = camera.look_at_target
        yaw = float(camera.yaw)
        Camera._write_vec3(
            "look_at_target",
            float(target.x) + value * -math.sin(yaw),
            float(target.y) + value * math.cos(yaw),
            float(target.z),
        )

    @staticmethod
    def RotateMovement(angle: float) -> None:
        """Rotates the camera. (``Camera.py:295-300``, ``camera_methods.cpp:42-65``)"""

        value = float(angle)
        if value == 0.0:
            return

        camera = Camera.camera_instance()
        position = camera.position
        target = camera.look_at_target
        pos_x, pos_y = float(position.x), float(position.y)
        px = float(target.x) - pos_x
        py = float(target.y) - pos_y

        new_x = pos_x + (math.cos(value) * px - math.sin(value) * py)
        new_y = pos_y + (math.sin(value) * px + math.cos(value) * py)

        Camera.SetYaw(float(camera.yaw) + value)
        Camera._write_vec3("look_at_target", new_x, new_y, float(target.z))

    @staticmethod
    def ComputeCameraPos() -> tuple[float, float, float]:
        """Computes the camera position. (``Camera.py:302-307``, ``camera_methods.cpp:96-114``)"""

        camera = Camera.camera_instance()
        target = camera.look_at_target
        dist = float(camera.distance)
        pitch = float(camera.pitch)
        yaw = float(camera.yaw)
        pitch_x = math.sqrt(1.0 - pitch * pitch)

        return (
            float(target.x) - dist * pitch_x * math.cos(yaw),
            float(target.y) - dist * pitch_x * math.sin(yaw),
            float(target.z) - dist * 0.95 * pitch,
        )

    @staticmethod
    def UpdateCameraPos() -> None:
        """Updates the camera position. (``Camera.py:309-314``, ``camera_methods.cpp:116-124``)"""

        x, y, z = Camera.ComputeCameraPos()
        Camera._write_vec3("position", x, y, z)

    @staticmethod
    def SetCameraPosition(x: float, y: float, z: float) -> None:
        """Sets the camera position. (``Camera.py:316-321``, ``camera.h:107-111``)"""

        Camera._write_vec3("position", float(x), float(y), float(z))

    @staticmethod
    def SetLookAtTarget(x: float, y: float, z: float) -> None:
        """Sets the look-at target of the camera. (``Camera.py:323-328``, ``camera.h:113-117``)"""

        Camera._write_vec3("look_at_target", float(x), float(y), float(z))

    @staticmethod
    def SetFog(fog: bool) -> None:
        """Sets the fog state of the camera. (``Camera.py:330-335``, ``camera_methods.cpp:145-147``)"""

        Camera._toggle_patch("fog", bool(fog))

    @staticmethod
    def IsPointInFOV(target_x: float, target_y: float) -> bool:
        """Whether a game position is inside the camera's field of view. (``Camera.py:337-367``)"""

        cam_x, cam_y, _ = Camera.GetPosition()
        yaw = Camera.GetYaw()

        if yaw == float("inf") or yaw == float("-inf"):
            return False

        fov = Camera.GetFieldOfView()

        dx = target_x - cam_x
        dy = target_y - cam_y

        dist = math.hypot(dx, dy)
        if dist == 0:
            return True

        angle_to_target = math.atan2(dy, dx)
        angle_diff = angle_to_target - yaw

        while angle_diff > math.pi:
            angle_diff -= 2 * math.pi
        while angle_diff < -math.pi:
            angle_diff += 2 * math.pi

        half_fov = (fov / 2) + 0.2
        return abs(angle_diff) < half_fov
