"""ONE test: does the literal UIMessage 0x10000186 (kTravel) actually travel?

Sends exactly one message: the literal id, with the pointer payload the port builds
(map_id, region, language, district packed as <Iiii>). Logs the exact id sent, so the result is
attributable to that id alone. No sweep, no sequence.

Refuses if the target is the map the client is already in - that is a no-op whatever the id is, and
it is exactly the mistake that invalidated the two earlier attempts.

USAGE (elevated): python live_reports/_test_ktravel.py --target 55
"""

from __future__ import annotations

import json
import struct
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import py4gw  # noqa: E402
from py4gw import Win32  # noqa: E402
from py4gw.map import Map  # noqa: E402
from py4gw import map_methods as mm  # noqa: E402

LITERAL = 0x10000186          # the candidate under test, written out so the log shows it
TRAVEL_OFFSET = 0xFA0          # map_methods._TRAVEL_OFFSET
TARGET = 55                    # Lion's Arch
SETTLE = 25.0


def map_id() -> int:
    try:
        return int(Map.GetMapID())
    except Exception as error:  # noqa: BLE001
        print(f"    (map id unreadable: {type(error).__name__}: {error})")
        return -1


def main() -> int:
    win32 = Win32()
    if not win32.is_elevated():
        print("REFUSING: an active test; run it elevated.")
        return 3
    clients = win32.find_guild_wars()
    if not clients:
        print("no Gw.exe process found.")
        return 2

    target = int(sys.argv[sys.argv.index("--target") + 1]) if "--target" in sys.argv else TARGET
    report: dict[str, object] = {"literal_under_test": hex(LITERAL), "target": target}

    with py4gw.connect(clients[0], game_thread=True) as client:  # type: ignore[misc]
        before = map_id()
        if before == target:
            print(f"REFUSING: already in map {before}; asking to travel there is a no-op. "
                  f"Nothing sent. Put the client in a DIFFERENT map and run again.")
            return 4

        region = Map.GetRegion()
        language = Map.GetLanguage()
        region = region[0] if isinstance(region, tuple) else region
        language = language[0] if isinstance(language, tuple) else language

        payload = struct.pack("<Iiii", target, region, language, 0)
        wparam = client.bridge.write_data(TRAVEL_OFFSET, payload)

        print(f"  enum says UIMessage.kTravel = {int(mm.UIMessage.kTravel):#010x}")
        print(f"  this test sends the LITERAL {LITERAL:#010x}")
        print(f"  payload <Iiii> = map_id={target} region={region} language={language} district=0")
        print(f"  wparam {wparam:#010x}  (a POINTER to that struct, as Map::Travel does)")
        print(f"  map before: {before}")

        print(f"\n--- ONE send: SendUIMessageRaw({LITERAL:#010x}, {wparam:#010x}, 0) ---")
        try:
            returned = mm.UIManager.SendUIMessageRaw(LITERAL, wparam, 0)
        except Exception as error:  # noqa: BLE001
            print(f"    RAISED: {type(error).__name__}: {error}")
            returned = None
        print(f"    returned: {returned}")

        after, changed, elapsed = before, False, 0.0
        started = time.time()
        while time.time() - started < SETTLE:
            time.sleep(1.0)
            after = map_id()
            if after != before:
                changed, elapsed = True, time.time() - started
                break
        print(f"    map after {time.time() - started:.1f}s: {after}")

        if changed and after == target:
            print(f"\nRESULT: {LITERAL:#010x} IS a working travel message ({before} -> {after}, "
                  f"the requested target, in {elapsed:.1f}s).")
        elif changed:
            print(f"\nRESULT: {LITERAL:#010x} moved the client {before} -> {after}, which is NOT "
                  f"the requested target {target} - the payload is being read differently.")
        else:
            print(f"\nRESULT: {LITERAL:#010x} did NOT move the client out of map {before}.")
        report.update({"before": before, "after": after, "changed": changed,
                       "seconds": round(elapsed, 2), "returned": returned, "wparam": hex(wparam)})

    Path(ROOT / "live_reports" / "test_ktravel.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
