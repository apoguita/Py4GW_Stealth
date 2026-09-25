# Porting rules

This project ports Py4GW Reforged and Py4GW_Reforged_Native. It does not design
its own way of doing what they already do.

These rules exist because that line was crossed here: a fabricated readiness
layer (`ReadinessReport`, `read_readiness()`, `evaluate_readiness()`) and a
fabricated `BitmapWords` type were built on top of the source instead of porting
it, and the docs then presented them as the library's contract. Both were deleted.

Read this before adding anything.

---

## The mandate

**Port only what can be ported. Identify what cannot, and record it for later,
for when the capability exists.**

Every source member resolves to exactly one of two outcomes. There is no third.

| Outcome | When | What you write |
| --- | --- | --- |
| **Ported** | the read works from outside `Gw.exe` | the member, source-identical |
| **Refused** | it needs code inside `Gw.exe`, or a capability this project does not have yet | the member, raising `NotImplementedError` naming the missing mechanism, **plus a recorded entry** |

A member is never approximated, softened, wrapped, defaulted, made to "work for
now", or silently left out.

### Why refused members are still declared

Reforged and Reforged Native are complete, working libraries that ship and run in
production. **Stealth is the port, and the port is at an early stage**: contexts
can be loaded and read, and the ported library **reads**: a separate capability
layer, `py4gw/game_thread/`, installs hooks, makes typed calls on the client's own
thread and registers callbacks, all live-verified, and nothing on a ported member's
read path touches it. What is still missing — a call vocabulary and callbacks — is what makes
members refuse today.

**The structure is built complete anyway, and that is deliberate.** Each class is
ported in the source's own shape and nesting *now*, so that when remote execution,
hooks or callbacks are added, the functionality is ported into a slot that already
exists. The alternative — port only what works today and leave the rest out —
means re-cutting the class when the capability arrives, and re-cutting is
redesign. Redesign is how the invented layers got into this project in the first
place.

So a refusal is not a gap to fill with something else, and not a member to be
rediscovered later. It is a placeholder carrying its name, its source line and the
mechanism that blocks it, waiting for the capability.

### The capability limit is temporary, the structure is not

Do not read "read-only" as "this member is impossible". It means *not yet*.
When the capability lands, that member is ported into place like any other — which
is only possible because it was declared in the first place.

## Never

These are absolute. They are the ways the failures below happened.

- **Never optimise.** Line count is not a consideration, and neither is
  repetition. Twenty-one near-identical four-line blocks in the source are the
  specification, not noise to factor out. Factoring them out is "port the
  summary, not the structure". If you catch yourself abstracting across ported
  members, stop.
- **Never use a structure the source does not have.** Not a different nesting, not
  a different placement, not a different call shape, not a different argument
  order. Where the source puts a member is part of the member.
- **Never reach a field through a dynamic name.** No `getattr(obj, "field")`, no
  field-name arguments, no dispatch tables, no `**kwargs` routing. The source's
  field must be written literally inside the member, where a reader and a type
  checker can both see it.
- **Never redesign.** No member the sources do not declare. No re-shaped
  namespace, no renamed parameter, no reordered arguments, no "cleaner" return
  value, no tidier short-circuit.
- **Never add functionality.** Not a helper, not a convenience, not a fallback,
  not a "small" accessor, not a cache, not a gate, not a report object. If the
  sources do not have it, the answer is no.
- **Never add a guard of your own.** Copy the checks the source makes, per member,
  in the source's order. Do not add a readiness gate the source does not have,
  do not add an error swallow or a default the source does not return, and do not
  defer a check the source does make to a "later stage". Added guards look like
  safety and are divergence.
- **Never treat precedence as permission.** An existing helper, an earlier commit,
  or a line in this document blesses nothing. Only Reforged and Reforged Native
  are authority. This list records defects; it does not license them.
- **Never monkey-patch.** Do not correct the source's behaviour, route around it,
  or make it "right". Port what it does. If the client and the source disagree,
  that is a finding to report - not a patch to write.
- **Never offer invented options.** Do not hand the user a menu of designs you
  made up - a TTL, a throttle, a caller-driven reset, a compatibility shim, a
  "middle ground". The choices are always: **port it, or refuse it and record
  it.** Asking the user to choose between two inventions is how a fabricated
  layer gets approved by accident.

## Never substitute a stand-in for an unported source file

**The most expensive mistake in this project so far, recorded so it is not
repeated.**

`Py4GWCoreLib/Context.py` (114 lines) declares the `GWContext` namespace and its
`_GWContextBase`. It was never ported, and every `Map` member calls into it:

```python
current_map_info = GWContext.InstanceInfo().GetMapInfo()
if current_map_info is None:
    return 0
return current_map_info.flags
```

With no ported home for that accessor, the port substituted its own -
`Map._char_context()`, `Map._instance_info_context()`, `Map._map_context()`,
`Map._world_context()`, `Map._area()` - and then collapsed twenty of those members
into `Map._area_value(name)`, a `getattr(area, name)` dispatcher with **no
counterpart in Reforged or Native at all**. An `IsMapReady()` gate was then
invented inside `_area()` to cover reads the source does not guard.

The sequence is the lesson:

```text
unported source file  ->  substituted accessor  ->  generic dispatcher  ->  invention
```

Each step moved further from the source, and the `getattr` was the **last** step,
not the first mistake. `Player._world()` and `Party._party()` are the same
substitution from the same root cause.

**The rule.** When the source calls something that has no ported home, the answer
is to port *that thing* - in the file and on the class where the source puts it.
It is never to write a local stand-in, and never to generalise the stand-in.

So for this case the fix runs backwards along the chain: port `Context.py`
(`_GWContextBase` with `GetPtr`/`GetContext`/`IsValid`, the `GWContext` namespace
with its nested context classes, and `InstanceInfo.GetMapInfo()`), then rewrite the
`Map` members to call what the source calls, then delete `_area`, `_area_value` and
the `_*_context` family. The transcription is direct, because Stealth's context
classes already expose the `get_context()` that `_GWContextBase.GetContext()`
calls.

A guard that exempts private names cannot see any of this. The parity check must
compare **every** name against the source, private ones included, or an invented
helper is reported as an acceptable extra.

## The source is the specification

Reforged and Reforged Native are working, in-production branches. Their behaviour
is the specification, including the parts that look surprising to a reader.

- **Do not call source behaviour a bug, a defect, a crash, or a mistake.** The
  branch ships. You do not have the full picture of why it is written that way.
- If a path looks wrong, the correct output is a short factual note of what the
  code does and the line it is on. Then port it as written.
- **Never ask the user to decide whether the source is right.** That question is
  not open.
- **Never ask the user what the source already answers.** Porting is reading. When
  a member's return value, its default, or its check is written in the source, read
  it there and transcribe it. Do not raise it as a decision, do not reason about
  what it "should" be, and do not ask which value is intended. Reforged and
  Reforged Native are production implementations: they are not hypothetical, and
  you are not designing the system. Framing a source fact as a choice is the same
  error as offering invented options - it hands the user a decision that does not
  exist.
- **Never "correct" it.**

---

## The rule

**Every public member must exist in Reforged Python or in Native, spelled the
same way.** If it is not there, it does not go here.

Corollaries:

- **No new layers.** No façade type, report object, registry, decorator, or
  "accessor" that the sources do not have. If Reforged calls
  `Map.IsMapReady()` before a read, this project calls `Map.IsMapReady()` before
  that read. It does not wrap reads in a gate of its own invention.
- **No new base types.** A helper type may only exist if the sources declare the
  corresponding type (`TargetStruct`, the native `InstanceInfo`, the
  `MISSION_BITMAP_ENTRIES` constants). "It would be convenient" is not a source.
- **Port the structure, not a summary of it.** Same nesting, same method order,
  same short-circuits, same return values, same defaults.
  `Map.IsObservingMatch()` returns `True` when the map data is not loaded because
  the source's first short-circuit says so - not because that is the tidier
  answer. Nested classes are nested here too: `Map.MissionMap.MapProjection` is
  not a top-level class.
- **Native and Reforged are the sources of truth; `external/GwAu3` is a
  reference project.** Where Native and Reforged Python disagree, Native wins -
  for example `PickHighest` rather than `max`, and no `750` warm-up.

## Where each member may come from

| Source | May be ported | Example |
| --- | --- | --- |
| Reforged Python (`Py4GWCoreLib/`) | yes, as written | `Map.IsMapReady`, `Party.IsPlayerLoaded`, `Player.GetMissionsCompleted` |
| Native (`Py4GW_Reforged_Native/src/`) | yes, as written | `PyPlayer::GetIsPlayerLoaded`, `PickHighest`, `unlocked_maps`, `mouse_over_id` |
| Shared-memory and UI-widget modules | **no** - out of scope | `AccountStruct`, `AgentPartyStruct`, `GlobalCache/*` |
| `external/GwAu3` | **no** - reference only | - |
| Anything else | **no** | - |

## What a member must carry

1. **The source location** in the docstring - file and line, or the enum and
   constant, so a reviewer can check it in one step.
2. **The provenance class** where it is not obvious: `context` (readable game
   memory), `capture` (DLL-owned state that only exists with code in the
   client), `computed`, or `action`.
3. **A refusal with a reason** if it cannot work externally: present the member,
   raise `NotImplementedError` naming the missing mechanism, and never return a
   plausible wrong value.

---

## Recording a refusal

"Identify what cannot be ported for later, for when we have capabilities" only
works if the list actually exists. There are two kinds, and both already have a
home. **Do not create a third.**

| Kind | Meaning | Recorded in |
| --- | --- | --- |
| **Member refusal** | this one member cannot work externally | that module's own port doc - e.g. [`PARTY_PORT.md`](PARTY_PORT.md), [`PLAYER_PORT.md`](PLAYER_PORT.md) |
| **Capability gap** | target-side code, writes, patches or hooks that the member needs and the project does not have yet | [`DEFERRED_INJECTION.md`](DEFERRED_INJECTION.md) - the existing, maintained register |

Rules:

- Record it in the same change that adds the refused member. Never later.
- Name the mechanism concretely and cite the source that needs it. "Requires
  in-process code" is not an entry; "`PyImGui.get_io()`, read by
  `Frame.is_mouse_over()`" is.
- **Verify that the capability is genuinely missing before you claim it is.**
  Several members that a reader might assume need target-side code are already
  reachable read-only here - the two map contexts are the worked example, live
  verified through the frame array and recorded as resolved in
  [`DEFERRED_INJECTION.md`](DEFERRED_INJECTION.md). Read that table before
  adding a row to it.
- State what the capability *is*, never a workaround for it. A workaround is a
  monkey patch.
- Delete the entry the moment the member is ported.

---

## There is no dispatcher: every read is lazy

Reforged is driven by a **perpetual per-frame loop**. Its callbacks and
dispatchers refresh state on every frame: `@frame_cache` clears its memo each tick,
each context facade registers a `PyCallback` that refreshes its cached pointer and
context, and `GLOBAL_CACHE` mirrors refresh on throttled timers. The wrapper code
then reads caches that are already warm.

**Stealth has no loop and no dispatcher.** Nothing runs unless the caller calls
something. There is no background refresh, no tick, and nothing to dispatch to.
Every read is therefore **lazy**: it happens on demand, at the point of use, inside
the member that needs the value.

This one difference explains every caching and refresh decision here, and it is why
none of them is an open question:

| Reforged mechanism | What Stealth does instead | Where |
| --- | --- | --- |
| `@frame_cache` memo, cleared by `PyCallback.Phase.PreUpdate` | dropped; the member reads when it is called | this document, below |
| context facades refreshed by `PyCallback.Context.Draw` | `GetContext` refreshes lazily through the source's own `_update_ptr`, then returns the context | `py4gw/context/gw_context.py` |
| `GLOBAL_CACHE.*` throttled mirrors (75-150 ms) | not ported; there is no tick to throttle against | [`WRAPPER_MIGRATION_ASSESSMENT.md`](WRAPPER_MIGRATION_ASSESSMENT.md) |

Never put in place of laziness: a TTL, a refresh timer, a throttle, a background
thread, or a cache with no invalidation. Each one either invents a dispatcher
Stealth does not have, or pins map-scoped data for the life of the process.

## Caching: `@frame_cache` is deliberately not ported

**Decided and closed. Do not re-open this, and do not ask again.**

Reforged decorates its wrapper methods with
`@frame_cache(category=..., source_lib=...)`, which memoises the call for the
duration of **one game frame**. Its invalidation is a single in-process tick:

```python
# py4gwcorelib_src/FrameCache.py
def enable(self):
    PyCallback.PyCallback.Register(self._callback_name,
                                   PyCallback.Phase.PreUpdate,
                                   self.reset_cache, priority=7)
```

There is no TTL, no per-entry invalidation, no size bound and no lock. All of the
correctness comes from that per-frame wipe.

Stealth is a different execution model, and that is why the decorator is dropped
rather than adapted:

| | Reforged | Stealth |
| --- | --- | --- |
| When does code run? | every game frame, from an in-process callback | only when the caller asks |
| Read cost | an in-process field access | a `ReadProcessMemory` call |
| What invalidates a memo? | the per-frame tick | nothing - there is no tick |

A verbatim port would therefore **never invalidate**. The first call would pin a
map-scoped value for the life of the process, which is precisely the stale data
`Map.IsMapReady()` exists to prevent. Dropping the decorator is not a shortcut;
it is the only behaviour that matches the source's observable result.

- **Drop `@frame_cache`.** The member reads the client when it is called.
- **Do not add a replacement tick.** No TTL, no throttle, no refresh timer, no
  `with py4gw.frame():` block, no caller-driven `cache.reset()` protocol. Those
  were once listed as candidate designs in
  [`WRAPPER_MIGRATION_ASSESSMENT.md`](WRAPPER_MIGRATION_ASSESSMENT.md); the answer
  is none of them, and that document now records the decision.
- **Do not add a cache in the name of parity.** Parity is observable behaviour,
  and a memo that never clears is not parity.
- **Caching large structures is still allowed.** Storing an expensive structure
  that the caller re-reads often is a cost decision the caller is entitled to
  make. What is forbidden is caching *as a frame-throttle*.
- The rule from [`READINESS_GATE.md`](READINESS_GATE.md) is unchanged and still
  governs any cache that is added: **cache what the pattern scan produced, because
  that is stable; never cache a dereferenced pointer, because that is map-scoped.**

Expect this on every ported file. Reforged decorates heavily: `Map` carries
`@frame_cache` on **36 of its 178 members**, and `Player` on 14 hot scalar reads.

---

## Before adding anything

1. Grep both source trees for the member name. No hit means no member.
2. If it exists in Native but not Reforged's Python (or the reverse), say which
   one you are following and why.
3. If it needs a helper, check the source does not already have one.
4. Decide the outcome: **ported** or **refused + register row**. If you are
   weighing a third option, you are designing, and the answer is no.
5. If you are about to write a word like "layer", "façade", "accessor",
   "registry", "unified", "abstraction", "shim", or "for now", stop and re-read
   this file.

## Auditing what is already here

The port is not finished and the audit is not complete. To continue it, diff
each accessor class against its source and delete every member that is not in
one of them:

```powershell
# members of the port
Select-String -Path py4gw/player.py -Pattern '^    def '

# the same surface in the source
Select-String -Path C:\Users\Apo\Py4GW_Reforged\Py4GWCoreLib\Player.py -Pattern '^    def '
Select-String -Path C:\Users\Apo\Py4GW_Reforged_Native\src\GW\player\player_bindings.cpp -Pattern 'def_readonly|\.def\('
```

## Open defects (the register)

**Every entry here is work to remove, not a licence.** The list must shrink. An
entry does not become correct by being old, and no new entry may be added without
an explicit instruction from the user.

| Defect | Why it is a defect | Fix |
| --- | --- | --- |
| `py4gw/player.py` `_world`, `_party_players`, `_agent_by_id`, `_uuid_of`, `_faction`, `_bitmap_words` | stand-ins for `GWContext.X.GetContext()` | call `GWContext`, then delete |
| `py4gw/party.py` `_party`, `_is_party_connected` | same substitution, same root cause | same fix |

Cleared so far:

- **`Py4GWCoreLib/Context.py` is ported** — `py4gw/context/gw_context.py` carries
  `_GWContextBase` (`GetPtr` / `GetContext` / `IsValid`), the `GWContext` namespace
  with all fifteen nested context classes, and `InstanceInfo.GetMapInfo()`. It was
  the gap every `Map` member reached through. One line is not literal: the source
  fills each facade cache from a `PyCallback.Context.Draw` callback, so `GetContext`
  calls the source's own `_update_ptr` first. Without it the cache is never filled
  and `GetContext` would answer `None` forever, which is not what the source does.
- `py4gw/map.py` `_area_value` — **deleted**. A `getattr(area, name)` dispatcher
  with no counterpart in either source project.
- `py4gw/map.py` `_area`, `_char_context`, `_instance_info_context`, `_map_context`,
  `_world_context` — **deleted**. `Map` now has **no** member the source does not
  declare; every call site reads what the source reads, including
  `GWContext.InstanceInfo().GetMapInfo()`.
- Added guards of mine — **removed**: the `IsMapReady()` gate inside `_area` that
  the source does not have, the `try`/`except` blocks in `GetMapID` and
  `IsInCinematic`, and eight `int()` casts the source does not make.
- `py4gw/map.py` `GetMapID` — the source's `if not Map.IsMapReady(): return 0`
  (`Map.py:122`) is restored.
- Three members returned the wrong value on the unset path because `_area_value`
  defaulted to `0`. The source returns `255` for `GetCampaign` and `GetContinent`,
  and `20` for `GetRegionType`.

Recorded so they are **not** mistaken for defects:

- `py4gw/client.py` `require_client()` — an addition the user requested explicitly,
  replacing a check each accessor class had copied.
- `py4gw/player.py` `GetUnlockedMaps`, `GetMouseOverID`, `IsAgentIDValid` — declared
  in native `PyPlayer`; ported from there.
- The `_disabled` refusal builder in `py4gw/map.py`, `py4gw/player.py` and
  `py4gw/party.py` — the mechanism that implements this document's own refusal
  contract ("present the member, raise `NotImplementedError` naming the missing
  mechanism"). It is sanctioned infrastructure, not field access.

## State of the ports

- `py4gw/party.py` — complete. All five namespaces are present, and
  `tests/test_party_offline.py` fails if a member is dropped. Four members return a
  constant because the source cannot produce anything else; see
  [`PARTY_PORT.md`](PARTY_PORT.md).
- `py4gw/player.py` — 70 Reforged members, 46 working and 24 refusing; see
  [`PLAYER_PORT.md`](PLAYER_PORT.md).
- `py4gw/map.py` — the full 178-member surface is declared and nested the way
  `Map.py` nests it, but only 44 members read the client so far; the other 134
  refuse naming their mechanism. [`MAP_PORT.md`](MAP_PORT.md) is the staged plan
  and the progress record.
- `Py4GWCoreLib/Context.py` — **not ported**, which is the root cause of the
  substitution defects in the register above.
