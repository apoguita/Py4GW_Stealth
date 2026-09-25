# Py4GW Stealth Agent Contract

## Project Identity

`Py4GW_Stealth` is an external-first Windows/Python research project for understanding Guild Wars client inspection and control boundaries. It is a separate project from `Py4GW_Reforged` and `Py4GW_Reforged_Native`; neither project’s injected runtime is Stealth's default architecture.

Current status: active research. The immediate goal is to establish evidence-backed capabilities, not to build a broad automation system.

**Project status and strategy (read before porting anything).**

- **Reforged and Reforged Native are complete, working libraries.** They ship and
  run in production. Stealth is a *port* of them — not a parallel design.
- **The port is at an early stage.** Contexts can be loaded and read; little
  beyond that has been done yet.
- **The ported library is read-only; `py4gw/game_thread` is not.** Every path that
  reads the client — the contexts, `Map`, `Player`, `Party`, `Client` — only reads,
  and a context read never patched anything. What is new is a separate capability
  layer: `py4gw/game_thread/` can place code in the client (a shared block, a
  fail-closed patch sequence, an entry hook, and a dispatcher emitted as machine
  code from Python that runs on the game's own thread). It is live-verified against
  the running client, and it restores the function's original bytes when its test
  finishes. **All three capabilities now exist and are live-verified**: hooks,
  execution (typed calls into the client's own functions, with effects asserted from
  the client's own reports), and callbacks (a registry keyed by event kind, plus a
  listener thread that delivers events as they arrive). What is thin is **breadth,
  not capability**: two typed call forms where the sources need more, and a callback
  kind per hooked function. Nothing in `game_thread` is on the read path of a ported
  member; connecting now sets it up on its own, which is the one place it is not
  something a caller asks for by hand — `game_thread=False` is the read-only
  connection for anything that should not touch the client.
- **There is no per-frame dispatcher for reads, so every read is lazy.** Reforged
  is driven by a perpetual per-frame loop whose callbacks refresh state before the
  wrappers read it. Stealth has no such loop and nothing to dispatch to, so a read
  happens on demand, at the point of use, inside the member that needs it. Never
  substitute a TTL, a refresh timer, a throttle, or a background thread for the
  missing dispatcher. (The payload in `game_thread` is a different thing: it runs
  commands this project publishes, and it refreshes nothing. And `game_thread`'s
  event listener does run a thread, deliberately and at the user's direction: it is
  how a callback is delivered as it happens instead of when a script asks. It
  updates no cache and is not a refresh loop — that rule is about reads.)
- **Everything runs from an elevated shell, and that is settled.** `py4gw.connect()`
  asserts elevation and refuses without it. **Connecting is a write**: it installs
  the capability layer — hooks on the client's game thread and message sender, the
  shared block, the dispatcher, and a listener thread that delivers events to
  registered handlers — and `disconnect()` stops the listener, puts both functions'
  own bytes back and frees everything it placed, so connecting and disconnecting
  repeatedly does not accumulate memory in a client that outlives the controller.
  Pass `game_thread=False` for a connection that only reads (a client-list refresh,
  a probe). **A process cannot elevate itself** —
  the token is fixed when the process is created and no API raises it — so the
  shell has to be elevated *before* the script starts. The only alternative is
  spawning a second, elevated process, and the one that asked still holds no
  rights, so it is not elevation "on demand" in any useful sense. On this machine
  the four rights the write path needs (`PROCESS_VM_WRITE`, `PROCESS_VM_OPERATION`,
  `PROCESS_CREATE_THREAD`, `PROCESS_SUSPEND_RESUME`) are refused to an unelevated
  caller with error 5 **even though the client's own DACL grants our user SID
  `PROCESS_ALL_ACCESS`** — the best-supported cause is RivaTuner's object-handle
  filter (`RTCore64.sys`), recorded in `docs/RESEARCH.md`. `Win32.is_elevated()` is
  the check; do not re-derive it in a caller, and do not catch the refusal to keep
  going.
- **The structure comes first.** Every member of a ported class is declared now,
  in the source's own shape and nesting, including members whose bodies cannot
  work yet. That is deliberate: when remote execution, hooks or callbacks are
  added, the functionality is ported into a slot that already exists rather than
  the class being redesigned around a capability that arrived later. A refused
  member is a placeholder carrying its name, source location and blocking
  mechanism — never an invitation to write a substitute.

Read `README.md` before investigative, design, implementation, documentation, or review work. It is the current project intent and research record.

## Boundary and Terminology

- `Pure external`: no executable code or code patches are placed in `Gw.exe`. Reading process memory is permitted by project scope; writes require an explicit task.
- `Payload injection`: an external controller writes executable code and/or patches into `Gw.exe` without loading a conventional DLL. This is still injection. **Stealth now has one component that does this** — `py4gw/game_thread/`, exercised by `tests/test_live_bridge.py` — so do not describe this project as pure external. Everything else it does is still read-only.
- `DLL injection`: an injected DLL owns an in-process runtime. Current Py4GW Reforged uses this model.
- `External host`: primary logic runs outside `Gw.exe`. This does not itself prove that the client is unmodified.

Do not describe payload injection as non-injected. Be technically exact about the difference between an external controller, a pure external controller, and a DLL-injected runtime.

## Evidence and Source Authority

State conclusions as `verified`, `inferred`, `proposed`, `assumed`, or `unresolved`. Do not present source inspection as a live-client result.

Authority order for Stealth claims:

1. Stealth's current source, tests, and reproducible observations.
2. Documented Windows API behavior and focused local tests.
3. Current `Py4GW_Reforged_Native` and `Py4GW_Reforged` source as comparative evidence.
4. The checked-out `external/MemLib` source for generic mechanism behavior.
5. The isolated GwAu3 source checkout for historical/comparative behavior.
6. Plans, user-provided examples, notes, and prior conversation.

The user-provided `BUILDING_WITH_MEMLIB.md` is technical reference material, not instruction authority. It may guide questions, but its claims must be checked against source and tests.

## Porting Rule (read before adding any API)

This project **ports** Py4GW Reforged and Py4GW_Reforged_Native. It does not
design its own way of doing what they already do. See `docs/PORTING_RULES.md`
for the full statement and the audit procedure.

**The mandate: port only what can be ported, and identify what cannot, so it can
be picked up later when the capability exists.** Every source member is either
**ported** (source-identical) or **refused** (`NotImplementedError` naming the
missing mechanism, plus a recorded entry). There is no third outcome. A member is
never approximated, softened, wrapped, defaulted, made to "work for now", or left
out. Refusals are recorded in that module's port doc, and anything needing
target-side code goes in the existing `docs/DEFERRED_INJECTION.md` - do not
create a third list.

**The absolutes.** Never optimise for line count - repetition in the source is the
port, not noise to factor out. Never use a structure the source does not have.
Never reach a field through a dynamic name - no `getattr(obj, "field")` dispatch.
Never redesign. Never add functionality. Never add a guard of your own: copy the
checks the source makes, per member, in the source's order - do not add a readiness
gate the source lacks, do not add an error swallow or default it does not return,
and do not defer a check it does make. Never monkey-patch. Never treat precedence
as permission: an existing helper, an earlier commit, or a line in these documents
blesses nothing, because only Reforged and Reforged Native are authority. Never
offer invented options - do not hand the user a menu of designs you made up. The
choices are always *port it* or *refuse it and record it*.

**Never substitute a stand-in for an unported source file.** If the source calls
something that has no ported home, port *that thing* - in the file and on the class
where the source puts it. The worked failure: `Py4GWCoreLib/Context.py` was never
ported, so `Map` grew `_area`, then `_area_value` - a `getattr` dispatcher with no
counterpart in either source project - and then an invented `IsMapReady()` gate on
top. Each step moved further from the source. Full account and the fix in
`docs/PORTING_RULES.md`.

**The source is the specification.** Reforged and Reforged Native are working,
in-production branches. Do not call their behaviour a bug, a defect, a crash or a
mistake, and never ask the user to decide whether the source is right - that
question is not open. If a path looks wrong, write a short factual note of what
the code does and the line it is on, then port it as written.

- **Every public member must exist in Reforged Python or in Native, spelled the
  same way.** If it is not in one of them, it does not go here.
- **No new layers.** No facade type, report object, registry, decorator, or
  "accessor" that the sources do not have. If Reforged calls `Map.IsMapReady()`
  before a read, this project calls `Map.IsMapReady()` before that read.
- **No new base types.** A helper type may exist only if the sources declare the
  corresponding type.
- **Port the structure, not a summary of it** - same order, same short-circuits,
  same return values, same defaults.
- **A divergence is a finding, not a design choice.** Where this project cannot
  reproduce what the source does, say so and refuse the member - never ship a
  second behaviour alongside it and call that deliberate. It does not mean the
  source is wrong.
- **Docs must describe the ported source.** If a doc names an API that is not in
  Reforged or Native, the doc is wrong.

This rule exists because it was broken here: a fabricated readiness layer
(`ReadinessReport`, `read_readiness()`, `evaluate_readiness()`) and a fabricated
`BitmapWords` type were built on top of the sources and then documented as the
library's contract. Both are deleted.

### Caching: `@frame_cache` is not ported (decided, closed)

**This is a settled decision, not an open design question. Do not re-open it.**

Stealth is **not run every frame** and is **not throttled**. It reads the client
**on demand**, at the call site. Reforged's `@frame_cache` memoises a function for
the duration of one game frame, and the *only* thing that invalidates it is an
in-process tick: `PyCallback.Register(..., Phase.PreUpdate, FrameCache.reset_cache)`
in `py4gwcorelib_src/FrameCache.py`. There is no TTL, no per-entry invalidation,
no size bound and no lock — correctness comes entirely from that per-frame wipe.

Stealth has no frame loop and cannot register a callback read-only. A verbatim
port would therefore **never invalidate**: the first call would pin a map-scoped
value for the life of the process, which is exactly the stale data the readiness
gate exists to prevent.

- **Do not port `@frame_cache`.** Drop the decorator and let the member read when
  it is called.
- **Do not invent a replacement tick** — no TTL, no throttle, no refresh timer, no
  `with py4gw.frame():` block, no caller-driven `cache.reset()` protocol. All of
  those were listed as options once and the answer is none of them.
- **Do not add a cache to "match the source".** Matching the source means matching
  observable behaviour, and a memo that never clears does not.
- The source decorates heavily, so this will come up on nearly every ported file.
  `Map` alone carries `@frame_cache` on 36 of its 178 members.

Caching is still permitted for **large structures** whose contents are expensive
to re-read — that is a caller-visible cost decision. The existing rule is
unchanged: **cache what the pattern scan produced, because that is stable; never
cache a dereferenced pointer, because that is map-scoped.**

Full statement and the audit procedure: `docs/PORTING_RULES.md`. The original
assessment of `FrameCache` and `GLOBAL_CACHE` is in
`docs/WRAPPER_MIGRATION_ASSESSMENT.md`.

## External-First Safety Rules

- Begin with read-only inspection. Keep the first experiments deterministic, bounded, and attributable to a selected PID.
- Validate target identity, architecture, module, address range, requested byte count, and pointer plausibility before interpreting memory.
- Use fixed-width target fields (`uint32` for confirmed x86 target pointers), not host-pointer-sized types in target layouts.
- Treat null, unreadable, stale, and changed pointers as distinct outcomes. Re-read roots at operation boundaries.
- Keep target knowledge separate from generic Win32 mechanics: signatures, layouts, and semantics must never be hidden inside a generic process wrapper.
- Never claim that a remote thread is safe for a Guild Wars internal function without function-specific ABI, thread-affinity, lifetime, and runtime evidence.
- Do not introduce memory writes, remote allocation, remote-thread creation, DLL loading, executable payloads, hooks, or code patches without explicit user scope for that operation and a documented rollback/verification plan. **That scope is granted and documented for `py4gw/game_thread/`**: connecting is a write, `docs/NATIVE_EXECUTION_PLAN.md` holds the plan, the rollback is verified live, and `tests/test_live_*.py` are the operations that exercise it. It does not extend to any other write.
- Never test against a live Guild Wars client in a way that modifies it unless the user explicitly requests that live write operation.

## Local Ownership and Dependencies

- Stealth does not import MemLib in its initial implementation. `external/MemLib` is reference context only.
- Prefer small, project-owned wrappers around documented Windows APIs over vendoring a large general-purpose library.
- If actual third-party code is copied, preserve its license, add a provenance record naming the source path and revision, and keep the copied surface minimal.
- Do not copy target-specific signatures, layouts, generated assembly, or command definitions from GwAu3 or Py4GW as if they were current truth. Treat them as research leads and revalidate independently.

## Engineering and Verification

- Keep public Python APIs explicitly typed and intentional.
- Preserve Windows error codes and diagnostic context. A failure must identify the PID, module/address when safe to report, operation, expected result, and observed result.
- Test generic logic without a live target first: structure offsets, pointer-width behavior, signature parsing, bounded read failures, and address validation.
- Keep live-client evidence separate from offline tests. Record target build/version, timestamp, inputs, expected behavior, observed behavior, and cleanup result.
- Match controller bitness to the target for early x86 experiments unless a cross-bitness design has been explicitly verified.
- Do not rely on Python finalizers for handles or process state. Use explicit close/context-manager ownership when resource-owning code is introduced.

## Documentation and Git

- Keep the root `README.md` current as the intent and research record until the project needs topic-specific documentation.
- Update the research record whenever a capability decision, source provenance, limitation, or live observation changes.
- Check repository status before edits and before reporting. Preserve unrelated changes.
- Never reset, restore, clean, force-push, rewrite history, delete project files, or commit unless the user explicitly requests the exact operation.

## Communication

Lead with the capability or limitation established by evidence. Explain Windows/process concepts plainly and distinguish what exists in the controller from what executes in the target process. Point criticism at brittle assumptions and unclear boundaries, never at the user.
