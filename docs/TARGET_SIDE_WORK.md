# Target-side implementation work list

This document is the work list of target-side code, writes, patches, and hooks that
are selected for Stealth. The architecture is decided and **built**: an
external controller installs Stealth-owned target code without a
conventional injected DLL. This is still injection. What follows records both what
now exists in `py4gw/game_thread/` and what is still to port on top of it, each
entry naming its next step; nothing below is treated as complete. See
[`NATIVE_EXECUTION_PLAN.md`](NATIVE_EXECUTION_PLAN.md) for the source inventory
and resumable overall plan.

This is also the register that [`PORTING_RULES.md`](PORTING_RULES.md) points to:
when a ported member needs target-side code, its entry goes here rather than in a
list of its own. Single-member entries that are not capability gaps stay in that
module's port doc.

## Current boundary

The current Stealth implementation may enumerate Guild Wars processes, scan
their modules, read validated memory ranges, and materialize bounded
source-defined structures. It **does** now write: `py4gw.connect()` installs the
capability layer, which means `py4gw/win32/write_access.py` opens the client for
writing, `patcher.py` puts nine-byte and eight-byte entry patches on two of its
functions, and `hooker.py` places generated stubs, a trampoline, a dispatcher and an
observer in memory allocated inside the client. `py4gw.disconnect()` restores both
functions' own bytes and frees everything it placed, and a controller that dies
mid-install is recovered from — a stale patch of ours is repaired, suspended client
threads are counted and can be resumed.

It still creates **no remote thread** and loads **no DLL**. It does call Guild Wars
functions: only through a descriptor a caller registered for that exact function and
argument form, which is how the live call test ran `ui.send_ui_message_func` and
`agent.change_target_func`. The client's code and memory
are modified while connected, so this is **payload injection** as defined above, and
the sections below list what is still to port on top of it rather than instead of it.

**Built, and now verified in a client.** The mechanism exists in the library: the
shared block and its queue rules (`py4gw/game_thread/shared_block.py`), the
fail-closed patch sequence (`patcher.py`), the entry hook (`hooker.py`), the
dispatcher the hook calls (`payload.py`) — emitted as machine code from Python, so
there is no compiler, no build step and no checked-in binary — and the host side
that publishes work and reads results (`bridge.py`). `tests/test_live_bridge.py`
runs the whole of it against the live client: it resolves
`leave_game_thread_func`, installs the entry hook, publishes commands the client's
own game thread runs, reads their results and events, and restores the function's
original bytes. The client's code section is hashed before and after and comes back
identical, so the nine-byte entry patch is the only client code ever written.

That is **payload injection** as this document defines it. It is what
`py4gw.connect()` installs by default and what `py4gw.disconnect()` removes, and the
live tests run it from an elevated shell with a rollback they verify. What the call
vocabulary still lacks is breadth: seven forms now cover the source's own function
declarations — no arguments, one, two, three and five words, a pointer to a four-float
array, and a message with a packed payload — and the forms still missing are the ones
with a **string** to place in the client rather than a pointer to one. A call's return
value and a writable data region in the block are in use
(`shared_block.COMMAND_OFFSET["value"]`, `data_offset`): the GW.dat read returns the
client's record and buffer pointers through the first and hands over its hash string and
size word through the second, live. The first eleven `Player` actions are ported onto the
forms that exist. See
[`PLAYER_PORT.md`](PLAYER_PORT.md) for that port and the members still to port
within it, and
[`NATIVE_EXECUTION_PLAN.md`](NATIVE_EXECUTION_PLAN.md).

`External host` does not mean `non-injected` by itself. A payload that is
written into the process is still injection even when Python remains outside.

**Live status (2026-09-23).** The game-thread bridge has now been verified
against the live client, and the mechanisms below are no longer speculative:
an entry hook on `leave_game_thread_func` was installed, fired, and restored,
the queue was serviced on the game thread, and `agent.move_to_func` was called
with the source-backed argument layout, moving the character exactly 10 units.
A one-right-at-a-time `OpenProcess` probe showed the decisive constraint:
`PROCESS_VM_WRITE`, `PROCESS_VM_OPERATION`, `PROCESS_CREATE_THREAD`, and
`PROCESS_SUSPEND_RESUME` are denied to an **unelevated** controller
(Windows error 5) and granted to an **elevated** one. This is ordinary UAC
token splitting, not a client protection filter — an earlier note here said
otherwise and was wrong. All target-side work on this client therefore requires
an elevated controller, which is a real change in the trust boundary: the
controller holds administrator rights over the machine. Full evidence and the
live run output are in [`RESEARCH.md`](RESEARCH.md). Callbacks are no longer
unimplemented: `py4gw/game_thread/callbacks.py` adds a registry keyed by event kind
and `EventListener`, a listener thread that reads the event region and delivers each
event as it arrives. What is thin there is the number of kinds — one per hooked
function — not the mechanism.

## Reference implementation on disk (not adopted)

`external/py4gw_stealth_game_thread_bridge_callbacks/` — imported 2026, kept under
the gitignored `external/` tree. It is **reference material for building our own**,
not a dependency: nothing was copied into `py4gw/` and `install_overlay.ps1` (which
copies `py4gw/execution/*.py` into a checkout) was deliberately not run.

It is Stealth's own prior research, so it is **neither** Reforged nor Native, and the
"where each member may come from" list in [`PORTING_RULES.md`](PORTING_RULES.md)
does not cover it. Treat it as a worked design to study and re-implement.

### What it is

ABI v3, bidirectional. A 604-byte relocation-free x86 dispatcher is injected and
reached through a 9-byte entry patch on `game_thread.leave_game_thread_func`:
Python produces into a **command ring**, the dispatcher produces into an **event
ring**, and **callbacks always execute in Python** — the target only writes
fixed-size records.

### Verified offline (its own verifier, no client opened)

```text
Bridge ABI: OK (64-byte header, 16x36-byte command ring, 128x32-byte event ring, 4736 bytes total)
Reverse event channel: OK (64 subscription bits + dropped-event counter)
Module-bound guard: OK (published 0x00400000+0xC00000)
WOW64 patch-safety structs: OK (THREADENTRY32=28, CONTEXT=716, EIP+184)
Dispatcher: OK (604 bytes, SHA-256 7939b258…ac2a24fd)
Position independence: OK (1 in-payload E8/E9 rel32 branch)
Game-thread hook builder: OK (9-byte entry patch, 45-byte stub, 14-byte trampoline)
```

### What we already have

- **The offsets catalog is the same one.** `offsets/` at the repo root is
  byte-identical to the package's 30 files (every hash matches) and is already
  git-tracked. All three resolvers it needs are present: `agent.move_to_func`,
  `agent.player_agent_id_addr`, `game_thread.leave_game_thread_func`.
- **The resolver engine is ours already.** `PatternCatalog` plus `RemoteScanner`
  implement all 12 ops used across the catalog's 233 resolvers, so the package's
  ~23 KB `selfscan.py` duplicates capability we own.
- **No third-party dependencies.** The package is stdlib + `kernel32` only, and
  `bridge.py` deliberately imports nothing from `py4gw`.

### What was actually missing, and where each piece now lives

When this section was written, all four pieces below were absent. Each now exists
in Stealth's own form — not the reference's — and is live-verified.

1. **A write/allocate transport.** `py4gw/win32/write_access.py` implements the
   Win32 surface the reference uses: `OpenProcess` (a second handle with
   `VM_WRITE | VM_OPERATION | CREATE_THREAD | QUERY_INFORMATION`, separate from the
   read-only one), `VirtualAllocEx`, `WriteProcessMemory`, `VirtualProtectEx`,
   `VirtualFreeEx`, `FlushInstructionCache`, `CreateToolhelp32Snapshot` with
   `Thread32First/Next`, `OpenThread`, `SuspendThread`, `ResumeThread`,
   `GetThreadContext`, and `CloseHandle`. Module enumeration is not part of it —
   the module window comes from `Win32.get_main_module` on the read side.
2. **A position-independent dispatcher payload.** `py4gw/game_thread/payload.py`
   emits its own dispatcher — the project's equivalent, not the reference's bytes.
3. **An entry-patch installer with save/restore.**
   `py4gw/game_thread/patcher.py` and `hooker.py`, with the displaced bytes
   declared by the caller rather than decoded.
4. **The ring consumer and callback registry.** `py4gw/game_thread/bridge.py` and
   `callbacks.py`, including the listener thread that consumes the event region.

### Design facts a re-implementation must reproduce

- **Layout.** Header 16×u32 at +0, in the order `magic(0x57473450)`, `version(3)`,
  `read_index`, `write_index`, `capacity(16)`, `reserved`, `heartbeat`,
  `module_base`, `module_size`, `event_read_index`, `event_write_index`,
  `event_capacity(128)`, `event_dropped`, `event_mask_lo`, `event_mask_hi`,
  `event_reserved`. Command ring 16×36 at +64; event ring 128×32 at +640; total
  4736. Command slot: `state(volatile), sequence, opcode, arg0..arg3, result(i32),
  result0`. Event slot: `sequence, type, arg0..arg3, tick, result(i32)`.
  The compiled payload independently attests this: every displacement in the
  shipped disassembly matches these offsets and strides.
- **Entry contract.** One `uint32_t __stdcall bridge_dispatch_once(Bridge*)` at
  **offset 0** of a relocation-free image, returning `1` executed / `0` idle or
  not-ready / `0xE001..0xE005` for a validation refusal (null bridge, then magic,
  version, command capacity, event capacity — returning **before** any other
  effect, so a mis-published header stalls rather than executes).
- **Index discipline.** `heartbeat` increments once per *validated* call, before
  anything else, and every event stamps `tick` from it. Then read both indices,
  return when equal, and dispatch **only** the head slot and **only** when its
  state is `CMD_READY` — that test is the sole guard against double execution, and
  a head that never becomes ready stalls the whole ring. **One command per call**,
  no loop. Write `result`, `result0`, the terminal state, then store
  `read_index = r + 1` as a literal. The payload **never writes `CMD_FREE`** —
  slot recycling is entirely the producer's job.
- **Opcodes.** `NOP=0`, `PING=1` (`result0 = 0xC0DEC0DE`), `ADD_U32=2`
  (`result0 = arg0 + arg1`), `ECHO_U32=3` (`result0 = arg0`), `MOVE=4`; anything
  else is `-100`. For `MOVE`, `arg3` is the raw function address and `arg0..arg2`
  are three float bit patterns passed as `{x, y, zplane, 0.0f}` to a
  `void (__cdecl*)(float*)` — the caller cleans the stack.
- **Refusals are terminal and observable.** A refused command still gets
  `state = CMD_ERROR`, a negative `result`, `read_index` advanced, and a forced
  completion event. Success leaves `result = 0`, `result0 = 0`, `CMD_DONE`.
- **Position independence.** No absolute-address instruction, no imports, no CRT,
  no jump table, no security cookie, no self-modification; every operand is
  register-relative; control flow is internal and near-relational only. The build
  parses COFF section headers and **refuses to emit** if any `.text` section
  carries a relocation, then rewrites the binary, its SHA-256 sidecar and the
  embedded Python literal together so they cannot drift.
- **Subscription.** `type < 32` → bit `type` of `event_mask_lo`; `32..63` → bit
  `type-32` of `event_mask_hi`; `>= 64` → never subscribed. `GAME_TICK` is
  mask-gated; `COMMAND_COMPLETE` is forced and ignores the mask.
- **Overflow.** Non-forced events stop at 120 pending (reserving the last 8 slots,
  256 bytes, for completions); forced events stop at 128. Both increment
  `event_dropped` and write **no** slot fields. An unsubscribed tick increments
  nothing.
- **Patch safety (fail-closed).** Verify the entry bytes before patching; refuse an
  unrecognised prologue; suspend threads and refuse when any EIP is implausible or
  lies inside the patch window; re-read and re-compare; restore protection in a
  `finally`; on uninstall, refuse to restore when the entry no longer contains this
  bridge's patch.
- **An offline harness is part of the deliverable.** `harness.c` links the *real*
  dispatcher object into a 32-bit executable, fakes the bridge image, the producer
  ordering, the module window and the move callee, and asserts 17 checks in 4
  scenarios with no game process: PING completion, the completion event fields, a
  subscribed `GAME_TICK`, a bad-range refusal (`-102`) with the callee **not**
  called, and a valid MOVE delivering the floats and a zeroed fourth argument.
  That is the evidence that the ABI works without opening the client — an
  equivalent is worth building before any live test.

### Caveats found in the reference — do not reproduce

- A synchronous command timeout **wedges the bridge permanently** rather than
  freeing the slot, and the wedge flag is never cleared; recovery needs a new object.
- `close()` can free the injected code pages even when `uninstall()` refused to
  restore the entry patch.
- Reinstall after `close()` is not supported: the transport is closed but the
  cached executable-region list prevents the gate from being reattached.
- The executable-region fallback narrows the patch gate enough to abort a normal
  patch, surfacing later as an implausible-EIP refusal.
- `watch_value` stores the new sample before running the encoder, so a raising
  encoder loses that transition permanently.
- `safe_patch_code` validates only 5 of the 9 patched bytes; the `sub esp, imm32`
  immediate is copied verbatim into the trampoline.
- **The module bound is not verified by the target.** `target_is_callable` only
  echoes the `module_base`/`module_size` fields the controller published; there is
  no `VirtualQuery`, no byte check at the address, no executability check, and
  `base + size` is computed without an overflow check. A wrong but non-zero window
  therefore authorises any call inside it.
- **`event_mask_hi` was optimised out of the shipped payload.** Both emit sites
  pass constant event types, so the compiler folded the mask test and deleted the
  `type >= 64` branch — there is no `[esi+0x38]` operand in the binary at all. As
  shipped, the payload cannot subscribe to event IDs 32–63. A re-implementation
  must implement the full 64-bit mask regardless.
- **No SEH and no re-entrancy guard.** A fault inside a called function is
  unhandled and surfaces as a game-thread crash; an exception that unwinds leaves
  the head slot at `CMD_RUNNING` and stalls the ring permanently with no recovery.
  A callee that re-enters `leave_game_thread_func` would consume the next command
  and desynchronise event order from command order.
- **The completion event re-reads `sequence`/`opcode` from the slot after
  `read_index` is published.** Not reachable with the shipped producer, but a
  reimplementation that frees slots on polling `read_index` rather than on the
  terminal state could emit `sequence=0, opcode=0` completions.
- `pending = write_index - read_index` is an unsigned difference with no ordering
  check, so a consumer that published `read_index > write_index` would drop every
  event until the counters reconverged 2^32 later.
- The ABI exists in four independent copies (`bridge.h`, `dispatcher.c`,
  `harness.c`, `protocol.py`); only the first two carry compile-time asserts and
  nothing includes `bridge.h`, so a field reordering could drift silently.
- Documentation says event field 2 is named `kind`; every code artifact calls it
  `type`.
- Payload provenance is **unresolved**: the notes attribute the shipped binary to
  Clang 17, but the only build path drives MSVC and its own note concedes the
  shipped bytes are not reproducible with it.
- **The harness covers less than it appears.** It never exercises the
  `0xE001..0xE005` validation refusals, the `1`/`0` return values, the heartbeat,
  an *unsubscribed* `GAME_TICK`, `NOP`/`ADD_U32`/`ECHO_U32`, an unknown opcode
  (`-100`), `arg3 == 0` (`-101`), the overflow counter, the 120-slot reserve,
  `event_mask_hi`, the not-`READY` stall, or the `read_index`-versus-completion
  ordering. Its two move counters are also not reset between scenarios, so the
  scenarios are silently order-dependent. Our equivalent must cover these.
- **Artifact-chain gap.** The harness links `dispatcher.obj` while the shipped
  bytes are `dispatcher_x86.bin`; nothing compares the two, and the run script
  rebuilds the object only when it is **absent**, so a stale object would be
  silently reused. Running it would also rewrite the binary, its sidecar and the
  embedded Python literal as a side effect.
- `relocations.txt` is only the objdump banner naming an object that is not
  shipped, so the position-independence claim cannot be re-derived from the
  package; the build script's relocation refusal is the stronger evidence.
- `Bridge.reserved` (+0x14) and `event_reserved` (+0x3C) have no reader or writer
  anywhere in the package; their intended meaning is unresolved. The 278-byte v1
  payload the build notes reference is not present either.
- The payload requires SSE and uses only unaligned-safe forms, so no 16-byte
  alignment is required of the bridge or the 36-byte command slots.

### Constraints

- **Elevation is required, and it must be in place before the process starts** —
  see the live probe above: unelevated, `VM_WRITE`, `VM_OPERATION`, `CREATE_THREAD`
  and `SUSPEND_RESUME` are denied with error 5. A process cannot elevate itself, so
  there is no "elevate on demand" that helps the process asking; only a shell
  started elevated can do this work. `py4gw.connect()` now asserts this once, up
  front, through `Win32.is_elevated()`, and raises a message naming the pid instead
  of leaving a bare `error 5` to appear later from whichever operation needed it.
- **32-bit controller**, matching a 32-bit `Gw.exe`; the package asserts it at
  import. Our interpreter is 32-bit 3.13, which satisfies this.
- **No remote thread is created in the normal path.** The dispatcher is reached by
  hijacking an existing thread at `leave_game_thread_func`; `CreateRemoteThread`
  appears only in an `execute_once()` helper that the package never calls. That
  matters for `AGENTS.md`'s rule on remote threads: this design does not rest on
  one.
- **The hook needs the client to reach `leave_game_thread_func` within 2 s** of
  install, or the liveness check tears the injection back down. A client sitting in
  a menu will abort its own install.
- **Two guards worth reproducing deliberately:** refusing to open a transport to
  `os.getpid()` (self-suspension would hang the controller), and refusing to
  restore the entry patch when it no longer contains this bridge's own bytes.
- Any live test needs **explicit user scope for the write**, per `AGENTS.md`.

## Not implemented yet

| Surface | Source behavior | Current status | Next source-backed step |
| --- | --- | --- | --- |
| Game-thread execution bridge | Native hooks `LeaveGameThread_Func` and dispatches queued work there. | **Implemented and live-verified.** `py4gw/game_thread/` hooks it, publishes commands, runs them on the game thread, reads results and events, and restores the bytes. | Broaden the call vocabulary: the typed forms the remaining source operations need, starting with pointer arguments. |
| Observation **after** a hooked client call returns, and a copy of the string it named | `GW::ui::RegisterUIMessageCallback(..., 0x1)` registers the dialog's handlers at altitude `0x1` (`dialog.cpp:1273-1292`), and `SendUIMessage` runs `altitude > 0` callbacks **after** the original send returns (`ui_methods.cpp:1390-1404`) — which is where `DupWideStringSafe(info->message)` copies a button's label (`dialog.cpp:639`). | **Implemented and live-verified, both halves.** `hooker.build_stub(..., post_payload=True)` / `Hooker.install(..., after=True)` take the hooked function's return address off the stack, call the trampoline so the body still returns into this project's code, run the payload there, and return to the client's caller with the body's value and stack intact; `POST_DEPTH` frames make a re-entrant send safe. The observer then **copies the string** that message declares — `DialogButtonInfo.message` at four, `DialogBodyInfo.message_enc` at eight (`ui.h:54-65`) — into the event record (`EVENT_TEXT_WORDS`, terminator included), because the client's own call is the only moment the string is the client's. `tests/test_hooker_offline.py` executes the stub against a synthetic patched function; `tests/test_payload_offline.py` executes the observer's copy (its bound, its terminator, its slot, its guard words); live, 2026-09-25, `tests/test_live_dat.py` is 10/10 with the client restored, the body's copy word-for-word equal to the host's own read, and both button labels copying to strings that decode to their real captions. | No action required. The dialog's own use of it is **done too**: `_on_button` takes the copy as the source's `encoded_copy` and runs `dialog.cpp:641-708` as written, and the captions the module answers are the client's own decoder's text for the labels the client announced (live, 2026-09-25). |
| Decoded `ChatBuffer` history | Reforged queues `AsyncDecodeStr` on the Guild Wars game thread and uses the client's archive/string decoder. | Encoded ring messages are readable; the decoding call has not been ported. Both decode resolvers are in the catalog (`ui.async_decode_string_func`, `ui.validate_async_decode_str_func`), and the ABI takes a **callback function pointer** — so the missing piece is a callback stub and a text area in the block, not the search. The dialog and button labels still need the same piece. **Route A does not need it**: the game's own string table, read out of `gw.dat` and decrypted on the host, renders the same codepoints with no callback at all (`py4gw/internals/string_table.py`, `docs/STRING_DECODE_PLAN.md`). | Add the decode callback as a game-thread stub, then hand the decoded text back through the block. |
| The **ImGui text measure** `PyImGui.calc_text_size` (and the style push/pop around it) | `Utils.TokenizeMarkupText` (`py4gwcorelib_src/Utils.py:280-408`) wraps markup text to a pixel width by measuring it: it pulls a `PyImGui.StyleConfig()`, zeroes `CellPadding`/`ItemSpacing` for the duration (`284-290`, restored `404-406`), and asks `PyImGui.calc_text_size(...)` for every word and protected colour block (`339`, `363`). | **Not built, and it is the first member in this port that needs the client's ImGui at all.** `PyImGui` is an in-client binding module; the port has no call into the client's ImGui, no text-measure resolver, and no string-in form for it. The member raises and names this (`py4gw/py4gwcorelib_src/utils.py`, `docs/UTILS_PORT.md`). | Establish how the client's ImGui is reached from outside — the measure is a pure function of a string, a font and the current style, so the question is the call's address, ABI and string form, not state — then port `TokenizeMarkupText` against it. The same call is what `Map`'s `IsMouseOver` and click-coordinate members will need, so it is worth taking once, deliberately. |
| **Control actions** — `ui::Keydown`/`Keyup`/`Keypress` | `ui::Keypress(key)` (`ui_methods.cpp:1408-1426`) is `SendFrameUIMessage(GetButtonActionFrame(), kKeyDown, &packet::KeyAction{key})` followed by a `game_thread::Enqueue` of the matching `kKeyUp`; `packet::KeyAction` is the 4-byte control-action id. Skills go through it: `GW::skillbar::UseSkill`/`PointBlankUseSkill` press `ControlAction_UseSkill1 + slot` (`skillbar_methods.cpp:439-447`), and the hero form presses `ControlAction_HeroNSkill1 + skill` (`skillbar_bindings.cpp:88-115`). | **Not built.** The pieces exist separately and are not joined: `ui.send_frame_ui_message_func` is in the catalog, the port's UI-message call form and its block data region can carry a 4-byte payload, and the frame array's `frame_id_by_hash` is the lookup `GetButtonActionFrame()` needs. What is missing is the control-action values, the button-action frame's identity, and the key-pairing on the game thread. Three `SkillBar` members raise for exactly this (`py4gw/skillbar.py`, `docs/SKILLBAR_PORT.md`). | Port `ui::Keydown`/`Keyup`/`Keypress` and the control-action table where native declares them, then the three `SkillBar` members. **A live client is required to verify it**: pressing a control action moves the game, so the test is a deliberate, user-present operation like the `Player` action suite. |
| GW.dat reader (the string table Route A decodes from) | `GWDatReader::ReadDatFile` (`gw_dat_reader.cpp:1441-1461`): `FileHashToFileId` → `FileHashToRecObj` (or `OpenFileByFileId`) → `ReadFileBuffer(rec, &size)` → a bounded copy out → `FreeFileBuffer` → `CloseRecObj`. | **The archive read is ported and live**: `py4gw/dat_reader.py` (the port of `PyDatReader`) issues all five calls on the client's own thread, and `tests/test_live_dat.py` read a real file (91,114 bytes, 1024 entries) and rendered a real dialog body from it. The block it needs is version 3 — the command record gained `arg4`/`arg5` for `OpenFileByFileId`'s five words — and that block was installed live for the first time in the same run. **`UnpackGWDat` is not on this path** (nothing here decompresses; the direct-file path uses it, for linked icon textures). **The rest of `GWDatReader` is not ported**: image decode, the D3D9 texture cache and dye blending (`gw_dat_reader.cpp:160-1439`), which need a device inside the client. | Port the texture half where the sources take the device from — an `EndScene`/`Reset` detour, the same one `GwDxContext` waits on (below). |
| Native action and setter paths | Item, trade, guild, camera, party, agent, chat, and UI modules call internal functions or write client state. | The call mechanism exists and is verified, and the first eleven are ported: `Player`'s target, interaction, movement, faction, title, dialog and status actions call their functions through it. The rest are still to port. | Port only concrete Native operations, one at a time, with their exact ABI, parameters, thread rule, and recovery behavior. |
| Packet layer (CToS / StoC) | Native and Reforged send and observe client-to-server and server-to-client packets; salvage option selection is packet-driven (`0x7A` materials, `0x7B` upgrade). | Not implemented in Stealth; the packet struct family is the largest block of unported declared data. | Port the packet struct declarations first (read-only), then decide which sends are in scope. |
| Callback-owned context pointers | Reforged Native captured `WorldMapContext`, `MissionMapContext`, and `SalvageSessionInfo` through UI callbacks. | **Resolved without injection.** Both map contexts are live-verified read-only through the frame array, open and closed; `SalvageSessionInfo` resolves the same way but its open/close handoff is untested. | No action required. See [`UI_FRAME_TREE.md`](UI_FRAME_TREE.md). |
| `GwDxContext` render state | Native captures it from `EndScene`/`Reset` detours (`src/GW/render/render.cpp:75-111`); it is not a frame callback. | The structure is declared (`py4gw/context/render_context.py`, `GwDxContextStruct`, 0x11A0); the pointer is not read yet, because native's own `Context::GetRenderContext()` is the `g_dx_context` **its detours assign** (`context_methods.cpp:315-316`) and nothing else publishes it. **A member now waits on it**: `Map.MissionMap.GetScale` is `frame_info.viewport_scale()` (`FrameTree/frame.py:1381-1398`) over `viewport_scale_x/y`, which Reforged does not read from a record — native *computes* them in `FramePosition::GetViewportScale` (`include/GW/ui/ui.h:553-561`) as `render.GetViewportWidth()/Height()` divided by the frame's own viewport size, and those two come from the DX context. `Utils.GwinchToPixels` and `Utils.PixelsToGwinch` raise from `Map.MissionMap.GetScale` for exactly this reason ([`UTILS_PORT.md`](UTILS_PORT.md)). | Port the capture where the source captures it: the two detour targets are already resolvable (`offsets/render.json`: `end_scene_func`, `reset_func`), the hook machinery exists in `py4gw/game_thread` (`hooker.build_stub(..., post_payload=True)` / `Hooker.install(..., after=True)` is the shape an `EndScene` capture wants — the context pointer is the hook's first argument), and the block has room for the pointer. Then `Map.MissionMap.GetScale` and the two `Utils` conversions follow. Needs a live client to verify. |

## What remains active

The following work can continue on the read side without touching target memory:

- `MapContext` read-only root and bounded source-backed records;
- the Reforged semantic item-modifier catalog, kept separate from raw item
  modifier words;
- source-parity audits and missing-property fixes for existing readers;
- porting source operations onto the mechanisms that already exist —
  `py4gw/game_thread/`'s hooks, call forms and callbacks — rather than Reforged's
  DLL/shared memory;
- pointer freshness, stale-data handling, error reporting, and performance;
- live verification against supported client builds; and
- packaging, tests, documentation, and the external NiceGUI inspection surface.

The fact that a feature is listed here does not mean it has been implemented.
Any future target-side experiment must be visible, bounded, and have a tested
restoration plan; do not use hidden writes or calls as a shortcut.

## Resume checklist

Before implementing any target-side item:

1. Name the exact source function, callback, or state being reproduced.
2. Use the selected mechanism: a Stealth-owned payload/patch, not a
   conventional injected DLL. Describe it accurately as injection; do not
   call it non-injected.
3. Record the target ABI, thread-affinity, pointer lifetime, synchronization,
   failure behavior, and rollback plan.
4. Confirm matching controller/target bitness and validate the target build.
5. Add offline safety tests and a bounded live test before enabling the feature.
6. Update this document, the parity audit, and the public API contract before
   implementation.
