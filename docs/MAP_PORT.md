# Map port

Plan and progress record for porting Reforged's `Py4GWCoreLib/Map.py` (2327 lines,
178 members) into `py4gw/map.py`.

The rules this follows are in [`PORTING_RULES.md`](PORTING_RULES.md): port everything,
and name what each member still needs as the next work item. No redesign, no additions,
no substitutes.

> **Plan vs source.** The structure diagram and the stage tables below are the
> *plan*. As each stage lands, the tables are updated with what was actually
> verified. Nothing here is a claim until it says `verified`.

## Source structure

Nested exactly as `Map.py` declares it. Line numbers are the source's.

```text
Map                                            74 members   lines 38-889
|
+-- readiness gate                              8   42,53,65,72,80,88,99,109
+-- identity                                    1   120
+-- name tables                                 7   128,134,142,165,188,211,231
+-- region, language, instance sizes           10   253,261,274,289,296,320,
|                                                   331,341,351,360
+-- foes, vanquish, campaign, flags            13   369,381,393,401,411,426,440,
|                                                   449,458,467,476,485,493
+-- AreaInfo field block                       22   520..688
+-- unloaded map, challenge, bounds             4   696,706,714,734
+-- actions (all to port)                       9   743,757,765,829,845,853,
|                                                   860,867,878
|
+-- class MissionMap                           16   lines 891-1404
|   +-- window + geometry                     11   898..1088
|   +-- input / ImGui (to port)                5   930,938,946,954,982
|   +-- class MapProjection                   15   lines 1097-1403
|
+-- class MiniMap                              15   lines 1406-1851
|   +-- window + geometry                     10   1412..1556
|   +-- input / ImGui (to port)                5   1432,1440,1448,1455,1480
|   +-- class MapProjection                   16   lines 1575-1850
|
+-- class WorldMap                             12   lines 1853-2023
|   +-- context + geometry                     7   1859,1866,1873,1951,1962,
|   |                                               1969,1976
|   +-- input / ImGui (to port)                5   1880,1888,1896,1903,1927
|
+-- class Pregame                               9   lines 2025-2097
|   +-- context + window                       7   2034..2074
|   +-- client calls (to port)                 2   2081,2088
|
+-- class Pathing                              16   lines 2099-2327
    +-- live pathing + quads                  13   2102..2303
    +-- overlay / navmesh (to port)            2   2138,2170
    +-- source cache (to determine)            1   2122
    +-- class Quad                             5   lines 2177-2222
```

## Where each member reads from

Four sources only. Nothing else is introduced.

| Source | What it covers | Stealth status |
| --- | --- | --- |
| **Contexts** | `InstanceInfo` (38 uses), `World`, `Char`, `WorldMap`, `PreGame`, `MissionMap`, `Map`, `AccAgent`, `Cinematic`, `Gameplay`, `AvailableCharacterArray`, `ServerRegion` | all already loaded — `ConnectedClient.read_*` |
| **UI frame tree** | `Frame.from_id`, `.exists`, `.coords()`, `.content_coords()`, `.viewport_scale()` — geometry only | `FramePositionStruct` already parses the record; field correspondence to be established in Stage 5 |
| **Local tables** | `enums_src/Map_enums.py`, `enums_src/Region_enums.py` | not ported yet (Stage 2) |
| **Native map methods** | `MapMethods.GetMapInfo` (a scanned `AreaInfo` array); the rest are actions | `GetMapInfo`'s scan is portable (Stage 4); actions still to port |

## Stage pipeline

```text
 Stage 1   shape .......... nest the namespaces, declare all 178, offline guard
    |
 Stage 2   tables ......... 9 members + name halves of 3 declared members
    |
 Stage 3   Map contexts ... 10 members
    |
 Stage 4   AreaInfo array .. 1 member  (any map id, loaded or not)
    |
 Stage 5   frame geometry .. 34 port + 2 verify + 17 to port
    |
 Stage 6   projections ..... 31 members
    |
 Stage 7   pathing ......... 18 port + 1 verify + 2 to port
    |
 Stage 8   record .......... this document, plus TARGET_SIDE_WORK entries
```

Stages 1–4 need no capability Stealth does not already have.

## Current state

| | Source | `py4gw/map.py` today |
| --- | ---: | ---: |
| Members | 178 | **178 declared** (44 working, 134 not yet ported) |
| Undeclared | — | **0** |
| Namespaces | nested under `Map` | nested identically: `Map.MissionMap.MapProjection`, `Map.MiniMap.MapProjection`, `Map.Pathing.Quad` |
| Member order | source order | preserved |

### Stand-in helpers: closed

`Map` had six private helpers the source does not declare. All are gone, and the
gap that caused them is closed.

**Root cause.** `Py4GWCoreLib/Context.py` declares the `GWContext` namespace and
`InstanceInfo.GetMapInfo()` — the accessor every `Map` member calls. It was not
ported, so the accessor was substituted locally, then collapsed into a `getattr`
dispatcher, then given an invented gate:

```text
unported Context.py  ->  substituted accessor  ->  getattr dispatcher  ->  invented gate
```

**Fixed.** `py4gw/context/gw_context.py` now ports that file: `_GWContextBase`
(`GetPtr` / `GetContext` / `IsValid`), the `GWContext` namespace with all fifteen
nested context classes, and `InstanceInfo.GetMapInfo()`. `Map` calls it exactly as
the source does, and no longer declares a single member the source lacks.

Also removed, all of them mine and none of them in the source:

| Removed | Where |
| --- | --- |
| `_area_value` (`getattr` dispatcher) | deleted |
| `_area`, `_char_context`, `_instance_info_context`, `_map_context`, `_world_context` | deleted |
| the `IsMapReady()` gate inside `_area` | removed — the source does not gate that path |
| `try`/`except` around the context reads | removed from `GetMapID` and `IsInCinematic` |
| eight `int()` casts | removed |
| `GetMapID`'s missing `IsMapReady()` gate | restored (`Map.py:122`) |
| wrong unset-path values (`0` instead of `255`/`255`/`20`) | corrected |

**One line in `gw_context.py` is not literal**, and it is the only one: the source
fills each facade cache from an in-process `PyCallback.Context.Draw` callback, so
`GetContext` calls the source's own `_update_ptr` before reading the cache. Without
it the cache is never filled and `GetContext` would answer `None` forever — which is
not what the source does. This is the same reasoning already recorded for dropping
`@frame_cache`: no in-process tick, so the refresh happens on demand.

The `_unported` builder is **not** a defect: it is the mechanism this project's
contract provides for a member that is not yet ported.

## Stage 1 — shape and guard  *(done)*

Restructured `py4gw/map.py` into one `Map` class with the nested classes above, in
source order, and declared all 178 members. The 44 working members carry over
unchanged; the other 134 are declared and not yet ported, each naming the mechanism
it needs next.

`tests/test_map_offline.py` was added: it parses `Map.py` and compares the surface
class by class, so a member cannot be dropped or invented, and it checks that every
member which is not implemented raises structurally rather than returning a value.

| Check | Command | Result |
| --- | --- | --- |
| surface parity | `python -m unittest tests.test_map_offline` | **7 tests OK** |
| members present | AST cross-check, source order preserved | **178/178, order exact** |
| no extras | only `_unported` and the nested helpers the source itself declares (`_point_in_quad`, and the ones inside `Travel`) | **pass** |
| working members, live | `python -m unittest tests.test_map` | **12 tests OK** — all 44 checked against the structs they read |
| types | `pyright` | **0 errors** |
| offline suite | `python -m unittest discover -s tests -p "*_offline.py"` | **323 tests OK** |
| live suites | `test_map_context`, `test_player`, `test_party`, `test_world_context`, `test_instance_info_context` | **88 tests OK** |
| examples | `examples/*.py` sweep | **29/29 ok** |

Live evidence, map 642 (Outpost): the gate members, `GetMapID`, `IsInCinematic`,
the 17 `AreaInfo` scalars, the 7 flag members, the 5 icon vectors and both
`file_id` halves all agreed with the contexts they claim to read — 44 of 44, no
disagreements.

`tests/test_map.py` is the live half and is deliberately written against the
structs rather than against fixed values, so it holds in any map. It also pins
the one known divergence: `GetCampaign`, `GetContinent` and `GetRegionType` return
their id with an **empty name** until Stage 2 ports the name tables.

## Stage 2 — local tables

Ported from `enums_src/Map_enums.py` and `enums_src/Region_enums.py`.

| Table | Entries |
| --- | ---: |
| `outposts` | 278 |
| `explorables` | 378 |
| `outpost_name_to_id`, `explorable_name_to_id`, `name_to_map_id` | derived |
| `map_variants_to_base` | 15 |
| `base_to_all_variants` | 9 keys |
| `InstanceTypeName` | 3 |
| `ServerRegion` / `ServerRegionName` | 7 |
| `Language` / `ServerLanguage` / `ServerLanguageName` | 12 |
| `District` / `DistrictName` | 14 |
| `Campaign` / `CampaignName` | 7 |
| `RegionType` / `RegionTypeName` | 22 |
| `Continent` / `ContinentName` | 7 |

Members landed: `GetOutpostIDs` (128), `GetOutpostNames` (134), `GetMapName` (142),
`GetMapIDByName` (165), `GetBaseMapID` (188), `GetAllMapVariants` (211),
`IsMapIDMatch` (231), `GetRegion` (261), `GetLanguage` (296) — and the name half of
the already-declared `GetInstanceTypeName` (65), `GetRegionType` (274),
`GetCampaign` (411), `GetContinent` (426).

**Verify:** offline only — table sizes and `name -> id -> name` round-trips — plus
one live check that `GetMapName(GetMapID())` resolves to a real name.

## Stage 3 — `Map` context reads

**Prerequisite: port `Py4GWCoreLib/Context.py`.** Every member in this stage calls
`GWContext.X.GetContext()` or `GWContext.InstanceInfo.GetMapInfo()`, and neither has
a ported home. Porting that file comes first, then the members are written against
the source's own accessors and the six substituted helpers are deleted. See the
defect section above.

`GetInstanceUptime` (253), `GetDistrict` (289), `GetAmountOfPlayersInInstance` (320),
`GetFoesKilled` (369), `GetFoesToKill` (381), `IsVanquishCompleted` (393),
`IsVanquishComplete` (485), `IsMapUnlocked` (493), `GetMapWorldMapBounds` (714),
`GetMapBoundaries` (734), plus `GetMapID`'s source gate at (120).

**Verify:** live, each member checked against the struct it claims to read.

## Stage 4 — the `AreaInfo` array

`GetUnloadedMapInfo` (696). Native `MapMethods.GetMapInfo` scans `6B C6 7C 5E 05`,
reads the immediate as the array base, and indexes `base + map_id * 0x7C`. This
gives metadata for **any** map id, loaded or not.

**Verify:** live — `GetUnloadedMapInfo(GetMapID())` must agree with the loaded
map's own `AreaInfo`.

## Stage 5 — frame geometry and the window namespaces

**First: establish the field mapping** between Reforged's `Frame.position`
(`left_on_screen`, `top_on_screen`, `right_on_screen`, `bottom_on_screen`,
`width_on_screen`, `height_on_screen`, `viewport_scale_x`, `viewport_scale_y`,
`content_left/top/right/bottom`) and Stealth's `FramePositionStruct`. Report it
before building on it.

| Namespace | Port | To determine | To port |
| --- | ---: | ---: | ---: |
| `Map` (`IsEnteringChallenge` 706) | 1 | | |
| `MissionMap` | 11 | | 5 |
| `MiniMap` | 8 | 2 | 5 |
| `WorldMap` | 7 | | 5 |
| `Pregame` | 7 | | 2 |

- **Port:** `MissionMap` 898, 916, 923, 1011, 1018, 1025, 1032, 1039, 1057, 1069,
  1088 · `MiniMap` 1412, 1417, 1425, 1505, 1517, 1522, 1549, 1556 · `WorldMap`
  1859, 1866, 1873, 1951, 1962, 1969, 1976 · `Pregame` 2034, 2041, 2048, 2055,
  2062, 2067, 2074.
- **To determine at the stage:** `MiniMap.IsLocked` (1512),
  `MiniMap.GetRotation` (1539).
- **To port** (each needs the mechanism named for it in *Members still to port*
  below): `OpenWindow` / `CloseWindow` on all three window namespaces, every
  `IsMouseOver`, every `GetLastClickCoords` and `GetLastRightClickCoords`,
  `Pregame.InCharacterSelectScreen` (2081),
  `Pregame.LogoutToCharacterSelect` (2088).

**Verify:** live with each window open **and** closed.

**Landed early, because `Utils` reached it:** `Map.MissionMap.GetZoom` (1032) —
`GWContext.Gameplay.GetContext().mission_map_zoom`, with the source's `1.0` when the context is
unavailable. `Utils.GwinchToPixels` and `Utils.PixelsToGwinch` read it alongside
`Map.MissionMap.GetScale` (`py4gwcorelib_src/Utils.py:156,168`), so the zoom half is ported and the
scale half is what those two members still wait on ([`UTILS_PORT.md`](UTILS_PORT.md)). The port's
implemented count for `Map` moved from 44 to 45 with it.

## Stage 6 — projections

`Map.MissionMap.MapProjection` (15, lines 1097-1403) and
`Map.MiniMap.MapProjection` (16, lines 1575-1850), in source order, as arithmetic
over the bounds and geometry the earlier stages expose.

**Verify:** offline with fixed inputs, plus a live round-trip.

## Stage 7 — pathing

- **Port:** `GetPathingMaps` (2102, live branch), `GetPathingMapsRaw` (2114),
  `GetAvailableMapIds` (2146, a table), `GetSpawns` (2152, live branch),
  `GetTravelPortals` (2161, live branch), `GetComputedGeometry` (2224),
  `GetScreenComputedGeometry` (2233), `GetShiftedComputedGeometry` (2242),
  `GetshiftedScreenComputedGeometry` (2252), `_point_in_quad` (2262),
  `GetMapQuads` (2277), `IsPointInPathing` (2290),
  `IsScreenPointInPathing` (2303), and `Quad` (2178, 2196, 2199, 2202, 2210).
- **To port:** `WorldToScreen` (2170, overlay kernel), `ForceReloadNavMesh` (2138,
  navmesh builder), and the offline branch of `GetPathingMaps` / `GetSpawns` /
  `GetTravelPortals` (`PyDatReader.read_file_by_id` + the FFNA format).
- **To determine at the stage:** `ClearPathingCache` (2122) — it manages the
  source project's own caches, which are not ported here. Report what it does and
  what it needs rather than guessing.

## Stage 8 — the record

Fold the verified results back into this document and add the capability entries
to [`TARGET_SIDE_WORK.md`](TARGET_SIDE_WORK.md).

## Members still to port

In-process mechanisms, not reading problems. Recorded here and in
[`TARGET_SIDE_WORK.md`](TARGET_SIDE_WORK.md).

| Mechanism | Members |
| --- | --- |
| **ImGui input state** — `PyImGui.get_io()`, and `frame_io_events` which only exists because a `PyCallback` handler fills it | every `IsMouseOver`, every `GetLastClickCoords` / `GetLastRightClickCoords` (9 members) |
| **UI message dispatch** — `SendUIMessage*`, `set_window_visible`, `Frame.click()` | `OpenWindow` / `CloseWindow` on `MissionMap`, `MiniMap`, `WorldMap` (6); `Map.CancelEnterChallenge`, `ConfirmEnterChallenge` (2) |
| **Keybind / coroutine execution** — `GLOBAL_CACHE.Coroutines`, `PyGameThread.enqueue` | covered by the actions block (9 in `Map`, plus `Pregame.LogoutToCharacterSelect`) |
| **Native call inside the client** — `NativeFunction`, `PySystem` calls | `Map.SkipCinematic`, `Pregame.InCharacterSelectScreen` |
| **Overlay / navmesh** — `PyOverlay`, `AutoPathing` | `Pathing.WorldToScreen`, `ForceReloadNavMesh` |
| **DAT / FFNA archive** — `PyDatReader.read_file_by_id` | offline branch of `GetPathingMaps`, `GetSpawns`, `GetTravelPortals` |

## Progress

- [x] **Stage 1** — shape and guard *(178/178 declared, order exact; 7 offline + 12 live tests; pyright clean; 29/29 examples)*
- [ ] **Stage 2** — local tables
- [ ] **Stage 3** — `Map` context reads
- [ ] **Stage 4** — the `AreaInfo` array
- [ ] **Stage 5** — frame geometry and the window namespaces
- [ ] **Stage 6** — projections
- [ ] **Stage 7** — pathing
- [ ] **Stage 8** — the record
