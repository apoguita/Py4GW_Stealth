"""Call ``Party.LeaveParty`` once — with the party window it presses actually on screen.

The member is native's ``leave_party``: behind the source's only guard (``get_party_size()``) it presses
the client's **party window** button callback —

    if (!g_party_window_button_callback_func) return false;
    if (!get_party_size()) return true;
    uint32_t ctx[14] = { 0 };
    ctx[0xd] = 1;
    g_party_window_button_callback_func(ctx, 0, 0);      # party_methods.cpp

— and the first attempt from outside, on 2026-09-29, **asserted the client**
(``Assertion: childId``, ``FrApi.cpp(3916)``, build 38888) with no such window on screen. So this tool
does the deliberate retry the owner asked for, in the order that makes the precondition testable:

1. read the party and whether the party window's frame is in the client's frame array (this port's own
   offline hash table: ``frame_names.NAME_TO_HASH``, ``'Party'`` → ``3332025202``);
2. if it is not, **open it** with the client's own control action —
   ``UIManager.Keypress(ControlAction_OpenParty, 0)``, the call shape ``Hero.FlagHero`` uses for its
   hero command keybinds — and wait for the frame to appear;
3. press the member **once**, paced, with the window there;
4. watch the party's own records for ``WATCH_SECONDS`` and report every reading.

Everything is printed and written to ``tests/live_reports/party_leave_live.json``.

Usage (elevated, owner present):  python tests/probe_party_leave.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

#: How long to watch the party after the press. The client applies a party change when it processes the
#: command, so a press that "did nothing" is only a fact once the client has had time to apply it.
WATCH_SECONDS = 6.0

#: How long to wait for the party window's frame to appear after the control action asks for it.
WINDOW_SECONDS = 5.0


def _party_state() -> dict[str, Any]:
    """The party as its own members read it — the numbers a leave would move."""

    from py4gw.party import Party

    return {
        "size": Party.GetPartySize(),
        "players": Party.GetPlayerCount(),
        "heroes": Party.GetHeroCount(),
        "henchmen": Party.GetHenchmanCount(),
        "leader": Party.GetPartyLeaderID(),
        "hero_agent_ids": [int(member.agent_id) for member in Party.GetHeroes()],
        "henchman_agent_ids": [int(member.agent_id) for member in Party.GetHenchmen()],
    }


def main() -> int:
    from py4gw.win32 import Win32

    win32 = Win32()
    clients = win32.find_guild_wars()
    if not clients:
        print("no Guild Wars client is running")
        return 1
    process = clients[0]
    pid = int(process["pid"])

    import py4gw

    from tests.probe_party_live import (
        _ask,
        _party_window_on_screen,
        entry_is_original,
    )

    report: dict[str, Any] = {"stage": "leave", "pid": pid, "watch_seconds": WATCH_SECONDS}
    if not entry_is_original(win32, pid):
        print("another controller is attached; nothing was done")
        return 7

    with py4gw.connect(process, game_thread=True):
        from py4gw.enums_src.ui_enums import ControlAction
        from py4gw.party import Party
        from py4gw.ui_manager import UIManager

        report["before"] = _party_state()
        report["window_before"] = _party_window_on_screen()
        print(f"party before:       {json.dumps(report['before'])}")
        print(f"party window before: {report['window_before']}")

        if not report["window_before"]:
            # The window the press belongs to. The client's own control action opens it — the same
            # call shape ``Hero.FlagHero`` uses for a hero command keybind — and then the frame array
            # is asked again until it carries the window's hash.
            print("opening the party window with ControlAction_OpenParty …")
            report["OpenParty"] = _ask(
                lambda: UIManager.Keypress(int(ControlAction.ControlAction_OpenParty), 0)
            )
            started = time.monotonic()
            while time.monotonic() - started < WINDOW_SECONDS:
                time.sleep(0.5)
                if _party_window_on_screen():
                    break
            report["window_opened"] = _party_window_on_screen()
            report["window_waited_s"] = round(time.monotonic() - started, 1)
            print(f"party window after the control action: {report['window_opened']} "
                  f"(waited {report['window_waited_s']}s)")

        if not _party_window_on_screen():
            report["LeaveParty"] = (
                "not pressed: the party window is not on screen, and the press asserted the client "
                "the last time it was made without one (Assertion: childId, FrApi.cpp(3916))"
            )
            print(report["LeaveParty"])
        else:
            # One press, with a pause before it so the client's queue is empty.
            time.sleep(1.0)
            report["LeaveParty"] = _ask(Party.LeaveParty)
            print(f"LeaveParty -> {report['LeaveParty']!r}")

            started = time.monotonic()
            report["timeline"] = []
            while time.monotonic() - started < WATCH_SECONDS:
                time.sleep(0.5)
                state = _party_state()
                report["timeline"].append(
                    {"after_s": round(time.monotonic() - started, 1), **state}
                )
            report["after"] = report["timeline"][-1] if report["timeline"] else _party_state()

    report["hooks_original_after_disconnect"] = entry_is_original(win32, pid)
    report.setdefault("after", report["before"])
    report["changed"] = report["before"] != report["after"]
    print("timeline after the press:")
    for row in report.get("timeline", []):
        print(f"  +{row['after_s']:>4}s size={row['size']} players={row['players']} "
              f"heroes={row['heroes']} henchmen={row['henchmen']}")
    print(f"party changed: {report['changed']} | "
          f"hooks original after disconnect: {report['hooks_original_after_disconnect']}")
    with open("tests/live_reports/party_leave_live.json", "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False, default=str)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
