"""Drive the three travel actions against the running client and record what actually happens.

ACTIVE TEST - this sends UI messages to the client, so the client will change maps.
Requested explicitly by the owner.

    0. snapshot the starting map
    1. MapMethods.TravelGH()   -> guild hall        (UIMessage.kGuildHall)
    2. MapMethods.LeaveGH()    -> leave the hall    (UIMessage.kLeaveGuildHall)
    3. MapMethods.Travel(55)   -> back to Lion's Arch (UIMessage.kTravel)

Why it records BOTH the member's return value and the client's own map id: those separate three
failure modes that look identical from outside.

    send returned False, map unchanged     -> the member refused before sending
    send returned True,  map unchanged     -> the client did not act on the message
    map moved, but to the wrong place      -> the payload is wrong

USAGE (elevated - see tests/scratch\1_elev_travel_actions.cmd)
    python tests/scratch\1_travel_actions_test.py [--lions-arch 55] [--settle 30]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import py4gw  # noqa: E402
from py4gw import Win32  # noqa: E402
from py4gw.map import Map  # noqa: E402
from py4gw.map_methods import MapMethods  # noqa: E402

#: The port's own pacing constant: the client processes one command at a time.
ACTION_INTERVAL_SECONDS = 0.75


def _call(fn: Callable[[], Any]) -> Any:
    try:
        return fn()
    except Exception as error:  # noqa: BLE001 - a failing read is a result, not a crash
        return f"{type(error).__name__}: {error}"


def snapshot() -> dict[str, Any]:
    """The client's own view of where it is."""

    region = _call(lambda: Map.GetRegion())
    language = _call(lambda: Map.GetLanguage())
    return {
        "map_id": _call(lambda: int(Map.GetMapID())),
        "region": region[0] if isinstance(region, tuple) else region,
        "language": language[0] if isinstance(language, tuple) else language,
        "map_ready": _call(lambda: bool(Map.IsMapReady())),
    }


def wait_for_map_change(before: dict[str, Any], seconds: float) -> tuple[dict[str, Any], bool, float]:
    """Poll until the client's map id differs from ``before``, or the budget runs out."""

    started = time.time()
    while time.time() - started < seconds:
        time.sleep(1.0)
        now = snapshot()
        if now.get("map_id") != before.get("map_id"):
            return now, True, time.time() - started
    return snapshot(), False, time.time() - started


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lions-arch", type=int, default=55)
    ap.add_argument("--settle", type=float, default=30.0)
    ap.add_argument("--out", default=str(ROOT / "tests/live_reports" / "travel_actions_test.json"))
    args = ap.parse_args(argv)

    win32 = Win32()
    if not win32.is_elevated():
        print("REFUSING: this is an active test and connecting is a write; run it elevated.")
        return 3
    clients = win32.find_guild_wars()
    if not clients:
        print("no Gw.exe process found.")
        return 2
    pid = int(clients[0]["pid"])

    report: dict[str, Any] = {"pid": pid, "lions_arch": args.lions_arch, "steps": []}

    with py4gw.connect(clients[0], game_thread=True) as _client:  # type: ignore[misc]
        print(f"connected to pid {pid} with the game thread")
        start = snapshot()
        report["start"] = start
        print(f"  start : {start}")
        print("  (Lion's Arch is map 55; a guild hall is not 55)")

        region = start["region"] if isinstance(start["region"], int) else 0
        language = start["language"] if isinstance(start["language"], int) else 0

        # Order matters. `kTravel` must be exercised while the client is somewhere ELSE, or the
        # request is a no-op: asking to travel to the map you are already standing in changes
        # nothing whatever the id is, and a "did not change" verdict would be the test's fault,
        # not the member's. The first run of this probe made exactly that mistake by putting
        # LeaveGH (which already returns to Lion's Arch) before Travel(Lion's Arch).
        steps: tuple[tuple[str, str, str, Callable[[], Any]], ...] = (
            ("TravelGH", "travel to the guild hall", "kGuildHall", lambda: MapMethods.TravelGH()),
            (
                f"Travel({args.lions_arch}) from the hall",
                "travel from the guild hall to Lion's Arch  <- the real kTravel test",
                "kTravel",
                lambda: MapMethods.Travel(args.lions_arch, region, 0, language),
            ),
            ("TravelGH again", "back into the guild hall", "kGuildHall", lambda: MapMethods.TravelGH()),
            ("LeaveGH", "leave the guild hall", "kLeaveGuildHall", lambda: MapMethods.LeaveGH()),
        )

        for label, description, message, action in steps:
            before = snapshot()
            print(f"\n--- {label}: {description}   ({message}) ---")
            print(f"    before: map_id={before.get('map_id')} ready={before.get('map_ready')}")
            returned, raised = None, None
            try:
                returned = action()
            except Exception as error:  # noqa: BLE001
                raised = f"{type(error).__name__}: {error}"
            print(f"    send returned: {returned}{'   RAISED: ' + raised if raised else ''}")

            after, changed, elapsed = wait_for_map_change(before, args.settle)
            verdict = (
                "map did NOT change"
                if not changed
                else f"map changed {before.get('map_id')} -> {after.get('map_id')} in {elapsed:.1f}s"
            )
            print(f"    after {elapsed:.1f}s: map_id={after.get('map_id')} ready={after.get('map_ready')}")
            print(f"    VERDICT: {verdict}")
            report["steps"].append(
                {
                    "label": label, "message": message, "returned": returned, "raised": raised,
                    "before": before, "after": after, "map_changed": changed,
                    "seconds_to_change": round(elapsed, 2), "verdict": verdict,
                }
            )
            time.sleep(ACTION_INTERVAL_SECONDS)

        report["end"] = snapshot()
        print(f"\nend: {report['end']}")

    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
