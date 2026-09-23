"""MapContext — the current map, its pathing grids, and props.

Three ways to read a context:

    print(context)        # the whole structure at a glance, values decoded
    context.<field>       # one field, exactly as the source layout declares it
    context.to_dict()     # every field as plain Python data, for code

This script prints ``map type``, ``map id``, ``start x``, ``map boundaries``, ``spawns``.

``start_pos`` is a nested record, so its parts read through the attribute.
``map_boundaries`` is a reader-backed property that resolves the pointer field.

See README.md in this folder for the other contexts, the ``None`` cases, and
the full list of access styles.
"""

import py4gw

client = py4gw.connect(py4gw.win32.list_processes()[0])
context = py4gw.context.mapcontext.get()

if context is None:
    raise SystemExit("no Guild Wars client is connected")

# the whole structure at a glance
print(context)
print()

# named values, read directly
print("map type:", context.map_type)
print("map id:", context.map_id)
print("start x:", context.start_pos.x)
print("map boundaries:", context.map_boundaries)
print("spawns:", context.spawns1_array.m_size)

# every field as plain data, decoded, for use in code
print("as dict:", context.to_dict())

py4gw.disconnect()
