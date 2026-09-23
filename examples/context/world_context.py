"""WorldContext — parties, players, agents, quests, skillbar, titles.

Three ways to read a context:

    print(context)        # the whole structure at a glance, values decoded
    context.<field>       # one field, exactly as the source layout declares it
    context.to_dict()     # every field as plain Python data, for code

This script prints ``player team token``, ``player character ptr``, ``map agents``, ``salvage session id``.

Most of the 107 fields are array headers, so the useful reads are the named
scalars plus the reader-backed properties such as ``map_agents``, which
materialises the agent records. It is ``None`` when there is no map, so this
script falls back to an empty list.

See README.md in this folder for the other contexts, the ``None`` cases, and
the full list of access styles.
"""

import py4gw

client = py4gw.connect(py4gw.win32.list_processes()[0])
context = py4gw.context.worldcontext.get()

if context is None:
    raise SystemExit("no Guild Wars client is connected")

# the whole structure at a glance
print(context)
print()

# named values, read directly
print("player team token:", context.player_team_token)
print("player character ptr:", context.player_controlled_character_ptr)
print("map agents:", len(context.map_agents or []))
print("salvage session id:", context.salvage_session_id)

# every field as plain data, decoded, for use in code
print("as dict:", context.to_dict())

py4gw.disconnect()
