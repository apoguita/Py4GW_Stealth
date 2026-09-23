"""WorldMapContext — the world map.

Three ways to read a context:

    print(context)        # the whole structure at a glance, values decoded
    context.<field>       # one field, exactly as the source layout declares it
    context.to_dict()     # every field as plain Python data, for code

This script prints ``frame id``, ``zoom``, ``top left x``, ``bottom right y``.

``frame_id`` is the index of the UI frame that publishes this context, and the
reader cross-checks it before handing the address over.

This context is published only through the UI frame that owns it, so ``get()``
returns ``None`` while that surface is closed. The field reads below are
guarded for that case.

See README.md in this folder for the other contexts, the ``None`` cases, and
the full list of access styles.
"""

import py4gw

client = py4gw.connect(py4gw.win32.list_processes()[0])
context = py4gw.context.worldmapcontext.get()

# the whole structure at a glance
print(context)
print()

# individual fields, read directly
if context is not None:
    print("frame id:", context.frame_id)
    print("zoom:", context.zoom)
    print("top left x:", context.top_left.x)
    print("bottom right y:", context.bottom_right.y)

    print("as dict:", context.to_dict())

py4gw.disconnect()
