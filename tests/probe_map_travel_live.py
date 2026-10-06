"""Live **travel** pass, elevated: `Map.TravelGH`, `Map.Travel`, `Map.LeaveGH`.

These are the members that move the character, so they are the one part of `Map` a test cannot
exercise on its own initiative. The owner asked for this run, and the sequence is the owner's:

1. read the current map id;
2. `Map.TravelGH()` - travel to the guild hall;
3. `Map.Travel(that map id)` - travel back;
4. `Map.TravelGH()` again, then `Map.LeaveGH()` - the owner's own note, *"if travel gh works it is
   likely that leave gh also works"*, checked rather than assumed.

It ends with the character back in the map it started in either way, and it reports the map id after
every step, because the map id is the only evidence that a send reached the client and the client
acted on it.

**The sends themselves are the port's own members, unmodified** - `Map.TravelGH`/`Map.Travel` ->
`MapMethods.TravelGH`/`Travel` (`py4gw/map_methods.py`) -> `UIManager.SendUIMessageRaw` with
`kGuildHall` / `kTravel`; `Map.LeaveGH` -> `MapMethods.LeaveGH` -> `UIManager.SendUIMessage` with
`kLeaveGuildHall`. Nothing here re-implements a send or picks a different message id.

Progress goes to stdout (flushed per line) and to a file, for the same reason
`tests/probe_map_live.py` does it: an elevated console cannot be redirected, and a run that looks
stalled cannot be judged.

Usage (elevated)::

    python tests/probe_map_travel_live.py tests/live_reports/map_travel_progress.txt tests/live_reports/map_travel.json
"""

from __future__ import annotations

import json
import sys
import threading
import time
from typing import Any, Callable

PROGRESS_PATH = sys.argv[1] if len(sys.argv) > 1 else ""
REPORT_PATH = sys.argv[2] if len(sys.argv) > 2 else ""

#: How long one map change may take before the step is reported as not landing. A guild-hall hop is
#: a load screen plus a server round trip; 120 s is generous and still bounded.
MAP_CHANGE_TIMEOUT = 120.0
POLL_SECONDS = 1.0

_progress_handle = None
_lock = threading.Lock()
_started = time.monotonic()
_connected = False


def say(message: str) -> None:
    elapsed = time.monotonic() - _started
    line = f"[{elapsed:7.2f}s] {message}"
    with _lock:
        print(line, flush=True)
        if _progress_handle is not None:
            _progress_handle.write(line + "\n")
            _progress_handle.flush()


class _Heartbeat:
    """Say something while a single slow call or a wait runs."""

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


def wait_for_map(
    map_class: Any,
    predicate: Callable[[int], bool],
    label: str,
    timeout: float = MAP_CHANGE_TIMEOUT,
) -> dict[str, Any]:
    """Poll until the client reports a map the predicate accepts, narrating as it goes.

    ``Map.GetMapID()`` answers ``0`` while the map is not ready - the source's own gate - so a step
    in flight reads as id ``0`` rather than as a wrong id.
    """

    began = time.monotonic()
    deadline = began + timeout
    seen: list[tuple[float, int, bool]] = []
    while time.monotonic() < deadline:
        map_id = map_class.GetMapID()
        ready = map_class.IsMapReady()
        if not seen or seen[-1][1] != map_id or seen[-1][2] != ready:
            say(f"    {label}: map_id={map_id} ready={ready} instance={map_class.GetInstanceTypeName()}")
            seen.append((time.monotonic() - began, map_id, ready))
        if map_id and predicate(map_id):
            return {
                "landed": True,
                "seconds": time.monotonic() - began,
                "map_id": map_id,
                "transitions": seen,
            }
        time.sleep(POLL_SECONDS)
    return {
        "landed": False,
        "seconds": time.monotonic() - began,
        "map_id": map_class.GetMapID(),
        "transitions": seen,
        "timeout": timeout,
    }


def main() -> int:
    global _progress_handle, _connected

    if PROGRESS_PATH:
        _progress_handle = open(PROGRESS_PATH, "w", encoding="utf-8")

    report: dict[str, Any] = {"steps": []}
    say("start: importing and finding the client")
    import py4gw
    from py4gw import Win32
    from py4gw.map import Map

    win32 = Win32()
    clients = win32.find_guild_wars()
    report["elevated"] = bool(win32.is_elevated())
    if not clients:
        report["error"] = "no Guild Wars client is running"
        return _finish(report)
    if not report["elevated"]:
        report["error"] = "this run travels, and connecting requires an elevated shell"
        say("NOT ELEVATED: refusing, because this run moves the character")
        return _finish(report)

    pid = int(clients[0]["pid"])
    report["pid"] = pid
    say(f"connecting to pid {pid}")
    with _Heartbeat("connecting"):
        py4gw.connect(clients[0])
    _connected = True
    say("connected")

    try:
        if not Map.IsMapReady():
            report["error"] = (
                f"the map is not ready ({Map.GetInstanceTypeName()}); log a character into a "
                "loaded map first"
            )
            say(report["error"])
            return _finish(report)

        start_id = Map.GetMapID()
        start_name = Map.GetMapName(start_id)
        start_is_gh = Map.IsGuildHall()
        report["start"] = {"map_id": start_id, "name": start_name, "is_guild_hall": start_is_gh}
        say(f"start: map {start_id} ({start_name}), guild hall={start_is_gh}")
        if start_is_gh:
            report["error"] = "already in a guild hall; the test needs a normal map to return to"
            say(report["error"])
            return _finish(report)

        # ── step 1: travel to the guild hall ─────────────────────────────
        say("step 1: Map.TravelGH()")
        began = time.monotonic()
        Map.TravelGH()
        report["steps"].append(
            {
                "step": "TravelGH",
                "call_seconds": time.monotonic() - began,
                **wait_for_map(Map, lambda _mid: Map.IsGuildHall(), "TravelGH"),
            }
        )
        at_gh = report["steps"][-1]["landed"] and Map.IsGuildHall()
        say(f"step 1 result: guild hall={at_gh} map={Map.GetMapID()} ({Map.GetMapName()})")
        if not at_gh:
            say("TravelGH did not land in a guild hall; stopping here rather than travelling on")
            return _finish(report)

        # ── step 2: travel back to the map we started in ─────────────────
        say(f"step 2: Map.Travel({start_id})")
        began = time.monotonic()
        Map.Travel(start_id)
        report["steps"].append(
            {
                "step": f"Travel({start_id})",
                "call_seconds": time.monotonic() - began,
                **wait_for_map(Map, lambda mid: mid == start_id, f"Travel({start_id})"),
            }
        )
        back = report["steps"][-1]["landed"]
        say(f"step 2 result: back in {Map.GetMapID()} ({Map.GetMapName()}) = {back}")
        if not back:
            say("Travel did not return to the starting map; stopping here")
            return _finish(report)

        # ── step 3: the owner's note - does LeaveGH work too? ────────────
        say("step 3: Map.TravelGH() again, then Map.LeaveGH()")
        Map.TravelGH()
        arrived = wait_for_map(Map, lambda _mid: Map.IsGuildHall(), "TravelGH (second)")
        report["steps"].append({"step": "TravelGH (second)", **arrived})
        if not arrived["landed"]:
            say("the second TravelGH did not land; LeaveGH cannot be judged from here")
            return _finish(report)
        say(f"in the guild hall at map {Map.GetMapID()}; calling Map.LeaveGH()")
        began = time.monotonic()
        Map.LeaveGH()
        report["steps"].append(
            {
                "step": "LeaveGH",
                "call_seconds": time.monotonic() - began,
                **wait_for_map(Map, lambda mid: not Map.IsGuildHall() and mid != 0, "LeaveGH"),
            }
        )
        left = report["steps"][-1]["landed"]
        report["final"] = {
            "map_id": Map.GetMapID(),
            "name": Map.GetMapName(),
            "is_guild_hall": Map.IsGuildHall(),
        }
        say(f"step 3 result: left the hall={left}; now {report['final']}")
    finally:
        if _connected:
            say("disconnecting (restores the client's own bytes)")
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
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException:  # noqa: BLE001 - the elevated console cannot be redirected
        import traceback

        text = traceback.format_exc()
        print(text, flush=True)
        if PROGRESS_PATH:
            with open(PROGRESS_PATH, "a", encoding="utf-8") as handle:
                handle.write("\n=== the probe itself failed ===\n" + text)
        raise SystemExit(1)
