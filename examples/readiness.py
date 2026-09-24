"""Read Reforged's map-readiness gate.

This is Reforged's ``Map`` gate, ported member for member from
``Py4GWCoreLib/Map.py`` lines 40-118. Nothing here is invented: the structure,
the short-circuits, and the return values are the source's.

The gate exists because a map-scoped context is **absent** while the client
changes maps, not merely stale. A read taken in that window belongs to no map.
So every map-scoped reader on ``ConnectedClient`` refuses while
``Map.IsMapReady()`` is false and answers ``None``.

Three of these members are easy to misread, because two of them deliberately
report ``True`` when the data is *not* loaded:

``IsObservingMatch()``
    ``True`` when the character spectates another map -- and also ``True`` when
    the map data is not loaded, per the source's first short-circuit.

``IsMapLoading()``
    ``True`` when the map data is not loaded, and otherwise ``True`` unless the
    instance type is ``Outpost`` or ``Explorable``. The client has exactly those
    two real phases.

``IsMapReady()``
    The three above combined. It is the one to call before reading map data.

Usage:
    python examples/readiness.py            # one verdict
    python examples/readiness.py --watch    # report every change, Ctrl+C to stop
"""

import sys
import time

import py4gw
from py4gw import Map

WATCH = "--watch" in sys.argv

client = py4gw.connect(py4gw.win32.list_processes()[0])
print(f"pid {client.pid}\n")


def show() -> None:
    """Print every gate member, in the order Reforged declares them."""

    print(f"IsMapDataLoaded    {Map.IsMapDataLoaded()}")
    print(f"GetInstanceType    {Map.GetInstanceType()}")
    print(f"GetInstanceTypeName {Map.GetInstanceTypeName()}")
    print(f"IsOutpost          {Map.IsOutpost()}")
    print(f"IsExplorable       {Map.IsExplorable()}")
    print(f"IsMapLoading       {Map.IsMapLoading()}")
    print(f"IsObservingMatch   {Map.IsObservingMatch()}")
    print(f"IsMapReady         {Map.IsMapReady()}   <- gate before reading map data")
    print()
    print(f"map id             {Map.GetMapID()}")
    print(f"in cinematic       {Map.IsInCinematic()}")


def show_gated_read() -> None:
    """Read map-scoped data only when the gate is open."""

    show()
    print()

    if not Map.IsMapReady():
        print("refusing to read map data: the map is not ready")
        return

    area = client.read_instance_info()
    if area is None:
        print("instance info is unavailable")
        return

    print(f"instance_type      {int(area.instance_type)}")
    print(f"terrain_info1_ptr  0x{int(area.terrain_info1_ptr):08X}")
    print(f"current_map_info   0x{int(area.current_map_info_ptr):08X}")

    map_info = area.current_map_info
    if map_info is None:
        print("current map metadata is not available")
        return

    print(
        f"area               campaign={int(map_info.campaign)} "
        f"continent={int(map_info.continent)} region={int(map_info.region)}"
    )
    print(f"area party size    {int(map_info.min_party_size)}-{int(map_info.max_party_size)}")
    print(f"area level range   {int(map_info.min_level)}-{int(map_info.max_level)}")
    print(f"area name id       {int(map_info.name_id)}")


if not WATCH:
    show_gated_read()
    py4gw.disconnect()
    raise SystemExit(0)

print("Watching. Change maps in game and watch the gate. Ctrl+C to stop.\n")
previous: tuple[bool, bool, int] | None = None

try:
    while True:
        state = (Map.IsMapReady(), Map.IsMapLoading(), Map.GetInstanceType())
        if state != previous:
            stamp = time.strftime("%H:%M:%S")
            print(f"[{stamp}] ready={state[0]} loading={state[1]} "
                  f"type={Map.GetInstanceTypeName()} map={Map.GetMapID()}")
            previous = state
        time.sleep(0.25)
except KeyboardInterrupt:
    print("\nInterrupted.")
finally:
    py4gw.disconnect()
