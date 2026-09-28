"""Live probe: the render capture, checked against the client's own values.

Round 34 wired the capture into the bridge; round 35 pinned ``EndScene``'s prologue from a live read
(``tests/probe_render_entry.py``). This is the run that installs it and reads it back: it connects with the
**write** connection — which places this port's hooks, the operation the owner scoped — waits for a frame,
reads the pointer the capture kept, and then reads *that pointer* as the ``GwDxContext`` whose
``viewport_width``/``viewport_height`` are the numbers ``GW::render::GetViewportWidth/Height`` answer with
(``render_methods.cpp:56-63``). Those two words are the divisor the frame geometry has been waiting on.

Disconnecting is part of the probe, not an afterthought: it takes the capture's hook out first and rewrites
the client's own entry bytes, which is what the bridge's removal order is for. The report says whether the
hook was there and whether it is gone.

Usage: (elevated) python tests/probe_render_capture.py [report-path]
"""

from __future__ import annotations

import ctypes
import json
import sys
import time
from typing import Any

import py4gw
from py4gw.win32 import Win32

REPORT_PATH = sys.argv[1] if len(sys.argv) > 1 else ""

#: How long to wait for the client to render a frame with the hook in place.
WAIT_SECONDS = 8.0

#: A viewport wider or taller than this is not a screen; it is a pointer read at the wrong place.
IMPLAUSIBLE = 8192


def main() -> int:
    report: dict[str, Any] = {}
    win32 = Win32()
    clients = win32.find_guild_wars()
    if not clients:
        report["error"] = "no Guild Wars client is running"
        return write_report(report)

    process = clients[0]
    report["pid"] = int(process["pid"])

    connected: Any = None
    bridge: Any = None
    with py4gw.connect(process) as client:
        connected = client
        bridge = client._bridge
        report["observing_render"] = bool(bridge.observing_render)
        report["hooks_installed"] = sorted(bridge.require_hooker().installed)

        deadline = time.time() + WAIT_SECONDS
        started = time.time()
        context = 0
        while time.time() < deadline:
            context = int(bridge.render_context_address())
            if context:
                break
            time.sleep(0.02)
        report["seconds_to_first_capture"] = round(time.time() - started, 3)
        report["render_context"] = hex(context)

        if context:
            from py4gw.context.render_context import GwDxContextStruct

            size = ctypes.sizeof(GwDxContextStruct)
            raw = client.reader.read(context, size)
            report["bytes_read"] = len(raw)
            if len(raw) == size:
                record = GwDxContextStruct.from_buffer_copy(raw)
                width = int(record.viewport_width)
                height = int(record.viewport_height)
                report["viewport"] = {"width": width, "height": height}
                report["device"] = hex(int(record.device))
                report["plausible"] = (
                    0 < width <= IMPLAUSIBLE and 0 < height <= IMPLAUSIBLE
                )

        report["note"] = (
            "the write connection was used, so this run installed the bridge's hooks and disconnect "
            "removed them. The captured pointer is the first argument of the client's own EndScene, which "
            "is where native keeps Context::g_dx_context (render.cpp:88)."
        )

    report["observing_render_after_disconnect"] = bool(
        bridge.observing_render if bridge is not None else False
    )
    return write_report(report)


def write_report(report: dict[str, Any]) -> int:
    text = json.dumps(report, indent=2, ensure_ascii=False)
    print(text)
    if REPORT_PATH:
        with open(REPORT_PATH, "w", encoding="utf-8") as handle:
            handle.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
