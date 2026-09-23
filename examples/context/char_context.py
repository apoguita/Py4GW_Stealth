"""CharContext — the character and map state of the logged-in character.

Three ways to read a context:

    print(context)        # the whole structure at a glance, values decoded
    context.<field>       # one field, exactly as the source layout declares it
    context.to_dict()     # every field as plain Python data, for code

This script prints ``map id``, ``current map id``, ``district``, ``player number``, ``language``, ``character name``, ``logged in``.

``player_name_str`` and ``is_logged_in`` are convenience properties. The raw
``player_name_enc`` field holds the same name as an encoded wide buffer, which
``to_dict()`` decodes for you.

See README.md in this folder for the other contexts, the ``None`` cases, and
the full list of access styles.
"""

import py4gw

client = py4gw.connect(py4gw.win32.list_processes()[0])
context = py4gw.context.charcontext.get()

if context is None:
    raise SystemExit("no Guild Wars client is connected")

# the whole structure at a glance
print(context)
print()

# individual fields, read directly
print("map id:", context.map_id)
print("current map id:", context.current_map_id)
print("district:", context.district_number)
print("player number:", context.player_number)
print("language:", context.language)
print("character name:", context.player_name_str)
print("logged in:", context.is_logged_in)

# every field as plain data, decoded, for use in code
print("as dict:", context.to_dict())

py4gw.disconnect()
