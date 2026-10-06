"""Live probe: ask this port for a path and then **walk it**.

The owner's test, in the owner's words: *take the player's position, ask for a path 500 units in front,
with the result path, walk it*. Nothing here is a new mechanism — it is the port's own members in the
order a caller would use them:

1. the player's own position and facing (`Player.GetAgent().pos`, `Agent.GetRotationCos`/`Sin`) — the
   facing the **client** holds, so "in front" is the client's own direction, not one this probe picked;
2. `AutoPathing.get_path(start, goal)` — the source's route (the client's planner first, the navmesh
   route second), and `AutoPathing.get_path_to(x, y)` beside it;
3. `Player.Move(x, y, zplane)` per waypoint — `agent.move_to_func` through the port's `FLOAT_PTR` call
   form — then **wait and watch**: the player's position, its distance to the waypoint and whether the
   client reports it moving, until it arrives or the leg's own timeout expires.

**This moves the character.** It is a deliberate live write, bounded on every axis: one connection, one
walk, a per-leg timeout, a whole-walk budget, a no-progress stop, and the client's position reported
before and after. Nothing else in the game is touched — no map, no party, no skill, no target.

Usage::

    python tests/probe_pathing_walk.py [report-path] [--distance 500] [--pid PID]   # elevated
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

REPORT_PATH = "tests/live_reports/pathing_walk.json"

#: How far in front of the player the goal sits, in game units.
GOAL_DISTANCE = 500.0

#: A waypoint counts as reached inside this radius: the client walks in a straight line to the point it
#: was given and stops on it, so this is slack for the walk's own end, not a tolerance on the path.
ARRIVAL_RADIUS = 60.0

#: One leg's budget, and the whole walk's. A leg that expires is reported, never retried.
LEG_TIMEOUT_SECONDS = 10.0
WALK_BUDGET_SECONDS = 90.0

#: How often the walk reads the player while it waits.
POLL_SECONDS = 0.1

#: If the distance to the leg's target has not improved by this much within this long, the client is
#: not walking: the leg ends and says so. (A character blocked by geometry walks into it forever.)
PROGRESS_EPSILON = 1.0
PROGRESS_WINDOW_SECONDS = 2.5


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


def walk_path(
    agent_id: int,
    path: list[tuple[float, float]],
    zplane: int,
    started_at: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Walk ``path`` waypoint by waypoint, reporting each leg and the trail the player left."""

    from py4gw.agent import Agent
    from py4gw.player import Player

    legs: list[dict[str, Any]] = []
    trail: list[dict[str, Any]] = []

    def observe(leg_target: tuple[float, float]) -> tuple[float, float, float]:
        x, y = Agent.GetXY(agent_id)
        distance = math.hypot(leg_target[0] - float(x), leg_target[1] - float(y))
        moving = bool(_ask(lambda: Agent.IsMoving(agent_id)))
        trail.append(
            {
                "t": round(time.monotonic() - started_at, 2),
                "x": round(float(x), 2),
                "y": round(float(y), 2),
                "to_waypoint": round(distance, 1),
                "moving": moving,
            }
        )
        return float(x), float(y), distance

    for index, target in enumerate(path):
        if index == 0:
            # The source's own path starts where the player is: nothing to walk to.
            x, y, _ = observe(target)
            legs.append(
                {
                    "index": 0,
                    "waypoint": [round(target[0], 2), round(target[1], 2)],
                    "skipped": "the path's first point is the player's own position",
                    "player": [round(x, 2), round(y, 2)],
                }
            )
            continue

        # The move targets **z-layer 0**, always, with no exceptions: the source's own default, and
        # what every Reforged caller passes (`Movement.py:83`, `Sequential.py:58`, `BuildMgr.py:1451`).
        # A run that passed the player's own zplane (22) started the walk and got the owner
        # disconnected from the server; with 0 the same call walks and the client stays.
        Player.Move(float(target[0]), float(target[1]))
        leg: dict[str, Any] = {
            "index": index,
            "waypoint": [round(target[0], 2), round(target[1], 2)],
            "moved_at": round(time.monotonic() - started_at, 2),
        }
        leg_started = time.monotonic()
        best_distance: float | None = None
        best_at = leg_started
        while True:
            _x, _y, distance = observe(target)
            if best_distance is None or distance < best_distance - PROGRESS_EPSILON:
                best_distance, best_at = distance, time.monotonic()
            if distance <= ARRIVAL_RADIUS:
                leg["arrived"] = True
                break
            now = time.monotonic()
            if now - leg_started > LEG_TIMEOUT_SECONDS:
                leg["arrived"] = False
                leg["timed_out"] = True
                break
            if now - best_at > PROGRESS_WINDOW_SECONDS:
                leg["arrived"] = False
                leg["no_progress"] = True
                break
            if now - started_at > WALK_BUDGET_SECONDS:
                leg["arrived"] = False
                leg["budget_exhausted"] = True
                break
            time.sleep(POLL_SECONDS)
        leg["seconds"] = round(time.monotonic() - leg_started, 2)
        leg["final_distance"] = round(distance, 1)
        legs.append(leg)
        if not leg.get("arrived"):
            break
    return legs, trail


def main() -> int:
    from py4gw.win32 import Win32
    from tests.probe_two_runtimes_live import connectable
    from tests.test_live_coexistence import _Entries

    win32 = Win32()
    argv = list(sys.argv[1:])
    distance = GOAL_DISTANCE
    if "--distance" in argv:
        index = argv.index("--distance")
        distance = float(argv[index + 1])
        del argv[index : index + 2]
    pid_argument = ""
    if "--pid" in argv:
        index = argv.index("--pid")
        pid_argument = argv[index + 1]
        del argv[index : index + 2]
    report_path = argv[0] if argv else REPORT_PATH

    report: dict[str, Any] = {"stage": "pathing-walk", "goal_distance": distance}
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
    from py4gw.pathing import AutoPathing
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
            start_x = float(player.pos.x)
            start_y = float(player.pos.y)
            zplane = int(player.pos.zplane)
            rotation_angle = float(_ask(lambda: Agent.GetRotationAngle(agent_id)))
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
                "rotation_angle": round(rotation_angle, 4),
                "rotation_cos_sin": [round(cos, 4), round(sin, 4)],
                "facing_unit": [round(unit[0], 4), round(unit[1], 4)],
            }
            report["goal"] = [round(goal[0], 2), round(goal[1], 2)]
            report["goal_distance_from_start"] = round(
                math.hypot(goal[0] - start_x, goal[1] - start_y), 2
            )
            print(
                f"player {agent_id} at ({start_x:.1f}, {start_y:.1f}) zplane {zplane} "
                f"facing ({unit[0]:.3f}, {unit[1]:.3f}) -> goal ({goal[0]:.1f}, {goal[1]:.1f})"
            )

            started_at = time.monotonic()
            auto = AutoPathing()
            for _ in auto.load_pathing_maps():
                pass

            path3 = _ask(lambda: auto.get_path((start_x, start_y, float(zplane)),
                                             (goal[0], goal[1], float(zplane))))
            report["get_path"] = (
                path3
                if isinstance(path3, str)
                else [[round(p[0], 2), round(p[1], 2), round(p[2], 2)] for p in path3]
            )
            path2 = _ask(lambda: auto.get_path_to(goal[0], goal[1]))
            report["get_path_to"] = (
                path2 if isinstance(path2, str) else [[round(p[0], 2), round(p[1], 2)] for p in path2]
            )

            walk_source = path3 if isinstance(path3, list) else []
            if not walk_source:
                report["walk"] = "not attempted: the port answered no path"
                code = 3
            else:
                points = [(float(p[0]), float(p[1])) for p in walk_source]
                report["walked_path"] = [[round(x, 2), round(y, 2)] for x, y in points]
                print(f"walking {len(points)} point(s): {report['walked_path']}")
                legs, trail = walk_path(agent_id, points, zplane, started_at)
                report["legs"] = legs
                report["trail"] = trail
                _final_x, _final_y = Agent.GetXY(agent_id)
                report["end"] = [round(float(_final_x), 2), round(float(_final_y), 2)]
                report["displacement"] = round(
                    math.hypot(float(_final_x) - start_x, float(_final_y) - start_y), 2
                )
                reached = math.hypot(goal[0] - float(_final_x), goal[1] - float(_final_y))
                report["distance_to_goal"] = round(reached, 2)
                report["goal_reached"] = bool(reached <= ARRIVAL_RADIUS)
                report["walk_seconds"] = round(time.monotonic() - started_at, 2)
                report["every_leg_arrived"] = bool(legs) and all(
                    leg.get("arrived") for leg in legs
                )
                print(
                    f"end ({_final_x:.1f}, {_final_y:.1f}) displacement "
                    f"{report['displacement']:.1f} | to goal {report['distance_to_goal']:.1f} | "
                    f"goal_reached={report['goal_reached']}"
                )
                code = 0 if report["every_leg_arrived"] else 4

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
        "one connection; the port's own get_path, then Player.Move per waypoint with the player's "
        "position and the client's moving flag watched until each waypoint was reached or its own "
        "timeout expired. Nothing but the character moved."
    )
    return _write(report, report_path, code)


if __name__ == "__main__":
    raise SystemExit(main())
