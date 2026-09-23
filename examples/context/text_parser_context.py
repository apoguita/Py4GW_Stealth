"""TextParser — the text parser and its language/file slots.

Three ways to read a context:

    print(context)        # the whole structure at a glance, values decoded
    context.<field>       # one field, exactly as the source layout declares it
    context.to_dict()     # every field as plain Python data, for code

This script prints ``language id``, ``entries per file``, ``decode start ptr``.

``language_slots`` is a fixed array of 11 language/file slot records.

See README.md in this folder for the other contexts, the ``None`` cases, and
the full list of access styles.
"""

import py4gw

client = py4gw.connect(py4gw.win32.list_processes()[0])
context = py4gw.context.textparser.get()

if context is None:
    raise SystemExit("no Guild Wars client is connected")

# the whole structure at a glance
print(context)
print()

# individual fields, read directly
print("language id:", context.language_id)
print("entries per file:", context.entries_per_file)
print("decode start ptr:", context.dec_start_ptr)

# every field as plain data, decoded, for use in code
print("as dict:", context.to_dict())

py4gw.disconnect()
