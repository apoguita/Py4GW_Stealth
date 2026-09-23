"""FriendList — friends and ignored players.

Three ways to read a context:

    print(context)        # the whole structure at a glance, values decoded
    context.<field>       # one field, exactly as the source layout declares it
    context.to_dict()     # every field as plain Python data, for code

This script prints ``friends``, ``ignored``, ``status``, ``first friend``.

``friend_records`` is materialised from the friend array, so entries are real
records with names rather than array slots.

See README.md in this folder for the other contexts, the ``None`` cases, and
the full list of access styles.
"""

import py4gw

client = py4gw.connect(py4gw.win32.list_processes()[0])
context = py4gw.context.friendlist.get()

if context is None:
    raise SystemExit("no Guild Wars client is connected")

# the whole structure at a glance
print(context)
print()

# named values, read directly
print("friends:", context.number_of_friends)
print("ignored:", context.number_of_ignores)
print("status:", context.status)
print("first friend:", context.friend_records[0])

# every field as plain data, decoded, for use in code
print("as dict:", context.to_dict())

py4gw.disconnect()
