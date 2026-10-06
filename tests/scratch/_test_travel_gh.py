"""ONE test: does the literal UIMessage 0x10000183 travel to the guild hall?

Sends exactly one message and logs the literal id it sent, so the result is attributable to that
id and nothing else. No sweep, no sequence, no second action.

Run it from an OUTPOST (not the hall). It reads the client's map id before and after.

USAGE (elevated): python tests/scratch\1_test_travel_gh.py
"""

from __future__ import annotations

import json
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

LITERAL = 0x10000183          # the candidate id under test, written out so the log shows it
SETTLE = 20.0


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

    report: dict[str, object] = {"literal_under_test": hex(LITERAL)}

    with py4gw.connect(clients[0], game_thread=True) as _client:  # type: ignore[misc]
        before = map_id()

        # The wparam the port uses for this message: the guild context's own player_gh_key field.
        guild_ctx = mm.GWContext.Guild.GetContext()
        base = mm.GWContext.Guild.GetPtr()
        if guild_ctx is None or not base:
            print(f"REFUSING: no guild context (ctx={guild_ctx}, base={base:#x}). Nothing sent.")
            return 4
        wparam = base + mm.GuildContextStruct.player_gh_key.offset

        print(f"  enum says UIMessage.kGuildHall = {int(mm.UIMessage.kGuildHall):#010x}")
        print(f"  this test sends the LITERAL {LITERAL:#010x}  (wparam {wparam:#010x})")
        print(f"  map before: {before}")
        if int(mm.UIMessage.kGuildHall) != LITERAL:
            print(f"  NOTE: literal differs from the enum value "
                  f"({int(mm.UIMessage.kGuildHall):#010x}) - the literal is what this test sends.")

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

        if changed:
            print(f"\nRESULT: {LITERAL:#010x} IS the travel-to-guild-hall message "
                  f"({before} -> {after} in {elapsed:.1f}s).")
        else:
            print(f"\nRESULT: {LITERAL:#010x} did NOT move the client out of map {before}.")
        report.update({"before": before, "after": after, "changed": changed,
                       "seconds": round(elapsed, 2), "returned": returned, "wparam": hex(wparam)})

    Path(ROOT / "tests/live_reports" / "test_travel_gh.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
