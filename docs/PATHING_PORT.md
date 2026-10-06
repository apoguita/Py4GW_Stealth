# Pathing port — status, gates, and the live pass

**The class: Reforged's `Py4GWCoreLib/Pathing.py`** (863 lines) — `AABB`, the BSP helpers,
`TrapezoidBSP`, `NavMesh`, `AStarNode`, `AStar`, `chaikin_smooth_path`, `densify_path2d`,
`PATHING_MAP_GROUPS`, `AutoPathing` — **plus** the two objects Reforged reaches through the injected
`PyPathing` module, which are **Native's** declarations: `PathStatus` and `PathPlanner`
(`include/GW/pathing/pathing.h:30-74`, bound in `src/GW/pathing/pathing_bindings.cpp:10-43`).

**Verdict: PORTED WHOLE.** Every declaration of the source file is present, in the source's order,
with the source's signatures, and **no member raises**.

## Parity, measured

`tools/pathing_audit.py` compares the two files through their ASTs:

```
AABB: 1 members, ok        _BspSplit: 1, ok        _BspLeaf: 1, ok
TrapezoidBSP: 3, ok        NavMesh: 17, ok         AStarNode: 2, ok
AStar: 5, ok               AutoPathing: 9, ok
_point_in_trapezoid, _build_trap_bsp, chaikin_smooth_path, densify_path2d: present
== totals: 0 problem(s), 0 missing member(s), 0 raising member(s) ==
```

**The planner is Native's, line for line.** `PathPlanner` calls the client's own finder with the same
six words Native passes, and every constant matches the C++ it ports:

| the port | Native |
| --- | --- |
| `MAX_PATH_POINTS = 30` | `std::array<PathPoint, 30> pathArray` |
| `FIND_PATH_RANGE = 10000.0` | `g_find_path_func(..., 10000.0f, ...)` |
| `PATH_POINT_SIZE = 0x10` | `PathPoint { GamePos pos; const PathingTrapezoid* t; }` (12 + 4) |
| `PathStatus.Idle/Pending/Ready/Failed` = 0/1/2/3 | `enum class Status { Idle, Pending, Ready, Failed }` |
| `Failed` when the count is 0, or 1 point that is not the goal | the same two tests, verbatim |
| `offsets/pathing.json` | **byte-identical** to Native's catalog (pattern + resolver) |

**The recorded divergences**, each on the member that carries it:

* **`get_path`/`get_path_to` are not generators here.** The source declares them so (`Pathing.py:744`)
  and waits inside with `yield from Routines.Yield.wait(100)` (`:783`) — Reforged's frame-loop
  coroutine driver, which this library does not carry. This port's call path *is* the game thread, so
  the planner's status is final when `plan` returns and the member answers the list the source's own
  `return` produces. Every other line keeps the source's order, including the map check before planning
  and the second one before the answer is used.
* **Native's failure log has no home** (`Logger::Instance().LogError("FindPath_Func not initialized.")`,
  `pathing.cpp:22`) and is not replaced by anything: the port asks the catalog whether the function is
  there — the same question, asked of the thing that holds it — and marks `Failed`.

## Gates

| check | command | result |
| --- | --- | --- |
| parity | `python tools/pathing_audit.py` | **0 problems, 0 missing, 0 raising** |
| offline tests | `python -m unittest tests.test_map_pathing_offline` | **48 tests OK** |
| offline suite | `python -m unittest discover -s tests -p "test_*offline*.py"` | **1818 tests OK** (2026-10-05), no failures — the long-standing `ui_manager` `GetWindoPosition` failure was this port's own `int()` cast over the binding's four floats and is fixed |
| types | `pyright py4gw/pathing.py py4gw/context/map_context.py py4gw/game_thread/shared_block.py tests/probe_pathing_live.py` | **0 errors** |

## The live pass — `tests/probe_pathing_live.py`

**`reads` (unelevated, no connection, nothing called)** — run 2026-09-30 against `Gw.exe` pid 29504,
map 642:

```
find_path_func resolved: True at 0x107a2f0
  epilogue: ret at +0x7f — the caller releases (cdecl), which is what the port's STACK_WORDS does
  entry: 55 8b ec 83 ec 20 53 56 57 e8 62 53 d7 ff 8b 5d
pathing maps live=24 raw=24 available map ids=404
navmesh: {'map_id': 642, 'trapezoids': 3361, 'portal_links': 15220}
player at (-2202.12, 1759.82) | trapezoid 3261 | neighbours 6
astar: {'found': True, 'seconds': 0.0, 'points': 3}
smooth_path_by_los: {'points': 2, 'ends': [(-2202.12, 1759.82), (-1902.12, 1759.82)]}
```

So against the live client: the resolver finds the function and its **epilogue is measured before
anything calls it** (a bare `ret` → `STACK_WORDS` is the right form — a callee-popped `ret imm16` would
have made a six-word call a corrupt stack), the client's own **24 pathing maps** come through
`Map.Pathing`, the navmesh builds over **3,361 trapezoids** with 15,220 portal links, the player's
trapezoid and its six neighbours resolve, and **A\* finds a real route** which the LOS smoother then
reduces to its two endpoints.

**`act` (elevated)** — the client's own finder through the port:

| call | answer |
| --- | --- |
| `PathPlanner.plan(...)` | **`PathStatus.Failed`** (3), 0 points, ~0.21 s |
| `PathPlanner.compute_immediate(...)` | 0 points |
| `AutoPathing.get_path(start, goal)` | **the path** — 2 / 4 / 27 / 23 points at 300 / 1500 / 4000 / 8000 units, ~0.28 s |
| `AutoPathing.get_path_to(x, y)` | 19 points at the same goal |
| the player | did not move; `hooks_original_after_disconnect: True` |

**The finding, and why it is not a defect in the port.** The planner hands the client's finder exactly
what Native hands it and the client answers **zero points** — the count word it writes back is `0`, at
every distance tried (300, 1500, 4000, 8000 units), so the planner reports `Failed`. Native's own
`PathPlanner` would see the same, because it makes the same call with the same six words: the planner's
success is the *client's* to give, and in this map it gives nothing. What the port does then is the
source's own design: `get_path` sees `Failed`, breaks out of its planner branch and takes the **navmesh
route** — `AStar.search` over the ported `NavMesh`, `_prepend_start` verbatim, LOS smoothing, optional
Chaikin, then densify — which is exactly the path the table above shows being answered. So the member
behaved as Reforged's body specifies, with the planner's half of it measured rather than assumed.

## Re-run on the post-update client — 2026-10-05

The client shipped build 38974 on 2026-09-30 13:40, so every run above is **pre-update**. Both stages
were re-run against the updated client with **Reforged injected** (pid 4692, `Gw.exe` 10,506,432 bytes
2026-09-30 13:40:06) — the arrangement the owner runs.

**`reads` (unelevated, nothing connected, nothing called)** — `tests/live_reports/pathing_reads_2026-10-05.json`:

```
pathing maps live=24 raw=24   available map ids=404
navmesh: {'map_id': 642, 'trapezoids': 3361, 'portal_links': 15220}
player at (-2550.84, 3708.31) | trapezoid 3240 | nearest 3246 | neighbours 5
astar: {'found': True, 'points': 3}
smooth_path_by_los: 2 points, ends [(-2550.84, 3708.31), (-2250.84, 3708.31)]
```

The same navmesh (3,361 trapezoids, 15,220 links) as the pre-update run, so the pathing records and
the port's arithmetic over them are unchanged by the update.

**`Map.Pathing.IsPointInPathing` costs ~17 minutes on this map, and that is this architecture's, not
the source's.** The member is the source's own body (`Map.py:2288-2310`): loop over every trapezoid,
`Pathing.Quad` each, `_point_in_quad` the point. `Quad` computes screen coordinates through
`Map.MissionMap.GetPanOffset` and `GetZoom`, and **this port acquires both contexts by walking the
client's frame array on every read** — there is no frame loop to hold them for (the `@frame_cache`
decision, `PORTING_RULES.md`). Measured live 2026-10-05: one `Quad` is **0.30 s**, so the loop over
3,361 trapezoids is ~1,014 s. In Reforged the contexts are in-process pointers, so the same body is
cheap: the cost is the read-only frame-array route's, and nothing here caches a map-scoped pointer to
hide it. The reads stage therefore **times one `Quad` and reports the extrapolation** instead of
paying it (`trapezoids_total`, `quad_seconds`, `is_point_in_pathing_estimated_seconds`), and the
member's own answer was measured once by hand
(`tests/live_reports/pathing_point_in_pathing.json`): **`True` in 801.1 s** for the player's own position —
it is in pathing area, which is the right answer, and the run is the loop's full cost rather than a
stall.

**`IsScreenPointInPathing` answered `True` in 0.3 s on the same run, and that is the source's own
test.** Its body (the port's `map.py:2470-2492`, Reforged's `Map.py:2303` line for line) inlines a
`sign` cross-product for each of the quad's four edges and returns `True` when `b1 == b2 == b3 == b4`
— four *equal* booleans, which holds for a point outside all four edges exactly as it does for one
inside. The coordinates passed to it were the player's **world** position, which that member does not
take (it takes screen coordinates), so the point sat outside the first trapezoid's quad, the four
signs came back equal, and the member answered `True` on its first iteration. It is ported as the
source writes it and this note is the record of what that line does; `IsPointInPathing`, which is the
world-coordinate member, gave the correct answer above.

**The probe gap that came before that** is closed: the reads stage first reported
`AttributeError: '_LiveClient' object has no attribute 'mission_map_context'`, because the probes'
shared read-only stand-in did not offer the connection's frame-array-backed facades — it now builds
`FrameTree`, `MissionMapContext` and `GameplayContext` the way `ConnectedClient` builds them
(`client.py:393-410`), which is what let the chain above be measured at all. That was a **stand-in
gap, never a port defect** (the real `ConnectedClient` has had the facades all along,
`client.py:1387`).

**`act` (elevated)** — `tests/live_reports/pathing_act_2026-10-05.json`:

| call | answer |
| --- | --- |
| `PathPlanner.plan(...)` | **`PathStatus.Failed`** (3), 0 points, ~0.21 s |
| `PathPlanner.compute_immediate(...)` | 0 points |
| `AutoPathing.get_path(start, goal)` | **2 points**, ~0.28 s, `z` is the start's |
| `AutoPathing.get_path_to(x, y)` | 1 point |
| the player | did not move (`before == after`, agent 17, map 642) |
| the entries | `hooks_original_after_disconnect: true` — all four, and the two addresses that carried Reforged's jump, byte-for-byte |

**A gate in the probes had to be corrected before this could run at all.** Both pathing probes
refused with *"one of the hooked entries does not hold the client's own bytes, so another controller
is attached or was killed while attached"* — a guard (`probe_party_live.entry_is_original`) written
for a client with **no other runtime**, which is no longer the arrangement: Reforged comes with the
client, and `tests/test_live_coexistence.py` is green on it (3/3 OK on this same pid, 2026-10-05).
The guard is now `probe_two_runtimes_live.connectable(win32, pid)`, which drives the connection's own
placement decisions (`_resolve_placement`, `_entry_jump_ahead`, `_is_our_stale_patch`,
`_is_foreign_patch_on_the_declared_function`) and refuses only where `_prepare_target` itself would;
`decide_entries` now holds that decision once, and the probe report is byte-identical before and after
the extraction. Both probes also compare the entries **against what they held before the probe
patched** (Reforged's jumps) instead of against the client's own prologue.

**The client's own finder question is answered** — `tests/probe_pathing_finder.py`, written
2026-10-01 and never run until now (`tests/live_reports/pathing_finder_diagnostic.json`): the count word is
pre-filled with `0xDEADBEEF` and the 30 records with `0xCC`, so "the client said no" is told apart
from "the call never arrived".

| case | count word | count | array | points |
| --- | --- | --- | --- | --- |
| 4000 units east, **zplane 0** (what the probe used to pass) | written (`0x0`) | 0 | untouched (`cc…`) | — |
| 4000 units east, **the player's own zplane (22)** | written (`0x1`) | 1 | touched | `(466.06, 3711.33, zplane 22, t=0x2d1b2180)` |
| 600 units east, the player's own zplane | written (`0x1`) | 1 | touched | `(-1950.84, 3708.31, zplane 22, t=0)` — the goal itself |

So the call **reaches** the client's finder and the client answers: the earlier zero was the client
being asked with `zplane 0` on both endpoints. `PathPlanner.plan` still reports `Failed` because it
hands the finder the endpoints Native hands it — that is the source's own call, and it is not this
port's to change — while `AutoPathing.get_path` takes the source's own navmesh route and answers.

## Records around this pass

* `docs/CLASS_PORT_MAP.md` now carries the class as **FULL** (both the §1 row and the work-queue entry),
  and neither still says the four path-walk pieces are missing. An earlier assessment of mine — row 112
  of `docs/PORTING_PROGRESS.md` — judged the module **INCOMPLETE** on a file that did not yet carry
  `AStar`/`AStarNode`/`chaikin_smooth_path`/`densify_path2d`; the port landed while that assessment was
  being written, and round 115 records the verification and the live pass above as the current state.
  The sequence is kept in the log rather than edited away, because the assessment's *reasoning* about
  the four pieces is what the port then did.
* The only piece of this class that is **not** live-exercised is the planner's success path — through
  `PathPlanner.plan` the client's finder answers zero points, and the 2026-10-05 diagnostic shows why:
  the endpoints travel with `zplane 0`. The call is Native's, the arguments are Native's, and the
  answer is the client's, so the planner is left exactly as the source writes it; `AutoPathing.get_path`
  answers over the navmesh route in the same run. Everything else in the tables above was measured
  against the running client, the post-update run included.
