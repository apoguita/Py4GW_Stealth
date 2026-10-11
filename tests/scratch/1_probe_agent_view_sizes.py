"""Read-only probe: how big is each agent record view, and can GwAu3's offsets be read from it?

The live suite found the second living-record defect (2026-10-10): the reader table is a `Switch` over
*living* fields, `Agent_GetAgentPtr` answers each agent's own view, and a gadget view raised
``AttributeError: 'AgentGadgetStruct' object has no attribute 'allegiance'``. The fix is "answer the
bytes GwAu3 reads" -- but whether those bytes are *reachable* depends on how much of the client's
element each view materializes, and that is a fact about this port's context layer, not a guess. So it
is measured here before anything is written.

For each agent in the client's array it prints:

* the record's own type and the length of its buffer;
* whether GwAu3's ``Allegiance`` offset (0x1B5) and ``HP`` offset (0x134) are inside that buffer;
* whether the record carries a bound remote reader, and what a read of the same offsets through it
  answers -- which is the same ``Memory_Read(ptr + offset, type)`` GwAu3 makes.

Reads only. Run elevated, with Guild Wars in a loaded map.
"""

from __future__ import annotations

import struct

import py4gw
from py4gw import Win32
from py4gw.agent_array import AgentArray
from py4gw.gwa3 import data_agent
from py4gw.player import Player

ALLEGIANCE = data_agent._RAW_READERS["Allegiance"]
HP = data_agent._RAW_READERS["HP"]
LEVEL = data_agent._RAW_READERS["Level"]


def _buffer_size(record: object) -> int:
    try:
        return len(bytes(record))  # type: ignore[arg-type]
    except Exception as error:  # pragma: no cover - diagnostic only
        return -int(getattr(error, "errno", 0) or 0) - 1


def _read_or_reason(record: object, offset: int, fmt: str) -> str:
    try:
        return repr(struct.unpack_from(fmt, record, offset)[0])  # type: ignore[arg-type]
    except Exception as error:
        return f"<{type(error).__name__}: {error}>"


def _remote_read(record: object, offset: int, fmt: str) -> str:
    reader = getattr(record, "_remote_reader", None)
    address = getattr(record, "_remote_address", None)
    if reader is None or not address:
        return "<no bound reader>"
    try:
        size = struct.calcsize(fmt)
        return repr(struct.unpack(fmt, reader.read(int(address) + offset, size))[0])
    except Exception as error:
        return f"<{type(error).__name__}: {error}>"


def main() -> int:
    win32 = Win32()
    clients = win32.find_guild_wars()
    if not clients:
        print("no client")
        return 1
    if not win32.is_elevated():
        print("not elevated")
        return 1

    client = py4gw.connect(clients[0], game_thread=False)
    print(f"connected read-only to pid {clients[0]['pid']}")
    player_id = int(Player.GetAgentID())
    print(f"player agent id {player_id}")

    seen: dict[str, int] = {}
    for agent_id in AgentArray.GetAgentArray():
        agent_id = int(agent_id)
        base = AgentArray.GetAgentByID(agent_id)
        views = {"base": base}
        for name, getter in (
            ("gadget", "GetAsAgentGadget"),
            ("item", "GetAsAgentItem"),
            ("living", "GetAsAgentLiving"),
        ):
            try:
                views[name] = getattr(base, getter)() if base is not None else None
            except Exception as error:
                views[name] = f"<{type(error).__name__}>"

        for name, record in views.items():
            if record is None or isinstance(record, str):
                continue
            kind = f"{name}:{type(record).__name__}"
            if seen.get(kind, 0) >= 2 and agent_id != player_id:
                continue
            seen[kind] = seen.get(kind, 0) + 1
            size = _buffer_size(record)
            print(
                f"agent {agent_id} {kind} buffer={size} "
                f"allegiance@0x{ALLEGIANCE[0]:X} in-buffer={size >= ALLEGIANCE[0] + 1} "
                f"raw={_read_or_reason(record, *ALLEGIANCE)} "
                f"remote={_remote_read(record, *ALLEGIANCE)} "
                f"| hp raw={_read_or_reason(record, *HP)} remote={_remote_read(record, *HP)}"
                f" | level raw={_read_or_reason(record, *LEVEL)}"
            )

    # GwAu3's own answers for the same agents, through the layer, to see which raise.
    for agent_id in [int(a) for a in AgentArray.GetAgentArray()][:40]:
        for key in ("Allegiance", "HP", "IsDead", "Level"):
            try:
                value = data_agent.Agent_GetAgentInfo(agent_id, key)
                outcome = repr(value)
            except Exception as error:
                outcome = f"<{type(error).__name__}: {error}>"
            print(f"layer {agent_id} {key} -> {outcome}")

    py4gw.disconnect()
    print("views seen:", seen)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
