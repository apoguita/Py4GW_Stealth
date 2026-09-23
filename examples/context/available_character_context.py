"""AvailableCharacterArray — the account's character roster.

Three ways to read a context:

    print(context)        # the whole structure at a glance, values decoded
    context.<field>       # one field, exactly as the source layout declares it
    context.to_dict()     # every field as plain Python data, for code

This script prints ``characters``, ``all names``, ``first name``.

The root structure is only the array header, so the useful data comes from the
``characters`` property, which the reader materialises into a list of records.
Each record carries an encoded name that decodes to readable text.

See README.md in this folder for the other contexts, the ``None`` cases, and
the full list of access styles.
"""

import py4gw

client = py4gw.connect(py4gw.win32.list_processes()[0])
context = py4gw.context.availablecharacters.get()

if context is None:
    raise SystemExit("no Guild Wars client is connected")

# the whole structure at a glance
print(context)
print()

# named values, read directly
print("characters:", len(context.characters))
print("all names:", [entry.player_name_str for entry in context.characters])
print("first name:", context.characters[0].player_name_str)

# every field as plain data, decoded, for use in code
print("as dict:", context.to_dict())

py4gw.disconnect()
