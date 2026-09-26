# Callback pointer research

> **Status after the frame-array work (2026-09-23).** The motivating use case for
> this document — acquiring `WorldMapContext` and `MissionMapContext` without a
> hook — was resolved read-only, and both routes are live-verified open and
> closed. See [`UI_FRAME_TREE.md`](UI_FRAME_TREE.md). The payload contract below
> is retained for the work that still needs target-side code. That code has since
> been built elsewhere and for different targets: `py4gw/game_thread/` installs
> two entry hooks, an emitted dispatcher and an observer, and `py4gw.connect()`
> installs it by default. **The WorldMap callback detour this document specifies has
> not been ported yet**, because the frame-array route reaches the same pointer without
> one; the mechanism it was waiting on now exists.

## Direction

Py4GW Stealth must be self-sufficient. Py4GW Reforged and
Py4GW_Reforged_Native are source references, not runtime dependencies. Stealth
must not require their DLL, Python runtime, or shared-memory mapping to obtain
game data.

The Native project is the primary reference for where Guild Wars pointers
come from and when they are valid. For each required context, record whether
its pointer is available through a direct source getter, a maintained pattern
or pointer chain, a callback/hook, or an unresolved mechanism. Do not guess a
new source when the Native implementation already identifies one.

Some context pointers are published only after the Native project receives a
Guild Wars UI callback. The current Stealth readers for `MissionMapContext`
and `WorldMapContext` are ready for a supplied address, and that address is now
obtained read-only through the client's UI frame array — the same value the
callback would publish. Reforged Native
identifies the callback route and pointer-lifetime behavior; the selected
Stealth implementation is stated below.

### Read-only frame-array route (implemented first)

The callback is not the only way to the same pointer. `Gw.exe` keeps a global
UI frame array in a module global that Stealth's existing `ui.frame_array_addr`
resolver addresses, and each frame stores its registered context pointer for
the lifetime of the frame. Reading that slot reproduces the value a callback
dereferences, with no hook, no payload, and no write.

`py4gw/ui/` implements this route, and three contexts acquire their root
through it: `WorldMapContext` (frame-id offset `0x0`), `MissionMapContext`
(`0x14`), and `SalvageSessionInfo` (`0x4`). Evidence, layout, and the read-only
test procedure are in [`UI_FRAME_TREE.md`](UI_FRAME_TREE.md). Live resolution,
array structure and the open/close handoff are **verified** for the two map
contexts on PID 29520 — the publishing frame, the frame-id cross-check, and the
cleared state after close were all read back. `SalvageSessionInfo` is resolved
but its open/close handoff is untested.

This does not retire the payload plan below. It removes the map and salvage
surfaces as features that forced the mechanism to exist before it was needed,
and it leaves the payload for the cases that still need target-side
code: game-thread operations, the `GwDxContext` `EndScene`/`Reset` detour, and
any future context whose owner is not readable.

Architecture decision for those remaining cases: Stealth's external controller
installs its own small payload/patch to capture the source-backed callback
and publish the pointer. A conventional DLL injector and a Reforged runtime are
not part of this design. The payload modifies `Gw.exe` and is injection; “no
DLL” does not mean the target is unmodified or that the payload is
undetectable. That mechanism is now built and live-verified in
`py4gw/game_thread/` for its own two targets; the WorldMap callback detour below
is not among them.

## Source evidence

In Reforged Native, `OnWorldMap_UICallback` and `OnMissionMap_UICallback`
capture the context pointer from the UI message's `wParam` and clear the saved
pointer when the UI frame is destroyed. `Manager::UpdatePointersRegion` then
copies those DLL-owned pointer values into Reforged's shared-memory region.
That mapping explains how Reforged exposes the pointers, but Stealth must not
depend on it as its own runtime solution.

The offsets also contain `ui.world_map_state_addr`. Native's
`GetIsWorldMapShowing()` reads that separate state word and checks bit
`0x80000`. This can indicate whether the WorldMap UI is visible, but it does
not contain or resolve `WorldMapContext`; it is not a substitute for capturing
the callback pointer. The flag may help the operator confirm that the map was
opened or closed during the callback test, but it is not an alternate
pointer-acquisition route. The selected plan remains callback capture; the
flag's live transition has not yet been tested in Stealth.

## Resumable first callback plan

### Intent and scope

Make the already-ported `WorldMapContext` reader receive its real root address
from the same UI callback route used by Native. Work on one callback only;
`MissionMapContext`, commands, and other in-game actions come after this path is
proven. Stealth remains independent: its own controller installs and
removes the target-side code, and it does not use Reforged's DLL or shared
memory.

For the first pointer handoff, the selected prototype scheme is one
Stealth-owned x86 callback detour and a small target-side mailbox. The
external controller allocates a separate executable region for the
position-independent callback/trampoline code and a non-executable region for
the mailbox, then redirects the resolved callback entry to that code. The
controller reads the mailbox through its existing process-memory reader.
The callback itself is the entry point; this first feature does not create a
remote thread. This is not a DLL, named shared-memory mapping, command queue,
or general-purpose remote-call system. The detour must forward the callback
before observing its message, matching Native's order.

The callback target is resolved from the maintained source-backed signature
for the selected client. Installation must confirm the expected bytes and
instruction boundaries before redirecting execution; the saved original
instructions must be represented correctly in the trampoline. This document
sets those behavioral requirements, not the machine-code implementation.

#### Manual execution ownership

The project owner performs the target-changing work manually. The plan does
not call for unattended payload installation, map toggling, or cleanup. For
the live test, the owner starts the locally built tool, waits for its ready
signal, opens the map, confirms it is open, waits for the data result, closes
the map when asked, confirms it is closed, and initiates detach. The tool may
report state, but it must not manipulate the Guild Wars UI on the owner's
behalf.

If this callback route fails, stop and investigate the source-backed payload
and its behavior. Do not substitute the map-visible flag, a read-only scan, or
another pointer guess for the chosen callback capture.

### Read-only preflight observation

On 2026-09-23, one running `Gw.exe` candidate was found (PID `29520`;
`F:\GW\GW1\Gw.exe`). The file was x86/PE32, 10,493,120 bytes, with SHA-256
`44FBD68767A8D02B5DD4FB1A8A09B684A86B24716731327EE64905DD698FE124`.
The module was based at `0x00FC0000`, size `16,027,648`. Resolver
`map.world_map_ui_callback_func` succeeded at `0x0110B5A0`, inside `.text`
(`0x00FCE000`–`0x013F7000`); the matching signature was at `0x0110B5C4`.
The first 16 bytes at the resolved function address were
`55 8B EC 83 EC 54 8B 45 08 56 8B 48 08 8B 40 04`.

This was a read-only resolver/byte inspection only. The user stated that this
was the only Guild Wars client running; the map was not opened or closed for
this observation, and no callback invocation or patchability was tested.
Re-enumerate and revalidate the PID and build immediately before a future live
test; addresses can change when the process restarts.

This selects a testable first scheme; it does not settle how every later
Native hook or parameter form will be represented. Those can be added as
separate, typed extensions when a concrete Native feature needs them.

### First-use-case contract

#### Callback behavior to reproduce

Native declares `UIInteractionCallback` as
`void __cdecl(InteractionMessage*, void*, void*)`. `InteractionMessage` has a
32-bit `frame_id`, a `message_id`, and a `void** wParam` field. Its WorldMap
callback does the following, in this order:

1. Calls the original callback once with the original three arguments.
2. If `message` and `message->wParam` are non-null, dereferences
   `message->wParam` once and records that `WorldMapContext*`.
3. If `message->message_id` is `kDestroyFrame`, clears the recorded pointer,
   even if the previous condition did not provide a pointer.

The callback returns `void`; there is no return value to synthesize. A null
`message` or null `message->wParam` on a non-destroy message leaves the last
pointer unchanged, matching Native. The first port is WorldMap only.

#### Mailbox record

Use a fixed 24-byte, x86 record. All fields are little-endian; the target
pointer is always `uint32`, never the controller's native pointer size.

| Offset | Size | Field | Meaning |
| --- | ---: | --- | --- |
| 0 | 4 | `magic` | Identifies this mailbox format. |
| 4 | 2 | `version` | Starts at 1; unknown versions are rejected. |
| 6 | 2 | `size` | Record size, exactly 24 for version 1. |
| 8 | 4 | `session_id` | Fresh controller-generated value for each installation. |
| 12 | 4 | `sequence` | Seqlock counter: odd while writing, even when stable. |
| 16 | 4 | `state` | `EMPTY=0`, `VALID=1`, `CLEARED=2`, `STOPPING=3`. |
| 20 | 4 | `context_address` | x86 `WorldMapContext*`; zero unless state is `VALID`. |

The callback writer updates the state and pointer between an odd and even
sequence value. The external reader accepts a record only if two reads show
the same even sequence and the expected magic, version, size, and session ID.
It treats `EMPTY` as not observed yet, `VALID` with a nonzero address as
available, `CLEARED` as no current context, and `STOPPING` as detached. Any
other combination is invalid, not a pointer to try.

The session ID prevents data from a previous attachment being accepted after
reconnect. The controller also binds the mailbox to its selected process
handle/PID; a PID change or closed process handle invalidates the connection.
The pointer is then passed to the existing bounded
`ConnectedClient.read_world_map_context()` path. A failed structure read is
reported separately from an absent or cleared pointer.

#### Install, forwarding, and removal requirements

- Resolve the callback target from the maintained offset/signature data for
  the selected client. Confirm x86 architecture and the expected target bytes
  before changing anything; abort if they do not match.
- Save the exact bytes to be replaced and create an original-call path that
  safely accounts for the replaced instructions. Do not overwrite a target
  that changed after resolution.
- Install only the WorldMap callback detour and this mailbox. Do not include
  MissionMap, generic game-thread commands, or unrelated hooks in this test.
- The detour forwards the original callback exactly once, with unchanged
  arguments, before publishing or clearing the pointer. Callback-side mailbox
  updates must not wait on the external controller.
- On normal detach, stop new callback dispatch, mark `STOPPING`, wait until
  no detour is in flight, restore the original bytes only if the installed
  patch is still present, then release target allocations. If any step is
  uncertain, do not free code or data that could still be in use.
- If the controller exits unexpectedly after installation completed, the
  target-side code and mailbox remain allocated. The callback stub has no
  dependency on the controller: it continues forwarding the original callback
  exactly once and only refreshes the pointer record. It does not accept
  commands. This avoids redirecting the client into freed memory, but does
  mean the patch remains until a later controller performs a verified detach
  or the client exits.
- On reconnect, the controller must recognize and validate the existing
  Stealth stub at the resolved callback entry before acting. It may attach to
  that known version or detach it cleanly; it must never stack another hook on
  top. If the branch target, stub header, version, or saved original bytes do
  not match expectations, stop without modifying the client.
- If controller loss occurs partway through installation, the controller
  must not publish the callback redirect until code, trampoline, and mailbox
  are complete and validated. The actual-client test procedure must cover
  setup failure and the recovery action. An unrecognized or partially written
  redirect is a hard failure, not something to patch over automatically.

The callback behavior must ultimately be verified in the actual Guild Wars
client. Offline checks are limited to the mailbox record's layout and
validation rules; they do not stand in for a real-client callback test. No
live patch is installed until the exact test scope, selected PID/build,
restoration procedure, and failure response are written down.

### Work plan and resume point

Status, in two parts. **The motivating case is closed:** the frame-array route to
the same pointer is implemented and live-verified open and closed, so neither map
context needs a callback. **The WorldMap callback hook itself is still not
implemented**, and the mechanism it would use now exists in `py4gw/game_thread/`.
The callback contract is complete and the mailbox-format codec and its offline tests
pass. Continue with the first unchecked implementation item if a surface still needs
a callback; live map testing is no longer required for the two map contexts.

- [x] Confirm the Native callback source and its pointer behavior: call the
  original callback, read through `message->wParam`, and clear the saved
  pointer on `kDestroyFrame`.
- [x] Confirm the callback is x86 `__cdecl` with three arguments and that the
  `InteractionMessage` contains `frame_id`, `message_id`, and `void** wParam`.
- [x] Confirm Stealth has the matching JSON callback signatures and that all
  loaded resolver chains passed on one live client. See the live record in
  [`RESEARCH.md`](RESEARCH.md); this confirms address resolution, not hook
  safety.
- [x] Record the exact callback input: the function arguments are
  `(InteractionMessage* message, void* wParam, void* lParam)`. Native reads
  the `void**` field `message->wParam`—not the callback's second argument—
  and dereferences it once to obtain the context address.
- [x] Define the fixed-width mailbox record, coherent-read check, clear state,
  and attachment identity.
- [x] Define how the controller binds and validates the record before passing
  a nonzero address to `ConnectedClient.read_world_map_context()`.
- [x] Define callback forwarding, install validation, detach order, and the
  requirement not to free memory while the detour may still be running.
- [x] Define owner-loss behavior after successful installation: keep the
  self-contained, command-free forwarding stub resident and require validated
  recovery or clean detach on reconnect.
- [x] Check the 24-byte mailbox record format offline; see
  `tests/test_mailbox.py`.
- [x] Run the read-only callback preflight against the only running client,
  `Gw.exe` PID 29520. The address/signature and readable target bytes are
  recorded in [`RESEARCH.md`](RESEARCH.md); this does not establish that the
  callback has fired or that a hook is safe.
- [x] Define the one-client test procedure, including PID/build selection,
  a fresh read-only preflight immediately before any future target change,
  user-confirmed WorldMap open/close stages, normal detach, and client-exit
  recovery if detach cannot be confirmed.
- [x] Implement the read-only frame-array route to the same pointer:
  `py4gw/ui/` primitives, the `FrameTree` walk, the frame-id cross-check, the
  offline tests, and `tests/preflight_frame_context_route.py`. See
  [`UI_FRAME_TREE.md`](UI_FRAME_TREE.md). This changes nothing in the client.

**The selected design contract is complete; the callback behavior is untested.**
The mailbox format checks pass. The
read-only frame-array route is implemented and **confirmed on a live client** for
both map contexts, with the surface open and closed, so the payload is not needed
for them. `SalvageSessionInfo` resolves through the same route but its open/close
handoff has not been tested. If a later surface does need a callback, the next
implementation step is that detour and its reviewed rollback. Before any live
target test, repeat the
read-only preflight against the selected client. Do not build a mock Guild
Wars callback target. A live callback test must be limited to the capture it
installs, the pointer clear, and clean detach. The user performs the surface
open/close actions while present; reconnect/owner-loss recovery is later work.

### Real-client test procedure

This is the planned interactive test for the callback detour. It is not needed for
the two map contexts, which are reached read-only, and it is not ready to run until
the WorldMap detour and rollback path exist and have passed code review.

1. The user starts one Guild Wars client and identifies the PID to use. The
   controller confirms that it is the expected x86 client and records the
   client build/module identity.
2. Immediately before any target change, run
   `python tests/preflight_frame_context_route.py --pid <pid> --once` and
   confirm each callback resolves inside its `.text` section. That preflight
   only reads memory; it neither proves the callback is being called nor
   changes the target.
3. Before changing the target, the controller checks the expected bytes and
   records the original bytes and recovery information. Any mismatch stops
   the test.
4. The controller installs only the WorldMap callback capture and mailbox.
   It reports when it is ready and waits for the user. It does not open,
   close, or otherwise control the map. The user must remain present for the
   entire live test; there is no unattended or timed map-toggle test.
5. Only after the controller says it is ready, the user opens the WorldMap
   and tells the controller it is open. The controller then reads the mailbox
   and the context through the existing bounded WorldMap reader. A nonzero
   address alone is not a pass: the context read must succeed and the game
   must remain responsive. The controller reports the result before asking
   the user to continue.
6. After the controller asks, the user closes the WorldMap and confirms it is
   closed. The controller confirms that the callback published the cleared
   state and that the old address is no longer offered as current.
7. The controller detaches, confirms that the original callback bytes are
   restored, and verifies the client continues normally. If restoration is
   uncertain, the controller preserves allocations that may still be in use
   and makes no further changes. If a safe restore cannot be completed, the
   user closes that Guild Wars client normally; process exit discards its
   in-memory patch and allocations. Do not start another test until the client
   has been restarted and rechecked.

The user actions and confirmations are essential. The controller must wait
for the user to make the WorldMap appear, report the read result, then ask the
user to close it and wait for confirmation. Do not run those stages as an
unattended test, and do not ask the user to manipulate the map until the
install/detach path is implemented, reviewed, and ready to report its status
clearly. That path is not implemented, so no map manipulation is needed yet.

### Later work (not started)

1. Implement and review the bounded WorldMap capture and rollback path if a
   surface needs a callback; no read-only route covers that case yet. Live patching
   itself is no longer hypothetical — `py4gw/game_thread/` installs two entry
   hooks and restores them, verified live.
2. When the implementation is ready, run the interactive test above with the
   user present; do not automate the map open/close actions or run this stage
   unattended.
3. If detach cannot be verified, do not free target code/data; use the
   documented recovery procedure and stop further testing.
4. Test reconnect/owner-loss handling for the new hook, then repeat for
   any further callback-owned context.

## Evidence boundaries

- Reforged Native establishes source behavior, not that Stealth has reproduced
  it; the frame-array route to the map contexts is Stealth's own boundary
  difference, not a reproduction of the source's callback.
- Reforged Python documents how the in-process facade consumes the published
  pointer; it is not a runtime dependency for Stealth.
- GwAu3 and MemLib are comparative references only. Their code does not define
  Stealth's pointer paths or approve copying their mechanisms.
- A pointer that is still unresolved in Native remains unresolved here; do not
  infer a callback or nearby-field relationship without source evidence.

The current source-by-source context inventory is in
[`CONTEXT_PARITY_AUDIT.md`](CONTEXT_PARITY_AUDIT.md). Runtime-changing work and
its approval gate are recorded in
[`TARGET_SIDE_WORK.md`](TARGET_SIDE_WORK.md).
