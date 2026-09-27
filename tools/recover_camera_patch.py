"""Put back the camera-update patch a failed disable left in the client.

``Camera.SetCameraUnlock(False)`` re-resolved the patch address after the patch was already applied; the
pattern those resolvers match is the *unpatched* code (``offsets/camera.json``: ``89 0E DD D9 89 56 04
DD`` and ``8B 45 E8 8B 4D EC 8B 55 F0``), and the patch rewrites the first two bytes to ``EB 0C`` /
``EB 0F``, so the resolve found nothing, raised, and the unlock stayed on in the live client. The class
now caches the address and the bytes, but the client that was left patched needs its own bytes back.

This is recovery, not a port: it scans the client's own module for the **patched** form of each pattern
-- which is unique -- verifies it is the patched form, writes the two original bytes back, and reads them
again. Nothing else is touched, and a client that is not patched is reported and left alone.

Usage (elevated): ``python tools/recover_camera_patch.py [report-path]``
"""

from __future__ import annotations

import json
import sys
from typing import Any

from py4gw.memory import ProcessMemoryReader
from py4gw.win32 import Win32
from py4gw.win32.write_access import WriteAccess

REPORT_PATH = sys.argv[1] if len(sys.argv) > 1 else ""

#: ``(original two bytes, patched image, what the pattern is)`` — the patched image is the source's own
#: pattern with its first two bytes replaced by the patch bytes (``camera_patterns.cpp:43-51``).
PATCHES = (
    (b"\x89\x0E", bytes.fromhex("EB 0C DD D9 89 56 04 DD"), "camera update (vs2017 attempt)"),
    (b"\x8B\x45", bytes.fromhex("EB 0F E8 8B 4D EC 8B 55 F0"), "camera update (vs2022 attempt)"),
)


def emit(stage: str, **values: Any) -> None:
    """Print one step and append it to the report."""

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
        emit("not_elevated", note="restoring bytes needs the write transport")
        return 3

    pid = int(clients[0]["pid"])
    module = win32.get_main_module(pid)
    base, size = int(module["base_address"]), int(module["size"])
    reader = ProcessMemoryReader(win32, pid)
    access = WriteAccess(pid)
    try:
        image = reader.read(base, size)
        emit("image", pid=pid, base=hex(base), size=size)

        for original, patched, label in PATCHES:
            hits = []
            start = image.find(patched)
            while start != -1 and len(hits) < 4:
                hits.append(start)
                start = image.find(patched, start + 1)
            emit("scan", patch=label, patched=patched.hex(" "), hits=[hex(base + h) for h in hits])
            if len(hits) != 1:
                emit(
                    "skip",
                    patch=label,
                    reason="no patched site" if not hits else "more than one site, refusing",
                )
                continue

            address = base + hits[0]
            current = bytes(reader.read(address, 2))
            if current != patched[:2]:
                emit("skip", patch=label, reason=f"the bytes at {hex(address)} are {current.hex(' ')}")
                continue
            access.write(address, original)
            after = bytes(reader.read(address, 2))
            emit(
                "restored",
                patch=label,
                address=hex(address),
                wrote=original.hex(" "),
                now=after.hex(" "),
                ok=after == original,
            )
        emit("done")
        return 0
    finally:
        access.close()
        reader.close()


if __name__ == "__main__":
    raise SystemExit(main())
