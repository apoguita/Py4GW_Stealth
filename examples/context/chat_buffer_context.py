"""ChatBuffer — the encoded chat message ring.

Three ways to read a context:

    print(context)        # the whole structure at a glance, values decoded
    context.<field>       # one field, exactly as the source layout declares it
    context.to_dict()     # every field as plain Python data, for code

This script prints ``next index``, ``ring slots``, ``latest message``.

``message_records`` is materialised from the encoded ring. Messages are stored
encoded, so text fields hold encoded data rather than plain text; decoding uses
the client's own string decoder.

See README.md in this folder for the other contexts, the ``None`` cases, and
the full list of access styles.
"""

import py4gw

client = py4gw.connect(py4gw.win32.list_processes()[0])
context = py4gw.context.chatbuffer.get()

if context is None:
    raise SystemExit("no Guild Wars client is connected")

# the whole structure at a glance
print(context)
print()

# named values, read directly
print("next index:", context.next_index)
print("ring slots:", len(context.message_records))
print("latest message:", context.message_records[0])

# every field as plain data, decoded, for use in code
print("as dict:", context.to_dict())

py4gw.disconnect()
