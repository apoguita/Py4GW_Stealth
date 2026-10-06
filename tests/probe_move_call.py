"""Live probe: **one** `Player.Move`, 500 units in front of the player, and nothing else.

Stripped to the single variable, at the owner's request. It reads the player's own position and the
facing the **client** reports (`Agent.GetRotationCos`/`Sin`), computes the point 500 units along that
facing, issues **one** `Player.Move` there, and then only watches — no path request, no planner, no
navmesh, no loop of moves, no second call of any kind. Whatever the client does can therefore only be
attributed to that one call (or to the connection itself, which installs hooks and calls nothing).

`Player.Move` is `agent.move_to_func` through the `FLOAT_PTR` call form: the source's own four-float
array `{x, y, (float)zplane, 0.0}` built in the client and passed by address
(`native_src/methods/PlayerMethods.py:157`, native's `agent::Move`). It is a click-to-move: one call,
one destination, and the client walks it.

**This moves the character.** Bounded: one connection, one call, a fixed watch window, and the
position reported before and after.

Usage::

    python tests/probe_move_call.py [report-path] [--distance 500] [--watch 6] [--pid PID]  # elevated
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

REPORT_PATH = "live_reports/move_call.json"

#: How far in front of the player the destination sits, in game units.
GOAL_DISTANCE = 500.0

#: How long the probe watches the client after the call. Reads only — nothing else is sent.
WATCH_SECONDS = 6.0
#: Fast enough to catch a walk that starts and is cut short: the owner saw the character begin moving
#: and then be disconnected, so the interesting samples are the first fraction of a second.
SAMPLE_SECONDS = 0.1


def _ask(call: Any) -> Any:
    """Run one member and report what it answered, or exactly how it refused."""

    try:
        return call()
    except Exception as error:  # noqa: BLE001 - reported, never hidden
        return f"{type(error).__name__}: {error}"


def _write(report: dict[str, Any], path: str, code: int) -> int:
    text = json.dumps(report, indent=2, ensure_ascii=False, default=str)
    print(text)
    if path:
        Path(path).write_text(text, encoding="utf-8")
    return code


def main() -> int:
    from py4gw.win32 import Win32
    from tests.probe_two_runtimes_live import connectable
    from tests.test_live_coexistence import _Entries

    win32 = Win32()
    argv = list(sys.argv[1:])
    distance = GOAL_DISTANCE
    watch = WATCH_SECONDS
    pid_argument = ""
    zplane_argument: int | None = None
    for flag, target in (
        ("--distance", "distance"),
        ("--watch", "watch"),
        ("--pid", "pid"),
        ("--zplane", "zplane"),
    ):
        if flag in argv:
            index = argv.index(flag)
            value = argv[index + 1]
            del argv[index : index + 2]
            if target == "distance":
                distance = float(value)
            elif target == "watch":
                watch = float(value)
            elif target == "zplane":
                zplane_argument = int(value)
            else:
                pid_argument = value
    report_path = argv[0] if argv else REPORT_PATH

    report: dict[str, Any] = {"stage": "move-call", "distance": distance, "watch_seconds": watch}
    clients = win32.find_guild_wars()
    if not clients:
        report["error"] = "no Guild Wars client is running"
        return _write(report, report_path, 1)
    process = next(
        (c for c in clients if pid_argument and int(c["pid"]) == int(pid_argument)),
        clients[0],
    )
    pid = int(process["pid"])
    report["pid"] = pid
    report["controller_elevated"] = bool(win32.is_elevated())
    connectable_now, decisions = connectable(win32, pid)
    report["entry_decisions"] = decisions
    if not connectable_now:
        report["error"] = (
            "connect would refuse at least one of the four entries, so nothing was done: "
            + "; ".join(decisions)
        )
        return _write(report, report_path, 7)

    import py4gw

    from py4gw.agent import Agent
    from py4gw.map import Map
    from py4gw.player import Player

    entries = _Entries(pid)
    before = entries.snapshot()
    before_jumps = entries.foreign_entries()

    code = 0
    with py4gw.connect(process, game_thread=True) as _client:
        agent_id = int(Player.GetAgentID())
        player = Player.GetAgent()
        if player is None:
            report["error"] = "the player's own agent record did not read"
            code = 2
        else:
            start_x, start_y = float(player.pos.x), float(player.pos.y)
            zplane = int(player.pos.zplane)
            cos = float(_ask(lambda: Agent.GetRotationCos(agent_id)))
            sin = float(_ask(lambda: Agent.GetRotationSin(agent_id)))
            norm = math.hypot(cos, sin) or 1.0
            unit = (cos / norm, sin / norm)
            goal = (start_x + unit[0] * distance, start_y + unit[1] * distance)
            report["player"] = {
                "agent_id": agent_id,
                "map_id": _ask(Map.GetMapID),
                "start": [round(start_x, 2), round(start_y, 2)],
                "zplane": zplane,
                "facing_unit": [round(unit[0], 4), round(unit[1], 4)],
            }
            report["goal"] = [round(goal[0], 2), round(goal[1], 2)]
            report["zplane_source"] = (
                "the source's own default (omitted, so 0 — what every Reforged caller passes: "
                "Movement.py:83, Sequential.py:58, BuildMgr.py:1451)"
                if zplane_argument is None
                else f"the --zplane argument ({zplane_argument})"
            )
            print(
                f"player {agent_id} at ({start_x:.1f}, {start_y:.1f}) zplane {zplane} "
                f"facing ({unit[0]:.3f}, {unit[1]:.3f}) -> goal ({goal[0]:.1f}, {goal[1]:.1f})"
            )

            # ---- the one call ----------------------------------------------------------------
            started = time.monotonic()
            if zplane_argument is None:
                # ``Player.Move(x, y, zPlane=0)`` — the source's own default, which is what every
                # Reforged caller passes. The player's own zplane is *not* passed: an earlier run
                # passed it and the character started moving and the client was disconnected.
                report["move_call"] = _ask(lambda: Player.Move(goal[0], goal[1]))
            else:
                report["move_call"] = _ask(
                    lambda: Player.Move(goal[0], goal[1], zplane_argument)
                )
            report["move_call_seconds"] = round(time.monotonic() - started, 3)
            print(f"Move returned {report['move_call']!r} in {report['move_call_seconds']}s")

            # ---- watch only ------------------------------------------------------------------
            samples = []
            while time.monotonic() - started < watch:
                x, y = Agent.GetXY(agent_id)
                samples.append(
                    {
                        "t": round(time.monotonic() - started, 2),
                        "x": round(float(x), 2),
                        "y": round(float(y), 2),
                        "moving": bool(_ask(lambda: Agent.IsMoving(agent_id))),
                        "from_start": round(
                            math.hypot(float(x) - start_x, float(y) - start_y), 1
                        ),
                        "to_goal": round(math.hypot(goal[0] - float(x), goal[1] - float(y)), 1),
                    }
                )
                time.sleep(SAMPLE_SECONDS)
            report["samples"] = samples
            end_x, end_y = Agent.GetXY(agent_id)
            report["end"] = [round(float(end_x), 2), round(float(end_y), 2)]
            report["displacement"] = round(
                math.hypot(float(end_x) - start_x, float(end_y) - start_y), 2
            )
            report["max_displacement_seen"] = max(
                (sample["from_start"] for sample in samples), default=0.0
            )
            report["distance_to_goal"] = round(
                math.hypot(goal[0] - float(end_x), goal[1] - float(end_y)), 2
            )
            report["moved"] = bool(report["max_displacement_seen"] > 1.0)
            report["ever_moving"] = any(sample["moving"] for sample in samples)
            print(
                f"end ({end_x:.1f}, {end_y:.1f}) displacement={report['displacement']} "
                f"max_seen={report['max_displacement_seen']} to_goal={report['distance_to_goal']} "
                f"moved={report['moved']} ever_moving={report['ever_moving']}"
            )

    after = entries.snapshot()
    after_jumps = entries.foreign_entries()
    entries.close()
    report["entries_before"] = {name: row["head"].hex(" ") for name, row in before.items()}
    report["entries_after_disconnect"] = {name: row["head"].hex(" ") for name, row in after.items()}
    report["hooks_original_after_disconnect"] = (
        {name: row["head"] for name, row in after.items()}
        == {name: row["head"] for name, row in before.items()}
        and {name: row["head"] for name, row in after_jumps.items()}
        == {name: row["head"] for name, row in before_jumps.items()}
    )
    report["note"] = (
        "exactly one client function was called: agent.move_to_func, once, through Player.Move "
        "(FLOAT_PTR: the source's own {x, y, zplane, 0.0} array). Everything after it is reads."
    )
    return _write(report, report_path, code)


if __name__ == "__main__":
    raise SystemExit(main())
