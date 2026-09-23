"""GameContext — the root game context and its child pointers.

Three ways to read a context:

    print(context)        # the whole structure at a glance, values decoded
    context.<field>       # one field, exactly as the source layout declares it
    context.to_dict()     # every field as plain Python data, for code

This script prints ``agent context ptr``, ``world context ptr``, ``char context ptr``, ``party context ptr``, ``cinematic ptr``.

Every field here is a target address for a child context, not the context
itself. Read a child through its own module, for example
``py4gw.context.worldcontext.get()``.

See README.md in this folder for the other contexts, the ``None`` cases, and
the full list of access styles.
"""

import py4gw

client = py4gw.connect(py4gw.win32.list_processes()[0])
context = py4gw.context.gamecontext.get()

if context is None:
    raise SystemExit("no Guild Wars client is connected")

# the whole structure at a glance
print(context)
print()

# individual fields, read directly
print("agent context ptr:", context.agent_context)
print("world context ptr:", context.world_context)
print("char context ptr:", context.char_context)
print("party context ptr:", context.party_context)
print("cinematic ptr:", context.cinematic)

# every field as plain data, decoded, for use in code
print("as dict:", context.to_dict())

py4gw.disconnect()
