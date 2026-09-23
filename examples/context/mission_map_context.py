"""MissionMapContext — the mission map.

Three ways to read a context:

    print(context)        # the whole structure at a glance, values decoded
    context.<field>       # one field, exactly as the source layout declares it
    context.to_dict()     # every field as plain Python data, for code

This script prints ``frame id``, ``size x``, ``player pos x``, ``last mouse y``.

``player_mission_map_pos`` tracks the player marker, and ``last_mouse_location``
the pointer over the map.

This context is published only through the UI frame that owns it, so ``get()``
returns ``None`` while that surface is closed. The field reads below are
guarded for that case.

See README.md in this folder for the other contexts, the ``None`` cases, and
the full list of access styles.
"""

import py4gw

client = py4gw.connect(py4gw.win32.list_processes()[0])
context = py4gw.context.missionmapcontext.get()

# the whole structure at a glance
print(context)
print()

# individual fields, read directly
if context is not None:
    print("frame id:", context.frame_id)
    print("size x:", context.size.x)
    print("player pos x:", context.player_mission_map_pos.x)
    print("last mouse y:", context.last_mouse_location.y)

    print("as dict:", context.to_dict())

py4gw.disconnect()
