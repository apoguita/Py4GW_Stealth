"""Does ``Agent.GetNameByID`` answer through the client's decoder when nothing else is loading?

The direct experiment (``tests/probe_name_scheme.py``) proved the mechanism: one decode at a time
answers the client's text in ~140 ms. Wired into the member, two live runs answered nothing -- and the
one thing different in between is that the connection starts the string-table warm-up, which occupies
the client's game thread with dat commands of about a second each for minutes. This probe removes that
variable: it stops the warm-up immediately after connecting, then asks the member for a few names
repeatedly and prints what each call answers and what the slots are doing.

Usage: ``python tests/probe_name_member.py [report-path]``
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
ATTEMPTS = 12
GAP_S = 0.15


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
        emit("not_elevated")
        return 3

    client = py4gw.connect(clients[0])
    try:
        from py4gw.game_thread.shared_block import DecodeState
        from py4gw.internals import string_table
        from py4gw.ui.async_decode import decode_state

        # The one variable under test: stop the table warm-up so the client's game thread is free.
        string_table._stop_warmup()
        emit("warmup_stopped", status=string_table._last_load_status)

        own = int(Player.GetAgentID())
        ids = [
            int(agent_id)
            for agent_id in client.agent_array.get_context().GetAgentArray()
            if int(agent_id) != own
        ][:6]

        from py4gw import agent as agent_module

        for attempt in range(ATTEMPTS):
            for agent_id in ids:
                started = time.perf_counter()
                text = Agent.GetNameByID(agent_id)
                ms = (time.perf_counter() - started) * 1000.0
                pending = list(agent_module._name_requests.values())
                emit(
                    "attempt",
                    index=attempt,
                    agent_id=agent_id,
                    text=text,
                    ms=round(ms, 3),
                    in_flight=len(pending),
                    states=[decode_state(slot).name for slot in pending[:4]],
                    cached=len(agent_module._name_cache),
                    why=agent_module._name_debug[-1] if agent_module._name_debug else "",
                )
                if text:
                    break
            if attempt == 0 or attempt % 4 == 3:
                emit(
                    "progress",
                    attempt=attempt,
                    cached=len(agent_module._name_cache),
                    in_flight=len(agent_module._name_requests),
                    states=[decode_state(slot).name for slot in list(agent_module._name_requests.values())[:6]],
                )
            time.sleep(GAP_S)

        emit(
            "done",
            cached={raw.hex(): text for raw, text in list(agent_module._name_cache.items())[:6]},
            in_flight=len(agent_module._name_requests),
            states=[decode_state(slot).name for slot in agent_module._name_requests.values()],
            decoded_states=[DecodeState.DONE.name, DecodeState.FAILED.name],
        )
        return 0
    finally:
        py4gw.disconnect()
        emit("disconnected")


if __name__ == "__main__":
    raise SystemExit(main())
