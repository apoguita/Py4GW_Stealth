"""Read-only: the party, and whether the party window (hash 3332025202) is on screen right now."""

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
    from py4gw.frame_tree.frame_names import NAME_TO_HASH
    from py4gw.map import Map
    from py4gw.party import Party

    from tests.probe_party_live import _LiveClient, _party_window_on_screen

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
            print(f"pid {pid}")
            print(f"party: size={_answer(Party.GetPartySize)} players={_answer(Party.GetPlayerCount)} "
                  f"heroes={_answer(Party.GetHeroCount)} henchmen={_answer(Party.GetHenchmanCount)}")
            print(f"outpost={_answer(Map.IsOutpost)} loaded={_answer(Party.IsPartyLoaded)} "
                  f"map={_answer(Map.GetMapID)}")
            print(f"party window on screen: {_answer(_party_window_on_screen)} "
                  f"(hash {NAME_TO_HASH.get('Party')})")
            wanted = {3332025202: "Party", 3199024334: "PartySearch", 177400827: "PartyContextMenu"}
            seen = []
            for candidate, record in stand_in.frame_array.iter_frames():
                if record is None:
                    continue
                value = int(getattr(record, "frame_hash", 0) or 0)
                if value in wanted:
                    seen.append((candidate, wanted[value], value))
            print(f"party-ish frames in the array: {seen if seen else 'none'}")
        finally:
            client_module._current_client = previous  # type: ignore[attr-defined]
    finally:
        reader.close()
    return 0


def _answer(call) -> object:
    try:
        return call()
    except Exception as error:  # noqa: BLE001 - reported
        return f"{type(error).__name__}: {error}"


if __name__ == "__main__":
    raise SystemExit(main())
