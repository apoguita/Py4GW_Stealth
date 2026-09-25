# Reforged Native hooks, callbacks, and execution plan

## Purpose and source boundary

This document records what Stealth needs to reproduce from the current
`Py4GW_Reforged_Native` source for hooks, callbacks, and calls into Guild Wars.
The Native project is the source of truth for which mechanisms and operations
belong in scope; this plan does not add hypothetical hook types or game
operations.

Inventory reviewed against `Py4GW_Reforged_Native` commit
`7a70e52e5fef4899dbc468c02e04db2ebef486d7`. These are source findings, not
proof that Stealth has implemented them or that they have been tested in a
live client.

Stealth's host remains external and does not depend on Reforged's DLL/runtime.
Native's callback-owned pointers and
game-thread operations are reproduced by a small Stealth-owned payload and patch in
the client,
without loading a conventional DLL. This modifies the process and is
injection. The no-DLL choice describes the delivery approach; it does not mean
the target is unmodified or that the payload is undetectable.

**Read this together with the component plan below and the Phase 5 status.** The
component plan is built and part of the library, not a standalone package:
`py4gw.connect()` installs the hooks, the block, the emitted dispatcher and the
callback listener on the game thread's own function and on the client's message
sender, and `py4gw.disconnect()` restores both functions' own bytes and frees
everything it placed. The reference implementations stay under the gitignored
`external/` tree as the worked design they were.

The first pointer the payload was planned for, the WorldMap context in
[`CALLBACK_POINTER_RESEARCH.md`](CALLBACK_POINTER_RESEARCH.md), now has a
read-only route through the client's UI frame array; it is implemented and
**confirmed on a live client, open and closed**. See
[`UI_FRAME_TREE.md`](UI_FRAME_TREE.md). That particular hook was therefore not
built; the payload is the mechanism for the work that genuinely needs target-side
code, and it now exists.

## What Native actually uses

| Native mechanism | Verified responsibility | Stealth implication |
| --- | --- | --- |
| `HookBase` / `THook<T>` (`include/base/hooker.h`, `src/base/hooker.cpp`) | Creates hooks through MinHook, retains the original-function trampoline, and supports enable, disable, remove, and in-hook tracking. It has both a raw-address path and a near-call-to-function path. | The lifecycle is a useful behavior reference, but the Native implementation is in-process and its DLL function-pointer model cannot simply be reused by the external host. |
| `MemoryPatcher` (`include/base/memory_patcher.h`, `src/base/memory_patcher.cpp`) | Saves original bytes, applies/restores patches, changes page protection, flushes the instruction cache, and supports E8/E9 redirection. Active users include chat timestamps, map bypass tolerance, camera/fog, gold confirmation, and cast-bar minimum patches. | Keep byte patches distinct from function hooks. Record the exact Native patch, original bytes, state toggle, and restore behavior for each port. `SetRedirect` exists, but no active call site was found in the reviewed source tree. |
| Game-thread bridge (`src/GW/game_thread/`) | Hooks `LeaveGameThread_Func`; runs queued single-shot work and persistent altitude-ordered callbacks before forwarding to the original function. `Enqueue` runs immediately if already on the game thread. | This is Native's central route for calling Guild Wars functions on the appropriate thread. A Stealth operation must identify its exact function and thread rule; it must not become an arbitrary remote-call facility. |
| UI callback hooks (`src/GW/ui/`) | Hooks UI message/frame/component paths and dispatches registered callbacks; some registrations are ordered and can block the original path. | Preserve each callback's arguments, original-call behavior, order, and block/forward semantics as described by its Native call site. |
| World/mission map UI callbacks (`src/GW/map/map.cpp`) | Calls the original callback, obtains the context pointer by dereferencing `message->wParam`, and clears the saved pointer on frame destruction. | This is the first planned pointer-capture use case: `WorldMapContext`, followed by `MissionMapContext`, using Stealth-owned state rather than Reforged shared memory. See [`CALLBACK_POINTER_RESEARCH.md`](CALLBACK_POINTER_RESEARCH.md). |
| Event and packet callbacks (`src/GW/events/`, `src/GW/stoc/`, packet-sniffer sources) | Provides event callbacks and packet-specific callbacks; the event hook is created but `EnableHooks()` currently leaves it disabled with a legacy-GWCA note. The CToS packet path uses a raw hook. | Track implemented, created-but-disabled, and registered callback paths separately. Do not treat the event hook as active behavior in this source snapshot. |
| Other Native hook call sites | Agent, chat, effects, friend list, item, map, merchant, party, render, skillbar, UI, world-render, agent-recolor, native-UI, quest, and listener modules create hooks for source-specific functions/callbacks. | Port only the source-backed functions and their real signatures/semantics. The per-module inventory is in the checklist below and must be refreshed when the Native source revision changes. |
| `PyCallback` (`src/callback/`) | Schedules embedded Python work in PreUpdate/Data/Update and Update/Draw/Main phases, with profiling. | This is a runtime scheduling layer above hooks, not itself a separate process hook. Reproduce only if/when Stealth ports source-backed script scheduling. |

Native hook call-site groups found in the reviewed source snapshot:

- `agent`: `DoWorldAction`, `CallTarget`, `SendAgentDialog`,
  `SendGadgetDialog`, `ChangeTarget`.
- `chat`: chat-log, whisper, sender/message color, send/receive whisper,
  editable-text, and chat-print paths.
- `effects`: `PostProcessEffect`.
- `events`: `SendEventMessage` (created but currently disabled).
- `game_thread`: `LeaveGameThread`.
- `friend_list`: `FriendEventHandler`.
- `item`: salvage-popup, click, weapon-set ping, move/use item, and gold paths.
- `map`: challenge entry and WorldMap/MissionMap UI callbacks.
- `merchant`: item transaction and quote paths.
- `party`: tick-button UI callback.
- `render`: end-scene, reset, and screen-capture paths.
- `skillbar`: skill use and skill loading.
- `ui`: UI message, frame message, component creation, and item-image-frame
  paths.
- `world_render`: `Dx9DdiDispatch`.
- Additional source call sites: agent recolor, native UI text, quest, skill
  filter listener, and raw CToS packet sending. Crash-handler stack handling
  is present but is not a Guild Wars gameplay feature and is not part of the
  initial Stealth port.

The Native source also uses the game-thread queue for operations across agent,
camera, chat, CToS, friend-list, guild, inventory/item, map/pathing, merchant,
party, player, quest, skillbar, and UI modules. Before each operation is
ported, inventory the actual target function, argument and return types,
calling convention, thread requirement, original behavior, and failure case
from its Native source. A module name alone is not a callable contract.

## Extensibility contract

The implementation should be reusable without pretending every future
mechanism is already known:

1. Keep a small core for payload lifetime, communication, operation dispatch,
   and cleanup. Keep target-specific hook and call definitions in separate,
   reviewable descriptors.
2. Represent each source-backed operation explicitly: mechanism kind,
   resolved target, calling convention, typed parameter layout, return
   handling, original-call policy, thread requirement, and lifecycle.
3. Keep mechanism adapters separate (for example, a Native-backed function
   hook, a byte patch, or a callback capture). Add an adapter only when the
   Native inventory shows a real need for it.
4. Make parameter encoding explicit and typed. If a later Native operation
   needs a parameter form not yet supported, add that form as a focused,
   tested extension without changing existing descriptors.
5. Reject unknown mechanism kinds, parameter forms, targets, and versions
   clearly. Do not fall back to calling an arbitrary address or accepting an
   untyped argument blob.
6. Version descriptors and payload/host protocol together. A mismatch must
   fail closed rather than guessing a layout.
7. Preserve Native behavior for forwarding, callback order, blocking,
   return values, and enable/disable state. Do not silently simplify those
   semantics in the name of reuse.

This makes later additions possible while keeping the initial system limited
to mechanisms and parameter forms actually required by Reforged Native.

## Component plan

The layers in dependency order. "Native" is what the source project has;
"Stealth" is what we need, which differs only where Python sits *outside* the
process instead of inside it. State records what has been **proven to work** in
the reference packages under `external/` — not code this project has adopted.
See "Inherit the invariants, design the shape" below.

| # | Layer | Native | Stealth | State |
| --- | --- | --- | --- | --- |
| 0 | Resolver | `Patterns::Resolve` | `PatternCatalog` + the tracked `offsets/` catalog | **done** — 233 resolvers, byte-identical to Native's |
| 1 | Transport | not needed; the queue is a `std::vector` in its own address space | one allocation inside the client plus a layout both sides agree on | **done** — header, module-bound trust anchor, command region, and the event region the listener reads |
| 2 | Installer | MinHook, in-process | ours: suspend, verify, write, protect, restore, roll back | **done, live-verified** |
| 3 | Payload | compiled into the DLL | a position-independent, import-free x86 blob | **done, live-verified** |
| 4 | Pump | `CallFunctions()` inside the `LeaveGameThread` detour | the same hook, installed from outside | **done, live-verified** |
| 5 | Action queue | `game_thread::Enqueue` | command ring + completion | **done, live-verified** |
| 6 | Callbacks | twelve typed per-feature registries | **one** registry keyed by event type, over an event ring | **done, live-verified** — a handler fired from a real client message with no `pump()` call |
| 7 | Call vocabulary | `NativeFunction` + `Prototypes` (17 ctypes signatures) | descriptor table + generated call stubs | **partly built** — the descriptor table and two typed forms are live-verified; breadth is the remaining work |

Why one registry and not twelve: Native needs a typed registry per feature because
each hook has its own signature. Every event *we* deliver arrives as the same
fixed-size record, so a single registry keyed by event type covers all of them —
and a new callback kind then costs one hook and one event id, not a new mechanism.

### The call vocabulary

Follow-up 1 from Phase 5, and the answer to extensibility rule 4.

Native describes a callable game function as **an address plus a prototype**, where
a prototype is a ctypes signature (`restype`, `argtypes`, convention) drawn from a
table of 17 reusable shapes. `prototype.build()(address)` returns a real callable
and ctypes handles the marshalling. Nothing about any individual function is
written down: the pattern finds the address, the prototype says how to call it.

That works in-process and cannot work for us — `ctypes.CFUNCTYPE(...)(address)`
builds its trampoline in *our* address space, and a `Gw.exe` internal function is
not callable from there.

**The adaptation:** keep the prototype table and let it drive code generation
instead of ctypes. From `(restype, argtypes, convention)` we know exactly how to
write the call, so the host emits a short stub per signature and places it in the
client. The payload then needs one generic command — *run the stub for descriptor
N with these argument words* — and never grows.

This also satisfies rule 5, which forbids "calling an arbitrary address with an
untyped argument blob". Today `arg3` carries an address. The contract-shaped form
is a **controller-populated descriptor table** with `OP_CALL_DESC <index>`, so no
address crosses the wire and every call shape is declared, reviewed and typed. The
v2 hardening bounded `arg3` to the client module; the descriptor table removes it.

Pointer parameters are the one real cost. A scalar is just a 32-bit word; a pointer
(`float*`, `wchar_t*`) must point into the client's address space, so the host
allocates a small scratch buffer in the target, writes the data there, and passes
that address. Native never pays this, because it can pass a pointer into its own
memory.

### Decisions this plan depends on

These are the user's to make, not assumptions to build on:

1. **Where the code lives.** The bridge is neither Reforged nor Native, so
   [`PORTING_RULES.md`](PORTING_RULES.md) does not cover it. Integrated into
   `py4gw/` it becomes Stealth-owned infrastructure beside `py4gw/scanner` and
   `py4gw/memory`; kept under `external/`, the library stays read-only.
2. **Which base to continue from — DECIDED: neither, in the sense of inheritance.**
   The packages under `external/` prove the mechanism works and are the reference
   for *invariants*; they are **not** a codebase to inherit. The implementation is
   tailored to this project and does not adopt their module split, object model,
   naming, sizes or ABI. Three of their modules are duplicate capability we already
   own and would not be re-created: `selfscan.py` for `RemoteScanner` +
   `PatternCatalog`, `modules.py` for `Win32.get_main_module` /
   `list_processes`, and their process reader for `ProcessMemoryReader`.
3. **Whether to verify the reference live first**, before writing our own. It
   injects, so it needs explicit scope — and it would not be our code doing it.

### Inherit the invariants, design the shape

The distinction to hold onto, because it is easy to lose:

**Invariants — properties any correct implementation needs, taken from the
reference as findings rather than as code:**

- the producer writes the whole record, then publishes the index **last**;
- the consumer copies pending records and advances its read index **before**
  running callbacks, so a slow callback cannot pin slots;
- the game thread never waits for the host — overflow increments a counter and
  drops, it does not block;
- patching is fail-closed: verify, suspend, refuse on an implausible state,
  re-read, restore protection, and roll back on failure;
- the payload is position-independent and import-free;
- no raw address crosses the wire — a descriptor index does;
- the map-ready check is applied twice: when work is published, and again on the
  game thread, because the map can change in the gap.

**Shape — ours to design, not theirs to dictate:**

- module split, naming and object model, following this project's existing
  module style rather than one large orchestrator object;
- the wire records, following the house style already set by
  `py4gw/memory/mailbox.py`: magic, version, size, session id, and a sequence
  used for stable reads, with every mismatch rejected explicitly;
- ring depths and record sizes, chosen for our needs rather than inherited;
- how it attaches to the library — through `ConnectedClient` and the existing
  readiness discipline, like every other reader here;
- what it refuses. The reference's own defects are recorded in
  [`DEFERRED_INJECTION.md`](DEFERRED_INJECTION.md) and are not inherited: the
  permanent wedge on a command timeout, `close()` freeing code after a refused
  restore, the broken reinstall path, the over-narrow executable-region fallback,
  and `watch_value`'s encoder ordering.

### Checklist

The first unchecked item is the resume point.

**Proven in the reference packages under `external/` — not our code**

These record that the mechanism is possible. None of it is in this library.

- [x] Resolver catalog present and identical to Native's
- [x] Transport layout: header, module-bound trust anchor, command ring
- [x] Installer: fail-closed patch discipline, refusal paths, rollback
- [x] Payload: relocation-free, with a build-time relocation gate
- [x] Pump: entry hook on `leave_game_thread_func`, live-verified
- [x] Action queue: publish, completion, timeout behaviour, live-verified
- [x] Offline harness that links the real dispatcher object
- [x] Callback transport designed and documented (v3 reference, not live-verified)

**Stealth implementation — our own, in the library**

- [x] **Step 1 — the shared block.** `py4gw/game_thread/shared_block.py` plus
  `tests/test_shared_block_offline.py`. Layout, records, their vocabularies,
  validation and queue arithmetic. 36 tests, no client involved, no writes. See
  the resume record.
- [x] **Step 2 — the installer.** `py4gw/win32/write_access.py` (the invasive
  Win32 surface) and `py4gw/game_thread/patcher.py` (the fail-closed patch
  sequence), plus `tests/test_patcher_offline.py` (19 tests, fake target) and
  `tests/test_write_access.py` (**10 tests, live, elevated, all passing**). The
  Win32 surface is now proven against the real client: threads suspended and
  resumed, instruction pointers read, page protection changed, bytes written and
  restored. Every write in that run targeted memory the test allocated itself,
  outside the client module; nothing was written to the client's own code or
  data, and the client was left healthy on the same PID.
- [x] **Step 3 — the hooker.** `py4gw/game_thread/hooker.py` plus
  `tests/test_hooker_offline.py`. Entry patch, trampoline, entry stub, and
  install / enable / disable / hits / remove. 33 tests against a fake target.
  **The hooker's own generated bytes have still never executed** — that is the
  first item under Still open, and it is now the only offline gap left.
- [x] **Step 4 — the payload.** `py4gw/game_thread/payload.py` plus
  `tests/test_payload_offline.py`: the dispatcher the stub calls — validate the
  block header, take at most one command, run it, publish the result and the
  completion event. **330 bytes of machine code, emitted from Python**, not
  written in C and compiled. The harness places those bytes in this process's own
  executable memory and calls them against a fake block, so the bytes that run are
  the bytes the installer would write. 21 tests, no compiler, no client.
- [x] **Step 5 — the queue.** `py4gw/game_thread/bridge.py`: publish a command,
  wait for its result, read the events back. Plus `tests/test_bridge_offline.py`
  (25 tests against a fake target) and **`tests/test_live_bridge.py`, which runs
  the whole chain in the live client** — 10 tests, elevated, all passing. The
  client's code section is hashed before and after and comes back identical. See
  the resume record.
- [x] **Step 6 — callbacks: the registry and the listener.**
  `py4gw/game_thread/callbacks.py`: handlers keyed by event kind
  (`register`/`unregister`/`kinds`), a one-shot `pump()`, and **`EventListener`** —
  a thread that reads the block and dispatches records **as they arrive**, which is
  what makes a callback a callback rather than a queue you drain. 22 offline tests
  and two live ones: one pumps and sees the handler run, the other starts the
  listener, causes a real target change through the call path, and is delivered
  **with nothing calling `pump()`**.

  Reading happens in one place — the event counter has exactly one consumer — and
  the command side has its own counter and its own writer, so a listener and a
  publisher need no lock between them. That is the block's design paying off.

  Two costs, recorded rather than designed away: **handlers run on the listener's
  thread**, alongside whatever the caller's main thread is doing; and **a handler
  that blocks slows the drain**, because the payload drops an event when the client's
  event region is full rather than making the game wait.
- [ ] **More callback kinds.** The registry is in place and two kinds flow through
  it (`COMMAND_COMPLETE`, `UI_MESSAGE`); each further kind is one watch-list entry
  and one hook, per the inventory.

**The call vocabulary — started, ahead of Step 6**

Chosen over Step 6 because of what the refusals actually need. Counted from the
refusal messages themselves: of 188 refusing members, **104 are plain porting
gaps** (a context field not ported yet), **52 need the client to do something**
("it asks the client to travel", "dispatches a tick UI message", "add a hero"),
6 name the callback runtime, and 6 need in-client UI or the geometry kernel. The
52 are the largest portable chunk left, and the 6 callback ones are the
`enable()` members that want a per-frame refresh this project refuses by design.
So the call path buys the port; callbacks (Step 6) buy a new event surface.

- [x] **Descriptor table addressed by index**, so no raw address crosses the wire.
  It lives in the client, is filled by the host from the pattern catalog, and a
  command names a slot. The dispatcher is emitted with its address and with the
  module bounds it checks before calling anything.
- [x] **A typed call form**: `ui::SendUIMessage(message_id, wparam, lparam)` —
  the shape nearly every Native action goes through — with the command's words
  packed into a zeroed sixteen-word payload. Proven by execution, not inspection.
- [ ] Prototype table in the host — Native's 17 shapes plus whatever we need
- [ ] Stub generator per signature, with a cache, placed in the client
- [ ] Scratch-buffer allocation and marshalling for pointer parameters, so
  `Void_FloatPtr` and `wchar_t*` calls work

**Settled — elevation is a precondition, not a step.** `py4gw.connect()` asserts
elevation and refuses without it, and **a process cannot elevate itself**: the token
is fixed when the process is created and no API raises it, so `AdjustTokenPrivileges`
cannot help (it only enables privileges already present, and a filtered token's
Administrators SID stays deny-only). Spawning a second elevated process is the only
thing UAC can authorize, and the process that asked still holds no rights. So
"elevate on demand" was evaluated and rejected as having no useful meaning here, and
a broker or a self-relaunch is not planned. The shell is elevated before the script
starts, every time. `Win32.is_elevated()` is the one check; see `AGENTS.md`.

**Still open**

- [ ] **Execute the stub, offline, the way the dispatcher now is.** The payload's
  bytes have run, and the live test shows the stub works, but no offline test has
  executed it. The same harness can prove the whole chain with no client — write an
  entry patch over a fake function in this process, call it, and check that the
  dispatcher ran and the original body still ran afterwards through the trampoline.
- [ ] Whether to verify the reference live before writing our own
- [ ] Re-entrancy guard and an "am I inside the hook" query
- [ ] **Owner-loss policy**, now with a measured cost. `disconnect()` frees
  everything *it* placed — two connect/disconnect cycles reused the same block and
  watch-list addresses, which is what proves the free path ran. What is still
  unreclaimed is an **orphan**: a controller killed while patched leaves its entry
  patch and its allocations behind (about 3 KB per attach, because a thread can be
  inside the stub at the moment of removal). Reconnect repairs the stale patch and
  counts suspended threads, but nothing frees the orphan's memory; the live suites
  that remove without freeing (`remove(free_code=False)`) have left pairs behind on
  purpose. Decide what reclaims an orphan, and whether a removal path should free
  the allocations after a bounded wait.
- [x] Offline harness coverage for the call path: `tests/test_payload_offline.py`
  emits a target function as machine code and runs the real dispatcher over a real
  call table, including the refusals.
- [x] Live validation of the call path, elevated, on a real client:
  `tests/test_live_call.py`, and `tests/probe_live_target.py` for the observable
  effect.
- [ ] Offline harness coverage for the callback masks.
- [ ] **Which module size becomes the trust anchor.** `Win32.get_main_module`
  prefers Toolhelp and falls back to PSAPI when Toolhelp is denied, and the two
  disagree by one page for `Gw.exe` (`0x0F48000` vs `0x0F49000`; the PE header
  agrees with PSAPI). Since Toolhelp is only available to an elevated controller —
  and elevation is required for all target-side work — the number that reaches
  the bridge depends on how it was launched. Measuring a re-run is needed before
  `module_base`/`module_size` is treated as settled. Evidence in
  [`RESEARCH.md`](RESEARCH.md).

## Resumable plan

Each phase is completed and reviewed before starting the next. The first
unfinished checkbox is the resume point.

### Phase 1 — Native source inventory

- [x] Record the source revision and inventory hook, patch, callback,
  game-thread, and embedded-Python scheduling mechanisms.
- [x] Separate active hooks from hooks that are created but disabled.
- [x] Record the map callback's pointer and frame-destroy behavior.
- [x] Define a source-backed extensibility boundary; do not invent schemes
  or arbitrary callable parameters.

### Phase 2 — First-use-case contract

- [x] Select one first mechanism: a Stealth-owned x86 callback detour with an
  original-call path and a fixed-width mailbox read by the external host.
- [x] Specify the Native callback ABI, forwarding order, pointer dereference,
  and frame-destroy clear behavior for WorldMap only.
- [x] Specify mailbox version/session checks, coherent reads, states, and
  orderly detach requirements.
- [x] Define owner-loss behavior for the first passive hook: the
  self-contained stub remains resident, forwards the original callback, and
  can be validated and detached on reconnect.
- Deferred until the normal attach/capture/detach path has passed: define
  how interrupted-install recovery and reconnect will be checked on the real
  client. This does not block the first bounded normal-path test.

### Phase 3 — Mailbox format and live preflight

- [x] Test only the mailbox record layout, version/session checks, stable
  reads, and state validation offline (`tests/test_mailbox.py`).
- [x] Run the read-only callback preflight on the user-selected PID and
  confirm the signature target and bytes against the live client. The latest
  recorded run is in [`RESEARCH.md`](RESEARCH.md); it verifies address
  resolution and readable target bytes only, not callback behavior or hook
  safety.
- [x] Define a bounded integration test against one selected, real Guild Wars
  client: target/build checks, callback forwarding, pointer capture/clear,
  orderly detach, and recovery if detach fails.
- [x] Do not create a mock Guild Wars callback target; it cannot establish
  that the actual client callback works.

### Phase 4 — First source-backed pointer capture (COMPLETE, read-only)

- [x] Implement the read-only frame-array route that reaches the same pointers
  the callbacks publish: `py4gw/ui/` primitives, the `FrameTree` walk, the
  frame-id cross-check, offline tests, and the read-only preflights. See
  [`UI_FRAME_TREE.md`](UI_FRAME_TREE.md). No target-side code, patch, or remote
  thread is involved, so there is nothing to restore.
- [x] Confirm live resolution and array structure on PID 29520.
- [x] Confirm the callback handoff for both map contexts, open **and** closed:
  `MissionMapContext` via frame 1591 (direct registration) and
  `WorldMapContext` via frame 3698 (registered through a `jmp` thunk, which
  required adding near-jump following to the walk).
- [x] Resolve `SalvageSessionInfo`: the handler is registered on no frame and
  stored in no frame record, **and** it is unused by both reference projects,
  so it is not a pointer-acquisition gap and not a reason to inject.
- [x] Record live build, selected PID, expected/observed behavior, and the
  close transitions in [`RESEARCH.md`](RESEARCH.md).

### Phase 5 — Source-backed game-thread operations (next)

- [ ] Port the reusable queue/dispatch behavior evidenced by Native's
  game-thread bridge, with no arbitrary remote-call API. This is the remaining
  justification for target-side code.
- [ ] Port one Native operation at a time, documenting its exact ABI,
  parameters, result, thread rule, and parity evidence.
- [ ] Add a new parameter form or mechanism only when a concrete Native
  operation requires it; add tests for old and new descriptor versions.

**Status 2026-09-23 — mechanism built and verified live.** A candidate
bridge was delivered (external controller + 9-byte entry hook on
`leave_game_thread_func` + queue-serviced dispatcher payload) and hardened
against this plan's extensibility rule 5. The version-1 payload accepted the
call target as a raw `arg3` field, which is exactly the "calling an arbitrary
address with an untyped argument blob" this contract forbids. Version 2 adds
`module_base`/`module_size` to the bridge header, publishes them at install,
and makes the dispatcher reject any call target outside the client module with
`CMD_ERROR` / `-102` before it is ever called.

Verified live against `Gw.exe` PID 29520 (elevated controller): hook installed
and fired, queue served on the game thread, `PING` returned `0xC0DEC0DE`, and
`agent.move_to_func` moved the character exactly 10 units. Original bytes
restored and the client left healthy on the same PID.

Verified offline (no client contacted):

- the guard is proven **by execution**, not inspection: a 32-bit harness links
  the real `dispatcher.obj` and shows an out-of-module target is refused with
  `-102` and is never entered, while an in-module target is called with the
  documented `float[4]` layout;
- the payload rebuilds from `native/dispatcher.c` via
  `native/build_payload.ps1`, which refuses to emit a payload that carries
  external relocations (position independence is a build-time gate);
- 16 offline tests pass, including guard, ABI, and hook-byte-builder checks.

The plan's rule 5 is now enforced in three places: the protocol rejects an
unusable module range, the controller refuses to publish an unvouched resolved
target, and the payload refuses to call one.

Two deliberate follow-ups, not yet done:

1. **Descriptor registry.** `arg3` still carries an address, now bounded. The
   fully contract-shaped design is a controller-populated descriptor table in
   the bridge and a `OP_CALL_DESC <index>` opcode, so no address crosses the
   wire at all. That was scoped out of the hardening pass and is the next
   architectural step for extensibility rule 4 (explicit typed parameter
   forms).
2. **Live validation — DONE (elevated).** The hook, the queue round trip, and a
   call into a real Guild Wars function are now verified live. `move_to_func`
   was called on the game thread with `arg = {x, y, (float)zplane, 0}` and the
   character moved exactly 10 units, with the original bytes restored afterwards
   and the client left responsive on the same PID. The ABI was cross-checked
   against `Py4GW_Reforged_Native/src/GW/agent/agent_methods.cpp:145-155` and
   against the real callee at static VA `0x00536E80`.

   The one operational constraint: the controller must run **elevated**. An
   unelevated controller is denied `PROCESS_VM_WRITE`,
   `PROCESS_VM_OPERATION`, `PROCESS_CREATE_THREAD`, and
   `PROCESS_SUSPEND_RESUME` with error 5. Two earlier notes here were wrong about
   why: it is not a client protection, and it is not UAC token splitting either —
   the client's own DACL grants our user SID `PROCESS_ALL_ACCESS`, so no access
   check explains it. See the measurement in [`RESEARCH.md`](RESEARCH.md).

   Still open from the questions above: whether the mover needs additional
   client state (loading screen, character select, dead/knocked-down), the
   semantic meaning of `zplane`, and whether calling at the hook entry is
   equivalent to Reforged Native's position after its queued callbacks — the
   ordering matches by inspection, but that has not been probed with a
   state-dependent operation.


### Phase 6 — Remaining hook and callback families (not started)

- [ ] Work module by module from the inventory above: UI, events, packet,
  effects, render, agent, chat, friend list, item, map, merchant, party,
  skillbar, and other listed call sites.
- [ ] For each, first mark source behavior as active, disabled, or conditional;
  then port exact callback order, original-call behavior, and cleanup.
- [ ] Exclude crash-handler hooks and any behavior not used by Native's
  Guild Wars feature surface unless a later source audit changes that scope.

## Resume record

**Resume point: the call vocabulary's remaining forms.** The objective's three legs
are all live-verified now — hooks, execution, and callbacks — so what is left is
depth rather than capability: pointer arguments (`Move(float*)`), the prototype
table, and per-signature stubs, which is what turns one typed form into the
vocabulary the refused action members need. Then the members themselves, one at a
time, each with its effect asserted rather than its completion trusted.

### How the payload is produced — corrected

An earlier draft of Step 4 said the payload would be written as C and compiled,
with the compiled bytes checked in. **That was wrong, and it was wrong because it
copied the reference package's approach rather than thinking about this project.**

The reference ships `dispatcher.c`, `build_payload.ps1` and a 604-byte
`dispatcher_x86.bin`. None of that is required. The hooker already emits the entry
patch, the trampoline and the 34-byte stub as raw bytes from Python. The dispatcher
is the same technique at a larger size, and the consequence of emitting it is that
this project gains **no C source, no build script, no toolchain dependency and no
binary blob in the repository**. The machine code is described by Python that a
reviewer can read, not checked in as an opaque artifact.

What made this decidable rather than a matter of taste: **Python can execute the
code it emits, in this process, so the harness needs no compiler and no client.**
Verified on this machine, 32-bit Python 3.13:

```text
emitted 6 bytes at 0x11e0000 -> call returns 42
cdecl pointer arg   -> 42          (argument at [esp+4])
stdcall pointer arg -> 0xc0dec0de  (callee pops: ret 4)
two stack args      -> 42
bitness: 32
```

So the harness allocates executable memory with `VirtualAlloc`, copies the emitted
bytes in, and calls them with a pointer to a fake block. Both calling conventions
that matter are testable the same way: `__cdecl` for the game functions the payload
calls, and `__stdcall` for the payload itself, which the stub calls and which pops
its own argument.

The honest cost: hand-emitting a dispatcher in Python is more work than writing C
and compiling it, and the dispatcher is more complex than the stub. The mitigation
is to keep it minimal and grow it in small, separately tested steps.

Asked and answered: *"why not write everything in C++ then?"* Because the value of
this project is a controller written in Python that can be read, run and changed
without a build step. Exactly one part has to be machine code — the part that
executes inside the client — and emitting that from Python keeps it small and
keeps every other line of the project readable.

### Call vocabulary, first slice — built, not yet called live

Built: `Operation.CALL` and `CallForm` in `shared_block.py`, the `Descriptor`
record and the call table, the CALL path in `payload.py` (354 bytes without a
table, 558 with one), and the host side in `bridge.py`. Offline suite 475 tests
green, `pyright` reports no errors.

**What the sources said, before anything was written.** `Py4GW_Reforged_Native`
declares its call ABIs as typedefs beside the code that uses them
(`src/GW/agent/agent_methods.cpp:18-22`), and almost every action it takes on the
player's behalf goes through one function:

```cpp
using SendUIMessageFn = void(__cdecl*)(UIMessage message_id, void* wparam, void* lparam);
```

`ChangeTarget`, `InteractAgent`, `CallTarget`, the party-search and tick and
invite messages, travel, difficulty, add/kick hero — all of them build a small
packet and call that. `ui_bindings.cpp:60-74` documents the packet contract: a
**zeroed sixteen-word POD** with the values packed into the front, passed as
`wparam`, with `lparam` null.

**And the address is already resolvable.** Native resolves it with
`PY4GW::Patterns::Resolve("ui.send_ui_message_func", ...)` (`ui.cpp`), and our
copied `offsets/ui.json` carries that exact resolver — `send_ui_message` pattern,
`to_function_start`. No new resolution machinery was needed for any of this.

**What was built, and what each piece refuses.**

| Piece | What it does |
| --- | --- |
| call table in the client | 16 slots of `{target, form}`. The host fills it from the pattern catalog. A slot the host did not fill stays zero and names nothing. |
| `Operation.CALL` | The command carries a **slot**, never an address: `arg0` is the index, `arg1`–`arg3` are the form's words. |
| module guard in the payload | Before calling: a zero target is `RESULT_NO_TARGET`, a target outside `module_base`/`module_size` is `RESULT_BAD_TARGET`, and neither is called. The host resolved the address, so it is inside the module by construction; the payload refuses anyway, because that is the rule the call path has to hold on its own. |
| `CallForm.UI_MESSAGE` | Zeroes sixteen words in its own frame, packs the command's two words into the front, and calls `void __cdecl(message_id, payload, nullptr)` — arguments right to left, caller releases them. |
| an unknown form | `RESULT_UNKNOWN_FORM`, never guessed at. A form the payload does not know is not called with the words it happens to have. |

**How it is proven.** `tests/test_payload_offline.py` emits a **target function**
as machine code as well, and that target writes down what it was handed: the
three arguments and the first four words behind `wparam`, plus a canary so "never
called" is distinguishable from "called with zeroes". Eight tests run the real
dispatcher over a real call table and check by execution that the message id
arrives first, that `wparam` points at a payload holding the command's words,
that `lparam` is null, that the words the command did not set are zero, and that
each of the four refusals above leaves the target **not called**.

**What is not proven yet.** ~~No call has been made in a live client.~~ **Called
live on 2026-09-24** — `tests/test_live_call.py`, 6 tests, elevated, in a map:
`ui::SendUIMessage(kSendChangeTarget, {agent_id, 0}, nullptr)` resolved to
`0x008441A0` and reached through call-table slot 0, completing `DONE` on the game
thread while the client ran its own frame. The two refusals were exercised **in the
client** as well: a slot naming an out-of-module address came back
`RESULT_BAD_TARGET` without being called, and a slot past the table came back
`RESULT_BAD_DESCRIPTOR`. Entry bytes restored, code section hash unchanged. See
[`RESEARCH.md`](RESEARCH.md) for the full record.

**What the live runs prove now.** On 2026-09-24 the call path was exercised in the
client twice, and the second time it *did* something: `tests/probe_live_target.py`
called `agent.change_target_func(player_agent_id, 0)` and then `(0, 0)`, and the
person watching saw the target ring appear and clear. **A Native action is two
things, not one** — the message the runtime broadcasts and the function it calls in
response — and only the second is part of a port; see
[`RESEARCH.md`](RESEARCH.md) for the chain that shows it. The message-sending form
(`UI_MESSAGE`) stays, because messages the *client* handles are still messages; what
changed is knowing that for the `kSend*` family the actor is the runtime, not the
client.

**What is still missing** is nothing, for the mechanism: the observation side was
built on 2026-09-24. `tests/test_live_call.py` hooks `ui.send_ui_message_func`,
watches `kChangeTarget`, and asserts the target id that comes back from the
client's own notice — 4 tests, elevated, all passing. The observer is
`payload.py`'s `build_observer`, the watch list lives in the client like the call
table, and the stub forwards the hooked function's arguments
(`hooker.build_stub(..., forwarded_arguments=2)`). See
[`RESEARCH.md`](RESEARCH.md) for the run, and for the two measured behaviours the
tests depend on: the client reports changes rather than requests, and the entry cut
must not include a relative branch.

**The first live call, as it stands.** `ui::SendUIMessage` with
`UIMessage::kSendChangeTarget` (`0x3000000B`, `constants/ui.h:186`) and a
two-word packet `{target_id, auto_target_id}`, which is exactly
`agent.cpp:94-95`'s own call. The call ran and the client survived it; the message
alone changes nothing, because what acts on it is the runtime's own handler. Two
routes to the effect were then built: the other side of the same hook, which is
built above (`test_live_call.py` watches `kChangeTarget` and asserts the target id
from the client's own notice), and a read-only resolver for the current-target
global — `offsets/gwau3_leads.json`, landing on `0x0129A174` and confirmed
differentially against the client's own reports. `Player.GetTargetID` is still
refused: Native keeps the value in `g_current_target_id`, a global its
`kChangeTarget` UI-message *hook* maintains (`agent.cpp:60,143-145`) and no context
holds, and the member has not been ported onto either route.

### The lifecycle: connect sets it up, disconnect takes it down

`py4gw.connect()` now installs the whole capability layer and `disconnect()` removes
it, so the pieces above are not something a caller assembles by hand:

- connect resolves `game_thread.leave_game_thread_func` and
  `ui.send_ui_message_func` from the catalog, **checks both entry byte sequences
  before writing anything**, opens the write transport, installs the bridge (command
  hook, observer hook, module bounds, empty call table and watch list), creates the
  registry and **starts the listener thread**;
- `client.callbacks` registers handlers, `client.watch(message_id)` and
  `client.unwatch(message_id)` change what the observer records at runtime — the
  list lives in the client and is re-read on every call, so no reinstall is needed;
- `client.bridge` is the queue and the hooks, for anything deeper;
- `disconnect()` stops the listener first (it is the only reader of the event
  region), restores both functions, **frees every allocation it placed**, and closes
  the handle — a handler that raised is re-raised last, after the client is back.

**Two recoveries for a controller that died**, because a crash-resistant install
that cannot clean up after a crash is half a feature:

- **A stale patch of ours is repaired.** The patch is a relative jump; if the entry
  bytes are one whose destination is *outside* the client's module, it is ours from
  a controller that died, and the known original bytes go back through the patcher.
  Anything else is refused — this does not guess at another tool's patch.
- **Suspended threads are counted and reported** (`client.suspended_threads`), with
  `resume_suspended_threads()` for the one case that freezes a client: a controller
  killed inside the window where the installer had the client's threads suspended.
  Resuming is explicit rather than automatic, because a thread can be suspended for
  the client's own reasons and guessing wrong is worse than reporting.

**Verified live.** Two connect/disconnect cycles allocated the block at the same
address both times (`0x01C90000`, watch list `0x09350000`), which is what proves the
free path ran; both hooked functions read back as their original bytes; the
connect-based live suites (`test_map`, `test_agent_array`) pass with the hooks being
installed and removed inside them.

### Step 5 complete — the queue, and the whole chain live

Built: `py4gw/game_thread/bridge.py` (the host side), `tests/test_bridge_offline.py`
(25 tests against a fake target) and `tests/test_live_bridge.py` (10 tests, live,
elevated, all passing). Offline suite 460 tests green, `pyright` reports no errors.

**What the bridge owns.** Three things in one client — the block, the dispatcher
and the hook — and it places them in that order, with the entry patch **last**, so
a failure at any earlier step releases what it made. It does not own the transport:
the caller opened it and the caller closes it.

**The round trip.** `publish(operation, arg0..arg3)` reads the header, refuses when
all 16 slots are outstanding, fills the slot at `command_written`, then advances
that counter — record first, counter second, so a payload reading below the counter
can never see a half-written command. A command's sequence number *is* that
counter, which is why its slot is the sequence's low bits. `wait(sequence)` reads
the record until it is terminal, and requires the record's own sequence to match: a
slot is reused every lap, and returning another command's answer would be worse
than returning nothing. `events()` reads what the payload published and advances
the host's `event_taken`, which is the only counter the host owns in that region.

**No readiness gate, and that is deliberate.** The step above says "gated on the
readiness discipline like every other read here", and the honest answer is that the
queue itself has nothing to gate: the payload's only precondition is the block
header, and the operations it knows are pure computation. Reforged gates game-thread
work with `Map.IsMapReady()` because *its* queued work touches map state. When the
call vocabulary arrives, that check belongs to the operation that needs it, applied
per operation the way the source applies it — not bolted onto publish, where it
would be a guard the source does not have.

**The live run.** `tests/test_live_bridge.py` resolves
`game_thread.leave_game_thread_func` read-only, checks the declared nine entry bytes
against the live ones, installs the hook, publishes work, and restores the original
bytes.

```text
leave_game_thread_func     = 0x00845880
displaced entry bytes      = 55 8b ec 81 ec 20 02 00 00
hook hits                  = 2
entry after remove         = 55 8b ec 81 ec 20 02 00 00
code section before        = 33984c4c6a98d23ec43b00798f9f2a11... (5473792 bytes)
code section after         = 33984c4c6a98d23ec43b00798f9f2a11... (5473792 bytes)
left mapped (on purpose)   = block 0x09540000, dispatcher 0x09550000
```

Everything the payload can do, it did **inside the client**: `PING` returned
`0xC0DEC0DE`, `ECHO_U32` its argument, `ADD_U32` the sum, `NOP` no result, and an
unknown operation `FAILED` with `-100`. The completion event arrived with the
sequence, operation, terminal state and result. The ring was driven past its depth
(17 commands across a lap boundary) with nothing left outstanding. The hooked
function kept running afterwards, which is the trampoline replaying the displaced
prologue. The client stayed alive and responsive on the same PID.

**Cleanup is verified, not asserted.** The entry bytes read back as the original
nine, and the client's whole `.text` section — 5,473,792 bytes — was hashed before
the hook was installed and after it was removed: same digest. Since the entry patch
is the only client code this project writes, the client's code came back exactly as
it was found. That check is part of the test, not a one-off.

**Two things the test itself decides**, so a rerun is not a coin flip:

- if the declared entry bytes do not match the live ones, it **fails** and names
  both — that means the build changed or the resolver moved, and nothing is written;
- if the hook is placed and verified but the function never runs within 5 s, it
  **skips**, saying the placement was verified and the game thread is not running
  that function (a menu rather than a map) — and it removes the hook before it does.

**What is left mapped on purpose.** The block and the dispatcher — about 3 KB —
because a thread can be inside the stub at the moment of removal and about to call
the dispatcher. The same reasoning the hooker already records for the stub. This is
now the concrete cost behind the owner-loss question under Still open.

**Dead end avoided.** The reference package's bridge has `selfscan.py`,
`modules.py`, its own process reader, `events.py`, `hook.py` and 29 KB of
`bridge.py` around the same idea. None of it was adopted: the scanner, the module
lookup and the pattern catalog already existed here, and the rest would have been a
second implementation of what the four small modules in `game_thread` now do.

### Step 4 complete — the payload

Built: `py4gw/game_thread/payload.py` (the emitter) and
`tests/test_payload_offline.py` (21 tests). `build_dispatcher()` returns **330
bytes**; `dispatcher_size()` returns its length so it can be allocated before it
is built. Offline suite 432 tests green, `pyright` reports no errors. **Nothing is
compiled and nothing is checked in as a binary**: the dispatcher is x86 described
by the Python that writes it.

**What the code does**, in the order it does it: save the registers, read the
block address from the stack argument, refuse a null block, check the five header
fields that decide how everything else is read, compare the host's
`command_written` against its own `command_taken`, compute the slot of the next
command as `taken`'s low bits, refuse a record that is not `READY`, run the
operation, write the result and the terminal state, advance `command_taken`, then
write a completion event and advance `event_written`.

**The four decisions worth keeping on resume:**

| Decision | Why |
| --- | --- |
| One command per call | It runs on the game's thread, inside somebody else's function. The work per call is bounded on purpose. |
| A record that is not `READY` is left alone | The payload only owns records the host has published; anything else in that slot is not a command waiting for it. |
| The result and the terminal state land before the counter moves | A host that sees a record taken is entitled to read it as a finished one. |
| A full event region drops the event and still completes the command | The command record already carries state and result, so the event is a notification. A host that never reads events must not be able to stall the payload. |

**Operations.** `NOP`, `PING`, `ADD_U32` and `ECHO_U32` — the four that need no
call into the client, numbered as the earlier bridge design numbered them, so a
command written for either is read the same way. An operation the payload does not
know completes as `FAILED` with `RESULT_UNKNOWN_OPERATION`; that includes any
call-based operation, which waits for the call vocabulary rather than being
approximated.

**No addresses.** The dispatcher takes the block as an argument and jumps only to
its own labels, so there is not one absolute address in it. It needs no relocation
step, and the harness proves the point by placing the same bytes at two different
addresses and getting the same results from both.

**The calling convention is a contract with the stub**, and both halves are now
pinned: the stub pushes the block and calls through `eax`; the dispatcher is
`__stdcall`, saves every register it touches, and ends `popad` / `ret 4`. The
harness calls it through `WINFUNCTYPE`, which is the same convention, so a wrong
`ret` would be visible rather than silently tolerated.

**What the harness runs.** The emitted bytes are copied into memory this process
allocated with `VirtualAlloc(PAGE_EXECUTE_READWRITE)` and called against a fake
block that sits inside a larger buffer with 256 untouched bytes on either side.
Proven by execution: header checks for all five fields, a null block, an empty
queue, a record that is not `READY`, each operation's result, an unknown
operation, one command per call, order of service, both rings wrapping, the
completion event's fields, a full event region, no write outside the block,
position independence, and 200 calls in a row without the stack moving.

**What it does not prove.** The stub's bytes still have not executed — the entry
jump, the enabled/disabled branch, the register save and the `E9` into this
dispatcher are verified as bytes and not as behaviour. That is now the only
offline gap left, it is recorded under Still open, and the same harness can close
it. Nothing here has run in a client either.

**Two things the work turned up**, both recorded where they belong rather than
worked around:

- `CommandRecord.result` is signed and `EventRecord.arg2` is unsigned, so the same
  32 bits read as `-1059143458` in one and `3235823838` in the other. `PING_RESULT`
  is defined as what a reader gets from the record, because the constant is
  compared against the record in every caller; the test masks it explicitly when
  it checks the event. A silent mix-up here would have read as a passing
  comparison in one place and a failure in the other.
- The emitter refuses a constant that does not fit a one-byte immediate. Those
  forms sign-extend, so `cmp edx, 128` would have become `cmp edx, -128` inside
  the client. `EVENT_DEPTH` is 64 and fits today; the check is what makes raising
  it a build-time error instead of a wrong comparison.

### Step 3 complete — the hooker

Built: `py4gw/game_thread/hooker.py`, `tests/test_hooker_offline.py` (33 tests).
Full offline suite 409 tests green, `pyright` reports no errors.

A hook is three pieces of generated code plus one byte patch:

```text
entry patch   E9 rel32 to the stub, padded with nops to the displaced length
stub          pushfd/pushad, inc [state+4] (hits), test [state] (enabled), then
              push <block>; mov eax, <dispatcher>; call eax; popad/popfd;
              E9 rel32 to the trampoline
trampoline    the displaced bytes, then E9 rel32 back to target + length
```

`install(name, target, displaced)` allocates a 16-byte state word
(`enabled`, `hits`), the trampoline and the stub, then patches the entry **last**.
That ordering is the safety property: nothing can reach the stub before it exists,
so a failure at any earlier step frees everything it made. The entry patch is the
only step that can leave the target modified, and it is verified before it lands
by the patcher.

The state word means `disable` does not unpatch. The stub still runs, `hits` still
counts, and only the dispatch is skipped, so a hook can be quiesced without
touching code.

Two deliberate choices, both recorded in the module docstring:

- **No instruction decoding.** The hooker does not work out how many bytes a jump
  needs. The caller states the displaced bytes, so the call site owns the
  knowledge of where a whole number of instructions ends, and the hooker only
  checks that the bytes there match what was declared.
- **`remove` does not free the generated code.** A thread can be inside the stub at
  that moment, and unmapping code an instruction pointer is heading into crashes
  the client. A hits/active counter cannot close that hole: a thread that has taken
  the entry jump but not yet incremented is invisible. A few hundred bytes per
  hook are left mapped, once.

**What is not proven.** The stub's own bytes have never executed. The entry jump
into it, the enabled/disabled branch, the register save and restore, and the `E9`
into the dispatcher are verified as *bytes* and not as *behaviour*.

Step 4 has since executed the **other** half of that contract: the dispatcher now
exists, and its side is proven by running it — including the `__stdcall` epilogue
the stub depends on. What the stub does on the way in is still unexecuted, and
closing that is the first item under Still open.

### Step 2 complete — the installer

Built: `py4gw/win32/write_access.py`, `py4gw/game_thread/patcher.py`,
`tests/test_patcher_offline.py` (19 tests). Full offline suite 376 tests green,
`pyright` reports no errors.

Two files, on purpose. `Win32` documents itself as never requesting permission to
write or execute code in another process, and that guarantee is worth keeping, so
the invasive surface lives beside it rather than inside it. `WriteAccess` opens one
process with `PROCESS_CREATE_THREAD | VM_OPERATION | VM_READ | VM_WRITE |
QUERY_INFORMATION` and provides allocate, write, free, protect, flush, plus thread
enumeration, suspend, context (EIP), resume and close. It refuses to open a
transport to `os.getpid()`, because suspending the controller's own threads would
hang it.

`Patcher` performs no Win32 calls of its own — it takes an object providing them,
so the sequence and every refusal are testable with no client. The sequence:

1. read the bytes and confirm they are what is expected, before touching anything;
2. suspend every thread of the target;
3. read each thread's EIP and refuse if any is inside the range about to be
   overwritten — release, wait 2 ms, retry, and time out rather than write;
4. re-read and re-confirm, because the bytes could have changed while suspending;
5. protect writable, write, flush the instruction cache, restore protection;
6. release every thread and close every handle, on success, refusal and timeout.

Restoring is conditional: if the bytes there are no longer the ones this installer
wrote, it refuses and leaves the target alone rather than putting stale bytes back.

One deliberate divergence from the reference: it treated an EIP outside a known
executable region as implausible and refused. A thread parked in a system DLL is
ordinary, so that test refused legitimate patches. Here only a zero instruction
pointer is treated as untrustworthy, which is what an unfilled context reads back
as.

**Verified live.** `tests/test_write_access.py`, run from an elevated shell against
`Gw.exe` PID 15380 (Guild Wars Reforged): **10 tests, all passing.** The sequence
that had only ever run against a fake target has now run against the real process —
client threads suspended and resumed, their instruction pointers read, page
protection changed, the write landed, the instruction cache flushed, and the
original bytes restored. The read-only transport was checked in the same run and
still works, so the boundary between the two is measured rather than assumed.

Scope of that run: **every write targeted memory the test allocated itself with
`VirtualAllocEx`.** The client's own memory — its code and its data — was not
modified, and the allocation is asserted to lie outside the client module. Every
allocation was released, the transport was closed, and the client was left running
and responsive on the same PID.

Unelevated, the same suite skips with that reason recorded: Windows denies
`PROCESS_VM_WRITE`, `PROCESS_VM_OPERATION` and `PROCESS_CREATE_THREAD` with error 5.
That was confirmed live as well, before the elevated run.

The recorded run, target, expected and observed behaviour, and the cleanup check
are in [`RESEARCH.md`](RESEARCH.md), including a module-size discrepancy the run
turned up that the trust anchor has to settle.

### Step 1 complete — the shared block

Built: `py4gw/game_thread/shared_block.py`, `py4gw/game_thread/__init__.py`, and
`tests/test_shared_block_offline.py` (34 tests, no client, no writes). The full
offline suite is green and `pyright` reports no errors.

What it is: the layout and the queue rules for the block of memory inside the
client that both the host and the payload read. Stealth's own infrastructure —
Reforged has no counterpart, because its queue is a `std::vector` in its own
address space.

The design decisions taken, so they are not re-litigated on resume:

| Decision | Choice | Why |
| --- | --- | --- |
| Regions | two, one per direction | each then has exactly one writer, so no shared mutable state |
| Counters | `written` and `taken` per region, one writer each | two single-writer counters remove the "sacrifice a slot" trick the reference needed to tell full from empty, and waste nothing |
| Torn records | producer fills the record, then advances its counter; consumer reads only below it | no per-record marker, one store per record, and a partial record is unreadable by construction |
| Record size | fixed | variable means trusting a length off the wire and bounds-checking it |
| Stale region | magic, version, header size, depths and a per-attach session id, all validated | every mismatch fails closed |
| Command state | `READY` written by the host; `RUNNING` and a terminal state written by the payload only | lets the host see completion per record without a second queue |

Layout: 64-byte header, then 16 command records of 32 bytes at offset 64, then 64
event records of 32 bytes at offset 576. Total 2624 bytes. The constants live in
the module and are validated on decode, so a payload and a host that disagree
fail rather than misread each other.

What it deliberately is not: it does not adopt the reference package's module
split, object model or record layout. Three of that package's modules duplicate
capability we already own — `selfscan.py` for `RemoteScanner` + `PatternCatalog`,
`modules.py` for `Win32.get_main_module`, and its process reader for
`ProcessMemoryReader` — and are not re-created here.

### Originating plan

Phases 1-4 are complete. The first pointer-acquisition problem that motivated this
plan — three contexts captured only through UI callbacks — was resolved without
any target-side code: both map contexts are live-verified read-only through the
client's UI frame array, open and closed, and the third (`SalvageSessionInfo`) is
unused by both reference projects. See
[`UI_FRAME_TREE.md`](UI_FRAME_TREE.md) and the live records in
[`RESEARCH.md`](RESEARCH.md).

The inventory still holds: exactly four pointers require a hook or callback in
the source project — the two map contexts, `g_salvage_context`
(`src/GW/item/item.cpp:211-225`), and `g_dx_context`
(`src/GW/render/render.cpp:75-111`). The first two are reached read-only, the
third is not a consumed surface, and the fourth is outside the required
in-game context scope.

What remains for target-side code is breadth, not the mechanism: decoded
`ChatBuffer` history, concrete Native operations, and more call forms and callback
kinds on the layer that already exists.

**Update 2026-09-23.** The game-thread bridge mechanism now exists and is
verified live: hook installed, fired, restored; queue served on the game
thread; `agent.move_to_func` called with the source-backed `float[4]` layout,
moving the character exactly 10 units. The controller must run **elevated** —
an unelevated one is denied the write/allocate/suspend rights by ordinary UAC
token splitting, which an earlier note here mis-described as a client
protection. No bytes remain written to any client. See the Phase 5 status above
and [`RESEARCH.md`](RESEARCH.md).

That update describes the **reference package under `external/`**, which is what
proved the mechanism was possible. Stealth's own version of it was built in five
steps afterwards and is live-verified in its own right — see the resume record
above. The difference that matters: the reference ships a C source, a build script
and a checked-in 604-byte binary; this project ships none of those, and emits its
330-byte dispatcher from Python instead.

**Update 2026-09-24.** Steps 1 to 6 of the Stealth implementation are done and the
chain is live: `tests/test_live_bridge.py` installs our hook on
`leave_game_thread_func` in the running client, runs our operations on the game
thread, reads their results and events, and restores the original bytes — with the
client's whole code section hashed before and after to show it came back identical.
The call vocabulary is built for two typed forms and is live-verified; callbacks are
built, registry and listener both. What remains is breadth — more forms, more kinds,
and porting members onto them. The cost that is now
measured rather than theoretical: each attach maps about 3 KB in the
client, and while `disconnect()` frees what it placed, an attach whose controller
was killed leaves it behind.

