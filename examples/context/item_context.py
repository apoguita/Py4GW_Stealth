"""ItemContext — bags, items, formulas, and storage state.

Three ways to read a context:

    print(context)        # the whole structure at a glance, values decoded
    context.<field>       # one field, exactly as the source layout declares it
    context.to_dict()     # every field as plain Python data, for code

This script prints ``inventory ptr``, ``bags``, ``item records``, ``first item id``.

The root structure is a set of array headers, so the item readers on
``ConnectedClient`` do the traversal: ``read_item_bags`` and
``read_item_records`` follow the bag-owned arrays.

See README.md in this folder for the other contexts, the ``None`` cases, and
the full list of access styles.
"""

import py4gw

client = py4gw.connect(py4gw.win32.list_processes()[0])
context = py4gw.context.itemcontext.get()

if context is None:
    raise SystemExit("no Guild Wars client is connected")

# the whole structure at a glance
print(context)
print()

# named values, read directly
print("inventory ptr:", context.inventory_ptr)
print("bags:", len(client.read_item_bags()))
print("item records:", len(client.read_item_records()))
print("first item id:", client.read_item_records()[0].item_id)

# every field as plain data, decoded, for use in code
print("as dict:", context.to_dict())

py4gw.disconnect()
