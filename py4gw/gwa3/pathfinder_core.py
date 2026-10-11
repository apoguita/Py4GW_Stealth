"""``Pathfinder_Core.au3``'s two state readers, over this project's own pathing data.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

**What the source file is.** ``API/Plugins/Pathfinder/Pathfinder_Core.au3`` is GwAu3's path-finding
plugin, and it is a **DLL plugin**: ``Pathfinder_Initialize`` (`:24-82`) checks for a ``maps.rar`` /
``maps`` directory beside ``$DLL_PATH`` (``:27-30``), downloads one from
``GwAu3-Projects/GwPathfinder-Maps`` when the GitHub release tag differs from ``maps.version``
(``:33``, ``:147-197``, ``:86-143``), ``DllOpen``s ``GWPathfinder.dll`` (``:65-72``) and returns **the
DLL's own** ``Initialize()`` result (``:74-81``) -- ``1`` = OK, ``2`` = up but no maps, ``0`` = error
(``:20-23``). Everything the plugin then does is a ``DllCall`` into that DLL: ``Pathfinder_IsMapAvailable``
(`:325-330`) asks it whether it holds a map, ``Pathfinder_FindPath``/``Pathfinder_FindPathRaw``
(`:216-323`) run its A* and marshal its ``tagPathResult``/``tagPathPoint`` records into ``(x, y, layer,
tp_type)`` rows.

**What this project has instead, and it is a different engine with the same facts.** The port's pathing
data is the client's own: every map's geometry is read out of the client's ``gw.dat`` -- the map table is
`Map.Pathing.GetAvailableMapIds` (`py4gw/map.py:2350`), the key set of the file ids
``FfnaMapMethods`` reads each map's pathing by (`py4gw/native_src/methods/ffna_map_methods.py:177`),
and the read itself is `Map.Pathing.GetPathingMaps` (`py4gw/map.py:2293`) /
`Map.Pathing.GetPathingMapsRaw` (`:2309`). Nothing is downloaded, no library is loaded, and this
project's path search is its own port of Reforged's navmesh and A* (`AutoPathing.get_path`,
``py4gw/pathing.py:975``). The two members here are the *state* pair a caller gates on -- "is the
pathfinder up", "does it hold this map" -- and each is answered from that table.

**What is deliberately not carried yet**: ``Pathfinder_FindPath``, ``Pathfinder_FindPathRaw``,
``Pathfinder_GetAvailableMaps``, ``Pathfinder_DownloadMaps``, ``Pathfinder_FreePathResult`` and
``Pathfinder_Shutdown``. They are the DLL's own search and lifetime, and the port's equivalent search is
``AutoPathing.get_path`` (`py4gw/pathing.py:975`) over the live navmesh -- a route this file has not been
asked to draw, and one the source's parameters (``$aObstacles``, ``$simplifyRange``,
``$clearanceWeight``) would each have to be matched against. They remain the named work items in
``docs/GWA3_ROUTE_MAP.md``.
"""

from __future__ import annotations

from typing import Any


def _available_map_ids() -> set[int]:
    """The map ids this project's own pathing table names (`py4gw/map.py:2350`).

    ``Map.Pathing.GetAvailableMapIds`` is the port's own member for it -- "the set of map IDs that
    offline pathing can be loaded for" -- and it goes to the same table
    `FfnaMapMethods.GetAvailableMapIds` answers (`py4gw/native_src/methods/ffna_map_methods.py:177`).
    """

    from ..map import Map

    return set(Map.Pathing.GetAvailableMapIds())


def Pathfinder_Initialize() -> int:
    """Whether the pathfinder has map data (``Pathfinder_Core.au3:24-82``).

    **GwAu3's contract is kept**: ``1`` when the maps are there, ``2`` when the pathfinder is up but has
    no maps source, ``0`` on an error (``:20-23``, the DLL's own three answers, which ``:81`` returns
    unchanged).

    **This project's equivalent state, and it is a state, not a download.** No library is opened and no
    archive is fetched; the maps are the client's own, addressed by the table the port carries:
    `Map.Pathing.GetAvailableMapIds` (`py4gw/map.py:2350`). So:

    * ``1`` -- the table names maps, so pathing data is available for them. This is the ordinary answer;
    * ``2`` -- the table is empty, which leaves the **live** map's own pathing records, the ones
      `Map.Pathing.GetPathingMaps` reads with no id (`py4gw/map.py:2293`) through the client's own map
      context. That is exactly GwAu3's second answer: the pathfinder works, its offline map source does
      not.

    **``0`` is unreachable here, and that is the honest answer rather than a missing one**: it is
    ``DllOpen``/``DllCall`` failing (`:67-69`, `:75-77`), and this project opens no DLL to fail. A caller
    that branches on ``0`` is branching on a state this engine cannot be in.

    **The divergence, in one sentence:** GwAu3 checks for a ``maps.rar``/``maps`` archive it downloaded
    beside ``GWPathfinder.dll`` (``:27-30``), where this answers whether the port's own table of
    ``gw.dat`` pathing file ids is populated.
    """

    return 1 if _available_map_ids() else 2


def Pathfinder_IsMapAvailable(a_mapID: Any) -> bool:
    """Whether the pathfinder holds a map (``Pathfinder_Core.au3:325-330``).

    **GwAu3's guard and its answer.** ``If $g_hPathfinderDLL = 0 Or $g_hPathfinderDLL = -1 Then Return
    False`` (`:326`), then ``DllCall($g_hPathfinderDLL, "int:cdecl", "IsMapAvailable", "int", $mapID)``
    with ``@error`` answering ``False`` (`:327-328`), and ``Return $result[0] = 1`` (`:329`). What the DLL
    answers with is its own loaded map set -- a **table lookup**, not a read of geometry.

    **This asks the same question of this project's table**: `Map.Pathing.GetAvailableMapIds`
    (`py4gw/map.py:2350`) -- the maps whose pathing this project can load, which is the set GwAu3's DLL
    holds for its own maps archive. The stronger reading it stands for is the data itself,
    `Map.Pathing.GetPathingMaps($mapID)` (`py4gw/map.py:2293`), which answers that map's trapezoids and
    needs the connection, because the port's ``gw.dat`` reads go through the client's own archive
    functions (`py4gw/native_src/textures/dat_reader.py:97-105`).

    A map id the table does not name answers ``False`` -- GwAu3's own answer for a map its DLL does not
    hold, and the same ``False`` its zero-handle guard gives (`:326`).
    """

    return int(a_mapID) in _available_map_ids()


__all__ = ["Pathfinder_Initialize", "Pathfinder_IsMapAvailable"]
