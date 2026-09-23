"""GadgetContext — gadgets such as chests and signposts.

Three ways to read a context:

    print(context)        # the whole structure at a glance, values decoded
    context.<field>       # one field, exactly as the source layout declares it
    context.to_dict()     # every field as plain Python data, for code

This script prints ``gadget array address``, ``gadget slots``, ``array buffer``.

The maintained layout exposes only the gadget array header here, so this script
reports the array rather than individual gadgets. The bounded reader on
``ConnectedClient`` walks the entries.

See README.md in this folder for the other contexts, the ``None`` cases, and
the full list of access styles.
"""

import py4gw

client = py4gw.connect(py4gw.win32.list_processes()[0])
context = py4gw.context.gadgetcontext.get()

if context is None:
    raise SystemExit("no Guild Wars client is connected")

# the whole structure at a glance
print(context)
print()

# named values, read directly
print("gadget array address:", context.address)
print("gadget slots:", context.array_size)
print("array buffer:", context.gadget_info_array.m_buffer)

# every field as plain data, decoded, for use in code
print("as dict:", context.to_dict())

py4gw.disconnect()
