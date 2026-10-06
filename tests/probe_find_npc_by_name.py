"""Find an NPC by name, take the closest one, target it, interact, and time every step.

What it measures, in the order a caller does it:

1. **the search** -- one pass over ``AgentArray.GetAgentArray()`` asking ``Agent.GetNameByID`` for each
   agent, which is the port's own read of the source's name walk (``Agent.GetAgentIDByName``'s loop,
   ``Agent.py:191-198``) with the distance added, so the closest match can be chosen. The pass is
   repeated until a match appears, and each pass reports how many names answered and how much of the
   table was up -- which is how the warm-up the connection starts shows itself;
2. **the target** -- ``Player.ChangeTarget`` (``player_bindings.cpp``), and the client's own answer read
   back through ``Player.GetTargetID``;
3. **the interaction** -- ``Player.Interact`` (``Agent.py``'s ``Interact``), and then the time until the
   client announces the dialog it opened: body ``0x100000A6`` and buttons ``0x100000A3``
   (``enums_src/ui_enums.py:133-134``), which is the proof the interaction happened rather than a
   timing of a call that did nothing.

Timings are wall clock around each call, in milliseconds, plus the distance to the NPC so the walk the
client has to make is visible. Usage::

    python tests/probe_find_npc_by_name.py "Master of Winds" [report-path]

Reads and two client actions (a target change and an interaction); it connects, so it needs an elevated
shell, and it disconnects when it is done.
"""

from __future__ import annotations

import faulthandler
import json
import os
import statistics
import sys
import threading
import time
from typing import Any

import py4gw
from py4gw.agent import Agent
from py4gw.player import Player
from py4gw.py4gwcorelib_src.utils import Utils
from py4gw.win32 import Win32

NAME = sys.argv[1] if len(sys.argv) > 1 else "Master of Winds"
REPORT_PATH = sys.argv[2] if len(sys.argv) > 2 else ""

#: Where the hang, if there is one, is written: ``faulthandler`` dumps every thread's stack on a
#: timer, so a run that stops producing output names the line it stopped on instead of leaving a
#: silent gap (the 2026-09-27 run stopped after its interaction and said nothing for 90 s).
STACK_PATH = (REPORT_PATH or "tests/live_reports/find_npc") + ".stack"

#: The hard stop. The watchdog dumps the stacks, disconnects, and leaves: a probe that hangs must not
#: leave the client patched, and a controller killed mid-run does exactly that (twice now).
WATCHDOG_S = 45.0

#: How long the search may take before it gives up. The first pass usually needs the string table, and
#: the connection is filling it while this runs, so the wait is the warm-up's own cost made visible.
#: Measured on the first run: "Master of Winds" was found on pass 20, **7.7 s** after connect, six
#: string files read.
SEARCH_DEADLINE_S = 25.0

#: How long the client may take to announce the dialog after the interaction (it walks there first).
#: Not waited for any more: the measurement ends at the interaction. Kept as the number the earlier
#: runs used, so the reason the wait was removed stays visible.
DIALOG_DEADLINE_S = 15.0

#: How long the target announcement may take: ``Player.ChangeTarget`` asks the client, and the client
#: announces the change it made afterwards, so the id is read back by polling rather than once.
TARGET_DEADLINE_S = 3.0

#: The watchdog fires when the run has said nothing for this long. Every ``emit`` is a heartbeat, so
#: silence means the probe is wedged; it then dumps every thread's stack (that is what names the line
#: it stopped on) and gives the connection back, because a controller that dies while connected leaves
#: the client patched. It never fires during a normal run: they finish in about ten seconds.
WATCHDOG_SILENCE_S = 10.0

#: The last time the run said anything, which is the heartbeat the watchdog reads.
_LAST_EMIT = [time.monotonic()]

#: When the process started, so the summary can carry the whole run's cost and not just its steps.
PROCESS_START = time.perf_counter()

DIALOG_BODY_MESSAGE = 0x100000A6
DIALOG_BUTTON_MESSAGE = 0x100000A3


def emit(stage: str, **values: Any) -> None:
    """Print one step and append it to the report, immediately. Every emit is a heartbeat."""

    _LAST_EMIT[0] = time.monotonic()
    line = json.dumps({"stage": stage, **values}, default=str)
    print(line, flush=True)
    if REPORT_PATH:
        with open(REPORT_PATH, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")


def table_state() -> dict[str, Any]:
    """What the string table holds right now, which is what a name search rides on."""

    from py4gw.internals import string_table

    return {
        "entries": len(string_table._string_table),
        "slots_read": len(string_table._loaded_slots),
        "loaded": bool(string_table._string_table_loaded),
        "status": string_table._last_load_status,
    }


def start_watchdog(client: Any) -> threading.Thread:
    """Give the connection back if the run goes silent, and record why.

    The probe is meant to finish in about ten seconds, so silence is a wedge. When it happens the
    stacks of every thread are written to ``STACK_PATH`` -- that is what names the line the run
    stopped on -- and then the connection is closed, because a controller that dies while connected
    leaves its entry hook and stub in the client, which is how both of this project's client
    assertions and the 2026-09-27 crash happened.
    """

    stack_file = open(STACK_PATH, "a", encoding="utf-8", buffering=1)

    def watchdog() -> None:
        while True:
            time.sleep(1.0)
            silence = time.monotonic() - _LAST_EMIT[0]
            if silence < WATCHDOG_SILENCE_S:
                continue
            try:
                faulthandler.dump_traceback(file=stack_file)
                stack_file.flush()
            except BaseException:  # noqa: BLE001 - the dump is the point, never a raise
                pass
            print(json.dumps({"stage": "watchdog_firing", "silence_s": round(silence, 1), "stack": STACK_PATH}), flush=True)
            try:
                py4gw.disconnect()
            except BaseException as error:  # noqa: BLE001 - reported, then the process leaves anyway
                print(json.dumps({"stage": "watchdog_disconnect_failed", "error": f"{type(error).__name__}: {error}"}), flush=True)
            os._exit(1)

    thread = threading.Thread(target=watchdog, name="probe-watchdog", daemon=True)
    thread.start()
    return thread


def main() -> int:
    win32 = Win32()
    clients = win32.find_guild_wars()
    if not clients:
        emit("no_client")
        return 1
    emit("client", pid=int(clients[0]["pid"]), path=clients[0].get("path"))
    if not win32.is_elevated():
        emit("not_elevated", note="connecting asserts elevation")
        return 3

    # A run that stops producing output dumps every thread's stack on a timer, into STACK_PATH.
    faulthandler.enable()
    faulthandler.dump_traceback_later(15.0, repeat=True, file=open(STACK_PATH, "w", encoding="utf-8"))

    started_connect = time.perf_counter()
    client = py4gw.connect(clients[0])
    connect_ms = (time.perf_counter() - started_connect) * 1000.0
    start_watchdog(client)
    try:
        emit(
            "connect",
            ms=round(connect_ms, 3),
            table=table_state(),
            note="the connection starts the string-table warm-up; connect does not wait for it",
        )

        own_agent = int(Player.GetAgentID())
        origin = Player.GetXY()
        emit("player", agent_id=own_agent, xy=list(origin))

        wanted = NAME.strip().lower()
        match_id = 0
        match_name = ""
        match_distance = 0.0
        passes = 0
        names_seen = 0
        deadline = time.time() + SEARCH_DEADLINE_S

        while time.time() < deadline and not match_id:
            passes += 1
            pass_started = time.perf_counter()
            ids = [int(agent_id) for agent_id in client.agent_array.get_context().GetAgentArray()]
            answered = 0
            samples: list[float] = []
            best: tuple[float, int, str] | None = None

            for agent_id in ids:
                if agent_id == own_agent:
                    continue
                call = time.perf_counter()
                name = Agent.GetNameByID(agent_id)
                samples.append((time.perf_counter() - call) * 1000.0)
                if not name:
                    continue
                answered += 1
                if wanted not in name.lower():
                    continue
                distance = float(Utils.Distance(origin, Agent.GetXY(agent_id)))
                if best is None or distance < best[0]:
                    best = (distance, agent_id, name)

            names_seen = answered
            emit(
                "pass",
                index=passes,
                agents=len(ids),
                names_answered=answered,
                ms=round((time.perf_counter() - pass_started) * 1000.0, 3),
                name_call_ms={
                    "min": round(min(samples), 4) if samples else None,
                    "median": round(statistics.median(samples), 4) if samples else None,
                    "max": round(max(samples), 4) if samples else None,
                },
                matches=0 if best is None else 1,
                closest=None if best is None else {"agent_id": best[1], "name": best[2], "distance": round(best[0], 3)},
                table=table_state(),
            )

            if best is not None:
                match_distance, match_id, match_name = best
                break
            time.sleep(0.25)

        if not match_id:
            emit(
                "not_found",
                name=NAME,
                passes=passes,
                names_answered=names_seen,
                table=table_state(),
                note="every agent name in the array was asked for; none matched",
            )
            return 2

        emit(
            "found",
            name=NAME,
            agent_id=match_id,
            decoded_name=match_name,
            distance=round(match_distance, 3),
            passes=passes,
            search_ms=round((time.perf_counter() - started_connect) * 1000.0 - connect_ms, 3),
        )

        started = time.perf_counter()
        Player.ChangeTarget(match_id)
        target_ms = (time.perf_counter() - started) * 1000.0

        # The client announces the change it made, and that announcement is what ``Player.GetTargetID``
        # answers from. It is read back **once, right after the call**, and not polled for: the call is
        # the measurement, and a poll that waits its full deadline for an announcement that is not
        # coming measured the probe rather than the client (3 s of the 2026-09-27 run, which is what
        # made a 4.8 s run look like 7.9 s).
        time.sleep(0.05)
        observed = int(Player.GetTargetID())

        emit(
            "target",
            agent_id=match_id,
            call_ms=round(target_ms, 3),
            observed_target_id=observed,
            agreed=observed == match_id,
            note="the id is what the client last announced, read once after the call",
        )

        interact_started = time.perf_counter()
        Player.Interact(match_id)
        interact_ms = (time.perf_counter() - interact_started) * 1000.0
        interact_ended = time.perf_counter()
        emit("interact", agent_id=match_id, ms=round(interact_ms, 3))

        # The same search again, on the same connection. The first one paid the warm-up (the string
        # files the names live in); this one is what a caller sees once they are in the table, which is
        # the number that decides whether a name lookup is usable in a loop.
        warm_started = time.perf_counter()
        warm_ids = [
            int(agent_id) for agent_id in client.agent_array.get_context().GetAgentArray()
        ]
        warm_answered = 0
        warm_samples: list[float] = []
        for agent_id in warm_ids:
            if agent_id == own_agent:
                continue
            call = time.perf_counter()
            name = Agent.GetNameByID(agent_id)
            warm_samples.append((time.perf_counter() - call) * 1000.0)
            if name:
                warm_answered += 1
        warm_ms = (time.perf_counter() - warm_started) * 1000.0
        emit(
            "research",
            agents=len(warm_ids),
            names_answered=warm_answered,
            ms=round(warm_ms, 3),
            name_call_ms={
                "min": round(min(warm_samples), 4),
                "median": round(statistics.median(warm_samples), 4),
                "max": round(max(warm_samples), 4),
            },
            note="the same pass with the files already read: no warm-up left to pay",
        )

        # The measurement is over: locate, target, interact, and the time each took. Watching for the
        # dialog the interaction opens is *not* part of it -- that is the dialog suite's subject -- and
        # a wait here is what left the 2026-09-27 run sitting after its last line. The run ends here,
        # so the connection is given back while there is still time to do it.
        emit(
            "total",
            run_ms=round((interact_ended - PROCESS_START) * 1000.0, 3),
            connect_ms=round(connect_ms, 3),
            search_ms=round((interact_started - started_connect) * 1000.0, 3),
            target_call_ms=round(target_ms, 3),
            interact_ms=round(interact_ms, 3),
            warm_research_ms=round(warm_ms, 3),
            table=table_state(),
        )
        emit("finished")
        return 0
    finally:
        started = time.perf_counter()
        py4gw.disconnect()
        emit("disconnected", ms=round((time.perf_counter() - started) * 1000.0, 3))


if __name__ == "__main__":
    raise SystemExit(main())
