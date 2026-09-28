"""Does ``Effects.GetAlcoholLevel`` answer the intensity the client's own call carried?

Native's answer is ``g_alcohol_level``, the word its entry hook stores from the ``intensity``
argument of the client's post-process effect function (``effects.cpp:15,26-41``), and the member that
returns it is ``PyEffects.GetAlcoholLevel`` (``effects_bindings.cpp:37-39``). This port hooks that same
function as the connection's third observed function and registers the effects module's handler on its
own event kind, so the experiment is the source's own: make the client call the function with a level
and read the level back.

The call is ``Effects.ApplyDrunkEffect(3, 0)`` — the binding's own member for that function
(``effects_bindings.cpp:182-183``), so no test-only path into the client is used — and then
``ApplyDrunkEffect(0, 0)`` clears it again, which is what the client itself does when the effect ends.

Run it from an **elevated** shell, because connecting is a write:

    python tests/probe_alcohol_live.py live_reports/alcohol_report.jsonl

It connects, watches, calls, reads, clears, and disconnects — restoring all three hooked functions'
own bytes. It must be allowed to finish; a killed run leaves a hook in the client.
"""

from __future__ import annotations

import json
import sys
import time
from typing import Any

import py4gw
from py4gw.effect import Effects
from py4gw.win32 import Win32

REPORT_PATH = sys.argv[1] if len(sys.argv) > 1 else ""
#: How long the observer's event may take to arrive through the listener thread.
WAIT_S = 4.0
POLL_S = 0.05


def emit(stage: str, **values: Any) -> None:
    """Print one step and append it to the report, immediately."""

    line = json.dumps({"stage": stage, **values}, default=str)
    print(line, flush=True)
    if REPORT_PATH:
        with open(REPORT_PATH, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")


def wait_for(level: int) -> tuple[int, float]:
    """Poll the member until it answers ``level``, and report what it answered and how long it took."""

    started = time.perf_counter()
    answer = Effects.GetAlcoholLevel()
    while (time.perf_counter() - started) < WAIT_S:
        answer = Effects.GetAlcoholLevel()
        if answer == level:
            break
        time.sleep(POLL_S)
    return int(answer), round((time.perf_counter() - started) * 1000.0, 3)


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
    try:
        bridge: Any = client._bridge
        emit(
            "connected",
            pid=client.pid,
            hooks=sorted(bridge.require_hooker().installed),
            observing=bridge.observing,
            observing_effects=bridge.observing_effects,
            effects_watch_address=bridge.effects_watch_address,
            effects_observer_address=bridge.effects_observer_address,
        )

        from py4gw import effect as effect_module

        emit(
            "start",
            level=Effects.GetAlcoholLevel(),
            watch=effect_module._WATCHED_INTENSITIES,
            resolves_post_process=client.resolves("effects.post_process_effect_func"),
        )

        emit("call", intensity=3, tint=0)
        Effects.ApplyDrunkEffect(3, 0)
        answer, ms = wait_for(3)
        emit("after_level_3", level=answer, ms=ms)

        emit("call", intensity=0, tint=0)
        Effects.ApplyDrunkEffect(0, 0)
        answer, ms = wait_for(0)
        emit("after_level_0", level=answer, ms=ms)
    finally:
        py4gw.disconnect()
        emit("disconnected")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
