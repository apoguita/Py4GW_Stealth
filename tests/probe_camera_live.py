"""``Camera`` against the live client: the reads, one write, and one patch toggle.

What only a running client can prove, in the order it is asked:

1. **the reads** — every getter against the client's own record, timed (they are field reads off one
   resolved pointer);
2. **a write** — ``SetPitch`` moves ``pitch_to_go`` by a thousandth of a radian and the client's own
   struct is read back to see it arrive, then the original value is put back. That is the assertion that
   the payload's ``WRITE_MEMORY`` operation reached the right field on the game's own thread, which is
   the one thing about this class that had never been exercised live;
3. **a patch** — ``SetCameraUnlock`` toggles the camera-update patch (``EB 0C`` on this attempt) and the
   client's bytes at the address are read before, during and after, so the toggle is proven by the
   client's memory rather than by this module's own flag.

The write is a thousandth of a radian and it is put back in the same breath; the patch is enabled and
disabled in the same breath. Nothing is left changed, and the probe disconnects when it is done.

Usage: ``python tests/probe_camera_live.py [report-path]``
"""

from __future__ import annotations

import json
import statistics
import sys
import time
from typing import Any

import py4gw
from py4gw.camera import Camera
from py4gw.win32 import Win32

REPORT_PATH = sys.argv[1] if len(sys.argv) > 1 else ""

#: The write this probe makes, and undoes: a thousandth of a radian of pitch target.
PITCH_DELTA = 0.001


def emit(stage: str, **values: Any) -> None:
    """Print one step and append it to the report, immediately."""

    line = json.dumps({"stage": stage, **values}, default=str)
    print(line, flush=True)
    if REPORT_PATH:
        with open(REPORT_PATH, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")


def main() -> int:
    win32 = Win32()
    clients = win32.find_guild_wars()
    if not clients:
        emit("no_client")
        return 1
    if not win32.is_elevated():
        emit("not_elevated", note="connecting asserts elevation")
        return 3

    started = time.perf_counter()
    client = py4gw.connect(clients[0])
    emit("connect", ms=round((time.perf_counter() - started) * 1000.0, 3), pid=client.pid)
    try:
        # 1. the reads
        reads: dict[str, Any] = {}
        samples: list[float] = []
        for name in (
            "GetLookAtAgentID",
            "GetMaxDistance",
            "GetYaw",
            "GetCurrentYaw",
            "GetPitch",
            "GetCameraZoom",
            "GetDistance2",
            "GetAccelerationConstant",
            "GetTimeInTheMap",
            "GetYawToGo",
            "GetPitchToGo",
            "GetDistanceToGo",
            "GetMaxDistance2",
            "GetFieldOfView",
            "GetFielsOfView2",
            "GetPosition",
            "GetLookAtTarget",
            "GetCameraPositionToGo",
            "GetCameraPositionInverted",
            "GetCameraUnlock",
        ):
            member = getattr(Camera, name)
            call = time.perf_counter()
            value = member()
            samples.append((time.perf_counter() - call) * 1000.0)
            reads[name] = value
        emit(
            "reads",
            values=reads,
            ms={"min": round(min(samples), 4), "median": round(statistics.median(samples), 4), "max": round(max(samples), 4)},
            count=len(samples),
        )
        emit("fov_probe", inside=Camera.IsPointInFOV(*Camera.GetLookAtTarget()[:2]))

        # 2. one write, and the client's own struct read back
        before = float(Camera.GetPitchToGo())
        started = time.perf_counter()
        Camera.SetPitch(before + PITCH_DELTA)
        write_ms = (time.perf_counter() - started) * 1000.0
        after = float(Camera.GetPitchToGo())
        Camera.SetPitch(before)
        restored = float(Camera.GetPitchToGo())
        emit(
            "write",
            field="pitch_to_go",
            before=before,
            after=after,
            expected=before + PITCH_DELTA,
            landed=abs(after - (before + PITCH_DELTA)) < 1e-6,
            restored=restored,
            restored_ok=abs(restored - before) < 1e-6,
            call_ms=round(write_ms, 3),
        )

        # 3. the patch, proven by the client's own bytes
        patterns, scanner = client._patterns, client._scanner
        resolution = patterns.resolve("camera.camera_update_patch_addr", scanner)
        address = int(resolution.value or 0)
        access = client.access
        original = bytes(access.read(address, 2)) if address else b""
        was_active = Camera.GetCameraUnlock()
        enabled = False
        try:
            Camera.SetCameraUnlock(True)
            enabled = True
            patched = bytes(access.read(address, 2)) if address else b""
            active_now = Camera.GetCameraUnlock()
        finally:
            # A patch that is left on is a client that behaves differently for the user, so the disable
            # runs even when the enable half raised: the first version of this class did leave one on
            # (see ``tools/recover_camera_patch.py``).
            if enabled:
                Camera.SetCameraUnlock(False)
        restored_bytes = bytes(access.read(address, 2)) if address else b""
        emit(
            "patch",
            address=hex(address),
            attempt=getattr(resolution, "selected_attempt", ""),
            original=original.hex(" "),
            while_enabled=patched.hex(" "),
            restored=restored_bytes.hex(" "),
            was_active=was_active,
            active_while_enabled=active_now,
            active_after=bool(Camera.GetCameraUnlock()),
            bytes_restored=restored_bytes == original,
            changed_while_enabled=patched != original,
        )
        emit("done")
        return 0
    finally:
        py4gw.disconnect()
        emit("disconnected")


if __name__ == "__main__":
    raise SystemExit(main())
