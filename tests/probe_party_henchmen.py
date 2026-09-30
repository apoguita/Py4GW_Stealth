"""Read-only: which henchmen are standing in this outpost, and their live agent ids.

``Henchmen.AddHenchman`` takes the henchman's **agent id**, which is a live value — the probe
deliberately never picks one for the tester. This lists the candidates instead: every living NPC whose
NPC model says ``is_henchman``, nearest first, with the distance it was ranked by. Nothing is called
and nothing is written; the walk is the port's own (``AgentArray``, the living record's
``player_number`` into the world's ``npc_models``, and ``NPC_ModelStruct.is_henchman``).

Usage: python tests/probe_party_henchmen.py
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from py4gw.memory import ProcessMemoryReader  # noqa: E402
from py4gw.scanner import PatternCatalog, RemoteScanner  # noqa: E402
from py4gw.win32 import Win32  # noqa: E402


def main() -> int:
    from py4gw import client as client_module
    from py4gw.agent import Agent
    from py4gw.party import Party
    from py4gw.player import Player

    from tests.probe_party_live import _LiveClient

    win32 = Win32()
    clients = win32.find_guild_wars()
    if not clients:
        print("no Guild Wars client is running")
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
            world = stand_in.read_world_context()
            models = list(world.npc_models or []) if world is not None else []
            mine = Player.GetAgentID()
            my_x, my_y = Agent.GetXY(mine)
            found: list[tuple[float, int, int]] = []
            for agent_id in stand_in.agent_array.read_context().GetAgentArray():
                if not Agent.IsLiving(agent_id):
                    continue
                record = Agent.GetAgentByID(agent_id)
                living = record.GetAsAgentLiving() if record is not None else None
                if living is None:
                    continue
                model_id = int(living.player_number)
                if model_id < 0 or model_id >= len(models):
                    continue
                model = models[model_id]
                if not bool(model.is_henchman):
                    continue
                x, y = Agent.GetXY(agent_id)
                found.append((math.hypot(float(x) - float(my_x), float(y) - float(my_y)),
                              int(agent_id), model_id))
            found.sort()
            print(f"party now: size={Party.GetPartySize()} players={Party.GetPlayerCount()} "
                  f"heroes={Party.GetHeroCount()} henchmen={Party.GetHenchmanCount()}")
            print(f"player agent id {mine} at ({my_x:.1f}, {my_y:.1f}); "
                  f"{len(found)} henchman candidate(s) in this map, nearest first:")
            for distance, agent_id, model_id in found[:12]:
                print(f"  agent_id={agent_id:<8} npc_model={model_id:<6} distance={distance:.1f}")
        finally:
            client_module._current_client = previous  # type: ignore[attr-defined]
    finally:
        reader.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
