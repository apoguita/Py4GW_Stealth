"""Read-only: what screen the client is on, by the port's own members."""

from __future__ import annotations

import sys
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


def main() -> int:
    from py4gw import client as client_module
    from py4gw.map import Map
    from py4gw.party import Party
    from py4gw.player import Player

    from tests.probe_party_live import _LiveClient

    win32 = Win32()
    clients = win32.find_guild_wars()
    if not clients:
        print("no client")
        return 1
    process = clients[0]
    pid = int(process["pid"])
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
            print(f"pid {pid}  base {module['base_address']:#x}")
            for label, call in (
                ("Map.GetMapID", Map.GetMapID),
                ("Map.IsMapReady", Map.IsMapReady),
                ("Map.IsOutpost", Map.IsOutpost),
                ("Map.IsExplorable", Map.IsExplorable),
                ("Map.GetInstanceType", Map.GetInstanceType),
                ("Map.GetRegion", Map.GetRegion),
                ("Map.IsMapLoading", Map.IsMapLoading),
                ("Map.IsInCinematic", Map.IsInCinematic),
                ("Player.GetAgentID", Player.GetAgentID),
                ("Party.IsPartyLoaded", Party.IsPartyLoaded),
                ("Party.GetPartySize", Party.GetPartySize),
                ("Party.GetPlayerCount", Party.GetPlayerCount),
            ):
                print(f"  {label:26s} = {_ask(call)}")
            game = stand_in._game_context.read()
            print(f"  game context: {game}")
            print(f"  char context: {jsonable(_ask(stand_in.read_char_context))}")
            print(f"  pre-game:     {jsonable(_ask(lambda: stand_in.pre_game_context.read()))}")
            print(f"  agent array size: {_ask(lambda: len(stand_in.agent_array.read_context().GetAgentArray()))}")
            print(f"  map ctx address: {_ask(stand_in._map_context.resolve_address)}")
            print(f"  pathing maps: {_ask(lambda: len(Map.Pathing.GetPathingMaps() or []))}")
            print(f"  world ctx:    {jsonable(_ask(stand_in.read_world_context))}")
        finally:
            client_module._current_client = previous  # type: ignore[attr-defined]
    finally:
        reader.close()
    return 0


def jsonable(value: object) -> str:
    fields = []
    for name in ("player_name_str", "character_name_str", "is_logged_in", "map_id", "instance_type"):
        if hasattr(value, name):
            fields.append(f"{name}={getattr(value, name)!r}")
    return ", ".join(fields) if fields else repr(value)[:120]


if __name__ == "__main__":
    raise SystemExit(main())
