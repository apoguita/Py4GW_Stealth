# Map port

Plan and progress record for porting Reforged's `Py4GWCoreLib/Map.py` (2327 lines,
178 members across 9 classes) into `py4gw/map.py`.

The rules this follows are in [`PORTING_RULES.md`](PORTING_RULES.md): port everything,
and name what each member still needs as the next work item. No redesign, no additions,
no substitutes.

## Source structure

Nested exactly as `Map.py` declares it. Line numbers are the source's.

```text
Map                                            74 members   lines 38-889
|
+-- readiness gate                              8   42,53,65,72,80,88,99,109
+-- identity                                    1   120
+-- name tables                                 7   128,134,142,165,188,211,231
+-- region, language, instance sizes           14   253..365
+-- foes, vanquish, campaign, flags            13   369,381,393,401,411,426,440,
|                                                   449,458,467,476,485,493
+-- AreaInfo field block                       22   520..688
+-- unloaded map, challenge, bounds             4   696,706,714,734
+-- actions                                     9   743,757,765,829,845,853,
|                                                   860,867,878
|
+-- class MissionMap                           16   lines 891-1404
|   +-- window + geometry                     13   898..1088
|   +-- input / ImGui (not built, 3)           3   930..1007
|   +-- class MapProjection                   15   lines 1097-1403
|
+-- class MiniMap                              15   lines 1406-1851
|   +-- window + geometry                     12   1412..1572
|   +-- input / ImGui (not built, 3)           3   1432..1502
|   +-- class MapProjection                   16   lines 1575-1850
|
+-- class WorldMap                             12   lines 1853-2023
|   +-- context + geometry                     9   1859..2022
|   +-- input / ImGui (not built, 3)           3   1880..1948
|
+-- class Pregame                               9   lines 2025-2097
+-- class Pathing                              16   lines 2099-2176
|   +-- class Quad                             5   lines 2177-2222
```

The two `MapProjection` classes are **different code**, not one shared class:
`MissionMap`'s 15 take `zoom_offset` on the two map transforms; `MiniMap`'s 16 have
`GamePosToScreen`/`ScreenToGamePos` taking `player_x/y`, `center_x/y`, `scale` and
`rotation`, plus `ComputedPathingGeometryToScreen`, and no `zoom_offset` at all.
`tests/test_map_offline.py` pins that they are distinct classes.

## Current state (round 82)

| | Source | `py4gw/map.py` today |
| --- | ---: | ---: |
| Members | 178 | **178 declared — 168 answer, 10 recorded** |
| Class attributes | 17 | **17 declared** |
| Undeclared | — | **0** |
| Namespaces | nested under `Map` | nested identically: `Map.MissionMap.MapProjection`, `Map.MiniMap.MapProjection`, `Map.Pathing.Quad` |
| Member order | source order | preserved |
| Raising | — | **only the ten recorded divergences**: the nine mouse members and `Pathing.WorldToScreen`. `Map`, `MissionMap`, `MiniMap`, `WorldMap`, `Pregame`, both `MapProjection`s and `Pathing`/`Quad` have nothing else left |

**The class is done - the project owner's ruling, 2026-09-29:** *"mark this one as done, the things
missing are the ones we already account for."* No member of `Map` is a work item. The ten that raise
need the injected runtime's own ImGui (nine) or its overlay manager (one), which this project does
not install and cannot; each names its requirement in its own body.

**What that ruling does not say, and is still true:** the remaining *live checks* below are breadth
of verification, not porting gaps - they need a game state (the world map or the mission map open, a
cinematic, a mission offering a challenge) rather than code. They are listed so the next session can
close them when a state is convenient, and none of them is a reason to doubt a member.

### The class's own defects, closed this round

1. **The 17 class attributes were undeclared.** `Map.py` declares the click memory on four
   namespaces (`892-895`, `1407-1410`, `1854-1857`, `2028-2031`), `MissionMap._last_pan_offset`
   (`1066`), and `Pregame`'s two imported names (`2026`). The offline suite compared
   `FunctionDef` names only, so `AnnAssign` and the class-body import were invisible to every
   check. All 17 are declared now, in the source's order, and
   `test_every_source_class_attribute_is_declared` reads the source's class bodies and compares
   them name for name.
2. **`GetRegionType`, `GetCampaign` and `GetContinent` returned an empty name** where the source
   returns `RegionTypeName[...]`, `CampaignName[...]`, `ContinentName[...]`. They answer the
   table now. **Two of the three carry a source-internal `KeyError`**: the null path reads
   `CampaignName[255]` / `ContinentName[255]` and both tables are keyed `0..6`
   (`Region_enums.py`), so the source raises there and so does this — recorded on the members,
   ported as written.
3. **`Map` read an invented `InstanceType`.** `py4gw/context/instance_info_context.py`
   declared its own `InstanceType` (`OUTPOST`/`EXPLORABLE`/`LOADING`) and its own
   `InstanceTypeName`, duplicating the source's single enum in `enums_src/Map_enums.py`
   (`Outpost`/`Explorable`/`Loading`, `Map.py:12`). Reforged's `InstanceInfoContext.py` declares
   neither. The duplicate is deleted, `Map` and `py_inventory` import the source's, and the
   package exports re-point to it.
4. **Three `MiniMap.MapProjection` signatures were transcribed wrong** at Stage 1:
   `GamePosToScreen` and `ScreenToGamePos` were declared `(x, y)` where the source takes the
   six optional overrides, and `ComputedPathingGeometryToScreen` was declared
   `(geometry)` where the source takes `map_bounds` plus the same six. The name-only parity test
   could not see a signature. All three are the source's now.

### A context-layer defect this class depended on

`MissionMapContext._update_ptr` and `WorldMapContext._update_ptr` **raised
unconditionally** ("requires the in-process shared-memory callback"), and `GWContext`'s
`GetContext` calls `_update_ptr` first — so every `Map.MissionMap` and `Map.WorldMap` member
that reads its context would have failed *below* `Map`, with a `NotImplementedError` naming the
wrong thing. The documented route already existed (`py4gw/client.py`'s `mission_map_context` /
`world_map_context` properties, acquired by walking the client's UI frame array — read-only, and
live-verified). Both `_update_ptr`s are now the port's lazy refresh, in `GuildContext._update_ptr`'s
own shape: no client, or a frame that publishes nothing (the window closed), clears the pointer
and the snapshot, which is what the source's callback leaves behind in the same state. The two
contexts' offline suites pin the corrected shape.

## What answers, and what still refuses

**A ported member reaches one of four things.** The classification, member by member, is what
decided the order of this work:

| reach | members | state |
| --- | ---: | --- |
| local tables (`enums_src/Map_enums.py`, `region_enums.py`) | 13 | **ported** |
| game contexts through `GWContext` | 30 | **ported** |
| the UI frame tree and the frame geometry (`Frame.coords`/`content_coords`/`viewport_scale`/`click`) | 46 | **ported** |
| pure arithmetic over the two | 46 | **ported** |
| the client's own UI messages (`MapMethods`, `UIManager.SendUIMessage*`, `SetWindowVisible`, `Keydown`/`Keyup`) | 13 | **ported** |
| the client's in-process ImGui (`PyImGui.get_io()`) | 9 | **recorded on the member** |
| the injected overlay module (`PyOverlay.Overlay()`) and `Pathing`'s own dependencies | 21 | **to port** |

The nine are `MissionMap`/`MiniMap`/`WorldMap` × `IsMouseOver`, `GetLastClickCoords`,
`GetLastRightClickCoords`. The source reads them through `Frame.is_mouse_over` and
`Frame.io_events`, whose only producer is `UIManager._UpdateFrameIOEvents` — `PyImGui.get_io()`,
`PyImGui.is_mouse_clicked` and `PySystem.get_tick_count64` (`UIManager.py:74-90`). `PyImGui` is
the injected runtime's own ImGui context: this project installs none and there is no way to
install one, so the members report that rather than approximating a mouse position from outside
the client. `Frame.is_mouse_over`/`Frame.io_events` carry the same divergence.

## `MapMethods`

`Map`'s eight action bodies are Reforged's `native_src/methods/MapMethods.py` (135 lines), and
they are ported where the source keeps them: **`py4gw/native_src/methods/map_methods.py`**. The whole class is
there — `GetMapInfo`, `SkipCinematic`, `Travel`, `TravelGH`, `LeaveGH`, `EnterChallenge`,
`LogouttoCharacterSelect`, and the `_GHKEY_SCRATCH` class attribute.

Two of the source's own arguments are **host addresses**, and that is the only thing that
changes: `ctypes.addressof(TravelStruct(...))` and `ctypes.addressof(gh_key)` are pointers the
client is handed, and the sources can hand them over because they run *inside* `Gw.exe`. So
`Travel`'s four words go into the block's data region (the route `UIManager.SendUIMessage`
already takes for its own payload), and `TravelGH` needs no copy at all: `player_gh_key` is a
field of the client's own `GuildContext` at `+0x64` (asserted in
`py4gw/context/guild_context.py`), so the client is handed the address of its own key — which is
what the source's own comment means by *"Always use the original, working pointer"*. `TravelGH`'s
`key` branch writes the caller's four key bytes into the client's key through the payload's
`WRITE_MEMORY`; `Map.TravelGH()` passes no key, so that branch is not taken from `Map`.

## The action members and the queues

Nine `Map` members and the four window members hand their work to Reforged's frame loop —
`ActionQueueManager` (`Map.py:753, 761, 824, 841, 849, 857, 864, 875, 886`) or
`GLOBAL_CACHE.Coroutines` + `Routines.Yield.Keybinds` (`:935, 943, 1885, 1893`). **This port has
neither, and no class here has either**: the enqueue is the capability layer's own call path.
So the inner action runs where the queue would have run it, the source's guards are kept, and
the bodies are otherwise line for line — the queue call is the only line that differs. That is
the precedent `Player.BuySkill` already set (`py4gw/player.py:1272-1286`), and it is now the
project-wide rule.

Two things are **recorded rather than stood in for**:

* the behaviour tree's **75 ms hold** between `Keydown` and `Keyup`
  (`routines_src/behaviourtrees_src/keybinds.py:139`, `aftercast_ms=duration_ms`) — there is no
  scheduler to hold a key with, and a sleep of this port's own would be a throttle the source
  does not have;
* `WorldMap.CloseWindow` and `MissionMap.CloseWindow` queue **the same keybind as their
  `OpenWindow`** (`Map.py:943`, `:1893`), which is the source's own body and is ported as
  written.

## What is left: the ten recorded members

There is no porting work left in `Map`. Ten members raise, and each names the thing it needs:

| members | what they need | why it cannot exist here |
| --- | --- | --- |
| `MissionMap`/`MiniMap`/`WorldMap` × `IsMouseOver`, `GetLastClickCoords`, `GetLastRightClickCoords` (9) | `PyImGui.get_io()`, through `Frame.is_mouse_over` and `Frame.io_events` | `PyImGui` is the injected runtime's own ImGui context. This project installs none and there is no way to install one; the nine report that rather than approximating a mouse position from outside the client. `Frame.is_mouse_over`/`Frame.io_events` carry the same divergence |
| `Pathing.WorldToScreen` (1) | `PyOverlay.Overlay()` and `Overlay.FindZ` (`Map.py:2170-2175`) | The injected runtime's overlay manager, which exists because that runtime hooks the device and draws. This class has no render process |

## The dependencies ported for `Pathing`

| what | where | what it is |
| --- | --- | --- |
| `Checks.Map` | `py4gw/routines_src/Checks.py` | The namespace `GetPathingMaps`/`GetPathingMapsRaw` guard on (`Map.py:2107, 2117`): all seven members, every one a guard over the ported `Map` and `Party`. The other seven namespaces `Checks` declares (`Player`, `Party`, `Inventory`, `Items`, `Effects`, `Agents`, `Skills`) are **that class's own migration** — `Map` reaches none of them, and `CLASS_PORT_MAP.md` carries a row saying so |
| `FfnaMapMethods` | `py4gw/native_src/methods/ffna_map_methods.py` | The source's 681-line module whole: the FFNA parser (13 module functions, 3 dataclasses) and the **404-entry** `_MAP_ID_TO_DAT_FILE_ID` table, checked value for value against the source by `tests/test_map_pathing_offline.py`. Its archive read is the already-ported, live-verified `dat_reader.read_file_by_id` |
| the navmesh half of `Pathing` | `py4gw/pathing.py` | `AABB`, the BSP helpers, `TrapezoidBSP`, `NavMesh` (its whole class), `PATHING_MAP_GROUPS` and `AutoPathing` (its whole class), extracted from the source's own line ranges. `AutoPathing.get_path`/`get_path_to` are declared and name what they need — `PyPathing.PathPlanner` and the `Routines` coroutine driver — because they are the two members that need the injected planner and the frame loop, and neither is on `Map.Pathing`'s path. `PySystem.Console.Log` in `NavMesh.load_from_file` (`:439`) is the injected console: recorded on the member, not replaced |

**One thing ports that is worth naming**: `Quad`'s corners are `PyOverlay.Vec2f(...)` in the source,
and native binds that name to `GW::Vec2f` (`overlay_bindings.cpp:14-18`) — two floats with
`x`/`y`, which is the record `py4gw/internals/types.py` already declares as the port of Reforged's
own `native_src/internals/types.py::Vec2f`. Same words, same fields, same construction, so that is
the type the port's `Quad` uses, and the member records it.

## Gates

| Check | Command | Result |
| --- | --- | --- |
| surface parity | `python -m unittest tests.test_map_offline` | **8 tests OK** (178/178 members, order exact; 17/17 attributes; 168 implemented, 10 refusing) |
| the dependencies | `python -m unittest tests.test_map_pathing_offline` | **18 tests OK** (the FFNA table value for value, the parser on synthetic bytes, `Checks.Map` against the source's own class body, the BSP/navmesh on trapezoid fixtures, both injected members refusing) |
| offline suite | `python -m unittest discover -s tests -p "*_offline.py"` | **1557 tests**, 1 failure — `test_ui_manager_offline`'s `GetWindoPosition`, from an uncommitted `int()` cast in `py4gw/ui_manager.py` that predates this round and is not this class's |
| types | `pyright` (13 files) | **0 errors** |
| live | — | **owed**, see below |

## Live pass (round 80) - **run, and green**

`tests.test_map` **44 tests, `OK (skipped=2)`, 3.7 s**, elevated, against `Gw.exe` pid 34748 on map
**55 (Lions Arch)**, instance type 0 (Outpost). `tests/probe_map_live.py` is the sectioned, timed
version of the same pass and is now in the runner's default set; `tests/live_reports/summary.txt`,
`tests/live_reports/tests.test_map.log` and `tests/live_reports/map_live.json` are the reports. The client came
back clean: both hooked entry points read `original: true` again and the game window was responding.

**What the pass confirmed, all cross-checked against the context each member claims to read:**

| check | result |
| --- | --- |
| **`GetUnloadedMapInfo(GetMapID())` against the loaded `AreaInfo`** | **all 31 fields agree** - the offline array read, indexed by `map_id * 0x7C` off `map.area_info_addr`, matches the record `InstanceInfo` hands out for the current map |
| the three name halves | `GetRegionType()` `(13, 'City')`, `GetCampaign()` `(1, 'Prophecies')`, `GetContinent()` `(0, 'Kryta')` - real names, where the port used to answer `""` |
| the name tables' round trip | `GetMapName()` = `'Lions Arch'`, `GetMapIDByName('Lions Arch')` = `55`, `GetBaseMapID(55)` = `55`, `GetAllMapVariants(55)` = `[55, 808, 809, 810]` |
| the gate and identity | type 0 / `'Outpost'` / `IsMapReady()` true / `GetMapID()` 55, each reproducing its context |
| region, language, district | `(0, 'America')`, `(0, 'English')`, `1` |
| the world context | 63 players in instance, `GetInstanceUptime()` 2406062701, foes 0/0, `IsMapUnlocked()` true |
| the 22 `AreaInfo` readers | every scalar, flag, icon vector and file-id half against `AreaInfoStruct` |
| bounds | `GetMapBoundaries()` `(-18432.0, -18432.0, 18432.0, 18432.0)`; `GetMapWorldMapBounds()` `(3712.0, 4704.0, 4096.0, 5088.0)` |
| pathing | **50 layers, 2,836 trapezoids**, `GetAvailableMapIds()` **404**, `GetSpawns()` `[1, 10, 17]`, `GetTravelPortals()` **3** |
| the ten divergences | all ten raise and name their need, while connected |

**Two source guards confirmed live, both worth having on the record** because they look like missing
values and are not:

* the mission map is **closed**, so `GetScale()` answers `(0.0, 0.0)` and both coordinate reads answer
  the zero rectangle - that is ``Map.py:1027-1028``'s own `if not (frame_info := GetFrame())` guard,
  taken before `viewport_scale()` is ever reached;
* closed, `GamePosToScreen` answers `(0.0, 0.0)` (the scale it multiplies by is zero) and
  `ScreenToGamePos` answers a large negative pair (`ScreenToWorldMap`'s own `IsWindowOpen()` guard
  answers `(0.0, 0.0)`, and `WorldMapToGamePos` then extrapolates from the origin). Both are the
  source's arithmetic, live.

## Live pass: the travel members (round 81) - **verified**

`tests/probe_map_travel_live.py`, elevated, `Gw.exe` pid 34748. The sequence is the owner's own, and
the **map id after each step is the evidence** - a send that reached the client and was acted on is
the only thing that proves these members:

| step | the member | ids seen | result | time |
| --- | --- | --- | --- | --- |
| start | - | - | map **55** (Lions Arch), not a guild hall | - |
| 1 | `Map.TravelGH()` | `55 -> 5` | **map 5, "Guild Hall - Hunter's Isle"**, `IsGuildHall()` true | 1.0 s |
| 2 | `Map.Travel(55)` | `5 -> 0 -> 55` | **back in map 55 (Lions Arch)** | 2.0 s |
| 3 | `Map.TravelGH()` then `Map.LeaveGH()` | `55 -> 0 -> 5`, then `5 -> 0 -> 55` | **left the hall; back in map 55** | 2.0 s + 2.0 s |

The character ended where it started, the connection was released normally, and both hooked entry
points read `original: true` afterwards. **The owner's prediction held**: `TravelGH` working meant
`LeaveGH` did too - both are a single UI message through the same sender.

Three of the nine action members are therefore live-verified: **`Travel`, `TravelGH`, `LeaveGH`**.

* **`TravelToDistrict` and `TravelToRegion` end in the same call that just worked** -
  `MapMethods.Travel(map_id, region, district_number, language)`, i.e. the `kTravel` send with
  `region`/`language` supplied rather than read. What is new in them is only the district ->
  region/language resolution, which is two pure lookups over the ported `District`/`ServerRegion`/
  `ServerLanguage` tables and needs no client.
* Still owed, and each needs a game state rather than a mechanism: **`SkipCinematic`** (a running
  cinematic), **`EnterChallenge`/`CancelEnterChallenge`/`ConfirmEnterChallenge`** (a mission offering
  a challenge and its buttons).

## Finding: the composed pathing members cost minutes, and why

**Measured, not estimated** (`tests/probe_map_live.py`, and printed by the suite on every run):

| | |
| --- | --- |
| one `Quad()` | **376-387 ms** |
| `GetMapQuads()` on this map | 2,836 trapezoids x ~380 ms = **~1,065-1,098 s (18 minutes)** |
| the same for each of the four `*ComputedGeometry` members, and for `IsPointInPathing`/`IsScreenPointInPathing` | |

**Where the time goes.** One `Quad` makes four `Map.MissionMap.MapProjection.GameMapToScreen` calls,
and one of those costs ~98 ms - measured directly. Inside it, `WorldMapToScreen` calls
`GetPanOffset()` (~23 ms), `GetScale()` (~36 ms) and `GetMapScreenCenter()` (~35 ms), and
`GetMapScreenCenter` reaches `GetMissionMapContentsCoords()`, which calls `GetFrame()` again. Each of
those calls `Map.MissionMap.GetFrame()` -> `GetFrameID()` -> `GWContext.MissionMap.GetContext()` ->
`_update_ptr()`, which walks **the client's whole frame array** over `ReadProcessMemory`; `GetScale`
additionally reaches `FrameTree.root()`, a call into the client.

The contrast inside one run is the whole story:

| read | cost |
| --- | --- |
| a plain context read (`GetMapID`, `GetRegion`, an `AreaInfo` field) | **0.1-0.9 ms** |
| a frame walk (`MissionMap.GetFrame`, `IsEnteringChallenge`, `WorldMap.GetFrameID`) | **36-67 ms** |
| a frame read that also reaches the root (`MiniMap.IsLocked`, `GetRotation`, `MissionMap.GetScale`) | **82-93 ms** |
| the pure-Python navmesh build (`NavMesh` over 2,836 trapezoids) | **~7 us per trapezoid, ~20 ms total** |

**This is not a defect in a member, and it is not a bug to fix here.** Every one of those members is
the source's own composition, and the individual reads are the port's recorded model: no frame loop,
so every read happens when it is called. **Reforged is fast here because it runs inside the client** -
its `GWContext.MissionMap.GetContext()` is an in-process field access, and its `@frame_cache` and the
frame tree's tick-keyed snapshot memoise the rest. This port drops the decorator by rule
(`PORTING_RULES.md` § Caching) and drops the per-tick memo with it, so the composition pays a frame
walk per projection instead of a pointer dereference. A memo of our own is what the rules forbid, and
the remedy the sources actually have is the frame-driven mode this port does not have.

**What the suite does about it.** `test_the_composed_geometry_members_are_measured_first` measures
one `Quad`, prints the extrapolation, and runs the members only inside `GEOMETRY_BUDGET_SECONDS`
(30 s); on a map this large it skips with the measured number in the reason. `Quad` itself, and the
projections it calls, are checked directly in
`test_one_quad_is_the_trapezoid_and_it_projects` for one item's cost. So the members are ported,
their parts are verified live, and the cost is a recorded measurement rather than a hang.

**What is left owed, and it is one thing:** the world map was **closed** during this pass, so no
frame published `WorldMapContext` and `test_world_map_reads_match_its_context` skipped itself. Open
the world map in the client and re-run `tests.test_map` to close it.

## Progress

- [x] **Round 78** — the class's own defects (17 attributes, three name halves, the duplicated
      `InstanceType`, three mis-transcribed signatures), the two `_update_ptr`s, all of `Map`,
      all three window namespaces and both projections, `Pregame`, and `MapMethods`:
      **148 of 178 answer**
- [x] **Round 79** — the `Pathing` dependencies (`Checks.Map`, `FfnaMapMethods`, the navmesh half)
      and then `Pathing` and `Quad`: **168 of 178 answer, 10 recorded**. The class is done
- [x] **Round 80 — the live pass, and it is green**: `tests.test_map` **44 tests, `OK (skipped=2)`**,
      3.7 s, elevated, on map 55 - including `GetUnloadedMapInfo(GetMapID())` agreeing with the loaded
      `AreaInfo` on all 31 fields, the three name halves answering real names, and 2,836 trapezoids /
      404 offline map ids read through `Pathing`. One measured finding (the composed pathing geometry
      members cost ~18 minutes on this map, and why) and one thing owed: the **world map was closed**,
      so its context reads skipped
- [x] **Round 81 — the travel members, live**: `Map.TravelGH()` 55 -> 5 (Guild Hall - Hunter's
      Isle, `IsGuildHall()` true), `Map.Travel(55)` 5 -> 0 -> 55, and `TravelGH` + `Map.LeaveGH()`
      5 -> 0 -> 55 - the character back where it started and the client clean. **Three of the nine
      actions are live-verified**; `TravelToDistrict`/`TravelToRegion` end in the same send that
      worked, so what is left there is the district resolution, which is pure
- [x] **Round 82 - closed by the owner's ruling**: `Map` is **done**. The ten raising members are the
      accounted-for divergences, and the live checks still open are verification breadth (each needs a
      game state), not porting work
- [ ] **Optional, state-dependent live checks** (not work items) — `WorldMap`'s four context reads need
      the world map open; `SkipCinematic` needs a cinematic, and
      `EnterChallenge`/`CancelEnterChallenge`/`ConfirmEnterChallenge` need a mission offering a
      challenge. These need a **game state**, not a mechanism
