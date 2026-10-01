"""Read-only watcher: report the moment the client has a map loaded (pathing data exists).

Reads the client every 10 seconds for up to ~8 minutes and prints one line per sample, flagging the
first sample where `Map.GetMapID()` is non-zero **and** the map publishes pathing records — which is
the state every pathing test needs, and the state a client at character-select does not have.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from py4gw.memory import ProcessMemoryReader  # noqa: E402
from py4gw.scanner import PatternCatalog, RemoteScanner  # noqa: E402
from py4gw.win32 import Win32  # noqa: E402


def _ask(call):
    try:
        return call()
    except Exception as error:  # noqa: BLE001 - reported
        return f"{type(error).__name__}: {error}"


def sample(pid: int, win32: Win32):
    from py4gw import client as client_module
    from py4gw.map import Map
    from py4gw.party import Party
    from py4gw.player import Player

    from tests.probe_party_live import _LiveClient

    module = win32.get_main_module(pid)
    reader = ProcessMemoryReader(win32, pid)
    try:
        scanner = RemoteScanner(reader, int(module["base_address"]), int(module["size"]))
        scanner.initialize()
        patterns = PatternCatalog.from_directory("offsets")
        stand_in = _LiveClient(pid, reader, scanner, patterns)
        previous = client_module._current_client
        client_module._current_client = stand_in  # type: ignore[attr-defined]
        try:
            return {
                "map_id": _ask(Map.GetMapID),
                "ready": _ask(Map.IsMapReady),
                "player": _ask(Player.GetAgentID),
                "party": _ask(Party.GetPartySize),
                "loaded": _ask(Party.IsPartyLoaded),
                "pathing_maps": _ask(lambda: len(Map.Pathing.GetPathingMaps() or [])),
                "agents": _ask(lambda: len(stand_in.agent_array.read_context().GetAgentArray())),
            }
        finally:
            client_module._current_client = previous  # type: ignore[attr-defined]
    finally:
        reader.close()


def main() -> int:
    win32 = Win32()
    clients = win32.find_guild_wars()
    if not clients:
        print("no client")
        return 1
    pid = int(clients[0]["pid"])
    print(f"watching pid {pid}", flush=True)
    for index in range(48):
        state = sample(pid, win32)
        stamp = time.strftime("%H:%M:%S")
        in_map = isinstance(state["map_id"], int) and state["map_id"] > 0
        print(
            f"{stamp}  map_id={state['map_id']} ready={state['ready']} player={state['player']} "
            f"party={state['party']} pathing_maps={state['pathing_maps']} agents={state['agents']}",
            flush=True,
        )
        if in_map and isinstance(state["pathing_maps"], int) and state["pathing_maps"] > 0:
            print(f"{stamp}  *** IN A MAP WITH PATHING DATA — the pathing tests can run ***", flush=True)
            return 0
        time.sleep(10)
    print("no map loaded within the watch window", flush=True)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
