"""Connect to one client and print every in-game context we can read.

Usage:
    python examples/all_contexts.py            # summary plus sample fields
    python examples/all_contexts.py --full     # every field of every context
"""

import sys

import py4gw
from py4gw.helpers.target_struct import format_value

FULL = "--full" in sys.argv

client = py4gw.connect(py4gw.win32.list_processes()[0])
print(f"pid {client.pid}\n")

readers = {
    "charcontext": py4gw.context.charcontext.get,
    "gamecontext": py4gw.context.gamecontext.get,
    "worldcontext": py4gw.context.worldcontext.get,
    "mapcontext": client.read_map_context,
    "missionmap": client.read_mission_map_context,
    "worldmap": client.read_world_map_context,
    "salvage": client.read_salvage_session,
    "gameplaycontext": py4gw.context.gameplaycontext.get,
    "pregamecontext": py4gw.context.pregamecontext.get,
    "instanceinfo": py4gw.context.instanceinfo.get,
    "serverregion": py4gw.context.serverregion.get,
    "textparser": py4gw.context.textparser.get,
    "cinematic": py4gw.context.cinematic.get,
    "camera": py4gw.context.camera.get,
    "partycontext": py4gw.context.partycontext.get,
    "guildcontext": py4gw.context.guildcontext.get,
    "friendlist": py4gw.context.friendlist.get,
    "chatbuffer": py4gw.context.chatbuffer.get,
    "tradecontext": py4gw.context.tradecontext.get,
    "itemcontext": py4gw.context.itemcontext.get,
    "accountcontext": py4gw.context.accountcontext.get,
    "gadgetcontext": py4gw.context.gadgetcontext.get,
    "accagentcontext": py4gw.context.accagentcontext.get,
    "availablecharacters": py4gw.context.availablecharacters.get,
    "agentarray": client.read_agent_array,
}

for name, reader in readers.items():
    try:
        context = reader()
    except Exception as error:
        print(f"{name:<20} ERROR  {type(error).__name__}: {error}")
        continue

    if context is None:
        print(f"{name:<20} none")
        continue

    fields = context.to_dict()
    print(f"{name:<20} {type(context).__name__:<28} {len(fields):>3} fields")
    if FULL:
        print(context)
    else:
        for field, value in list(fields.items())[:4]:
            print(f"    {field} = {format_value(value)}")

py4gw.disconnect()
