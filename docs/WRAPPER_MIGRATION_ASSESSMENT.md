# Wrapper-class migration assessment

Status: **assessment, kept current.** Its counts and verdicts describe the wrapper
classes as they stand — `Map`, `Player`, `Party`, `Scanner` and `Dialog` are ported, and
each one's remaining members are named in its own port doc. This document was rewritten after
an initial version recommended `Dialog` as a pilot. That recommendation was
wrong and the reasons are recorded below, because the mistake identifies the
real problem.

## Scope entry that needs updating

`docs/SCOPE.md:141` lists, under **"Out of scope for the current capability"**:

> reproduce Py4GW `Py*` bindings, widgets, or automation helpers

The wrapper classes are exactly that layer. `SCOPE.md:19-21` also states the
current position plainly: **"full source/API parity has been achieved for no
context"**, and existing readers are "verified external read slices with
documented gaps". `SCOPE.md:15-17` calls the work capability-by-capability.

So the wrapper layer is outstanding porting work, and `SCOPE.md` still records it
under out of scope. `SCOPE.md` needs to say that the wrapper layer
is in scope and where it sits relative to the unfinished context work.

## Why the first recommendation was wrong

The first version of this document recommended `Dialog`, on the reasoning that
its data came from `WorldContext.dialog_buff`. **That was an unverified
inference and it is false.** The chain was:

| What I assumed | What the source says |
| --- | --- |
| `PyDialog.get_active_dialog` reads `WorldContext.dialog_buff` | `dialog_bindings.cpp:106` binds it to `GW::dialog::GetActiveDialog` |
| `GetActiveDialog` reads game structures | `dialog.cpp:1627-1630`: `std::scoped_lock lock(dialog_mutex); return active_dialog_cache;` |

`GetActiveDialog` returns a **cache held inside the in-process project**. The
data is captured in the DLL, not stored in a game structure Stealth reads. Two things
named "dialog" was a coincidence, and I treated it as evidence.

The same pattern appears in `Quest`. `request_quest_name`,
`is_quest_name_ready` and `get_quest_name` operate on `g_quest_name_map`, a
DLL-side map filled by an asynchronous capture (`quest_bindings.cpp`).

## The axis that was missing

The first version classified methods by name prefix into read / derive /
execute / write. That axis does not answer the question that decides
portability: **where does the data come from?** A method called `get_*` can be
context-backed, DLL-cache-backed, or computed, and only the provenance decides
whether Stealth can implement it.

The classification each wrapper method needs is:

| Class | Data source | Stealth status |
| --- | --- | --- |
| `context` | a structure Stealth already reads | implementable now |
| `computed` | pure calculation over other values | implementable now |
| `capture` | in-process cache filled by a hook, callback, or async reply | **partly in use** — the hook and callback layer exists in `py4gw/game_thread/`, and `Player.GetTargetID` and the dialog module's state read values the connection captured from the client's own messages; the other wrappers' captures are not wired |
| `action` | a game call, UI click, packet, queue, or memory write | **in use for `Player`** — eleven members are ported onto the game-thread call path; the other wrappers' actions are not ported yet |

`capture` is the dangerous one, because it is invisible in the Python layer: the
wrapper looks read-only and the cost only appears when the native binding is
traced.

## What is verified so far

Wrapper surface size, measured from the source. This is **size, not
portability** — it says nothing about provenance.

| Wrapper | Lines | Methods | Native binding involved |
| --- | ---: | ---: | --- |
| `Map` | 2327 | 191 | `Py4GWCoreLib`, `PyOverlay`, `PySystem` |
| `Agent` | 1657 | 148 | `Py4GWCoreLib`, `PyAgent`, `PyCallback`, `PySystem` |
| `Inventory` | 1477 | 59 | `Py4GWCoreLib`, `PyInventory`, `PySystem` |
| `UIManager` | 1302 | 111 | `PyUIManager` (via `FrameTree`) |
| `Player` | 1017 | 79 | `PyPlayer`, `PySystem` |
| `GWUI` | 887 | 56 | `PyUIManager` |
| `Pathing` | 862 | 45 | `Py4GWCoreLib`, `PyPathing`, `PySystem` |
| `Item` | 827 | 92 | `Py4GWCoreLib`, `PyInventory`, `PyItem` |
| `Party` | 810 | 70 | `Py4GWCoreLib`, `PyParty` |
| `PacketSniffer` | 564 | 21 | `Py4GW` |
| `Skill` | 511 | 87 | `PySkill` |
| `Listeners` | 488 | 64 | `PyCallback` |
| `AgentArray` | 482 | 28 | `Py4GWCoreLib`, `PyAgent` |
| `Camera` | 367 | 46 | `PyCamera` |
| `Quest` | 245 | 26 | `PyQuest` |
| `ItemArray` | 212 | 13 | `Py4GWCoreLib`, `PyInventory` |
| `Skillbar` | 209 | 18 | `Py4GWCoreLib`, `PySkillbar` |
| `Merchant` | 197 | 17 | `Py4GWCoreLib`, `PyMerchant` |
| `Effect` | 176 | 15 | `PyEffects` |
| `Dialog` | 173 | 10 | `PyDialog` |

Layer stack:

```text
native_src/context/*    context structs and facades      (Stealth has these)
native_src/methods      native plumbing
GlobalCache/*           per-system caches + aggregate     (~4,600 lines)
<Wrapper>.py            Player, Party, Map, Agent, ...    (the target)
native bindings         PyPlayer, PyInventory, PyDialog, ...
host framework          PyCallback, PySystem, PyImGui
```

Native binding usage across the library: `PyCallback` 70, `PySystem` 70,
`PyImGui` 66, `Py4GW` 20, `PyInventory` 17, `PyParty` 11, `PyOverlay` 8,
`PyUIManager` 6, `PyAgent` 5, `PyItem` 5, `PyPlayer` 4, `PySkillbar` 3,
`PyKeystroke` 2. Most usage is the host framework, not game interaction.

## How actions actually reach the game

Traced from the Python wrappers into the bindings. **Five mechanisms exist, and
all five require code executing inside `Gw.exe`.** When this was written none was
reachable from Stealth; the position has since changed for the first and third,
because `py4gw/game_thread/` can now run code inside the client. The table records
what each mechanism needs and what Stealth has of it today.

| Mechanism | Example | Path | Mechanically reachable? |
| --- | --- | --- | --- |
| **A** game function via a game-thread queue | `Player.Move`, `DepositFaction`, `SkipCinematic` | `NativeFunction` (pattern-scanned address) -> `PyGameThread.enqueue` -> `ctypes` call | **in use** — the emitted dispatcher calls a registered game function on the client's own thread. `Player` has eleven such members ported onto it (`Move`, `DepositFaction`, `ChangeTarget`, `CallTarget`, `Interact`, `SetActiveTitle`, `RemoveActiveTitle`, `SendRawDialog`, `SendDialog`, `SendAutomaticDialog`, `SetPlayerStatus`); the rest of the wrappers' actions are not ported yet |
| **B** native binding call | `SkillBar.UseSkill`, `Inventory.SalvageItem`, `Trading.BuyItem` | `PySkillbar.Skillbar().UseSkill(...)`, `PyInventory.PyInventory().Salvage(...)` | **not ported** — the binding is Reforged's own DLL code, not a game function we can resolve |
| **C** UI-message dispatch | chat, travel, target, dialog | `UIManager.SendUIMessage` -> `PyUIManager` -> game's own message handler, which emits the CtoS packet | **yes, mechanism exists** — the `UI_MESSAGE` call form reaches the client's own `send_ui_message_func`, live-verified |
| **D** frame click | `Frame.click()`, `SalvageOptionsWindow.SelectOption` | `PyUIManager.UIManager.button_click(frame_id)` | **not established** — it is a call into the engine's frame/mouse handler, so the same call mechanism would apply, but its address and ABI have not been resolved or verified |
| **E** memory write | guild-hall key copy, `Frame.set_text` | writes into the game struct, or a native binding that writes it | **transport exists, nothing ported** — `py4gw/win32/write_access.py` writes; no ported member writes through it |

### The frame click is not simulated input

This is worth stating separately because it rules out the obvious substitute.
`Frame.click()` is `PyUIManager.UIManager.button_click(self.frame_id)`
(`FrameTree/frame.py:1260-1263`), and `mouse_action` is
`test_mouse_action(frame_id, ...)`. There is **no `SendInput`, `PostMessage`,
`SetCursorPos`, or `mouse_event` anywhere in that path** — it is a direct
in-process call into the engine's frame/mouse handler.

So the route to UI automation is that in-process frame/mouse call itself, not
synthesised Windows input; `UIManager`, `GWUI`, and the salvage-dialog helpers
are not ported yet, and that call is what they need.

Consequence for the four-class table above: an `action` method needs a call
vocabulary entry for its exact function and argument form, and a `capture` method
needs its source mechanism ported onto the hook and callback layer. The call
vocabulary now covers the shapes `Player`'s actions need, and eleven of them are
ported; `Player`'s remaining members are waiting on a string buffer, a
value-returning form, or two unported modules rather than on the call path itself.
A `capture` member is ported onto the callback layer now: `Player.GetTargetID` reads
the target the connection captured from the client's own `kChangeTarget` notice, and
`Dialog` reads its agent and button state from two more of the client's messages.

## Caching: the `frame_cache` decorator and `FrameCache`

Recorded in full because it is small, it is the pattern the wrappers use, and it
is directly portable.

`py4gwcorelib_src/FrameCache.py` is 165 lines and does one thing: **memoise a
function for the duration of one game frame.**

```python
@dataclass(frozen=True)
class FrameCacheKey:                 # the dict key
    category: str
    source_lib: str
    function_name: str
    key: Hashable = ""

class FrameCache:                    # singleton, one flat dict
    _values: dict[FrameCacheKey, Any]

    def get_or_create(self, category, function_name, factory, source_lib="", key=""):
        cache_key = FrameCacheKey(category, source_lib, function_name,
                                 self._normalize_key(key))
        if cache_key not in self._values:
            self._values[cache_key] = factory()
        return self._values[cache_key]

    def reset_cache(self):           # clears everything
        self._values.clear()

    def enable(self):                # per-tick invalidation
        PyCallback.PyCallback.Register(self._callback_name,
                                       PyCallback.Phase.PreUpdate,
                                       self.reset_cache, priority=7)

FRAME_CACHE = FrameCache()
FRAME_CACHE.enable()                 # live as soon as the module is imported
```

The decorator resolves a key from the call and memoises the result under it:

| Call shape | Resolved key |
| --- | --- |
| `key` is callable | `key(*args, **kwargs)` |
| `key` is a constant | that constant |
| no args, no kwargs | `"global"` |
| kwargs present | `{"args": args, "kwargs": kwargs}` |
| otherwise | `args` |

`_normalize_key` makes arbitrary values hashable: lists and tuples become
tuples, sets become frozensets, dicts become tuples of pairs, and anything still
unhashable falls back to `id(key)`.

`Player.py` applies it to 14 hot scalar reads — `GetPlayerNumber`,
`GetLoginNumber`, `GetPartyNumber`, `IsPlayerLoaded`, `GetAgentID`, `GetName`,
`GetXY`, `GetTargetID`, `GetObservingID`, `GetAccountName`, `GetAccountEmail`,
`GetMorale`, `GetLevel`, `GetAccountFlags` — and leaves the heavier or rarer
reads uncached.

Properties of the design worth stating plainly: **there is no TTL, no per-entry
invalidation, no size bound and no lock.** Correctness comes entirely from the
per-frame wipe, and the cost model assumes an in-process frame loop where a read
is expensive and a tick is free.

### Decision: the class is Reforged's, and this port is not frame-based

**Resolved: nothing here supplies a tick, because there is no frame to tie one to.**
`@frame_cache` is a Reforged feature of a frame-based environment. The rule is in
[`PORTING_RULES.md`](PORTING_RULES.md); the contract is in `AGENTS.md`.

The dictionary, the key normalisation and the decorator would be a direct port with no
dependency — the only coupling is the invalidation trigger,
`PyCallback.Phase.PreUpdate`. That coupling is decisive:

- **Stealth is not frame-based.** Nothing runs per frame, nothing is throttled by
  frame, and there is no frame boundary to key a memo to. Reads happen on demand, at
  the call site.
- A copy of the decorator would **never be cleared**: there is no frame tick to fire
  its invalidation, so the memo would outlive the thing it describes.
- An uncleared memo of a map-scoped read is a stale-data bug, not a performance
  win. It would also silently defeat the `Map.IsMapReady()` gating, which is
  re-evaluated per read precisely so that a map change is noticed by re-asking the
  client rather than by a timer expiring.

**Not now, not never:** if this port ever gains a frame-driven mode, `FrameCache` is the
class to use — `py4gwcorelib_src/FrameCache.py` as written — and nothing invented here.
Until then ported members carry no `@frame_cache` and no substitute of our own: no TTL,
no refresh timer, no `with py4gw.frame():` block, no caller-driven `cache.reset()`.
Caching is still permitted for large structures whose contents are expensive to
re-read; what is not this port's model is caching *as a frame-throttle*.

Recorded in three places on purpose, because this is the question most likely to
be asked again: `AGENTS.md` (the contract), [`PORTING_RULES.md`](PORTING_RULES.md)
(the rule), and here (the assessment and its history).

## Caching inventory (other layers)

Recorded as reference. The intended Stealth model is now decided: **none of these
layers is ported** — see the decision above. The table is kept because it explains
what each layer was compensating for.

| Layer | File | Shape |
| --- | --- | --- |
| `FrameCache` | `py4gwcorelib_src/FrameCache.py` | singleton dict keyed by `(category, source_lib, function_name, key)`; **no TTL** — a `PyCallback` PreUpdate clears the whole dict every tick |
| `GLOBAL_CACHE` | `GlobalCache/GlobalCache.py` | singleton owning per-domain caches; refresh throttled by `ThrottledTimer`s from 50 ms to 10 s (party/item/camera 150 ms, skillbar 75 ms), forced during map load and cinematics |
| Frame state | `FrameTree/frame.py` | a frame is read at most once per tick; the cached state is retained for up to `BUFFER_TICKS = 5` |
| Native snapshot | `native_src/ShMem/SysShaMem.py` | the DLL publishes a seqlock-protected shared-memory block that Python copies with a 3-retry check |
| JSON | `Skill.py` | `_desc_cache`, loaded once |

Note that these caches compensate for expensive in-process reads. Stealth reads
over `ReadProcessMemory`, where the cost profile is different, so the same
structure should not be copied without measuring.

## There are two caching layers, and Stealth only needs the first

This matters for the "simpler approach" and is easy to mistake for one system.

| Layer | Where | What it does |
| --- | --- | --- |
| **1. `@frame_cache`** | `py4gwcorelib_src/FrameCache.py` | a per-frame memo on the top-level wrapper methods; one flat dict, cleared every tick |
| **2. `GLOBAL_CACHE.*`** | `GlobalCache/*.py` | per-domain **mirrors** of the same wrappers (`CameraCache`, `ItemCache`, `InventoryCache`, `PartyCache`, `QuestCache`, `SkillCache`, `SkillbarCache`, `TradingCache`, `EffectsCache`) with their own throttled refresh at 75-150 ms, and actions routed through `ActionQueueManager` |

Layer 2 is roughly 4,600 lines that re-implement layer 1's API surface plus
throttling and queueing. The mirror exists to batch in-process reads behind a
game-frame tick, and this port has no frame loop to batch against.

**Neither layer is used here, for the same single reason: they are frame-based, and this
port is not.** Layer 2 is a throttled mirror of layer 1, and layer 1's only invalidation
is the frame tick (see the decision above). The caching surface for the port is
therefore **nothing** — the members read on demand. Neither the 4,600-line `GlobalCache`
tree nor the 165-line `FrameCache` is needed for that. If a frame-driven mode ever
arrives, both are Reforged's to use as written.

Note the framing this replaces: an earlier draft of this document concluded that
"layer 1 alone gives the source-visible behaviour — the value is memoised for the
duration of one caller-defined frame and then re-read". That assumed a
caller-defined frame existed to hang the memo on. It does not, and a memo with no
invalidation boundary is not the source's behaviour.

## Player: the pilot candidate

Measured from the source.

| | Count |
| --- | ---: |
| Total methods | 68 |
| `read` | 44 |
| `derive` | 4 |
| `execute` | 20 |
| `write` | 0 |

All methods are `@staticmethod` on a namespace class (`Player.py:14`) — there is
no instance to manage.

**Data provenance is mostly `context`, with one trap.** `PyPlayer() { GetContext(); }`
reads contexts, but three agent identity calls are not equivalent:

| Call | Implementation | Class |
| --- | --- | --- |
| `GW::agent::GetControlledCharacterId()` | `world->playerControlledChar->agent_id` (`agent_methods.cpp:60`) | `context` |
| `GW::agent::GetObservingId()` | `Context::GetObservingId()` -> `*g_player_agent_id_addr`, a pattern-resolved game address (`context_methods.cpp:115`) | `context` |
| `GW::agent::GetTargetId()` | `return g_current_target_id;` — a DLL global set from a `kChangeTarget` UI-message hook (`agent.cpp:60, 163`) | **`capture`** |

The classification was right and the conclusion drawn from it was wrong. `capture` does
not mean "cannot be implemented externally"; it means the value arrives on a message
rather than sitting in a context — and this project now has a hook, an event region and
a registry, so it can listen to the same message the runtime listens to. **Ported and
live-verified**: the client announced target `16` and `Player.GetTargetID()` read `16`
(`docs/PLAYER_PORT.md`). The rest of `GetContext()`
(`player_methods.cpp:141-195`) reads `Context::GetWorldContext`,
`Context::GetCharContext` (`player_email`, `player_uuid`), `world->accountInfo`
(name, wins, losses, rating, qualifier points, rank, tournament points),
`world->morale`, `world->morale_dupe` and `world->player_morale_info` — all
structures Stealth already reads.

**Full Player split (68 methods):** 41 `context`, 4 `computed`, 3 `capture`,
20 `action`.

Not yet ported: `GetChatHistory`, `IsChatHistoryReady` (both read `g_chat_history` /
`g_chat_ready`, DLL globals behind an async fetch — the decode increment). The third
`capture`, `GetTargetID`, is ported; it is the worked example of the class.

## Other wrappers with no execute or write methods

From the method inventory, these classes contain no action code at all, which
makes them candidates after Player:

| Class | Location | Notes |
| --- | --- | --- |
| Pathing geometry (`AABB`, `TrapezoidBSP`, `NavMesh`, `AStar`, `AStarNode`) | `Pathing.py:14, 71, 141, 446, 454` | pure math over `PathingTrapezoid`; no game access |
| `ItemArray` + Filter/Manipulation/Sort | `ItemArray.py:8` | reads only |
| `Skill` + Data/Attribute/Flags/Animations | `Skill.py:6` | 80 read / 6 derive / 0 execute; also fills the 49-field `Skill` declaration gap |
| `ItemArray` cache mirror | `ItemCache.py:609` | reads only |
| `AgentArray` + Manipulation/Sort/Filter | `AgentArray.py:12` | 18 read / 6 derive / 0 execute |
| `Agent` | `Agent.py:13` | 127 read / 21 derive / 0 execute; but its module import registers a `PyCallback` hook |
| `Effect` | `Effect.py:5` | 12 read / 1 derive / 2 execute |

## Two classification caveats from the inventory

1. **`request_*` methods are not plain reads.** `Item.RequestName`,
   `Quest.request_quest_*`, `Player.RequestChatHistory` and similar call native
   asynchronous fetch/decode bindings. They mutate nothing and send no packet,
   but they are native calls whose fetch/decode side is not ported yet, so they
   belong to the `capture` class rather than `read`.
2. **`Party.IsPlayerLoaded` is a no-op stub** (`Party.py:249`, a bare `pass`),
   and 19 `Agent` methods are constant-returning stubs with the logic commented
   out. Those should be declared for parity but must not be presented as working.

## What the project's own contract requires

`docs/DESIGN.md` fixes the migration contract, and the context work followed
it: **declared parity** and **runtime availability** are separate. Every source
class, property, helper and method must exist with its source name; operations
whose mechanism is not ported stay declared and report what they need
instead of returning a value. Nothing is silently dropped.

That contract applies to wrappers unchanged, so a wrapper is migrated when its
whole surface is declared, its `context` and `computed` methods work, and its
`capture` and `action` methods report why they do not.

## Recommended sequence

1. **Resolve the scope question.** Decide whether `SCOPE.md` now includes the
   wrapper layer, and if so record where it sits relative to context parity.
2. **Finish the context layer first.** Wrappers read contexts; a wrapper
   migrated on top of a context with documented gaps inherits those gaps and
   cannot be certified. `CONTEXT_PARITY_AUDIT.md` and
   `PARITY_CERTIFICATION_CHECKLIST.md` define the existing one-at-a-time gate.
3. **Run a provenance audit before choosing a pilot.** For a candidate wrapper,
   trace every method into its native binding and classify it `context`,
   `computed`, `capture`, or `action`. The pilot must have no `capture` methods,
   because a `capture` method needs target-side machinery, which the wrapper port
   has not reached yet.
4. **Then migrate one wrapper at a time**, with the same sign-off gate the
   contexts used.

## Open questions for the owner

1. **Scope**: does the wrapper layer become in scope now, and how is that
   recorded in `SCOPE.md`?
2. **Caching**: **answered** — neither `FrameCache` nor `GlobalCache/*` is
   ported; see the decision above and
   [`PORTING_RULES.md`](PORTING_RULES.md). `GlobalCache/*` is ~4,600 lines with no
   Stealth counterpart, and it is a throttled mirror of a layer that is itself
   not ported.
3. **`capture` methods**: should they keep an explicit not-yet-ported status
   (the current contract), or does the owner want some of the capture work
   taken next?
4. **Pilot choice**: after the provenance audit, which wrapper is accepted
   first.
