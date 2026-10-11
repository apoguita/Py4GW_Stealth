"""Read-only probe: where does the client actually lay a skillbar's slots out?

The live suite's skillbar comparison failed with the layer's `SkillID` column shifted one slot early
against `py4gw.skillbar`'s read of the same bar, and the two structures' offsets agree on paper -- so the
question is a fact about the client's layout that reading either source cannot answer. This prints it:

* the **flat dword dump** of a matched skillbar from ``+0x04`` (where the port declares `skills`) through
  the end of the eight slot records, so the ids and the stride are visible as they are;
* the same dump from ``+0x00``, so a leading word before the slot array would show too;
* what the layer answers per slot (`Skill_GetSkillbarInfo`);
* what the port's own read answers per slot (`py4gw.skillbar.SkillBar.GetSkillbar`);
* each slot record's own fields through the port's structure, to see which word holds the id.

Reads only. Run elevated, with Guild Wars in a loaded map and skills on the bar.
"""

from __future__ import annotations

import struct

import py4gw
from py4gw import Win32
from py4gw.gwa3 import data_skill
from py4gw.player import Player
from py4gw.skillbar import SkillBar

SLOT_STRIDE = 0x14
SLOT_COUNT = 8


def _dwords(reader: object, address: int, offset: int, count: int) -> list[int]:
    raw = reader.read(address + offset, count * 4)  # type: ignore[attr-defined]
    return list(struct.unpack(f"<{count}I", raw))


def main() -> int:
    win32 = Win32()
    clients = win32.find_guild_wars()
    if not clients:
        print("no client")
        return 1
    if not win32.is_elevated():
        print("not elevated")
        return 1

    py4gw.connect(clients[0], game_thread=False)
    print(f"connected read-only to pid {clients[0]['pid']}")
    player_id = int(Player.GetAgentID())
    print(f"player agent id {player_id}")

    client = py4gw.require_client() if hasattr(py4gw, "require_client") else None
    if client is None:
        from py4gw.client import require_client

        client = require_client()

    world = client.read_world_context()
    bars = world.skillbars or []
    print(f"skillbars the port reads: {len(bars)}")

    matched = None
    matched_index = -1
    for index, bar in enumerate(bars):
        if int(bar.agent_id) == player_id:
            matched = bar
            matched_index = index
            break
    if matched is None:
        print("no skillbar matched the player's agent id; here is what the array holds:")
        for bar in bars:
            print(f"  agent_id {bar.agent_id}")
        py4gw.disconnect()
        return 1

    # `SkillbarStruct` binds a reader but no address (unlike the party and agent records), so the bar's
    # address is computed the way the world's own array read walks it: the array's buffer plus the
    # element stride, which is the structure's own size.
    import ctypes

    stride = ctypes.sizeof(type(matched))
    address = int(world.party_skillbar_array.m_buffer) + matched_index * stride
    reader = matched._remote_reader
    print(f"matched skillbar index {matched_index} at {address:#x} (stride {stride:#x})")

    print("\n--- flat dwords from +0x00 (index: offset value) ---")
    dump = _dwords(reader, address, 0x00, (0xC0 // 4))
    for index, value in enumerate(dump):
        print(f"  {index:2d} +0x{index * 4:03X} {value:>12} {value:#010x}")

    print("\n--- the port's slot records, as the port declares them ---")
    for slot in range(1, SLOT_COUNT + 1):
        record = matched.skills[slot - 1]
        print(
            f"  slot {slot}: adrenaline_a={record.adrenaline_a} adrenaline_b={record.adrenaline_b} "
            f"recharge={record.recharge} skill_id={record.skill_id} event={record.event}"
        )

    print("\n--- candidate bases: which 0x14 stride shows the port's ids at skill_id +0xC? ---")
    port_ids = [int(skill_id) for skill_id in SkillBar.GetSkillbar()]
    print(f"  port ids: {port_ids}")
    for base in (0x00, 0x04, 0x08, 0x0C, 0x10, 0x14, 0x18):
        ids = [_dwords(reader, address, base + index * SLOT_STRIDE + 0x0C, 1)[0] for index in range(SLOT_COUNT)]
        firsts = [_dwords(reader, address, base + index * SLOT_STRIDE, 1)[0] for index in range(SLOT_COUNT)]
        print(f"  base +0x{base:02X}: id-word {ids}")
        print(f"           first-word {firsts}")

    print("\n--- the layer's answers ---")
    for slot in range(1, SLOT_COUNT + 1):
        print(
            f"  slot {slot}: SkillID={data_skill.Skill_GetSkillbarInfo(slot, 'SkillID')} "
            f"HasSkill={data_skill.Skill_GetSkillbarInfo(slot, 'HasSkill')} "
            f"Adrenaline={data_skill.Skill_GetSkillbarInfo(slot, 'Adrenaline')} "
            f"Event={data_skill.Skill_GetSkillbarInfo(slot, 'Event')}"
        )

    print(f"\n  layer AgentID={data_skill.Skill_GetSkillbarInfo(1, 'AgentID')} (player {player_id})")
    print(f"  layer timer={data_skill.Skill_GetSkillTimer()}")

    py4gw.disconnect()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
