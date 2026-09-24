"""InstanceInfo — the current instance, map dimensions, and area info.

Three ways to read a context:

    print(context)        # the whole structure at a glance, values decoded
    context.<field>       # one field, exactly as the source layout declares it
    context.to_dict()     # every field as plain Python data, for code

This script prints ``instance type``, ``map info``, ``terrain entries``.

The pointer fields are followed by reader-backed properties, so
``current_map_info``, ``terrain_info1``, and ``terrain_info2`` read as records
rather than as addresses.

The instance info lives behind a module-global pointer that the client nulls
while a map loads.  The library caches the *address of* that pointer and
re-dereferences it on every read, so ``None`` here means "the map is not ready
yet" rather than "something is wrong".  ``client.instance_info.slot_address`` is
the cached half and ``client.instance_info.pointer()`` is the fresh half.  See
``../../docs/READINESS_GATE.md``.

See README.md in this folder for the other contexts, the ``None`` cases, and
the full list of access styles.
"""

import py4gw

client = py4gw.connect(py4gw.win32.list_processes()[0])
context = py4gw.context.instanceinfo.get()

if context is None:
    # A null instance pointer is a normal state, not a failure to resolve: the
    # client is between maps. The readiness gate names the same condition the
    # native runtime reports as InstanceType.Loading.
    print(
        "instance info is not available yet: "
        f"{py4gw.Map.GetInstanceTypeName()}, map ready={py4gw.Map.IsMapReady()}"
    )
else:
    # the whole structure at a glance
    print(context)
    print()

    # named values, read directly
    print("instance type:", context.instance_type)
    print("map info:", context.current_map_info)
    print("terrain entries:", context.terrain_count)

    # every field as plain data, decoded, for use in code
    print("as dict:", context.to_dict())

py4gw.disconnect()
