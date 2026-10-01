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
| offline suite | `python -m unittest discover -s tests -p "test_*offline*.py"` | **1795 tests**, 1 pre-existing failure (`ui_manager` `GetWindoPosition`) |
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

**What is still unmeasured**: whether the client's finder ever answers (it may need a target the engine
considers reachable across trapezoids, or a caller running inside its own frame). Nothing in the port
can settle that: the call is Native's, the arguments are Native's, and the answer comes from the
client. It is recorded here as the open question, with the numbers, rather than left implied.

## Records around this pass

* `docs/CLASS_PORT_MAP.md` now carries the class as **FULL** (both the §1 row and the work-queue entry),
  and neither still says the four path-walk pieces are missing. An earlier assessment of mine — row 112
  of `docs/PORTING_PROGRESS.md` — judged the module **INCOMPLETE** on a file that did not yet carry
  `AStar`/`AStarNode`/`chaikin_smooth_path`/`densify_path2d`; the port landed while that assessment was
  being written, and round 115 records the verification and the live pass above as the current state.
  The sequence is kept in the log rather than edited away, because the assessment's *reasoning* about
  the four pieces is what the port then did.
* The only piece of this class that is **not** live-exercised is the planner's success path — the
  client's finder returns zero points — and that is the client's answer, not the port's behaviour.
  Everything else in the tables above was measured against the running client.
