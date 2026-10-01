"""Live probe: the ported pathing against the running client — reads first, the client's finder last.

Two stages, and the split is the project's own discipline (``AGENTS.md``: a live write is deliberate,
bounded and attributable):

* ``reads`` — **the default, and it needs no elevation.** A read-only stand-in over the live process
  (the same shape ``tests/probe_party_live.py`` uses) runs everything pathing does *without* calling
  the client: the two pathing-map reads, the navmesh build over the client's own trapezoids
  (``AutoPathing.load_pathing_maps`` is pure Python over ``MapContext`` reads), the BSP and the
  neighbour graph, **an A-star search between the player's position and a point nearby**, and the LOS
  smoothing of that path. It also measures the ABI of ``pathing.find_path_func`` — its entry bytes and
  its epilogue — because the stage that calls it must know whether the callee releases its own
  arguments before it pushes six words at it.
* ``act`` — **elevated.** Connects, then calls the client's own finder through the port's
  ``PathPlanner`` (``plan`` and ``compute_immediate``) and through ``AutoPathing.get_path``, reporting
  each answer beside the client state before and after — the player's position must not move, because
  a path is computed, not walked.

Usage::

    python tests/probe_pathing_live.py reads [report-path]
    python tests/probe_pathing_live.py act   [report-path]      # elevated
"""

from __future__ import annotations

import json
import struct
import sys
import time
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from py4gw.memory import ProcessMemoryReader  # noqa: E402
from py4gw.scanner import PatternCatalog, RemoteScanner  # noqa: E402
from py4gw.win32 import Win32  # noqa: E402

REPORT_PATH = "live_reports/pathing_live.json"

#: How far the search's goal sits from the player, in game units. Far enough to leave the trapezoid
#: the player stands in, near enough to be a route the client's own finder can answer.
GOAL_OFFSET = 300.0


def _ask(call: Any) -> Any:
    """Run one member and report what it answered, or exactly how it refused."""

    try:
        return call()
    except Exception as error:  # noqa: BLE001 - reported, never hidden
        return f"{type(error).__name__}: {error}"


def _epilogue(reader: ProcessMemoryReader, address: int, window: int = 0x400) -> dict[str, Any]:
    """Read a function's opening bytes and find the ``ret`` that ends it.

    The point is the *shape* of that ``ret``: a bare ``C3`` means the **caller** releases the stack
    words (``__cdecl``, which is what Native declares this function as, and what the port's
    ``STACK_WORDS`` form does), while ``C2 imm16`` means the callee pops them and the caller must not.
    A six-word call into a callee that pops is a corrupt stack, so this is measured before the call
    rather than discovered by it.
    """

    raw = reader.read(address, window)
    candidates: list[dict[str, Any]] = []
    for index, byte in enumerate(raw):
        if byte == 0xC3:
            candidates.append({"offset": index, "form": "ret"})
        elif byte == 0xC2 and index + 2 < len(raw):
            popped = struct.unpack_from("<H", raw, index + 1)[0]
            if popped and popped <= 0x40 and popped % 4 == 0:
                candidates.append({"offset": index, "form": f"ret {popped:#x}", "pops": popped})
    return {
        "entry": raw[:16].hex(" "),
        "window": window,
        "candidates": candidates[:24],
        "first": candidates[0] if candidates else None,
    }


def reads_stage(win32: Win32, process: dict[str, Any], report: dict[str, Any]) -> int:
    """Everything pathing does that needs no client call, against the live process."""

    from py4gw import client as client_module
    from py4gw.agent import Agent
    from py4gw.map import Map
    from py4gw.pathing import AStar, AutoPathing
    from py4gw.player import Player

    from tests.probe_party_live import _LiveClient

    pid = int(process["pid"])
    module = win32.get_main_module(pid)
    report["module"] = {
        "base": hex(int(module["base_address"])),
        "size": hex(int(module["size"])),
    }
    reader = ProcessMemoryReader(win32, pid)
    try:
        scanner = RemoteScanner(reader, int(module["base_address"]), int(module["size"]))
        scanner.initialize()
        patterns = PatternCatalog.from_directory("offsets")
        stand_in = _LiveClient(pid, reader, scanner, patterns)
        previous = client_module._current_client
        client_module._current_client = stand_in  # type: ignore[attr-defined]
        try:
            resolved = patterns.resolve("pathing.find_path_func", scanner)
            report["resolve"] = {
                "ok": bool(resolved.ok),
                "address": hex(int(resolved.value)) if resolved.ok else None,
            }
            if resolved.ok:
                report["abi"] = _epilogue(reader, int(resolved.value))

            # -- the map's own pathing data, through the ported members -------------------------
            report["pathing_maps_live"] = _ask(lambda: len(Map.Pathing.GetPathingMaps() or []))
            report["pathing_maps_raw"] = _ask(
                lambda: len(Map.Pathing.GetPathingMapsRaw() or [])
            )
            report["available_map_ids"] = _ask(
                lambda: len(Map.Pathing.GetAvailableMapIds() or set())
            )
            report["map"] = {"id": _ask(Map.GetMapID), "outpost": _ask(Map.IsOutpost)}

            # -- the navmesh: built from reads alone, then searched over ------------------------
            started = time.monotonic()
            auto = AutoPathing()
            report["load_pathing_maps"] = "driven to completion"
            for _ in auto.load_pathing_maps():
                pass
            report["navmesh_seconds"] = round(time.monotonic() - started, 3)

            navmesh = _ask(auto.get_navmesh)
            if navmesh is None or isinstance(navmesh, str):
                report["navmesh"] = navmesh
                report["astar"] = "not attempted: no navmesh"
            else:
                report["navmesh"] = {
                    "map_id": int(navmesh.map_id),
                    "trapezoids": len(navmesh.trapezoids),
                    "portal_links": sum(len(v) for v in navmesh.portal_graph.values()),
                }
                agent_id = _ask(Player.GetAgentID)
                x, y = _ask(lambda: Agent.GetXY(int(agent_id)))
                report["player"] = {
                    "agent_id": agent_id,
                    "x": round(float(x), 2),
                    "y": round(float(y), 2),
                }
                here = _ask(
                    lambda: navmesh.find_trapezoid_id_by_coord((float(x), float(y)))
                )
                report["trapezoid_at_player"] = here
                report["nearest_trapezoid"] = _ask(
                    lambda: navmesh.find_nearest_trapezoid_id(float(x), float(y))
                )
                if isinstance(here, int):
                    report["neighbours"] = _ask(lambda: len(navmesh.get_neighbors(here)))
                report["is_point_in_pathing"] = _ask(
                    lambda: Map.Pathing.IsPointInPathing(float(x), float(y))
                )

                astar = AStar(navmesh)
                started = time.monotonic()
                found = _ask(
                    lambda: astar.search(
                        (float(x), float(y)), (float(x) + GOAL_OFFSET, float(y))
                    )
                )
                report["astar"] = {
                    "found": found,
                    "seconds": round(time.monotonic() - started, 4),
                    "points": len(astar.get_path()) if found is True else 0,
                }
                if found is True and astar.get_path():
                    smoothed = _ask(
                        lambda: navmesh.smooth_path_by_los(astar.get_path(), 100, 200.0)
                    )
                    if not isinstance(smoothed, str):
                        report["smooth_path_by_los"] = {
                            "points": len(smoothed),
                            "ends": [smoothed[0], smoothed[-1]],
                        }
                    else:
                        report["smooth_path_by_los"] = smoothed
        finally:
            client_module._current_client = previous  # type: ignore[attr-defined]
    finally:
        reader.close()

    report["note"] = (
        "read stage: unelevated, nothing connected and no client function called. The navmesh, the "
        "BSP, the neighbour graph and the A* search are all this port's own arithmetic over the "
        "client's pathing records, so they run here; 'abi' is the epilogue measurement the elevated "
        "stage's six-word call depends on."
    )
    return 0


def act_stage(report: dict[str, Any], *, elevated_pid: int,
              goal_offset: float = GOAL_OFFSET) -> int:
    """The client's own finder, through the port's planner and through ``AutoPathing``."""

    from py4gw.agent import Agent
    from py4gw.map import Map
    from py4gw.pathing import AutoPathing, PathPlanner, PathStatus
    from py4gw.player import Player

    def where() -> dict[str, Any]:
        agent_id = _ask(Player.GetAgentID)
        xy = _ask(lambda: Agent.GetXY(int(agent_id))) if not isinstance(agent_id, str) else "?"
        return {"agent_id": agent_id, "xy": xy, "map_id": _ask(Map.GetMapID)}

    report["before"] = where()
    if isinstance(report["before"]["xy"], str):
        report["error"] = f"no player position to plan from: {report['before']['xy']}"
        return 1
    x, y = report["before"]["xy"]
    start = (float(x), float(y), 0.0)
    goal = (float(x) + goal_offset, float(y), 0.0)

    planner = PathPlanner()
    planner.reset()
    started = time.monotonic()
    report["plan_call"] = _ask(
        lambda: planner.plan(
            start_x=start[0], start_y=start[1], start_z=start[2],
            goal_x=goal[0], goal_y=goal[1], goal_z=goal[2],
        )
    )
    report["plan_seconds"] = round(time.monotonic() - started, 4)
    report["plan_status"] = str(_ask(planner.get_status))
    report["plan_is_ready"] = _ask(planner.is_ready)
    report["plan_was_successful"] = _ask(planner.was_successful)
    planned = _ask(planner.get_path)
    report["plan_points"] = len(planned) if isinstance(planned, list) else planned
    if isinstance(planned, list) and planned:
        report["plan_ends"] = [planned[0], planned[-1]]
    report["expected_status_ready"] = str(PathStatus.Ready)

    report["compute_immediate_points"] = _ask(
        lambda: len(
            planner.compute_immediate(
                start_x=start[0], start_y=start[1], start_z=start[2],
                goal_x=goal[0], goal_y=goal[1], goal_z=goal[2],
            )
        )
    )

    auto = AutoPathing()
    started = time.monotonic()
    path = _ask(lambda: auto.get_path(start, goal))
    report["get_path_seconds"] = round(time.monotonic() - started, 4)
    report["get_path"] = {
        "type": type(path).__name__,
        "points": len(path) if isinstance(path, list) else path,
    }
    if isinstance(path, list) and path:
        report["get_path_ends"] = [path[0], path[-1]]
        report["get_path_z_is_start_z"] = all(point[2] == start[2] for point in path)

    to = _ask(lambda: auto.get_path_to(goal[0], goal[1]))
    report["get_path_to"] = {
        "type": type(to).__name__,
        "points": len(to) if isinstance(to, list) else to,
    }
    if isinstance(to, list) and to:
        report["get_path_to_ends"] = [to[0], to[-1]]

    report["after"] = where()
    report["player_did_not_move"] = report["before"]["xy"] == report["after"]["xy"]
    report["note"] = (
        "act stage: the client's own find_path_func, called through the port's PathPlanner and "
        "AutoPathing. A path is computed, not walked, so the player's position must be identical "
        "afterwards; anything else is a defect."
    )
    return 0 if report["player_did_not_move"] else 4


def summary_lines(report: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    if report.get("error"):
        lines.append(f"error: {report['error']}")
    if report.get("stage") == "reads":
        resolve = report.get("resolve") or {}
        lines.append(f"find_path_func resolved: {resolve.get('ok')} at {resolve.get('address')}")
        abi = report.get("abi") or {}
        first = abi.get("first")
        if first:
            lines.append(
                f"  epilogue candidate: {first['form']} at +{first['offset']:#x} — "
                + (
                    "the caller releases (cdecl), which is what the port's STACK_WORDS does"
                    if first["form"] == "ret"
                    else "the CALLEE releases — the port's six-word call would corrupt the stack"
                )
            )
        lines.append(f"  entry: {abi.get('entry')}")
        lines.append(f"pathing maps live={report.get('pathing_maps_live')} "
                     f"raw={report.get('pathing_maps_raw')} "
                     f"available map ids={report.get('available_map_ids')}")
        navmesh = report.get("navmesh")
        lines.append(f"navmesh: {json.dumps(navmesh) if not isinstance(navmesh, dict) else navmesh}")
        lines.append(f"player at {report.get('player')} | trapezoid {report.get('trapezoid_at_player')} "
                     f"| neighbours {report.get('neighbours')}")
        lines.append(f"astar: {report.get('astar')}")
        lines.append(f"smooth_path_by_los: {report.get('smooth_path_by_los')}")
    if report.get("stage") == "act":
        lines.append(f"plan -> {report.get('plan_status')} in {report.get('plan_seconds')}s "
                     f"({report.get('plan_points')} points)")
        lines.append(f"  ends: {report.get('plan_ends')}")
        lines.append(f"compute_immediate: {report.get('compute_immediate_points')} points")
        lines.append(f"get_path: {report.get('get_path')} in {report.get('get_path_seconds')}s")
        lines.append(f"  ends: {report.get('get_path_ends')} | z is start z: "
                     f"{report.get('get_path_z_is_start_z')}")
        lines.append(f"get_path_to: {report.get('get_path_to')} ends {report.get('get_path_to_ends')}")
        lines.append(f"player did not move: {report.get('player_did_not_move')}")
    return lines


def _write(report: dict[str, Any], path: str, code: int = 0) -> int:
    for line in summary_lines(report):
        print(line)
    text = json.dumps(report, indent=2, ensure_ascii=False, default=str)
    print(text)
    if path:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
    return code


def main() -> int:
    argv = list(sys.argv[1:])
    stage = argv[0] if argv else "reads"
    report_path = argv[1] if len(argv) > 1 else REPORT_PATH

    # ``--goal-distance <units>`` moves the goal, which is how the client's own finder is asked
    # whether it answers at all: the first live run had it report ``Failed`` for a 300-unit hop while
    # the port's A* fallback answered, and a longer hop is the way to tell "the call is wrong" from
    # "the client has nothing to say about a goal inside the trapezoid the player already stands in".
    goal_offset = GOAL_OFFSET
    if "--goal-distance" in argv:
        index = argv.index("--goal-distance")
        goal_offset = float(argv[index + 1])
        del argv[index : index + 2]

    report: dict[str, Any] = {"stage": stage, "goal_offset": goal_offset}
    win32 = Win32()
    clients = win32.find_guild_wars()
    if not clients:
        report["error"] = "no Guild Wars client is running"
        return _write(report, report_path, 1)
    process = clients[0]
    report["pid"] = int(process["pid"])

    if stage == "reads":
        return _write(report, report_path, reads_stage(win32, process, report))

    from tests.probe_party_live import entry_is_original

    report["controller_elevated"] = bool(win32.is_elevated())
    if not entry_is_original(win32, int(process["pid"])):
        report["error"] = (
            "one of the hooked entries does not hold the client's own bytes, so another controller "
            "is attached or was killed while attached. Nothing was done."
        )
        return _write(report, report_path, 7)

    import py4gw

    with py4gw.connect(process, game_thread=True) as _client:
        report["game_thread"] = True
        code = act_stage(
            report, elevated_pid=int(process["pid"]), goal_offset=goal_offset
        )

    report["hooks_original_after_disconnect"] = entry_is_original(win32, int(process["pid"]))
    return _write(report, report_path, code)


if __name__ == "__main__":
    raise SystemExit(main())
