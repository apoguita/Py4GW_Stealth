"""Does the layer's control-action route actually move the client? One press, read back.

**What this probe is for.** ``py4gw/gwa3/core.py``'s ``Core_PerformAction`` performs a control action by
**pressing** it -- ``UIManager.Keydown(action, 0)`` / ``UIManager.Keyup(action, 0)``, the route Reforged's
own ``Keybinds`` use for these actions (``routines_src/behaviourtrees_src/keybinds.py:101,119``). That
route was established by reading both sources; **nothing had yet shown that the client acts on the
press.** This probe shows it, on the one control action whose effect the client *reports back*:

* the active weapon set is a client field this port reads (``Item_GetInventoryInfo("ActiveWeaponSet")``,
  the inventory struct's own ``active_weapon_set``), so a switch that happened is visible as a different
  number, and a switch that did not happen is visible as the same one.

The order: read the set, press the switch through the layer's member (``Item_SwitchWeaponSet``), poll the
client's own field for the change, then do the same through `UAI_ChangeWeaponSet` -- the UtilityAI
spelling, which presses two cancels first. Both presses are made **once each**, paced, and the original
set is restored at the end.

The cancel and the bundle drop are pressed too, but nothing is asserted about them: neither has an effect
the client reports when no cast is in flight and nothing is held. They are here so that the presses
themselves are exercised against a live client rather than only mocked offline.

Everything is printed and written to ``tests/live_reports/gwa3_control_action_live.json``.

Usage (elevated, owner present):  python tests/probe_gwa3_control_action_live.py
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

#: How long to watch the client's own ``active_weapon_set`` after a press. The client applies the change
#: when it processes the key action, so "nothing happened" is only a fact after this window.
WATCH_SECONDS = 3.0


def _active_set() -> int:
    """The client's own active weapon set, read through the layer's own reader."""

    from py4gw.gwa3.data_item import Item_GetInventoryInfo

    return int(Item_GetInventoryInfo("ActiveWeaponSet"))


def _wait_for_set(target: int) -> tuple[bool, int, float]:
    """Poll the client's field until it reports ``target``. The answer is the client's, not ours."""

    started = time.monotonic()
    seen = _active_set()
    while time.monotonic() - started < WATCH_SECONDS:
        if seen == target:
            return True, seen, time.monotonic() - started
        time.sleep(0.2)
        seen = _active_set()
    return seen == target, seen, time.monotonic() - started


def _presses() -> dict[str, Any]:
    """The four members under test, each pressed once, with what the client reported after each."""

    from py4gw.gwa3.cmd_agent import Agent_CancelAction
    from py4gw.gwa3.cmd_item import Item_DropBundle, Item_SwitchWeaponSet
    from py4gw.gwa3.uai_weaponsets import UAI_ChangeWeaponSet, UAI_IsOnWeaponSet

    report: dict[str, Any] = {}

    original = _active_set()
    report["active_set_before"] = original
    report["is_on_weapon_set_before"] = {n: bool(UAI_IsOnWeaponSet(n)) for n in (1, 2, 3, 4)}
    print(f"active weapon set before: {original}")
    print(f"UAI_IsOnWeaponSet 1..4:   {report['is_on_weapon_set_before']}")

    # 1. The layer's own member, over GwAu3's ``HEADER_SWITCH_SET`` spelling.
    target = original % 4 + 1
    report["switch_target"] = target
    report["Item_SwitchWeaponSet_returned"] = Item_SwitchWeaponSet(target)
    took, seen, waited = _wait_for_set(target)
    report["after_Item_SwitchWeaponSet"] = {"took": took, "active_set": seen, "waited_s": round(waited, 2)}
    print(f"Item_SwitchWeaponSet({target}) -> took={took}, client reports {seen} "
          f"after {waited:.2f}s")

    # 2. The UtilityAI spelling: two cancels, then the set, repeated until the client agrees.
    original_after_first = _active_set()
    second_target = original_after_first % 4 + 1
    report["uai_switch_target"] = second_target
    report["UAI_ChangeWeaponSet_returned"] = UAI_ChangeWeaponSet(second_target)
    took, seen, waited = _wait_for_set(second_target)
    report["after_UAI_ChangeWeaponSet"] = {"took": took, "active_set": seen, "waited_s": round(waited, 2)}
    print(f"UAI_ChangeWeaponSet({second_target}) -> took={took}, client reports {seen} "
          f"after {waited:.2f}s")

    # 3. The two presses with no reportable effect: exercised, not asserted.
    report["Agent_CancelAction_returned"] = Agent_CancelAction()
    print(f"Agent_CancelAction() -> {report['Agent_CancelAction_returned']} (no effect to report)")
    report["Item_DropBundle_returned"] = Item_DropBundle()
    print(f"Item_DropBundle() -> {report['Item_DropBundle_returned']} (no effect to report)")

    # 4. Put the character back where it started.
    if _active_set() != original:
        report["restore_returned"] = UAI_ChangeWeaponSet(original)
        took, seen, waited = _wait_for_set(original)
        report["restored"] = {"took": took, "active_set": seen, "waited_s": round(waited, 2)}
        print(f"restore to set {original} -> took={took}, client reports {seen}")
    else:
        report["restored"] = {"took": True, "active_set": original, "waited_s": 0.0}
        print("the character was already back on its original set")

    report["active_set_after"] = _active_set()
    return report


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

    from tests.probe_party_live import entry_is_original

    if not entry_is_original(win32, pid):
        print("another controller is attached; nothing was done")
        return 7

    report: dict[str, Any] = {"stage": "gwa3-control-action", "pid": pid, "watch_seconds": WATCH_SECONDS}
    with py4gw.connect(process, game_thread=True):
        from py4gw.gwa3.data_map import Map_GetMapID

        report["map_id"] = int(Map_GetMapID())
        print(f"pid {pid}, map {report['map_id']}")
        report.update(_presses())

    report["hooks_original_after_disconnect"] = entry_is_original(win32, pid)
    #: The route is verified when the client's own field moved to the set that was pressed, and moved
    #: back. A press that "worked" only because the set was already the one asked for is not a result.
    first = report["after_Item_SwitchWeaponSet"]
    second = report["after_UAI_ChangeWeaponSet"]
    report["route_verified"] = bool(
        first["took"]
        and first["active_set"] != report["active_set_before"]
        and second["took"]
        and report["restored"]["took"]
    )
    print(f"route verified (the client's own field moved): {report['route_verified']}")
    print(f"hooks original after disconnect: {report['hooks_original_after_disconnect']}")

    Path("tests/live_reports").mkdir(parents=True, exist_ok=True)
    with open("tests/live_reports/gwa3_control_action_live.json", "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False, default=str)
    return 0 if report["route_verified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
