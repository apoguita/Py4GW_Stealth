"""Live ``Map`` pass, **elevated**, with progress on stdout and in a file.

Why this exists rather than a plain ``unittest`` run: a live suite is silent until it finishes, and
``Map.Pathing``'s geometry members are ``O(trapezoids)`` — a map's ``GetMapQuads()`` builds one
``Quad`` per trapezoid, and **each** ``Quad`` calls ``Map.MissionMap.MapProjection.GameMapToScreen``
four times, which re-reads the map bounds, the mission-map frame and the viewport scale every time.
Reforged memoises those reads for one frame with ``@frame_cache``; this port drops the decorator by
rule (``docs/PORTING_RULES.md``), so the same loop costs a re-read per call. That is a real,
measurable property of the port, so this probe **measures it and reports the numbers** instead of
running an unbounded loop that looks like a hang.

Two outputs, deliberately:

* **stdout**, flushed per line, so the elevated window shows where it is;
* a **progress file**, appended per line, so the same lines can be read while it runs.

Usage (elevated)::

    python tests/probe_map_live.py live_reports/map_live_progress.txt
"""

from __future__ import annotations

import json
import math
import sys
import threading
import time
from typing import Any, Callable

PROGRESS_PATH = sys.argv[1] if len(sys.argv) > 1 else ""
REPORT_PATH = sys.argv[2] if len(sys.argv) > 2 else ""

#: How many quads the per-item measurement builds before extrapolating. Small, because the point is
#: the per-item cost, not the total.
QUAD_SAMPLE = 20

_progress_handle = None
_progress_lock = threading.Lock()
_started = time.monotonic()


def say(message: str) -> None:
    """One progress line, on the console and in the file, immediately."""

    elapsed = time.monotonic() - _started
    line = f"[{elapsed:7.2f}s] {message}"
    with _progress_lock:
        print(line, flush=True)
        if _progress_handle is not None:
            _progress_handle.write(line + "\n")
            _progress_handle.flush()


class _Heartbeat:
    """Keep saying something while a single slow call runs.

    ``py4gw.connect()`` performs the one-time signature scan and installs the layer, which takes
    seconds with no output of its own — long enough to look like a hang. A cancelled probe teaches
    nothing, so the wait is narrated.
    """

    def __init__(self, label: str, every: float = 2.0) -> None:
        self._label = label
        self._every = every
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        while not self._stop.wait(self._every):
            say(f"    ... still {self._label}")

    def __enter__(self) -> "_Heartbeat":
        self._thread.start()
        return self

    def __exit__(self, *_: Any) -> bool:
        self._stop.set()
        self._thread.join(timeout=1.0)
        return False


def timed(label: str, call: Callable[[], Any]) -> tuple[Any, float]:
    """Run one section, report its elapsed time, and never let it kill the run."""

    begin = time.monotonic()
    try:
        value = call()
        elapsed = time.monotonic() - begin
        say(f"{label}: {elapsed * 1000:.1f} ms -> {_brief(value)}")
        return value, elapsed
    except Exception as error:  # noqa: BLE001 - reported, never hidden
        elapsed = time.monotonic() - begin
        say(f"{label}: {elapsed * 1000:.1f} ms -> !! {type(error).__name__}: {error}")
        return f"{type(error).__name__}: {error}", elapsed


def _brief(value: Any) -> str:
    text = repr(value)
    return text if len(text) <= 150 else text[:147] + "..."


def main() -> int:
    global _progress_handle

    if PROGRESS_PATH:
        _progress_handle = open(PROGRESS_PATH, "w", encoding="utf-8")

    report: dict[str, Any] = {}
    say("start: importing and finding the client")
    try:
        import py4gw
        from py4gw import Win32
        from py4gw.context.gw_context import GWContext
        from py4gw.context.instance_info_context import AreaInfoStruct
        from py4gw.map import Map
        from py4gw.player import Player
    except Exception as error:  # noqa: BLE001
        say(f"import failed: {type(error).__name__}: {error}")
        return _finish(report)

    win32 = Win32()
    clients = win32.find_guild_wars()
    report["elevated"] = bool(win32.is_elevated())
    report["clients"] = len(clients)
    say(f"elevated={report['elevated']} clients={len(clients)}")
    if not clients:
        report["error"] = "no Guild Wars client is running"
        return _finish(report)

    pid = int(clients[0]["pid"])
    report["pid"] = pid
    say(f"connecting to pid {pid} (this installs the capability layer)")
    try:
        with _Heartbeat("connecting"):
            client = py4gw.connect(clients[0])
    except Exception as error:  # noqa: BLE001 - reported with its own traceback
        import traceback

        say(f"connect failed: {type(error).__name__}: {error}")
        if _progress_handle is not None:
            _progress_handle.write(traceback.format_exc())
            _progress_handle.flush()
        report["error"] = f"connect failed: {type(error).__name__}: {error}"
        return _finish(report)
    say("connected")

    try:
        # ── the gate and identity ────────────────────────────────────────
        say("-- section: the readiness gate and identity")
        report["gate"] = {
            "IsMapDataLoaded": timed("IsMapDataLoaded", Map.IsMapDataLoaded)[0],
            "GetInstanceType": timed("GetInstanceType", Map.GetInstanceType)[0],
            "GetInstanceTypeName": timed("GetInstanceTypeName", Map.GetInstanceTypeName)[0],
            "IsMapReady": timed("IsMapReady", Map.IsMapReady)[0],
            "GetMapID": timed("GetMapID", Map.GetMapID)[0],
            "IsInCinematic": timed("IsInCinematic", Map.IsInCinematic)[0],
            "IsObservingMatch": timed("IsObservingMatch", Map.IsObservingMatch)[0],
        }
        map_id = Map.GetMapID()

        # ── name tables ──────────────────────────────────────────────────
        say("-- section: the name tables")
        report["names"] = {
            "outposts": timed("GetOutpostIDs", lambda: len(Map.GetOutpostIDs()))[0],
            "map_name": timed("GetMapName", Map.GetMapName)[0],
            "id_by_name": timed(
                "GetMapIDByName", lambda: Map.GetMapIDByName(Map.GetMapName())
            )[0],
            "base_map_id": timed("GetBaseMapID", Map.GetBaseMapID)[0],
            "variants": timed("GetAllMapVariants", lambda: Map.GetAllMapVariants(map_id))[0],
        }

        # ── region, language, instance ───────────────────────────────────
        say("-- section: region, language, district, uptime, players")
        report["instance"] = {
            "GetRegion": timed("GetRegion", Map.GetRegion)[0],
            "GetLanguage": timed("GetLanguage", Map.GetLanguage)[0],
            "GetDistrict": timed("GetDistrict", Map.GetDistrict)[0],
            "GetRegionType": timed("GetRegionType", Map.GetRegionType)[0],
            "GetCampaign": timed("GetCampaign", Map.GetCampaign)[0],
            "GetContinent": timed("GetContinent", Map.GetContinent)[0],
            "GetInstanceUptime": timed("GetInstanceUptime", Map.GetInstanceUptime)[0],
            "GetAmountOfPlayersInInstance": timed(
                "GetAmountOfPlayersInInstance", Map.GetAmountOfPlayersInInstance
            )[0],
        }

        # ── foes, vanquish ───────────────────────────────────────────────
        say("-- section: foes and vanquish")
        report["foes"] = {
            "GetFoesKilled": timed("GetFoesKilled", Map.GetFoesKilled)[0],
            "GetFoesToKill": timed("GetFoesToKill", Map.GetFoesToKill)[0],
            "IsVanquishable": timed("IsVanquishable", Map.IsVanquishable)[0],
            "IsVanquishCompleted": timed("IsVanquishCompleted", Map.IsVanquishCompleted)[0],
            "IsMapUnlocked": timed("IsMapUnlocked", Map.IsMapUnlocked)[0],
        }

        # ── the AreaInfo block, and the array checked against it ─────────
        say("-- section: AreaInfo readers, then the array against the loaded record")
        area = GWContext.InstanceInfo().GetMapInfo()
        report["area_present"] = area is not None
        if area is not None:
            mismatches: list[str] = []
            unloaded = Map.GetUnloadedMapInfo(map_id)
            if unloaded is None:
                mismatches.append("GetUnloadedMapInfo answered None for the current map")
            else:
                for field in AreaInfoStruct._fields_:
                    name = field[0]
                    if int(getattr(unloaded, name)) != int(getattr(area, name)):
                        mismatches.append(
                            f"{name}: array={int(getattr(unloaded, name))} "
                            f"loaded={int(getattr(area, name))}"
                        )
            report["unloaded_vs_loaded_mismatches"] = mismatches
            say(
                "GetUnloadedMapInfo(GetMapID()) vs the loaded AreaInfo: "
                + (f"{len(mismatches)} disagreements" if mismatches else "all fields agree")
            )

        say("-- section: bounds")
        report["bounds"] = {
            "GetMapBoundaries": timed("GetMapBoundaries", Map.GetMapBoundaries)[0],
            "GetMapWorldMapBounds": timed(
                "GetMapWorldMapBounds", Map.GetMapWorldMapBounds
            )[0],
        }

        # ── the frame-lookup members ─────────────────────────────────────
        say("-- section: the window namespaces")
        report["frames"] = {
            "IsEnteringChallenge": timed("IsEnteringChallenge", Map.IsEnteringChallenge)[0],
            "MissionMap.GetFrame": timed(
                "MissionMap.GetFrame", lambda: repr(Map.MissionMap.GetFrame())
            )[0],
            "MissionMap.IsWindowOpen": timed(
                "MissionMap.IsWindowOpen", Map.MissionMap.IsWindowOpen
            )[0],
            "MiniMap.GetFrameID": timed("MiniMap.GetFrameID", Map.MiniMap.GetFrameID)[0],
            "WorldMap.GetFrameID": timed("WorldMap.GetFrameID", Map.WorldMap.GetFrameID)[0],
            "Pregame.GetFrameID": timed("Pregame.GetFrameID", Map.Pregame.GetFrameID)[0],
        }

        # ── the frame geometry (this is what needs the root frame) ───────
        say("-- section: frame geometry (needs the root frame and the render viewport)")
        report["geometry"] = {
            "MissionMap.GetMissionMapWindowCoords": timed(
                "MissionMap window coords", Map.MissionMap.GetMissionMapWindowCoords
            )[0],
            "MissionMap.GetMissionMapContentsCoords": timed(
                "MissionMap contents coords", Map.MissionMap.GetMissionMapContentsCoords
            )[0],
            "MissionMap.GetScale": timed("MissionMap.GetScale", Map.MissionMap.GetScale)[0],
            "MissionMap.GetZoom": timed("MissionMap.GetZoom", Map.MissionMap.GetZoom)[0],
            "MissionMap.GetPanOffset": timed(
                "MissionMap.GetPanOffset", Map.MissionMap.GetPanOffset
            )[0],
            "MiniMap.GetWindowCoords": timed(
                "MiniMap.GetWindowCoords", Map.MiniMap.GetWindowCoords
            )[0],
            "MiniMap.GetScale": timed("MiniMap.GetScale", Map.MiniMap.GetScale)[0],
            "MiniMap.GetRotation": timed(
                "MiniMap.GetRotation", Map.MiniMap.GetRotation
            )[0],
            "MiniMap.IsLocked": timed("MiniMap.IsLocked", Map.MiniMap.IsLocked)[0],
        }

        # ── one projection round trip ────────────────────────────────────
        say("-- section: the projections")
        x, y = 0.0, 0.0
        if area is not None:
            x, y = float(area.icon_start_x), float(area.icon_start_y)
        screen, _ = timed(
            "MissionMap GamePosToScreen", lambda: Map.MissionMap.MapProjection.GamePosToScreen(x, y)
        )
        if isinstance(screen, tuple):
            back, _ = timed(
                "MissionMap ScreenToGamePos",
                lambda: Map.MissionMap.MapProjection.ScreenToGamePos(*screen),
            )
            if isinstance(back, tuple):
                report["projection_round_trip_error"] = (
                    abs(back[0] - x),
                    abs(back[1] - y),
                )
        report["normalized"], _ = timed(
            "NormalizedScreenToScreen(0, 0)",
            lambda: Map.MissionMap.MapProjection.NormalizedScreenToScreen(0.0, 0.0),
        )

        # ── pathing: counts, then the per-quad measurement ───────────────
        say("-- section: pathing reads")
        maps, _ = timed("Pathing.GetPathingMaps", Map.Pathing.GetPathingMaps)
        trapezoids = 0
        if isinstance(maps, list):
            trapezoids = sum(len(layer.trapezoids) for layer in maps)
        report["pathing_maps"] = len(maps) if isinstance(maps, list) else maps
        report["pathing_trapezoids"] = trapezoids
        report["available_map_ids"] = timed(
            "Pathing.GetAvailableMapIds", lambda: len(Map.Pathing.GetAvailableMapIds())
        )[0]
        report["spawns"] = timed(
            "Pathing.GetSpawns", lambda: [len(g) for g in Map.Pathing.GetSpawns()]
        )[0]
        report["travel_portals"] = timed(
            "Pathing.GetTravelPortals", lambda: len(Map.Pathing.GetTravelPortals())
        )[0]

        say("-- section: the per-quad cost, on a sample (NOT the whole map)")
        sample_cost = 0.0
        if isinstance(maps, list) and trapezoids:
            first = next(
                (t for layer in maps for t in layer.trapezoids), None
            )
            if first is not None:
                begin = time.monotonic()
                for _ in range(QUAD_SAMPLE):
                    Map.Pathing.Quad(first)
                sample_cost = (time.monotonic() - begin) / QUAD_SAMPLE
                say(f"one Quad(): {sample_cost * 1000:.2f} ms  ({QUAD_SAMPLE} built)")
                say(
                    f"GetMapQuads() would build {trapezoids} of them: "
                    f"~{sample_cost * trapezoids:.1f} s"
                )
        report["quad_ms_each"] = sample_cost * 1000
        report["quad_estimate_seconds"] = sample_cost * trapezoids

        # ── the end-to-end pathing check, with its cost stated first ─────
        estimate = sample_cost * trapezoids
        if estimate > 60.0:
            say(
                f"SKIPPING IsPointInPathing: the estimate above is {estimate:.0f} s, and this probe "
                "reports the cost rather than hanging. That estimate IS the finding."
            )
            report["point_in_pathing"] = {"skipped": True, "estimated_seconds": estimate}
        else:
            position = Player.GetXY()
            say(f"player at {position}; running IsPointInPathing (est. {estimate:.1f} s)")
            inside, elapsed = timed(
                "Pathing.IsPointInPathing(player)",
                lambda: Map.Pathing.IsPointInPathing(float(position[0]), float(position[1])),
            )
            report["point_in_pathing"] = {
                "player": position,
                "inside": inside,
                "seconds": elapsed,
            }

        # ── the recorded divergences ─────────────────────────────────────
        say("-- section: the recorded divergences must still refuse")
        refusals: dict[str, str] = {}
        for label, call in (
            ("MissionMap.IsMouseOver", Map.MissionMap.IsMouseOver),
            ("MiniMap.GetLastClickCoords", Map.MiniMap.GetLastClickCoords),
            ("WorldMap.GetLastRightClickCoords", Map.WorldMap.GetLastRightClickCoords),
            ("Pathing.WorldToScreen", lambda: Map.Pathing.WorldToScreen(0.0, 0.0)),
        ):
            try:
                call()
                refusals[label] = "DID NOT RAISE"
            except NotImplementedError as error:
                refusals[label] = str(error)[:90]
            except Exception as error:  # noqa: BLE001
                refusals[label] = f"{type(error).__name__}: {error}"
        report["refusals"] = refusals
        say(
            "refusals: "
            + ("all four named their need" if all(
                v != "DID NOT RAISE" for v in refusals.values()
            ) else "SOMETHING DID NOT RAISE")
        )

        say("disconnecting (restores the client's own bytes)")
    finally:
        try:
            py4gw.disconnect()
            say("disconnected")
        except Exception as error:  # noqa: BLE001
            say(f"disconnect failed: {type(error).__name__}: {error}")

    return _finish(report)


def _finish(report: dict[str, Any]) -> int:
    say(f"done in {time.monotonic() - _started:.1f}s")
    if _progress_handle is not None:
        _progress_handle.close()
    text = json.dumps(report, indent=2, ensure_ascii=False, default=str)
    if REPORT_PATH:
        with open(REPORT_PATH, "w", encoding="utf-8") as handle:
            handle.write(text)
    print(text, flush=True)
    return 0


if __name__ == "__main__":
    # The elevated console's output cannot be redirected (`Start-Process -Verb RunAs` does not
    # support redirection), so a failure has to be written where it can be read: the same progress
    # file the sections go to.
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException:  # noqa: BLE001 - reported to the file, then re-raised
        import traceback

        text = traceback.format_exc()
        print(text, flush=True)
        if PROGRESS_PATH:
            with open(PROGRESS_PATH, "a", encoding="utf-8") as handle:
                handle.write("\n=== the probe itself failed ===\n" + text)
        raise SystemExit(1)
