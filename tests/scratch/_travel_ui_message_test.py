"""Decide the 2026-09-30 UIMessage shift empirically, by watching the client's own messages.

THE QUESTION
------------
PR #9 shifted 76 `UIMessage` values on the assumption that three new client messages
(`0x10000113`, `0x10000148`, `0x10000181`) were *inserted* mid-sequence. But all three of those
slots were already blank in the pre-update table:

    kMapChange = 0x10000111, kCalledTargetChange = 0x10000115   -> 0x112-0x114 unnamed
    kPreBuildLoginScene = 0x10000144, kQuestAdded = 0x1000014E  -> 0x145-0x14D unnamed
    kGuildHall = 0x10000180, kLeaveGuildHall = 0x10000182       -> 0x181 unnamed

If those slots were simply unassigned, new messages fill them and NOTHING shifts - so the old values
were right all along and PR #9 renumbered 76 ids that did not need it. A wrong id here fails
silently: `SendUIMessage` hands the client a different message than intended, so travel, guild hall
and the rest simply do nothing.

HOW THIS DECIDES IT
-------------------
Nothing is sent. The connection installs Stealth's observer on the client's own UI-message entry
point and watches BOTH candidate ids of each feature. You then perform the action by hand. The id
the CLIENT emits is the truth, and it lands in exactly one of each pair:

    0x1000011E  vs  0x1000011F     kPartyAddHero       (shift +1 -> tests the 0x113 insertion)
    0x10000180  vs  0x10000183     kGuildHall          (shift +3 -> tests all three)
    0x10000182  vs  0x10000185     kLeaveGuildHall     (shift +3)
    0x10000183  vs  0x10000186     kTravel             (shift +3)  <- the reported symptom

The watch list holds exactly 8 ids and these are the 8, so the library's defaults are replaced for
this run and restored on exit.

WHAT TO DO WHILE IT RUNS (the whole point - it observes, it does not act)
------------------------------------------------------------------------
  1. ADD A HERO to the party.
  2. OPEN the guild hall, then LEAVE it.
  3. TRAVEL to another map / outpost.

Any of those may be done more than once.

USAGE (elevated - see tests/scratch\1_elev_travel_test.cmd)
    python tests/scratch\1_travel_ui_message_test.py [--seconds 120]
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
from py4gw.game_thread.shared_block import EventKind  # noqa: E402

#: (old, new) per feature, from the pre-update table and PR #9's rewrite.
PAIRS = (
    ("kPartyAddHero", 0x1000011E, 0x1000011F),
    ("kGuildHall", 0x10000180, 0x10000183),
    ("kLeaveGuildHall", 0x10000182, 0x10000185),
    ("kTravel", 0x10000183, 0x10000186),
)
WATCH = tuple(value for _, old, new in PAIRS for value in (old, new))


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=120.0)
    ap.add_argument("--out", default=str(ROOT / "tests/live_reports" / "travel_ui_message_test.json"))
    args = ap.parse_args(argv)

    win32 = Win32()
    if not win32.is_elevated():
        print("REFUSING: the observer needs an elevated controller (connecting is a write).")
        return 3
    clients = win32.find_guild_wars()
    if not clients:
        print("no Gw.exe process found.")
        return 2
    pid = int(clients[0]["pid"])

    original = py4gw.client._WATCHED_MESSAGES  # type: ignore[attr-defined]
    py4gw.client._WATCHED_MESSAGES = tuple((value, 0) for value in WATCH)  # type: ignore[attr-defined]

    events: list[str] = []

    def spy(*call_args: Any, **call_kwargs: Any) -> None:
        record = call_args[0] if call_args else call_kwargs.get("record")
        text = repr(record)
        events.append(text)
        print("  MSG", text)

    print(f"connecting to pid {pid} with the game thread (this is a write) ...")
    client = py4gw.connect(clients[0])
    client.callbacks.register(EventKind.UI_MESSAGE, spy)  # type: ignore[attr-defined]

    print()
    print("=" * 78)
    print("  watching BOTH candidates for each feature. Nothing is being sent.")
    print("  PLEASE DO THIS NOW, by hand, in the game:")
    print("    1. add a hero to the party")
    print("    2. open the guild hall, then leave it")
    print("    3. travel to another map / outpost")
    print("=" * 78)
    print()

    deadline = time.time() + args.seconds
    try:
        while time.time() < deadline:
            time.sleep(0.25)
            remaining = int(deadline - time.time())
            if remaining % 15 == 0:
                print(f"  ... {remaining}s left, {len(events)} ui message(s) observed")
    except KeyboardInterrupt:
        print("  interrupted")
    finally:
        py4gw.disconnect()
        py4gw.client._WATCHED_MESSAGES = original  # type: ignore[attr-defined]

    report = {
        "pid": pid,
        "pairs": [{"name": n, "old": hex(o), "new": hex(x)} for n, o, x in PAIRS],
        "watched": [hex(v) for v in WATCH],
        "events": events,
    }
    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")

    print()
    print("=" * 78)
    print("  RESULT - which candidate the client actually emitted")
    print("=" * 78)
    for name, old, new in PAIRS:
        old_hit = sum(1 for e in events if hex(old) in e)
        new_hit = sum(1 for e in events if hex(new) in e)
        verdict = (
            "OLD is correct -> PR #9's shift is WRONG"
            if old_hit and not new_hit
            else "NEW is correct -> PR #9's shift holds"
            if new_hit and not old_hit
            else "BOTH seen - inconclusive, look at the event lines"
            if old_hit and new_hit
            else "neither seen - that action was not performed"
        )
        print(f"  {name:<18} old {old:#010x} x{old_hit:<3} new {new:#010x} x{new_hit:<3} {verdict}")
    print(f"\n  {len(events)} event(s); wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
