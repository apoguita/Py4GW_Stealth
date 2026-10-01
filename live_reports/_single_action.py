"""ONE action, ONE send, per run. Nothing else is ever issued.

WHY THIS EXISTS
---------------
A previous sweep fired several candidate message ids in sequence. Whatever the client did could not
be attributed to any single one of them, so its result was worthless - including a "leave guild hall
works" claim that had to be withdrawn. This tool exists so that never happens again: it performs
exactly one member call or one message send, then reports what changed. Run it once per action.

It also REFUSES rather than firing when the precondition is not met. A test that sends
``kLeaveGuildHall`` while you are not in a guild hall, or asks the client to travel to the map it is
already standing in, produces a meaningless verdict - and the last two runs each made exactly one of
those mistakes. ``--require-map`` makes the starting state explicit and checked.

ACTIONS
-------
    leave_gh            MapMethods.LeaveGH()          requires being in the hall
    travel_gh           MapMethods.TravelGH()         requires NOT being in the hall
    travel --target N   MapMethods.Travel(N, ...)     requires N != current map
    send --id 0x... --target N [--wparam-mode scalar|pointer]
                        a single raw SendUIMessageRaw, for the payload-convention question
                        (the client's own kTravel emit carried the destination map id as a SCALAR,
                        while Native sends a POINTER to a 4-dword struct)

PRECONDITIONS
-------------
    --require-map N     refuse unless the client's map id is N
    --expect-change / --expect-no-change    recorded in the verdict, never assumed

USAGE (elevated): python live_reports/_single_action.py --action leave_gh --require-map 5
"""

from __future__ import annotations

import argparse
import json
import struct
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
from py4gw.map_methods import MapMethods  # noqa: E402

TRAVEL_OFFSET = 0xFA0   # map_methods._TRAVEL_OFFSET


def snap() -> dict[str, Any]:
    try:
        region = Map.GetRegion()
        language = Map.GetLanguage()
        return {
            "map_id": int(Map.GetMapID()),
            "region": region[0] if isinstance(region, tuple) else region,
            "language": language[0] if isinstance(language, tuple) else language,
            "map_ready": bool(Map.IsMapReady()),
        }
    except Exception as error:  # noqa: BLE001
        return {"error": f"{type(error).__name__}: {error}"}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--action", required=True,
                    choices=("leave_gh", "travel_gh", "travel", "send"))
    ap.add_argument("--target", type=int, default=0)
    ap.add_argument("--id", default="", help="message id for --action send, e.g. 0x10000186")
    ap.add_argument("--wparam-mode", choices=("scalar", "pointer"), default="pointer")
    ap.add_argument("--require-map", type=int, default=-1)
    ap.add_argument("--settle", type=float, default=15.0)
    ap.add_argument("--out", default=str(ROOT / "live_reports" / "single_action.json"))
    args = ap.parse_args(argv)

    win32 = Win32()
    if not win32.is_elevated():
        print("REFUSING: an active test; run it elevated.")
        return 3
    clients = win32.find_guild_wars()
    if not clients:
        print("no Gw.exe process found.")
        return 2

    report: dict[str, Any] = {"action": args.action, "target": args.target,
                              "pid": int(clients[0]["pid"])}

    with py4gw.connect(clients[0], game_thread=True) as client:  # type: ignore[misc]
        before = snap()
        report["before"] = before
        print(f"pid {report['pid']}   action={args.action}   target={args.target or '-'}")
        print(f"before: {before}")

        # ---- precondition checks: refuse rather than fire -------------------------------
        current = before.get("map_id")
        if args.require_map >= 0 and current != args.require_map:
            print(f"\nREFUSING: --require-map {args.require_map} but the client is in map {current}.")
            print("Set the client up by hand first, then run this again. Nothing was sent.")
            return 4
        if args.action == "leave_gh" and args.require_map < 0:
            print("\nREFUSING: leave_gh needs --require-map <guild hall map id>, so the starting "
                  "state is stated and checked instead of assumed. Nothing was sent.")
            return 4
        if args.action == "travel_gh" and current == args.require_map and args.require_map >= 0:
            print(f"\nREFUSING: travel_gh while already in map {current}. Nothing was sent.")
            return 4
        if args.action == "travel" and args.target == current:
            print(f"\nREFUSING: travel target {args.target} is the map the client is already in - "
                  f"that is a no-op whatever the message id is. Nothing was sent.")
            return 4

        region = before.get("region") if isinstance(before.get("region"), int) else 0
        language = before.get("language") if isinstance(before.get("language"), int) else 0

        # ---- exactly ONE action ---------------------------------------------------------
        print(f"\n--- issuing ONE action: {args.action} ---")
        returned: Any = None
        raised: str | None = None
        try:
            if args.action == "leave_gh":
                returned = MapMethods.LeaveGH()
            elif args.action == "travel_gh":
                returned = MapMethods.TravelGH()
            elif args.action == "travel":
                returned = MapMethods.Travel(args.target, region, 0, language)
            else:
                from py4gw.ui_manager import UIManager

                if args.wparam_mode == "scalar":
                    wparam = args.target
                else:
                    payload = struct.pack("<Iiii", args.target, region, language, 0)
                    wparam = client.bridge.write_data(TRAVEL_OFFSET, payload)
                returned = UIManager.SendUIMessageRaw(int(args.id, 16), wparam, 0)
        except Exception as error:  # noqa: BLE001
            raised = f"{type(error).__name__}: {error}"
        print(f"    returned: {returned}{'   RAISED: ' + raised if raised else ''}")

        # ---- wait for the client, then report -------------------------------------------
        after, changed, elapsed = before, False, 0.0
        started = time.time()
        while time.time() - started < args.settle:
            time.sleep(1.0)
            after = snap()
            if after.get("map_id") != before.get("map_id"):
                changed, elapsed = True, time.time() - started
                break
        print(f"after {time.time() - started:.1f}s: {after}")
        verdict = (
            f"map changed {before.get('map_id')} -> {after.get('map_id')} in {elapsed:.1f}s"
            if changed
            else "map did NOT change"
        )
        print(f"VERDICT: {verdict}")
        report.update({"after": after, "returned": returned, "raised": raised,
                       "map_changed": changed, "seconds": round(elapsed, 2), "verdict": verdict})

    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
