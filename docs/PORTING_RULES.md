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

**Port everything.** Reforged and Reforged Native are complete, working, in-production
code, and this project's job is to reproduce them member for member. The default
outcome for a source member is that it **works**.

| Outcome | When | What you write |
| --- | --- | --- |
| **Ported** | always, unless the exception below applies | the member, source-identical |
| **Not yet ported** | while the code that makes it work is still being written | the member, raising `NotImplementedError` naming exactly what it still needs — and that thing is the **next work item**, not a resting state |

A member is never approximated, softened, wrapped, defaulted, made to "work for
now", or silently left out. It is also never left doing nothing when the source does
something.

**Nothing here is blocked, deferred or unportable, and the documentation does not say
it is.** This rule and the docs around it were written when the project could not
execute anything inside the client. That is no longer true, so the old language is gone:

- `py4gw/game_thread/` places code in the client, hooks its own functions, calls them on
  the game's own thread, registers callbacks, emits machine code from Python, and carries
  a shared block with a command queue, an event ring and room for data. Connecting is
  live-verified and restores the client's bytes on close.
- Everything the sources reach, this project can now reach. A call form it does not have,
  a string region it has not written, a callback stub, a table it cannot yet resolve —
  those are **unfinished work with names**, and they are built, not documented as
  limitations.
- **A no-op is very hard to justify.** If a member does nothing where the source does
  something, the justification has to be written down, specific, and rare. Two members
  qualify today, and both have the same cause: they return or consume an object the
  injected runtime owns in-process (`Player.player_instance`,
  `Dialog._call_native_dialog_method`). That is a documented divergence of those two
  members — no stand-in is ever returned in place of the object — and it is not a pattern
  to copy for anything else.

---

## Full class ports only

**The unit of work is the class, not the member.** When a class is migrated, it is
migrated **whole** — every member of its source surface working — in one pass. Not
"the part the caller I am writing touches". Not "the read half now, the rest later".

This is a directive from the project owner, stated repeatedly and violated
repeatedly:

> *"I do not want partial migrations or ports. If I migrate a class I expect a FULL
> migration, not just some features."*
>
> *"If the dialog needs the dialog class, we migrate the dialog class; if the dialog
> class needs another class, we migrate such classes too."*

### What that changes in practice

- **A dependency is part of the task, not a follow-up.** If a member needs another
  class, a resolver, a call form, a stub, a block region or a table, **build that
  thing and finish the member** — in the same change. Cascades are ported as they are
  reached. Leaving a dependency for a later pass is the defect this rule exists to stop.
- **Do not stop at the first member that needs something.** Reaching a member that
  needs a capability is the signal to build the capability, not to move on without it.
- **Nothing here is blocked.** If a member needs something that does not exist yet,
  that is work with a name — go and build it. There is no class of member that cannot
  be reached, and there is no list of unportable features.
- **Do not port by call site.** Working outward from one caller — "port what this
  function uses" — is how a class ends up half present, and it costs *more* than
  porting the class: every later member re-opens the same missing mechanism.
- **The capability layer is not a reason to leave a class undone.** `py4gw/game_thread/`
  exists precisely so a member that needs code in the client can be ported. When a
  class needs a form the layer does not have (a string argument, a return value, a
  callback stub, a text region), the layer is extended and the class is finished.

### While a member is not ported yet

The code that exists today still has members that raise, because the work is in
progress. That is the whole of it — an interim state, not a category of member:

| | Means | How it is written |
| --- | --- | --- |
| **Works** | the member does what the source does | the member, source-identical |
| **Not yet ported** | the member is declared in the source's shape and raises naming exactly what it still needs | the class is **INCOMPLETE** and the thing it needs is on its remaining list, as the next work item |
| **Reports a divergence** | the source returns or consumes an object the injected runtime owns in-process | the member says so plainly, and no stand-in is returned in its place. `Player.player_instance`, `Dialog._call_native_dialog_method` |

**Nothing is reported as blocked, deferred or unportable.** The remaining list is a
queue: `py4gw/game_thread/` already emits machine code from Python, so a
value-returning call, a callback stub, a string or text region are work, not boundaries.

**Two habits follow from this:**

- **Report outstanding work as a queue with names** — "next: the decode; then the
  journals; then `is_dialog_active`" — never as a list of things that cannot be done.
- **The loud failure stays while the work is in progress**: a member that cannot produce
  a correct value yet must raise and name what it needs rather than return a wrong
  number. That is a correctness rule for the interval, not a resting state.

### Every class carries a verdict

The class port map states, per class, one of two words:

| Verdict | Means |
| --- | --- |
| **FULL** | every member of the source surface works |
| **INCOMPLETE** | the class is declared and the members still to port are named, with what each one needs |

- **Never describe an INCOMPLETE class as ported.** Not in a commit message, not in a
  doc, not in a summary, not in conversation. "Ported" means FULL.
- The verdict is updated in the same change that moves the class, so the map cannot
  drift from the code.
- The remaining list is the plan: the capabilities named there are the work, and they
  are taken in dependency order until the class is FULL.

### Why the whole surface is declared up front

Reforged and Reforged Native are complete, working libraries that ship and run in
production. **Stealth is the port**, and the capability layer it needed now exists:
`py4gw/game_thread/` installs hooks, makes typed calls on the client's own thread and
registers callbacks, all live-verified.

**The structure is built complete, and that is deliberate.** Each class is ported in the
source's own shape and nesting, so that a member's own code goes into a slot that already
exists. The alternative — declare only the members that work today and add the rest as
they come — means re-cutting the class later, and re-cutting is redesign. Redesign is how
the invented layers got into this project in the first place.

A member that raises today therefore carries three things and waits for nothing: its
name, its source line, and the exact thing it still needs — which is the next piece of
work, in the same file, with nothing invented in the meantime.

### The capability layer removes the old obstacles

Do not read an old note about "read-only" or "external only" as this member being
unreachable. It meant *not yet*, and the "yet" has arrived: hooks, typed calls on the
game thread, callbacks, emitted stubs and a shared block with room for data.

**And "not yet" is not a resting place.** The capability is built as part of the class's
own migration, so the class reaches **FULL** in one pass instead of being revisited
member by member.

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
  "middle ground". The choices are always: **port it as the source writes it, or
  write the member so it names what it still needs.** Asking the user to choose
  between two inventions is how a fabricated layer gets approved by accident.

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
| Shared-memory and UI-widget modules | their game-side members are read, and the game-side data is ported | `AccountStruct`, `AgentPartyStruct`, `GlobalCache/*` |
| `external/GwAu3` | **no** - reference only | - |
| Anything else | **no** | - |

## What a member must carry

1. **The source location** in the docstring - file and line, or the enum and
   constant, so a reviewer can check it in one step.
2. **The provenance class** where it is not obvious: `context` (readable game
   memory), `capture` (state that arrives through the capability layer), `computed`,
   or `action`.
3. **What it still needs, if it is not ported yet**: present the member, raise
   `NotImplementedError` naming exactly that, and never return a plausible wrong
   value. The thing it names is the next work item.

---

## Recording outstanding work

Every class's remaining work has a home, and the row is deleted the moment the
member is ported. **Do not create a second register.** Two kinds:

| Kind | Meaning | Recorded in |
| --- | --- | --- |
| **A member not yet ported** | this one member still needs code that is not written | that module's own port doc - e.g. [`PARTY_PORT.md`](PARTY_PORT.md), [`PLAYER_PORT.md`](PLAYER_PORT.md), [`DIALOG_PORT.md`](DIALOG_PORT.md) |
| **Target-side work** | code, writes, patches, hooks or block regions that the member needs placed in the client | [`TARGET_SIDE_WORK.md`](TARGET_SIDE_WORK.md) - the existing, maintained register |

Rules:

- Record it in the same change that adds the member. Never later.
- Name the thing concretely and cite the source that needs it. "Requires
  in-process code" is not an entry; "`PyImGui.get_io()`, read by
  `Frame.is_mouse_over()`" is.
- **Verify that the capability is genuinely missing before you claim it is.**
  Several members a reader might assume need target-side machinery are already
  reachable read-only here - the two map contexts are the worked example, live
  verified through the frame array and recorded as resolved in
  [`TARGET_SIDE_WORK.md`](TARGET_SIDE_WORK.md). Read that table before
  adding a row to it.
- State what the capability *is*, never a workaround for it. A workaround is a
  monkey patch.
- Take the entries in dependency order: the one that unblocks the most members is
  next, and the register is expected to shrink to empty.

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

## Caching: `@frame_cache` is Reforged's, and this port is not frame-based

`@frame_cache` is a Reforged feature, and Reforged is a frame-based environment.
It decorates its wrapper methods with `@frame_cache(category=..., source_lib=...)`,
which memoises the call for the duration of **one game frame**. Its invalidation is a
single in-process tick:

```python
# py4gwcorelib_src/FrameCache.py
def enable(self):
    PyCallback.PyCallback.Register(self._callback_name,
                                   PyCallback.Phase.PreUpdate,
                                   self.reset_cache, priority=7)
```

There is no TTL, no per-entry invalidation, no size bound and no lock. All of the
correctness comes from that per-frame wipe.

**Stealth is not frame-based, and cannot throttle by frame:**

| | Reforged | Stealth |
| --- | --- | --- |
| When does code run? | every game frame, from an in-process callback | only when the caller asks |
| Read cost | an in-process field access | a `ReadProcessMemory` call |
| What invalidates a memo? | the per-frame tick | nothing — there is no frame to key it to |

So the decorator is not used here — not because it is wrong, but because the execution
model it depends on is not this one. A copy of it would **never invalidate**: the first
call would pin a map-scoped value for the life of the process, which is precisely the
stale data `Map.IsMapReady()` exists to prevent. Reading when the member is called is not
a shortcut; it is the only behaviour that matches the source's observable result.

**If this port ever gains a frame-driven mode, `@frame_cache` is what gets used — the
source's class, as the source writes it — and nothing written here.** Until then:

- **The member reads the client when it is called.**
- **Do not stand in a throttle of our own.** No TTL, no refresh timer, no
  `with py4gw.frame():` block, no caller-driven `cache.reset()` protocol — none of those
  is this port's model, and none of them is a throttle by frame, which is the only
  invalidation the source's memo has.
- **Do not add a cache in the name of parity.** Parity is observable behaviour,
  and a memo that never clears is not parity.
- **Caching large structures is still allowed.** Storing an expensive structure
  that the caller re-reads often is a cost decision the caller is entitled to
  make. What is not this port's model is caching *as a frame-throttle*.
- The rule from [`READINESS_GATE.md`](READINESS_GATE.md) is unchanged and still
  governs any cache that is added: **cache what the pattern scan produced, because
  that is stable; never cache a dereferenced pointer, because that is map-scoped.**

Expect this on every ported file. Reforged decorates heavily: `Map` carries
`@frame_cache` on **36 of its 178 members**, and `Player` on 14 hot scalar reads.

---

## Inventing a method is forbidden

**There is no third option between "port it as the source writes it" and "write it so it names
exactly what it still needs".** Inventing a solution is a violation of this project, not a
judgement call: the sources are explicit about how every member works, and the owner's standing
instruction is to stay as true to them as possible. Something that works by another route is
still the wrong answer — the next member, the next build and the next client are measured against
the source, and a port that reaches the same outcome another way will not match.

### The three questions, in the change itself

Every behavioural change names, in the code or in the commit that carries it:

1. **Which source line does this?** File and lines — `dialog.cpp:646-708`. No line means there is
   nothing to port and nothing to write.
2. **What does the source do it *with*?** The same call, the same arguments in the same order, the
   same short-circuits, the same caps, the same return values. The *mechanism*, not the outcome.
3. **What is being added that the source does not have?** Almost always: nothing. When it is
   something, it is a divergence — a register row in the class's port doc, with the work to close
   it — and never a quiet addition to the code.

If a member appears to need something the source does not have, **stop and write it down**. The
member's name, the lines that were read, and what is missing. That is the finding, and the missing
thing becomes the work item. Building a different method that happens to produce the same value is
the failure this section exists to stop.

### The worked failures, from this project's own log

Each of these was invented here, each was wrong, and each cost live runs, client restarts and the
owner's time:

| invented | the source's own method | cost |
| --- | --- | --- |
| A host-side render of dialog text with the game's string table (Route A inside `dialog.py`), plus a string-table load to feed it | `SafeAsyncDecodeStr(req->encoded, OnDialogBodyDecoded, req)` — hand the string to the client, take the text from its callback (`dialog.cpp:885`, `995-1054`) | weeks of detours; the ported protocol worked on its first live attempt |
| A deferred "complete the text at the next point of use" queue, standing in for a callback loop | the client's callback *is* the completion; nothing polls | a substitute for a mechanism that already existed |
| Reading a button's caption from `TextLabelFrame` labels via `frame_array.decoded_label` | the dialog module touches frames **once**, for `IsDialogActive()` (`dialog.cpp:1666-1683`); captions come from the label decode or the catalog (`1632-1664`) | a wrong answer presented as a reading, and a correction from the owner |
| Reading the announced label pointer at a moment the port chose | `DupWideStringSafe(info->message)`, where native reads it (`dialog.cpp:639`) | a string the client's own parser asserts on — a client crash |
| A validity check written here | `SafeIsValidEncStr` → the source's own `EncStrValidate` (`ui_methods.cpp:260-362`) | an approximation that disagreed with the client |
| A `ret 8` epilogue taken from the observer's shape | `DecodeStr_Callback` is `void(__cdecl*)(...)` (`ui.h:299`) — the caller cleans the stack | stack corruption in the client |

### What a reviewer checks

1. `git diff` — for each behavioural line, ask **"which source line is this?"** If the author
   cannot name file and lines, the change is rejected on sight.
2. Grep both source trees for the function being ported. A helper written here that the source
   already has is a finding in itself.
3. Compare the *sequence*: the same order, the same early returns, the same caps and bounds. A
   check the source does not make, or omits, is a divergence at best.
4. Any divergence must already be in a register row. A divergence discovered in review and not in
   the register means the register is stale, and that is a defect of its own.

## Before adding anything

1. Grep both source trees for the member name. No hit means no member.
2. If it exists in Native but not Reforged's Python (or the reverse), say which
   one you are following and why.
3. If it needs a helper, check the source does not already have one.
4. Decide the outcome: **ported**, or **not yet ported + register row** naming what it
   still needs. If you are weighing a third option, you are designing, and the answer
   is no.
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
- The `_unported` builder-message mechanism in `py4gw/map.py`, `py4gw/player.py` and
  `py4gw/party.py` — the interim mechanism that implements this document's own
  contract ("present the member, raise `NotImplementedError` naming what it still
  needs"). It is sanctioned infrastructure, not field access, and the members that use
  it are the work queue.

## State of the ports

- `py4gw/party.py` — the five namespaces are present, and
  `tests/test_party_offline.py` fails if a member is dropped. Four members return a
  constant because the source cannot produce anything else; the 30 action members are
  the remaining work. See [`PARTY_PORT.md`](PARTY_PORT.md).
- `py4gw/player.py` — 71 Reforged members: 51 reading, 18 acting through the
  game-thread call path, and 1 raising — `player_instance`, the documented divergence
  (a `PyPlayer` binding object; this project has no player object). Every other member of
  the class works, including the chat history (`RequestChatHistory`/`IsChatHistoryReady`/
  `GetChatHistory`, kept warm by the connection's watched log) and `GetInstanceUptime`
  (`py4gw/ui/preferences.py` ports native's `GW::ui::GetFrameLimit`); see
  [`PLAYER_PORT.md`](PLAYER_PORT.md).
- `py4gw/ui/preferences.py` — the port of native's preference and frame-limit reads
  (`ui_methods.cpp:364-367`, `1432-1436`, `1833-1858`): `PrefsInitialised`, `GetPreference`,
  `get_command_line_number`, `get_renderer_value` and `GetFrameLimit`, which is what
  `Agent.GetInstanceUptime` divides by and therefore what `Player.GetInstanceUptime` needed.
- `py4gw/py4gwcorelib_src/utils.py` — the port of `py4gwcorelib_src/Utils.py` with its `Color`
  (`color.py`): 37 of its 40 members work, and the three that do not name the surface each one needs
  (the client's ImGui text measure, and `Map.MissionMap.GetScale` behind the two unit conversions —
  both target-side captures, not porting work). It landed to unblock `Player.BuySkill`,
  `Player.UnlockBalthazarSkill`, `Agent.GetEnergyPips` and `Agent.GetHealthPips`; see
  [`UTILS_PORT.md`](UTILS_PORT.md).
- `py4gw/skill.py` — the port of `Py4GWCoreLib/Skill.py` over the client's skill constant table
  (`py4gw/context/skill_context.py`) and native's generated name table (`py4gw/skill_names.py`):
  79 of its 87 members work, and the eight that do not name the data file or enum module each one
  needs (Reforged's bundled `skill_descriptions.json`, `Region_enums.CampaignName`,
  `Texture_enums.SkillTextureMap`). It completed `Utils.BalthazarSkillIdToDialogId` and therefore
  `Player.UnlockBalthazarSkill`; see [`SKILL_PORT.md`](SKILL_PORT.md).
- `py4gw/skillbar.py` — the port of `Py4GWCoreLib/Skillbar.py` over native's `PySkillbar` binding and
  the ported world context's skillbar array, with the client's current tooltip read added beside it
  (`py4gw/ui/tooltip.py`): 12 of its 18 members work — every read, plus `ChangeHeroSecondary` — and
  the six that do not name what they need (the control-action mechanism for the three skill presses,
  native's `DecodeSkillTemplate` for the two loaders, and the skill timer for `get_recharge`). It
  completed `Utils.GenerateSkillbarTemplate`; see [`SKILLBAR_PORT.md`](SKILLBAR_PORT.md).
- `py4gw/map.py` — the full 178-member surface is declared and nested the way
  `Map.py` nests it, with 45 members reading the client so far and 133 still to port
  (projections, pathing reads, frame lookup).
  [`MAP_PORT.md`](MAP_PORT.md) is the staged plan and the progress record.
- `py4gw/dialog.py` — Reforged's 10-member `Dialog.py` plus the native `PyDialog`
  surface behind it: 32 statics and 6 records, **all 32 answering** — nothing refuses, the only
  refusal in the module being the facade helper that would reach a binding object by dynamic
  name, which is a documented divergence and not a member. The text decode, the journals and
  the frame-by-hash read are all ported and live-verified. What it still cannot read on this
  build is named in the class's row of [`CLASS_PORT_MAP.md`](CLASS_PORT_MAP.md), and the
  per-member record is [`DIALOG_PORT.md`](DIALOG_PORT.md).
- `Py4GWCoreLib/Context.py` — **ported** (`py4gw/context/gw_context.py`); the
  substitution defects it caused are listed in the register above as cleared.
