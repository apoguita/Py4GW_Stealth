"""Cinematic — cinematic playback state.

Three ways to read a context:

    print(context)        # the whole structure at a glance, values decoded
    context.<field>       # one field, exactly as the source layout declares it
    context.to_dict()     # every field as plain Python data, for code

This script prints ``field 0``, ``field 1``.

The maintained layout declares only two unnamed dwords here, so the glance is
the most useful view and there are no named fields to read singly. Fields named ``hXXXX`` are unknown or padding bytes. They are kept so the layout stays a faithful port of the source declaration; ignore them.

See README.md in this folder for the other contexts, the ``None`` cases, and
the full list of access styles.
"""

import py4gw

client = py4gw.connect(py4gw.win32.list_processes()[0])
context = py4gw.context.cinematic.get()

if context is None:
    raise SystemExit("no Guild Wars client is connected")

# the whole structure at a glance
print(context)
print()

# individual fields, read directly
print("field 0:", context.h0000)
print("field 1:", context.h0004)

# every field as plain data, decoded, for use in code
print("as dict:", context.to_dict())

py4gw.disconnect()
