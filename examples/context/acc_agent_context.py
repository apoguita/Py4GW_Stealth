"""AccAgentContext — the agent context root and its movement arrays.

Three ways to read a context:

    print(context)        # the whole structure at a glance, values decoded
    context.<field>       # one field, exactly as the source layout declares it
    context.to_dict()     # every field as plain Python data, for code

This script prints ``agents with movement``, ``first agent ids``, ``instance timer``.

``valid_agents_ids`` lists the array indexes whose movement pointer is
currently non-null, which is the practical way to enumerate live agents here.

See README.md in this folder for the other contexts, the ``None`` cases, and
the full list of access styles.
"""

import py4gw

client = py4gw.connect(py4gw.win32.list_processes()[0])
context = py4gw.context.accagentcontext.get()

if context is None:
    raise SystemExit("no Guild Wars client is connected")

# the whole structure at a glance
print(context)
print()

# named values, read directly
print("agents with movement:", len(context.valid_agents_ids))
print("first agent ids:", context.valid_agents_ids[:10])
print("instance timer:", context.instance_timer)

# every field as plain data, decoded, for use in code
print("as dict:", context.to_dict())

py4gw.disconnect()
