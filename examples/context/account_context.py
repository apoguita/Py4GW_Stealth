"""AccountContext — account unlocks and stored items.

Three ways to read a context:

    print(context)        # the whole structure at a glance, values decoded
    context.<field>       # one field, exactly as the source layout declares it
    context.to_dict()     # every field as plain Python data, for code

This script prints ``account flags``, ``unlock counts``, ``material storage stack``.

``account_unlocked_count_list`` is materialised from the unlock array, so it
reads as a list of records rather than as an array header.

See README.md in this folder for the other contexts, the ``None`` cases, and
the full list of access styles.
"""

import py4gw

client = py4gw.connect(py4gw.win32.list_processes()[0])
context = py4gw.context.accountcontext.get()

if context is None:
    raise SystemExit("no Guild Wars client is connected")

# the whole structure at a glance
print(context)
print()

# named values, read directly
print("account flags:", context.account_flags)
print("unlock counts:", context.account_unlocked_count_list)
print("material storage stack:", context.material_storage_stack_size)

# every field as plain data, decoded, for use in code
print("as dict:", context.to_dict())

py4gw.disconnect()
