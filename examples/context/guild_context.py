"""GuildContext — the guild, its members, and its history.

Three ways to read a context:

    print(context)        # the whole structure at a glance, values decoded
    context.<field>       # one field, exactly as the source layout declares it
    context.to_dict()     # every field as plain Python data, for code

This script prints ``guilds``, ``guild count``, ``first guild``.

``guilds`` is materialised through the reader into a Python list of guild
records, so it is iterable and indexable directly. It is ``None`` when the
character is in no guild, so this script falls back to an empty list.

See README.md in this folder for the other contexts, the ``None`` cases, and
the full list of access styles.
"""

import py4gw

client = py4gw.connect(py4gw.win32.list_processes()[0])
context = py4gw.context.guildcontext.get()

if context is None:
    raise SystemExit("no Guild Wars client is connected")

# the whole structure at a glance
print(context)
print()

# individual fields, read directly
guilds = context.guilds or []
print("guilds:", guilds)
print("guild count:", len(guilds))
print("first guild:", guilds[0] if guilds else None)

# every field as plain data, decoded, for use in code
print("as dict:", context.to_dict())

py4gw.disconnect()
