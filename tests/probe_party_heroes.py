"""Read-only: the party's heroes as the members see them, and the name -> id lookup."""

from __future__ import annotations

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
    from py4gw.party import Party

    from tests.probe_party_live import _LiveClient

    win32 = Win32()
    process = win32.find_guild_wars()[0]
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
            heroes = Party.GetHeroes()
            print(f"size={Party.GetPartySize()} players={Party.GetPlayerCount()} "
                  f"heroes={Party.GetHeroCount()} henchmen={Party.GetHenchmanCount()}")
            print("party hero records:")
            for member in heroes:
                print(f"  agent_id={int(member.agent_id)} hero_id={int(member.hero_id)} "
                      f"owner={int(member.owner_player_id)} level={int(member.level)}")
            for position in range(0, 3):
                print(f"  GetHeroIDByPartyPosition({position}) = "
                      f"{Party.Heroes.GetHeroIDByPartyPosition(position)}")
            for name in ("Norgu", "Goren", "Tahlkora", "Koss", "Dunkoro", "Acolyte Jin"):
                print(f"  GetHeroIdByName({name!r}) = {Party.Heroes.GetHeroIdByName(name)}")
            print("hero-flag records (hero_id, agent_id, behaviour):")
            for flag in stand_in.read_world_context().hero_flags or []:
                print(f"  hero_id={int(flag.hero_id)} agent_id={int(flag.agent_id)} "
                      f"behaviour={int(flag.hero_behavior)}")
            print("hero-info records (hero_id, agent_id):")
            world = stand_in.read_world_context()
            for info in world.hero_info or []:
                print(f"  hero_id={int(info.hero_id)} agent_id={int(info.agent_id)} "
                      f"name_str={info.name_str!r}")
        finally:
            client_module._current_client = previous  # type: ignore[attr-defined]
    finally:
        reader.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
