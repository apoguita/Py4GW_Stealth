"""Read-only, elevated: the three model-state sets GwAu3's two files disagree about, measured.

`UAI_DecodeAgentInto` (the plugin's cache) and `GwAu3_Data_Agent.au3` (the Data module) define
``IsAttacking``/``IsIdle``/``IsMoving`` from the agent's model state, and they disagree:

| predicate | ``GwAu3_Data_Agent.au3`` | ``UAI_DecodeAgentInto`` |
| --- | --- | --- |
| ``IsAttacking`` | ``0x60``, ``0x440``, ``0x460`` | those **plus ``0x40``** |
| ``IsIdle`` | ``0x44``, ``0x40``, ``0x64`` | ``0x44``, ``0x64`` (**no ``0x40``**) |
| ``IsMoving`` | velocity, or ``0xC``, ``0x4C``, ``0xCC`` | velocity, or ``0x4C``, ``0xCC`` (**no ``0xC``**) |

This project's own ported `AgentLivingStruct.is_attacking`/`is_idle`/`is_moving` -- read from Reforged
Native -- use exactly the Data module's three sets, so the authority this port follows agrees with one
of the two. What this probe adds is the **live distribution**: which model states the client actually
puts agents in, and how often the two definitions would answer differently.

Nothing is written: ``game_thread=False``, no hook, no patch, no call into the client.
"""

from __future__ import annotations

import collections
import sys

import py4gw
from py4gw.agent_array import AgentArray
from py4gw.gwa3 import data_agent
from py4gw.win32 import Win32

#: The two definitions, as the two GwAu3 files write them.
DATA_FILE_STATES = {"IsAttacking": (0x60, 0x440, 0x460), "IsIdle": (0x40, 0x44, 0x64)}
DECODER_STATES = {"IsAttacking": (0x40, 0x60, 0x440, 0x460), "IsIdle": (0x44, 0x64)}


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

    states: collections.Counter[int] = collections.Counter()
    disagreements = collections.Counter()
    agents_seen = 0
    for agent_id in list(AgentArray.GetAgentArray()):
        agent_id = int(agent_id)
        if agent_id == 0:
            continue
        record = data_agent.Agent_GetAgentPtr(agent_id)
        if record is None or not getattr(record, "is_living_type", False):
            continue
        agents_seen += 1
        state = int(record.model_state)
        states[state] += 1

        for key, data_states in DATA_FILE_STATES.items():
            from_definition = state in data_states
            from_decoder = state in DECODER_STATES[key]
            if from_definition != from_decoder:
                disagreements[f"{key}: 0x{state:X}"] += 1

        # The layer's own answer, and the two GwAu3 answers, side by side.
        ours = {
            "IsAttacking": data_agent.Agent_GetAgentInfo(agent_id, "IsAttacking"),
            "IsIdle": data_agent.Agent_GetAgentInfo(agent_id, "IsIdle"),
            "IsMoving": data_agent.Agent_GetAgentInfo(agent_id, "IsMoving"),
        }
        native = {
            "IsAttacking": bool(record.is_attacking),
            "IsIdle": bool(record.is_idle),
            "IsMoving": bool(record.is_moving),
        }
        if ours != native:
            disagreements[f"layer vs native: {ours} != {native}"] += 1

    print(f"living agents: {agents_seen}")
    print("model states seen:")
    for state, count in sorted(states.items()):
        flags = []
        for key, values in DATA_FILE_STATES.items():
            if state in values:
                flags.append(f"data-file says {key}")
        for key, values in DECODER_STATES.items():
            if state in values:
                flags.append(f"decoder says {key}")
        print(f"  0x{state:03X} ({state:4}) x{count:3}  {'; '.join(flags)}")
    print("disagreements between the two GwAu3 definitions, and layer-vs-Native:")
    for key, count in disagreements.most_common():
        print(f"  {count:3}  {key}")
    if not disagreements:
        print("  none: no agent held a disputed model state during this sample")

    py4gw.disconnect()
    return 0


if __name__ == "__main__":
    sys.exit(main())
