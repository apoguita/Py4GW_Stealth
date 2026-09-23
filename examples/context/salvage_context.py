"""SalvageSessionInfo — the salvage session.

Three ways to read a context:

    print(context)        # the whole structure at a glance, values decoded
    context.<field>       # one field, exactly as the source layout declares it
    context.to_dict()     # every field as plain Python data, for code

This script prints ``frame id``, ``item id``, ``kit id``, ``chosen``.

``salvagable_1``/``2``/``3`` are the prefix, suffix, and inscription the game
offers, and ``chosen_salvagable`` is the option in effect (the source comments
``3`` as materials).

This context is published only through the UI frame that owns it, so ``get()``
returns ``None`` while that surface is closed. The field reads below are
guarded for that case.

See README.md in this folder for the other contexts, the ``None`` cases, and
the full list of access styles.
"""

import py4gw

client = py4gw.connect(py4gw.win32.list_processes()[0])
context = py4gw.context.salvagecontext.get()

# the whole structure at a glance
print(context)
print()

# individual fields, read directly
if context is not None:
    print("frame id:", context.frame_id)
    print("item id:", context.item_id)
    print("kit id:", context.kit_id)
    print("chosen:", context.chosen_salvagable)

    print("as dict:", context.to_dict())

py4gw.disconnect()
