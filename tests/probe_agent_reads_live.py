"""Read-only probe: do the agent reads follow the client, or answer a stored record?

There is no connection here, no hook, no call and no elevation: it opens a read-only handle, samples
the player's position through the ported members, and reports whether those reads **move** while the
character moves. That is the whole test — a read of a dereferenced record must be taken when it is
asked for, which is what ``README.md`` means by *"never cache a dereferenced pointer, because that is
map-scoped"*.

It exists because the opposite was measured live on 2026-10-05: with the per-id record cache being
served, a character walked 500 units in 1.6 s while ``Agent.GetXY`` answered the identical
coordinates to the millimetre for the whole walk, and only ``Agent.IsMoving`` — which converts to a
living record and re-reads — tracked it. The cache served a *materialized snapshot* of the record,
so every field read straight off it was frozen for the life of the connection.

**Move the character while this runs** (mouse-click somewhere in the game): the probe reports how many
distinct positions the reads produced and whether they advanced, and where two independent member
paths disagree.

Usage::

    python tests/probe_agent_reads_live.py [report-path] [--seconds 20] [--pid PID]
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

REPORT_PATH = "tests/live_reports/agent_reads_live.json"
DEFAULT_SECONDS = 20.0
SAMPLE_SECONDS = 0.25


def _ask(call: Any) -> Any:
    """Run one member and report what it answered, or exactly how it refused."""

    try:
        return call()
    except Exception as error:  # noqa: BLE001 - reported, never hidden
        return f"{type(error).__name__}: {error}"


def main() -> int:
    from py4gw import client as client_module
    from py4gw.agent import Agent
    from py4gw.map import Map
    from py4gw.memory import ProcessMemoryReader
    from py4gw.player import Player
    from py4gw.scanner import PatternCatalog, RemoteScanner
    from py4gw.win32 import Win32

    from tests.probe_party_live import _LiveClient

    argv = list(sys.argv[1:])
    seconds = DEFAULT_SECONDS
    pid_argument = ""
    for flag, target in (("--seconds", "seconds"), ("--pid", "pid")):
        if flag in argv:
            index = argv.index(flag)
            value = argv[index + 1]
            del argv[index : index + 2]
            if target == "seconds":
                seconds = float(value)
            else:
                pid_argument = value
    report_path = argv[0] if argv else REPORT_PATH

    report: dict[str, Any] = {"stage": "agent-reads", "seconds": seconds}
    win32 = Win32()
    clients = win32.find_guild_wars()
    if not clients:
        report["error"] = "no Guild Wars client is running"
        return _write(report, report_path, 1)
    process = next(
        (c for c in clients if pid_argument and int(c["pid"]) == int(pid_argument)), clients[0]
    )
    pid = int(process["pid"])
    report["pid"] = pid
    report["controller_elevated"] = bool(win32.is_elevated())
    report["probe"] = "read-only: nothing was connected, called or written"

    module = win32.get_main_module(pid)
    reader = ProcessMemoryReader(win32, pid)
    try:
        scanner = RemoteScanner(reader, int(module["base_address"]), int(module["size"]))
        scanner.initialize()
        patterns = PatternCatalog.from_directory("offsets")
        client_module._current_client = _LiveClient(pid, reader, scanner, patterns)

        agent_id = int(Player.GetAgentID())
        report["player_agent_id"] = agent_id
        report["map_id"] = _ask(Map.GetMapID)
        print(f"sampling agent {agent_id} for {seconds:.0f}s — MOVE THE CHARACTER NOW (click to walk)")

        samples: list[dict[str, Any]] = []
        started = time.monotonic()
        while time.monotonic() - started < seconds:
            x, y = _ask(lambda: Agent.GetXY(agent_id))
            px, py = _ask(lambda: Player.GetXY())
            sample = {
                "t": round(time.monotonic() - started, 2),
                "agent_xy": [round(float(x), 3), round(float(y), 3)]
                if not isinstance(x, str)
                else x,
                "player_xy": [round(float(px), 3), round(float(py), 3)]
                if not isinstance(px, str)
                else px,
                "moving": _ask(lambda: Agent.IsMoving(agent_id)),
            }
            samples.append(sample)
            # Live progress, so a run can be watched while it happens rather than only read after it:
            # a position that never changes *while the character is moving* is the failure this probe
            # exists to catch.
            if len(samples) % 8 == 1:
                print(
                    f"  t={sample['t']:>6.2f}  agent_xy={sample['agent_xy']}  "
                    f"moving={sample['moving']}",
                    flush=True,
                )
            time.sleep(SAMPLE_SECONDS)
        report["samples"] = samples

        positions = [
            tuple(sample["agent_xy"]) for sample in samples if isinstance(sample["agent_xy"], list)
        ]
        distinct = sorted(set(positions))
        report["distinct_positions"] = len(distinct)
        report["first_position"] = list(positions[0]) if positions else None
        report["last_position"] = list(positions[-1]) if positions else None
        if positions:
            travelled = sum(
                math.dist(positions[index - 1], positions[index])
                for index in range(1, len(positions))
            )
            report["path_length_seen"] = round(travelled, 3)
            report["net_displacement_seen"] = round(math.dist(positions[0], positions[-1]), 3)
        else:
            report["path_length_seen"] = 0.0
            report["net_displacement_seen"] = 0.0
        report["ever_moving"] = any(sample["moving"] is True for sample in samples)
        # The two member paths are independent reads of the same record: they must agree.
        disagreements = [
            sample
            for sample in samples
            if isinstance(sample["agent_xy"], list)
            and isinstance(sample["player_xy"], list)
            and math.dist(sample["agent_xy"], sample["player_xy"]) > 1.0
        ]
        report["agent_vs_player_disagreements"] = len(disagreements)
        report["verdict"] = (
            "the reads followed the client: "
            f"{len(distinct)} distinct positions, {report['path_length_seen']} units of path seen"
            if report["distinct_positions"] > 1
            else "THE READS DID NOT MOVE: every sample answered the same position, so a stored "
            "record is being served instead of a read taken when asked"
        )
        print(report["verdict"])
        print(
            f"ever_moving={report['ever_moving']} agent_vs_player_disagreements="
            f"{report['agent_vs_player_disagreements']}"
        )
        return _write(report, report_path, 0 if report["distinct_positions"] > 1 else 5)
    finally:
        reader.close()


def _write(report: dict[str, Any], path: str, code: int) -> int:
    text = json.dumps(report, indent=2, ensure_ascii=False, default=str)
    print(text)
    if path:
        Path(path).write_text(text, encoding="utf-8")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
