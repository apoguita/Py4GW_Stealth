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
The selected architecture for Native's callback-owned pointers and
game-thread operations is a small Stealth-owned payload or patch in the client,
without loading a conventional DLL. This still modifies the process and is
injection. The no-DLL choice describes the delivery approach; it does not mean
the target is unmodified or that the payload is undetectable. The current
Stealth implementation remains read-only; no payload, patch, remote thread,
or target-side call has been implemented or tested as part of this inventory.

The first pointer the payload was planned for, the WorldMap context in
[`CALLBACK_POINTER_RESEARCH.md`](CALLBACK_POINTER_RESEARCH.md), now has a
read-only route through the client's UI frame array; it is implemented and
offline-verified, but not yet confirmed on a live client. See
[`UI_FRAME_TREE.md`](UI_FRAME_TREE.md). The payload remains the fallback for
that pointer and the mechanism for the work that genuinely needs target-side
code.

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

### Phase 6 — Remaining hook and callback families (not started)

- [ ] Work module by module from the inventory above: UI, events, packet,
  effects, render, agent, chat, friend list, item, map, merchant, party,
  skillbar, and other listed call sites.
- [ ] For each, first mark source behavior as active, disabled, or conditional;
  then port exact callback order, original-call behavior, and cleanup.
- [ ] Exclude crash-handler hooks and any behavior not used by Native's
  Guild Wars feature surface unless a later source audit changes that scope.

## Resume record

Current resume point: **Phase 5, the game-thread bridge.** Phases 1-4 are
complete. The first pointer-acquisition problem that motivated this plan —
three contexts captured only through UI callbacks — was resolved without any
target-side code: both map contexts are live-verified read-only through the
client's UI frame array, open and closed, and the third (`SalvageSessionInfo`)
is unused by both reference projects. See
[`UI_FRAME_TREE.md`](UI_FRAME_TREE.md) and the live records in
[`RESEARCH.md`](RESEARCH.md).

The inventory still holds: exactly four pointers require a hook or callback in
the source project — the two map contexts, `g_salvage_context`
(`src/GW/item/item.cpp:211-225`), and `g_dx_context`
(`src/GW/render/render.cpp:75-111`). The first two are reached read-only, the
third is not a consumed surface, and the fourth is outside the required
in-game context scope.

What remains for target-side code is execution, not acquisition: the
game-thread bridge, decoded `ChatBuffer` history, and concrete Native
operations. No live mailbox transfer, payload, hook, target write, remote
thread, or live patch test has been implemented, and no bytes have been written
to any client.
