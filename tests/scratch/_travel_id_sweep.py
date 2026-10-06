"""Try each candidate UIMessage id as a travel request, one at a time, and log what the client does.

WHY
---
You saw the client answer "you cannot travel to this map". That is the client ACCEPTING the message
and REJECTING the map id inside it - so the message is delivered and handled as a travel request,
and the suspect is either the id (a different travel-family message whose payload it reads
differently) or the payload layout.

This sends ONE message per step, with a real wait between them, and records the client's own map id
before and after each, so the table shows exactly which id did what:

    map changed to the guild hall  -> that id is a guild-hall request
    map changed to the target      -> that id is the travel request
    map unchanged                  -> the client refused it (this is where "cannot travel" appears)

WATCH THE SCREEN WHILE IT RUNS and note which id shows "you cannot travel to this map" - that is the
other half of the evidence and it cannot be read from memory.

Each step starts and ends in the guild hall where possible, so every attempt is a genuine cross-map
travel rather than a request to stay put.

USAGE (elevated): python tests/scratch\1_travel_id_sweep.py [--ids 0x10000183,0x10000185,0x10000186,0x10000187]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import py4gw  # noqa: E402
from py4gw import Win32  # noqa: E402
from py4gw.map import Map  # noqa: E402
from py4gw.native_src.methods.map_methods import MapMethods  # noqa: E402

STEP_SETTLE = 10.0        # seconds to wait for a map change after one send
BETWEEN_STEPS = 2.0       # seconds between attempts, so the client is quiet before the next
TRAVEL_OFFSET = 0xFA0     # map_methods._TRAVEL_OFFSET


def snap() -> dict[str, Any]:
    try:
        region = Map.GetRegion()
        language = Map.GetLanguage()
        return {
            "map_id": int(Map.GetMapID()),
            "region": region[0] if isinstance(region, tuple) else region,
            "language": language[0] if isinstance(language, tuple) else language,
        }
    except Exception as error:  # noqa: BLE001
        return {"error": f"{type(error).__name__}: {error}"}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", default="0x10000183,0x10000185,0x10000186,0x10000187")
    ap.add_argument("--target", type=int, default=55, help="map id to request (55 = Lion's Arch)")
    ap.add_argument("--out", default=str(ROOT / "tests/live_reports" / "travel_id_sweep.json"))
    args = ap.parse_args(argv)

    ids = [int(part, 16) for part in args.ids.split(",") if part.strip()]

    win32 = Win32()
    if not win32.is_elevated():
        print("REFUSING: an active test; run it elevated.")
        return 3
    clients = win32.find_guild_wars()
    if not clients:
        print("no Gw.exe process found.")
        return 2
    pid = int(clients[0]["pid"])

    report: dict[str, Any] = {"pid": pid, "target": args.target, "attempts": []}

    with py4gw.connect(clients[0], game_thread=True) as client:  # type: ignore[misc]
        print(f"connected to pid {pid}   target map {args.target}")
        start = snap()
        print(f"start: {start}")

        # Put ourselves in the guild hall so every travel attempt is a real cross-map move.
        print("\n--- placing the client in the guild hall first ---")
        try:
            print(f"    TravelGH() -> {MapMethods.TravelGH()}")
        except Exception as error:  # noqa: BLE001
            print(f"    TravelGH raised: {error}")
        time.sleep(3.0)
        hall = snap()
        print(f"    now: {hall}   (a guild hall is not {args.target})")

        region = hall.get("region") if isinstance(hall.get("region"), int) else 0
        language = hall.get("language") if isinstance(hall.get("language"), int) else 0

        for message_id in ids:
            before = snap()
            print(f"\n=== sending {message_id:#010x} with the travel payload (target {args.target}) ===")
            print(f"    before: map_id={before.get('map_id')}")
            # Same payload MapMethods.Travel builds: <Iiii> = map_id, region, language, district.
            import struct

            payload = struct.pack("<Iiii", args.target, region, language, 0)
            address = client.bridge.write_data(TRAVEL_OFFSET, payload)
            raised = None
            try:
                from py4gw.ui_manager import UIManager

                returned = UIManager.SendUIMessageRaw(message_id, address, 0)
            except Exception as error:  # noqa: BLE001
                returned, raised = None, f"{type(error).__name__}: {error}"
            print(f"    send returned: {returned}{'   RAISED: ' + raised if raised else ''}")

            after, changed, elapsed = before, False, 0.0
            started = time.time()
            while time.time() - started < STEP_SETTLE:
                time.sleep(1.0)
                after = snap()
                if after.get("map_id") != before.get("map_id"):
                    changed, elapsed = True, time.time() - started
                    break
            verdict = (
                f"map changed {before.get('map_id')} -> {after.get('map_id')} in {elapsed:.1f}s"
                if changed
                else "map unchanged (this is where 'cannot travel to this map' appears)"
            )
            print(f"    VERDICT: {verdict}")
            report["attempts"].append(
                {
                    "message_id": hex(message_id), "returned": returned, "raised": raised,
                    "before": before, "after": after, "map_changed": changed, "verdict": verdict,
                }
            )
            time.sleep(BETWEEN_STEPS)

        report["end"] = snap()
        print(f"\nend: {report['end']}")

    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
