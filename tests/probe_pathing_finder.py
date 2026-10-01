"""Diagnose the client's own path finder: is our call reaching it at all, and what does it answer?

The port calls `pathing.find_path_func` exactly as Native does — six words, a 16-byte `PathPoint` per
endpoint, a 30-record array and a count word, all in the block's data region, pushed right to left by
the payload's `STACK_WORDS` form. Live, the client answers **zero points** at every distance tried, and
the port's `AutoPathing.get_path` then takes the source's own navmesh fallback. Before concluding
anything about the client, this asks the questions that separate the cases:

1. **Does the client write the count word?** The word is pre-filled with a sentinel
   (`0xDEADBEEF`) instead of being cleared, so a zero afterwards means *the function ran and said no
   points*, while the sentinel surviving means *it never wrote* — a different fault with a different
   fix (our argument, its address, or the call itself).
2. **Does it fill the array?** The 30 records are pre-filled with `0xCC`, so a path that is written but
   not counted, or points written past `count` records, is visible in the bytes.
3. **Does the endpoint's `zplane` matter?** The engine's `GamePos` carries one, and the port's probe
   passed `0` for both ends; the player's own `pos.zplane` is tried beside it.
4. **Does a real route destination answer?** Beside the probe's "4000 units east" goal, the client's own
   travel portals are asked (`Map.Pathing.GetTravelPortals`).

Nothing is walked and nothing moves: the finder computes a path, it does not take one. Elevated, one
connection, then the hooks come out.

Usage: python tests/probe_pathing_finder.py [report-path]
"""

from __future__ import annotations

import json
import struct
import sys
import time
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

REPORT_PATH = "live_reports/pathing_finder_diagnostic.json"

#: Written into the count word before the call: only the client can turn this into a real count.
SENTINEL = 0xDEADBEEF

#: Written into every byte of the 30-record array before the call, so the client's own writes show.
ARRAY_FILL = 0xCC

#: How long to wait after the call before reading the block back, in case the answer lands late.
SETTLE_SECONDS = 0.35


def _prepare_and_call(
    client: Any,
    start: tuple[float, float, int],
    goal: tuple[float, float, int],
    array_offset: int,
    count_offset: int,
    start_offset: int,
    goal_offset: int,
    arguments_offset: int,
    argument_words: int,
    point_size: int,
    max_points: int,
    range_units: float,
    function: str,
) -> dict[str, Any]:
    """One call, with the sentinel count and the filled array, read back byte for byte."""

    from py4gw.game_thread.shared_block import CallForm, float_bits

    bridge = client.bridge
    bridge.write_data(start_offset, struct.pack("<ffI", float(start[0]), float(start[1]), int(start[2]) & 0xFFFFFFFF) + b"\x00\x00\x00\x00")
    bridge.write_data(goal_offset, struct.pack("<ffI", float(goal[0]), float(goal[1]), int(goal[2]) & 0xFFFFFFFF) + b"\x00\x00\x00\x00")
    count_address = bridge.data_address(count_offset, 4)
    array_address = bridge.data_address(array_offset, max_points * point_size)
    bridge.write_data(count_offset, struct.pack("<I", SENTINEL))
    bridge.write_data(array_offset, bytes([ARRAY_FILL]) * (max_points * point_size))
    bridge.write_data(
        arguments_offset,
        b"".join(
            struct.pack("<I", word)
            for word in (
                bridge.data_address(start_offset, 16),
                bridge.data_address(goal_offset, 16),
                float_bits(range_units),
                max_points,
                count_address,
                array_address,
            )
        ),
    )

    started = time.monotonic()
    client.call_function(function, CallForm.STACK_WORDS, arguments_offset, argument_words)
    seconds = time.monotonic() - started
    time.sleep(SETTLE_SECONDS)

    raw_count = bridge.read_data(count_offset, 4)
    count = struct.unpack("<I", raw_count)[0]
    raw_array = bridge.read_data(array_offset, max_points * point_size)
    points = []
    for index in range(min(count, max_points)):
        offset = index * point_size
        x, y, zplane = struct.unpack_from("<ffI", raw_array, offset)
        pointer = struct.unpack_from("<I", raw_array, offset + 12)[0]
        points.append({"x": x, "y": y, "zplane": zplane, "t": hex(pointer)})
    return {
        "call_seconds": round(seconds, 3),
        "count_word_before": hex(SENTINEL),
        "count_word_after": hex(count),
        "count_written": count != SENTINEL,
        "count": None if count == SENTINEL else count,
        "array_first_48_bytes": raw_array[:48].hex(" "),
        "array_touched": raw_array[: max_points * point_size] != bytes([ARRAY_FILL]) * (max_points * point_size),
        "points": points,
    }


def main() -> int:
    from py4gw.win32 import Win32

    win32 = Win32()
    argv = list(sys.argv[1:])
    report_path = argv[0] if argv else REPORT_PATH
    clients = win32.find_guild_wars()
    report: dict[str, Any] = {"stage": "finder-diagnostic"}
    if not clients:
        report["error"] = "no Guild Wars client is running"
        print(json.dumps(report, indent=2))
        return 1
    process = clients[0]
    pid = int(process["pid"])
    report["pid"] = pid
    report["controller_elevated"] = bool(win32.is_elevated())

    import py4gw

    from py4gw.agent import Agent
    from py4gw.map import Map
    from py4gw.pathing import (
        FIND_PATH_FUNC,
        FIND_PATH_RANGE,
        MAX_PATH_POINTS,
        PATHING_ARGUMENTS_OFFSET,
        PATHING_ARGUMENT_WORDS,
        PATHING_ARRAY_OFFSET,
        PATHING_COUNT_OFFSET,
        PATHING_GOAL_OFFSET,
        PATHING_START_OFFSET,
        PATH_POINT_SIZE,
    )
    from py4gw.player import Player

    from tests.probe_party_live import entry_is_original

    if not entry_is_original(win32, pid):
        report["error"] = "another controller is attached; nothing was done"
        print(json.dumps(report, indent=2))
        return 7

    with py4gw.connect(process, game_thread=True) as client:
        report["find_path_func"] = FIND_PATH_FUNC
        report["resolves"] = bool(client.resolves(FIND_PATH_FUNC))
        agent_id = int(Player.GetAgentID())
        x, y = Agent.GetXY(agent_id)
        agent = Player.GetAgent()
        zplane = int(getattr(getattr(agent, "pos", None), "zplane", 0) or 0)
        report["player"] = {"agent_id": agent_id, "x": x, "y": y, "zplane": zplane}
        report["map_id"] = Map.GetMapID()
        print(f"player {agent_id} at ({x:.1f}, {y:.1f}) zplane={zplane} map={report['map_id']}")

        cases: list[tuple[str, tuple[float, float, int], tuple[float, float, int]]] = [
            ("4000 east, zplane 0 (what the probe passed)", (float(x), float(y), 0), (float(x) + 4000.0, float(y), 0)),
            ("4000 east, the player's own zplane", (float(x), float(y), zplane), (float(x) + 4000.0, float(y), zplane)),
            ("600 east, the player's own zplane", (float(x), float(y), zplane), (float(x) + 600.0, float(y), zplane)),
        ]

        portals = []
        try:
            portals = list(Map.Pathing.GetTravelPortals() or [])
            report["travel_portals"] = [
                {"x": float(p[0]), "y": float(p[1])} if isinstance(p, (list, tuple)) and len(p) >= 2 else str(p)
                for p in portals[:6]
            ]
        except Exception as error:  # noqa: BLE001 - reported
            report["travel_portals"] = f"{type(error).__name__}: {error}"
        if portals:
            first = portals[0]
            if isinstance(first, (list, tuple)) and len(first) >= 2:
                cases.append(
                    (
                        "the first travel portal, the player's own zplane",
                        (float(x), float(y), zplane),
                        (float(first[0]), float(first[1]), zplane),
                    )
                )

        results: dict[str, Any] = {}
        for label, start, goal in cases:
            # Paced: the client answers one call at a time.
            time.sleep(0.75)
            result = _prepare_and_call(
                client,
                start,
                goal,
                PATHING_ARRAY_OFFSET,
                PATHING_COUNT_OFFSET,
                PATHING_START_OFFSET,
                PATHING_GOAL_OFFSET,
                PATHING_ARGUMENTS_OFFSET,
                PATHING_ARGUMENT_WORDS,
                PATH_POINT_SIZE,
                MAX_PATH_POINTS,
                FIND_PATH_RANGE,
                FIND_PATH_FUNC,
            )
            result["start"] = start
            result["goal"] = goal
            results[label] = result
            print(
                f"{label}: count={'sentinel (never written)' if not result['count_written'] else result['count']}"
                f" array_touched={result['array_touched']} in {result['call_seconds']}s"
            )
        report["cases"] = results

    report["hooks_original_after_disconnect"] = entry_is_original(win32, pid)
    text = json.dumps(report, indent=2, ensure_ascii=False, default=str)
    print(text)
    with open(report_path, "w", encoding="utf-8") as handle:
        handle.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
