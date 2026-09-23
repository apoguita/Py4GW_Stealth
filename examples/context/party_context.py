"""PartyContext — the player's party, heroes, henchmen, and flags.

Three ways to read a context:

    print(context)        # the whole structure at a glance, values decoded
    context.<field>       # one field, exactly as the source layout declares it
    context.to_dict()     # every field as plain Python data, for code

This script prints ``party leader``, ``hard mode``, ``defeated``, ``parties``, ``has player party``.

The named booleans answer most party questions without touching the array
headers. ``parties`` is materialised into a list of records.

See README.md in this folder for the other contexts, the ``None`` cases, and
the full list of access styles.
"""

import py4gw

client = py4gw.connect(py4gw.win32.list_processes()[0])
context = py4gw.context.partycontext.get()

if context is None:
    raise SystemExit("no Guild Wars client is connected")

# the whole structure at a glance
print(context)
print()

# named values, read directly
print("party leader:", context.is_party_leader)
print("hard mode:", context.in_hard_mode)
print("defeated:", context.is_defeated)
print("parties:", len(context.parties))
print("has player party:", context.player_party is not None)

# every field as plain data, decoded, for use in code
print("as dict:", context.to_dict())

py4gw.disconnect()
