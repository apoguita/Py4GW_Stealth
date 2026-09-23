"""AgentArray — the bounded agent snapshot.

Three ways to read a context:

    print(context)        # the whole structure at a glance, values decoded
    context.<field>       # one field, exactly as the source layout declares it
    context.to_dict()     # every field as plain Python data, for code

This script prints ``reported size``, ``non-null slots``, ``first agent id``.

``references`` is a bounded snapshot, so the glance shows only the first few
entries. The counters underneath say what was scanned and how many slots were
empty, stale, or unreadable, so a partial read is never mistaken for a full one.

See README.md in this folder for the other contexts, the ``None`` cases, and
the full list of access styles.
"""

import py4gw

client = py4gw.connect(py4gw.win32.list_processes()[0])
context = py4gw.context.agent_array.get()

if context is None:
    raise SystemExit("no Guild Wars client is connected")

# the whole structure at a glance
print(context)
print()

# individual fields, read directly
print("reported size:", context.reported_size)
print("non-null slots:", context.non_null_slots)
print("first agent id:", context.references[0].agent_id)

# every field as plain data, decoded, for use in code
print("as dict:", context.to_dict())

py4gw.disconnect()
