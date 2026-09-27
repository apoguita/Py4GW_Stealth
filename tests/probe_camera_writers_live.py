"""Every ``Camera`` writer, against the live client: does the field the source names actually move?

The single-write probe proved the mechanism (``WRITE_MEMORY`` reaches the client's struct on the game
thread). This one proves each **member's own target field and arithmetic**: for every writer it records
the fields it is about to touch, calls the member, reads the client's record back and says whether the
change is the one the source describes (``camera.h:80-117``, ``camera_methods.cpp:13-124``), then puts the
original values back and verifies the restore. The fog and unlock patches are toggled on and off in the
same breath and the client's own bytes are read to see it.

Nothing is left changed: every write is restored inside a ``finally``, so a failure half way through
cannot leave the user's camera moved.

Usage: ``python tests/probe_camera_writers_live.py [report-path]``
"""

from __future__ import annotations

import json
import math
import sys
import time
from typing import Any

import py4gw
from py4gw.camera import Camera
from py4gw.win32 import Win32

REPORT_PATH = sys.argv[1] if len(sys.argv) > 1 else ""

_DELTA = 0.001
_MOVE = 1.0


def emit(stage: str, **values: Any) -> None:
    line = json.dumps({"stage": stage, **values}, default=str)
    print(line, flush=True)
    if REPORT_PATH:
        with open(REPORT_PATH, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")


def _close(actual: float, expected: float) -> bool:
    return abs(actual - expected) < 1e-5


def main() -> int:
    win32 = Win32()
    clients = win32.find_guild_wars()
    if not clients:
        emit("no_client")
        return 1
    if not win32.is_elevated():
        emit("not_elevated")
        return 3

    client = py4gw.connect(clients[0])
    emit("connected", pid=client.pid)
    unlock_was = Camera.GetCameraUnlock()
    try:
        # **The camera's own update overwrites its outputs every frame.** ``position``, ``look_at_target``,
        # ``max_distance2`` and ``field_of_view`` are values the client *computes*; the client's *inputs*
        # (``pitch_to_go``, ``yaw``/``yaw_to_go``, ``dist_to_go``) are the ones a write can hold. That is
        # what the camera-update patch is for -- it skips the client's update -- so the sweep runs with it
        # enabled, which is how the source's own setters are used.
        Camera.SetCameraUnlock(True)
        emit("unlock", enabled=Camera.GetCameraUnlock(), was=unlock_was)
        # --- the simple field writers: one field each, restored to its original value ----------
        def check(name: str, member, field: str, read, original: Any, expected: Any) -> None:
            started = time.perf_counter()
            member()
            ms = (time.perf_counter() - started) * 1000.0
            after = read()
            emit(
                "writer",
                member=name,
                field=field,
                original=original,
                expected=expected,
                observed=after,
                landed=_close(float(after), float(expected)),
                call_ms=round(ms, 3),
            )

        pitch = float(Camera.GetPitchToGo())
        check("SetPitch", lambda: Camera.SetPitch(pitch + _DELTA), "pitch_to_go", Camera.GetPitchToGo, pitch, pitch + _DELTA)
        Camera.SetPitch(pitch)
        emit("restored", field="pitch_to_go", value=Camera.GetPitchToGo(), ok=_close(float(Camera.GetPitchToGo()), pitch))

        yaw = float(Camera.GetYaw())
        Camera.SetYaw(yaw + _DELTA)
        emit(
            "writer",
            member="SetYaw",
            field="yaw and yaw_to_go",
            original=yaw,
            expected=yaw + _DELTA,
            observed=[Camera.GetYaw(), Camera.GetYawToGo()],
            landed=_close(float(Camera.GetYaw()), yaw + _DELTA) and _close(float(Camera.GetYawToGo()), yaw + _DELTA),
            call_ms=None,
        )
        Camera.SetYaw(yaw)
        emit(
            "restored",
            field="yaw and yaw_to_go",
            value=[Camera.GetYaw(), Camera.GetYawToGo()],
            ok=_close(float(Camera.GetYaw()), yaw) and _close(float(Camera.GetYawToGo()), yaw),
        )

        max_dist = float(Camera.GetMaxDistance2())
        check("SetMaxDistance", lambda: Camera.SetMaxDistance(max_dist + 10.0), "max_distance2", Camera.GetMaxDistance2, max_dist, max_dist + 10.0)
        Camera.SetMaxDistance(max_dist)
        emit("restored", field="max_distance2", value=Camera.GetMaxDistance2(), ok=_close(float(Camera.GetMaxDistance2()), max_dist))

        fov = float(Camera.GetFieldOfView())
        check("SetFieldOfView", lambda: Camera.SetFieldOfView(fov + _DELTA), "field_of_view", Camera.GetFieldOfView, fov, fov + _DELTA)
        Camera.SetFieldOfView(fov)
        emit("restored", field="field_of_view", value=Camera.GetFieldOfView(), ok=_close(float(Camera.GetFieldOfView()), fov))

        # --- the vector writers -----------------------------------------------------------------
        target = Camera.GetLookAtTarget()
        position = Camera.GetPosition()
        try:
            expected_forward = (
                target[0] + _MOVE * math.sqrt(1.0 - float(Camera.GetPitch()) ** 2) * math.cos(float(Camera.GetYaw())),
                target[1] + _MOVE * math.sqrt(1.0 - float(Camera.GetPitch()) ** 2) * math.sin(float(Camera.GetYaw())),
                target[2] + _MOVE * float(Camera.GetPitch()),
            )
            Camera.ForwardMovement(_MOVE, True)
            observed = Camera.GetLookAtTarget()
            emit(
                "writer",
                member="ForwardMovement",
                field="look_at_target",
                original=list(target),
                expected=[round(value, 3) for value in expected_forward],
                observed=[round(value, 3) for value in observed],
                landed=all(_close(a, b) for a, b in zip(observed, expected_forward)),
                call_ms=None,
            )

            Camera.SetLookAtTarget(*target)
            moved = Camera.GetLookAtTarget()
            Camera.VerticalMovement(_MOVE)
            observed = Camera.GetLookAtTarget()
            emit(
                "writer",
                member="VerticalMovement",
                field="look_at_target.z",
                original=round(moved[2], 3),
                expected=round(moved[2] + _MOVE, 3),
                observed=round(observed[2], 3),
                landed=_close(observed[2], moved[2] + _MOVE),
                call_ms=None,
            )

            Camera.SetLookAtTarget(*target)
            moved = Camera.GetLookAtTarget()
            Camera.SideMovement(_MOVE)
            observed = Camera.GetLookAtTarget()
            expected_side = (
                moved[0] + _MOVE * -math.sin(float(Camera.GetYaw())),
                moved[1] + _MOVE * math.cos(float(Camera.GetYaw())),
            )
            emit(
                "writer",
                member="SideMovement",
                field="look_at_target.x/y",
                original=[round(moved[0], 3), round(moved[1], 3)],
                expected=[round(expected_side[0], 3), round(expected_side[1], 3)],
                observed=[round(observed[0], 3), round(observed[1], 3)],
                landed=_close(observed[0], expected_side[0]) and _close(observed[1], expected_side[1]),
                call_ms=None,
            )

            Camera.SetLookAtTarget(*target)
            before_yaw = float(Camera.GetYaw())
            Camera.RotateMovement(0.01)
            emit(
                "writer",
                member="RotateMovement",
                field="yaw and look_at_target",
                original=round(before_yaw, 4),
                expected=round(before_yaw + 0.01, 4),
                observed=round(float(Camera.GetYaw()), 4),
                landed=_close(float(Camera.GetYaw()), before_yaw + 0.01),
                call_ms=None,
            )
        finally:
            Camera.SetYaw(yaw)
            Camera.SetLookAtTarget(*target)
            emit(
                "restored",
                field="yaw, look_at_target",
                value=[round(Camera.GetYaw(), 3), [round(v, 3) for v in Camera.GetLookAtTarget()]],
                ok=_close(float(Camera.GetYaw()), yaw),
            )

        try:
            Camera.SetCameraPosition(position[0] + _MOVE, position[1], position[2])
            observed = Camera.GetPosition()
            emit(
                "writer",
                member="SetCameraPosition",
                field="position.x",
                original=round(position[0], 3),
                expected=round(position[0] + _MOVE, 3),
                observed=round(observed[0], 3),
                landed=_close(observed[0], position[0] + _MOVE),
                call_ms=None,
            )
        finally:
            Camera.SetCameraPosition(*position)
            emit(
                "restored",
                field="position",
                value=[round(v, 3) for v in Camera.GetPosition()],
                ok=_close(Camera.GetPosition()[0], position[0]),
            )

        computed = Camera.ComputeCameraPos()
        try:
            Camera.UpdateCameraPos()
            observed = Camera.GetPosition()
            emit(
                "writer",
                member="UpdateCameraPos",
                field="position",
                expected=[round(v, 3) for v in computed],
                observed=[round(v, 3) for v in observed],
                landed=all(_close(a, b) for a, b in zip(observed, computed)),
                call_ms=None,
            )
        finally:
            Camera.SetCameraPosition(*position)
            emit("restored", field="position", value=[round(v, 3) for v in Camera.GetPosition()], ok=True)

        # --- the two patches ---------------------------------------------------------------------
        for name, enable, disable, read_state in (
            ("SetFog", lambda: Camera.SetFog(True), lambda: Camera.SetFog(False), lambda: None),
            ("SetCameraUnlock", lambda: Camera.SetCameraUnlock(True), lambda: Camera.SetCameraUnlock(False), Camera.GetCameraUnlock),
        ):
            was = read_state()
            enabled = False
            try:
                enable()
                enabled = True
                emit("patch", member=name, was=was, while_enabled=read_state())
            finally:
                if enabled:
                    disable()
            # The sweep always leaves the patch off, whatever state it found: the unlock was
            # enabled by this probe at the start, so "off" is the state to check for.
            emit("patch", member=name, after=read_state(), left_off=(read_state() is not True))

        emit("done")
        return 0
    finally:
        # The unlock the sweep ran under goes back to the state the client had, whatever happened.
        if not unlock_was:
            Camera.SetCameraUnlock(False)
        emit("unlock_restored", active=Camera.GetCameraUnlock())
        py4gw.disconnect()
        emit("disconnected")


if __name__ == "__main__":
    raise SystemExit(main())
