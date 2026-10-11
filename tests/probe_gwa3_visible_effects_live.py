"""Read-only, elevated: what the visible-effect list actually holds, and what its fields mean.

`UAI_AgentHasVisibleEffect` matches a node whose **first dword is the effect type** (GwAu3 calls it
``EffectType``) and whose **second is the effect id** (``EffectID``) -- the port reads the same two
dwords under the names ``unk`` and ``id``, and this probe is what says the mapping is the source's:

* every conditioned agent should carry a **type-1** node (``$GC_I_EFFECT_TYPE_STATUS``) whose id is one
  of the condition ids GwAu3 filters on (bleeding 23, blinded 24, burning 25, diseased 26,
  poisoned 27, dazed 28, weakness 29);
* an agent the client says is bleeding should carry id 23, and so on for the conditions the port can
  read independently from the agent record's own effect bits.

Nothing is written: ``game_thread=False``, no hook, no patch, no call into the client.
"""

from __future__ import annotations

import sys

import py4gw
from py4gw.gwa3 import constants, data_agent, uai_effects
from py4gw.win32 import Win32


def main() -> int:
    win32 = Win32()
    clients = win32.find_guild_wars()
    if not clients:
        print("no Guild Wars client")
        return 1
    if not win32.is_elevated():
        print("this probe must run elevated: connecting asserts it")
        return 2

    py4gw.connect(clients[0], game_thread=False)
    print(f"--- connected read-only to pid {int(clients[0]['pid'])} ---")

    from py4gw.agent_array import AgentArray

    agents = list(AgentArray.GetAgentArray())
    print(f"agents: {len(agents)}")

    conditioned_seen = 0
    status_rows = 0
    for agent_id in agents:
        agent_id = int(agent_id)
        if agent_id == 0:
            continue
        living = data_agent.Agent_GetAgentPtr(agent_id)
        if living is None or not getattr(living, "is_living_type", False):
            continue
        try:
            rows = uai_effects.UAI_GetAgentVisibleEffectInfo(agent_id)
        except Exception as error:  # noqa: BLE001 - the failure is the measurement
            print(f"  agent {agent_id}: walk failed: {type(error).__name__}: {error}")
            continue
        count = int(rows[0][0]) if rows else 0
        if count == 0:
            continue

        status = [row for row in rows[1:] if int(row[0]) == constants.GC_I_EFFECT_TYPE_STATUS]
        status_rows += len(status)
        # The agent record's own effect word: the port's live read, independent of the TList walk.
        effect_word = int(living.effects)
        bits = {
            "IsBleeding": bool(effect_word & 0x0001),
            "IsConditioned": bool(effect_word & 0x0002),
        }
        role = "player" if agent_id == int(py4gw.player.Player.GetAgentID()) else "agent"
        print(
            f"  {role} {agent_id}: {count} visible effect(s) {rows[1:]} "
            f"(type-1 nodes: {len(status)}; effect bits {bits})"
        )
        if bits["IsConditioned"] or bits["IsBleeding"]:
            conditioned_seen += 1

    print(f"--- conditioned agents with visible effects: {conditioned_seen}; type-1 nodes: {status_rows} ---")
    print("--- condition ids: bleeding=23 blinded=24 burning=25 diseased=26 poisoned=27 dazed=28 weakness=29 ---")
    py4gw.disconnect()
    return 0


if __name__ == "__main__":
    sys.exit(main())
