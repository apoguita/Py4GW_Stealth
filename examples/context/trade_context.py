"""TradeContext — the open trade and both sides' offers.

Three ways to read a context:

    print(context)        # the whole structure at a glance, values decoded
    context.<field>       # one field, exactly as the source layout declares it
    context.to_dict()     # every field as plain Python data, for code

This script prints ``trade flags``, ``your gold``, ``their gold``.

``player`` and ``partner`` are nested records, so their parts read through the
attribute: ``context.player.gold``, ``context.player.items.m_size``.

See README.md in this folder for the other contexts, the ``None`` cases, and
the full list of access styles.
"""

import py4gw

client = py4gw.connect(py4gw.win32.list_processes()[0])
context = py4gw.context.tradecontext.get()

if context is None:
    raise SystemExit("no Guild Wars client is connected")

# the whole structure at a glance
print(context)
print()

# individual fields, read directly
print("trade flags:", context.flags)
print("your gold:", context.player.gold)
print("their gold:", context.partner.gold)

# every field as plain data, decoded, for use in code
print("as dict:", context.to_dict())

py4gw.disconnect()
