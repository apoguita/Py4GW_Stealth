"""One NPC's name, from the live client: one agent, one read, one decode.

Nothing else. This exists because the broad sweeps proved coverage but never proved the *single*
thing a caller does — ask for one agent's name — and because a narrow run is a short run: connecting
installs the capability layer (the string table is read out of GW.dat through the client, which
needs it), so the window in which an interrupted run could leave a patch behind is seconds.

What it does, in order, printing each step to stdout **and** to the report file as it goes, so an
interruption still leaves the answer that was already found:

1. find the client, ``py4gw.connect()`` it;
2. report whether the string table came up with the connection (``ConnectedClient.__init__`` refreshes
   the ``TextParser`` context once, which is where Reforged's first frame loads it);
3. take the **first non-player agent that has an encoded name**;
4. print, for that one agent: the id, the pointer the walk answered with, the raw bytes,
   ``Agent.GetEncNameStrByID``, and ``Agent.GetNameByID`` — the decoded text;
5. ``py4gw.disconnect()`` and stop.

Usage: python tests/probe_one_npc_name.py [report-path]
"""

from __future__ import annotations

import json
import sys
import time
from typing import Any

import py4gw
from py4gw.agent import Agent
from py4gw.player import Player
from py4gw.win32 import Win32

REPORT_PATH = sys.argv[1] if len(sys.argv) > 1 else ""

#: How many agents to look at before giving up on finding a named non-player one. A name is the
#: first thing most agents have, so this is a bound on a search that normally ends on the first try.
CANDIDATE_LIMIT = 10

#: The player-prefixed encoded form (``string_table._PLAYER_PREFIX``): those names are other
#: characters', and what this probe wants is an NPC's.
PLAYER_PREFIX = [0xA9, 0x0B]


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
    emit("client", pid=int(clients[0]["pid"]), path=clients[0].get("path"))
    if not win32.is_elevated():
        emit(
            "not_elevated",
            note="run this from an elevated shell: a name needs the client's own GW.dat read, and "
            "connecting (which is what installs that path) requires elevation",
        )
        return 3

    client = py4gw.connect(clients[0])
    try:
        from py4gw.internals import string_table

        emit(
            "connected",
            string_table_loaded=bool(string_table._string_table_loaded),
            table_status=string_table._last_load_status,
            entries=len(string_table._string_table),
        )

        own_agent = int(Player.GetAgentID())
        view = client.agent_array.get_context()
        agents = [int(agent_id) for agent_id in view.GetAgentArray()]
        emit("agents", total=len(agents), own_agent=own_agent)

        target_id = 0
        looked_at = 0
        for agent_id in agents:
            if looked_at >= CANDIDATE_LIMIT:
                break
            if agent_id == own_agent:
                continue
            looked_at += 1
            encoded = Agent.GetEncNameByID(agent_id)
            if not encoded:
                continue
            if encoded[:2] == PLAYER_PREFIX:
                emit("skipped_player_form", agent_id=agent_id, bytes=len(encoded))
                continue
            target_id = agent_id
            break

        if not target_id:
            emit("no_npc_name_found", looked_at=looked_at)
            return 2

        encoded = Agent.GetEncNameByID(target_id)
        emit(
            "npc",
            agent_id=target_id,
            name_bytes=encoded,
            byte_count=len(encoded),
            encoded_string=Agent.GetEncNameStrByID(target_id),
        )

        # The three parts, timed and reported apart, because they have three different costs: the
        # fetch (one index + one record read), the decode's first call (which reads the one string
        # file this name's entry lives in) and the decode's next call (the cache the source answers
        # from once a name has been decoded).
        started = time.perf_counter()
        Agent.GetEncNameByID(target_id)
        emit("timing_fetch_ms", value=round((time.perf_counter() - started) * 1000, 3))

        started = time.perf_counter()
        first = Agent.GetNameByID(target_id)
        emit(
            "timing_first_decode_ms",
            value=round((time.perf_counter() - started) * 1000, 3),
            answer=first,
            table_status=string_table._last_load_status,
        )

        deadline = time.time() + 5.0
        second = ""
        while time.time() < deadline:
            second = Agent.GetNameByID(target_id)
            if second:
                break
            time.sleep(0.05)

        started = time.perf_counter()
        third = Agent.GetNameByID(target_id)
        emit(
            "timing_cached_decode_ms",
            value=round((time.perf_counter() - started) * 1000, 3),
            answer=third,
            table_status=string_table._last_load_status,
        )
        emit(
            "result",
            ok=bool(second),
            agent_id=target_id,
            name=second,
            is_name_ready=Agent.IsNameReady(target_id),
        )
        return 0
    finally:
        py4gw.disconnect()
        emit("disconnected")


if __name__ == "__main__":
    raise SystemExit(main())
