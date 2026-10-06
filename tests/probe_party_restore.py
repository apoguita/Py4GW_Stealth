"""Put the party back to the state a recorded act run started from, then show the readings.

Why this exists: the **first** live `act` run (round 24, before the probe waited for the client) left
two fields changed. The client applies a party change when it processes the command, so each
flip-and-restore step computed its restore from the value it was replacing, the member's own guard
refused the write, and the flip stayed:

* hero at position 1: ``hero_behavior`` 1 -> 0
* hero at position 1: skillbar slot 1 -> **disabled** (``disabled`` 0 -> 1)

This tool reads the **recorded** pre-change state from a report whose ``before`` block was written
before anything was called (``tests/live_reports/party_act_flags_live.json`` — the `flags` step changes
nothing about hero behaviour or skill AI, so its snapshot is the original), writes each hero's
``hero_behavior`` word and each skill slot back to those values with the port's own members, waits for
the client to show each write, and prints the readings before and after.

It is **not** a port of anything and it changes no library code: it is this project's own repair for its
own probe's defect, and it reports what it did rather than claiming it.

Usage (elevated, owner present):  python tests/probe_party_restore.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# The probe is a script under ``tests``; run this from anywhere and it still finds the package.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

RECORDED = "tests/live_reports/party_act_flags_live.json"


def _recorded_state() -> dict[int, dict[str, int]]:
    """The heroes' behaviour words and disabled words as the recorded run found them."""

    with open(RECORDED, encoding="utf-8") as handle:
        report = json.load(handle)
    return {
        int(hero["position"]): {
            "behavior": int(hero["behavior"]),
            "disabled": int(hero["disabled"]),
        }
        for hero in report["before"]["heroes"]
    }


def restore(report: dict[str, Any]) -> None:
    """Write the recorded values back, waiting for the client to show each one."""

    from py4gw.party import Party

    from tests.probe_party_live import _ask, _hero_behavior, _hero_disabled, _settle, _world

    wanted = _recorded_state()
    report["recorded"] = wanted
    world = _world()

    for position, values in wanted.items():
        agent_id = int(Party.Heroes.GetHeroAgentIDByPartyPosition(position) or 0)
        if not agent_id:
            report.setdefault("skipped", []).append(f"position {position}: no agent id in this party")
            continue

        behavior = _hero_behavior(world, position)
        if behavior is not None and int(behavior) != values["behavior"]:
            report[f"SetHeroBehavior({agent_id}, {values['behavior']})"] = _ask(
                lambda agent_id=agent_id, value=values["behavior"]: Party.Heroes.SetHeroBehavior(
                    agent_id, value
                )
            )
            report[f"SetHeroBehavior({agent_id}) settled"] = _settle(
                lambda position=position: _hero_behavior(world, position), values["behavior"]
            )

        disabled = _hero_disabled(world, position)
        if disabled is None:
            continue
        for slot in range(1, 9):
            bit = 1 << (slot - 1)
            want_enabled = not (values["disabled"] & bit)
            have_enabled = not (int(disabled) & bit)
            if want_enabled == have_enabled:
                continue
            report[f"SetSkillAIEnabled({agent_id}, {slot}, {want_enabled})"] = _ask(
                lambda agent_id=agent_id, slot=slot, want_enabled=want_enabled: (
                    Party.Heroes.SetSkillAIEnabled(agent_id, slot, want_enabled)
                )
            )
            report[f"SetSkillAIEnabled({agent_id}, {slot}) settled"] = _settle(
                lambda position=position, bit=bit: bool(int(_hero_disabled(world, position) or 0) & bit),
                not want_enabled,
            )

    checks: list[dict[str, Any]] = []
    for position, values in wanted.items():
        got = {
            "behavior": _hero_behavior(world, position),
            "disabled": _hero_disabled(world, position),
        }
        checks.append(
            {
                "position": position,
                "agent_id": int(Party.Heroes.GetHeroAgentIDByPartyPosition(position) or 0),
                "wanted": values,
                "read_back": got,
                "matches": got["behavior"] == values["behavior"]
                and got["disabled"] == values["disabled"],
            }
        )
    report["checks"] = checks
    report["restored"] = all(check["matches"] for check in checks)


def difficulty_probe(report: dict[str, Any], timeout: float = 10.0) -> None:
    """Press hard mode once and watch the client's own flag for longer than a step would.

    The probe's `difficulty` step waited 3 s for the mode to change and the client never showed it.
    This tells "slow" apart from "refused": it asks the same member, then polls the client's own
    ``IsHardMode`` for ten seconds, and puts the mode back if it does move. Nothing else is touched.
    """

    from py4gw.map import Map
    from py4gw.party import Party

    from tests.probe_party_live import _ask, _settle

    if not Map.IsOutpost():
        report["difficulty"] = "skipped: not an outpost, and the client only changes mode there"
        return

    report["difficulty_before"] = _ask(Party.IsHardMode)
    report["difficulty_unlocked"] = _ask(Party.IsHardModeUnlocked)
    report["difficulty_SetHardMode"] = _ask(Party.SetHardMode)
    landed = _settle(Party.IsHardMode, True, timeout=timeout)
    report["difficulty_flip"] = landed
    if landed["settled"]:
        report["difficulty_SetNormalMode(back)"] = _ask(Party.SetNormalMode)
        report["difficulty_restore"] = _settle(Party.IsHardMode, False, timeout=timeout)
    report["difficulty_unlocked_after"] = _ask(Party.IsHardModeUnlocked)


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

    from tests.probe_party_live import client_state, entry_is_original

    report: dict[str, Any] = {"stage": "restore", "pid": pid}
    print(f"recorded original state: {json.dumps(_recorded_state())}")
    print(f"state before repair:     {json.dumps(client_state(), default=str)}")

    if not entry_is_original(win32, pid):
        print("another controller is attached; nothing was done")
        return 7

    with py4gw.connect(process, game_thread=True):
        restore(report)
        difficulty_probe(report)

    report["hooks_original_after_disconnect"] = entry_is_original(win32, pid)
    report["state_after"] = client_state()
    print(f"restored: {report['restored']}")
    for check in report["checks"]:
        print(
            f"  position {check['position']} (agent {check['agent_id']}): wanted "
            f"{check['wanted']}, read back {check['read_back']}, matches={check['matches']}"
        )
    print(f"state after repair:      {json.dumps(report['state_after'], default=str)}")
    print(f"hooks original after disconnect: {report['hooks_original_after_disconnect']}")
    print(f"difficulty: before={report.get('difficulty_before')} "
          f"unlocked={report.get('difficulty_unlocked')} -> "
          f"{json.dumps(report.get('difficulty_flip'), default=str)}")
    with open("tests/live_reports/party_restore_live.json", "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False, default=str)
    return 0 if report["restored"] else 5


if __name__ == "__main__":
    raise SystemExit(main())
