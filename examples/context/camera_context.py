"""Camera — camera position, zoom, yaw, and pitch.

Three ways to read a context:

    print(context)        # the whole structure at a glance, values decoded
    context.<field>       # one field, exactly as the source layout declares it
    context.to_dict()     # every field as plain Python data, for code

This script prints ``looking at agent``, ``distance``, ``max distance``, ``yaw``, ``pitch``.

Angle fields are radians and distance fields are world units. ``look_at_agent_id``
names the agent the camera is following, and is 0 when it follows nothing.

See README.md in this folder for the other contexts, the ``None`` cases, and
the full list of access styles.
"""

import py4gw

client = py4gw.connect(py4gw.win32.list_processes()[0])
context = py4gw.context.cameracontext.get()

if context is None:
    raise SystemExit("no Guild Wars client is connected")

# the whole structure at a glance
print(context)
print()

# individual fields, read directly
print("looking at agent:", context.look_at_agent_id)
print("distance:", context.distance)
print("max distance:", context.max_distance)
print("yaw:", context.yaw)
print("pitch:", context.pitch)

# every field as plain data, decoded, for use in code
print("as dict:", context.to_dict())

py4gw.disconnect()
