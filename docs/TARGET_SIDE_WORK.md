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
| **The alcohol level** (`PyEffects.get_alcohol_level`, `Effects.GetAlcoholLevel`) | Native hooks the client's post-process function and stores its first argument: `OnPostProcessEffect(intensity, tint)` does `g_alcohol_level = intensity` before calling the original (`effects.cpp:24-41`), and `GetAlcoholLevel()` returns that word (`effects_methods.cpp:19-21`). The function is the catalog's `effects.post_process_effect_func` (``offsets/effects.json``, from ``effects_patterns.cpp``). | **Not built.** The port reads the effect and buff arrays (`py4gw/effect.py`) and *calls* that same function for `ApplyDrunkEffect`, but the level itself exists only as the argument of a call the controller is not in the middle of. `Effects.GetAlcoholLevel` therefore raises and names this entry; `py4gw/effect.py` carries the member's own note. | **Built wrongly first, then fixed, and the real shape is still owed (round 62).** What was here read like the dialog's shape and was not: the hook was handed a **packet watch list**, so the observer dereferenced its second argument — and this function's second argument is a plain word. On 2026-09-27 17:49:25 the client called it with `tint = 6` and died inside the emitted observer (`mov ecx,[edx]` with `edx=00000006`; `eip` outside `Gw.exe`, `ebx` on this block — `docs/RESEARCH.md` carries the dump). **Fixed**: the hook carries no watch list, so the observer validates and returns, and the same experiment re-ran with no crash and a clean drain (222 → 221). **Still owed, and it is the real item**: an observer that carries the call's **own two words** into the event — exactly what native's handler does (`OnPostProcessEffect(uint32_t intensity, uint32_t tint)` stores `intensity`, `effects.cpp:32-41`) — which is what makes `Effects.GetAlcoholLevel` answer. Needs a live client to verify: the level only changes when the client renders the drunk post-process. |
| Game-thread execution bridge | Native hooks `LeaveGameThread_Func` and dispatches queued work there. | **Implemented and live-verified.** `py4gw/game_thread/` hooks it, publishes commands, runs them on the game thread, reads results and events, and restores the bytes. | Broaden the call vocabulary: the typed forms the remaining source operations need, starting with pointer arguments. |
| Observation **after** a hooked client call returns, and a copy of the string it named | `GW::ui::RegisterUIMessageCallback(..., 0x1)` registers the dialog's handlers at altitude `0x1` (`dialog.cpp:1273-1292`), and `SendUIMessage` runs `altitude > 0` callbacks **after** the original send returns (`ui_methods.cpp:1390-1404`) — which is where `DupWideStringSafe(info->message)` copies a button's label (`dialog.cpp:639`). | **Implemented and live-verified, both halves.** `hooker.build_stub(..., post_payload=True)` / `Hooker.install(..., after=True)` take the hooked function's return address off the stack, call the trampoline so the body still returns into this project's code, run the payload there, and return to the client's caller with the body's value and stack intact; `POST_DEPTH` frames make a re-entrant send safe. The observer then **copies the string** that message declares — `DialogButtonInfo.message` at four, `DialogBodyInfo.message_enc` at eight (`ui.h:54-65`) — into the event record (`EVENT_TEXT_WORDS`, terminator included), because the client's own call is the only moment the string is the client's. `tests/test_hooker_offline.py` executes the stub against a synthetic patched function; `tests/test_payload_offline.py` executes the observer's copy (its bound, its terminator, its slot, its guard words); live, 2026-09-25, `tests/test_live_dat.py` is 10/10 with the client restored, the body's copy word-for-word equal to the host's own read, and both button labels copying to strings that decode to their real captions. | No action required. The dialog's own use of it is **done too**: `_on_button` takes the copy as the source's `encoded_copy` and runs `dialog.cpp:641-708` as written, and the captions the module answers are the client's own decoder's text for the labels the client announced (live, 2026-09-25). |
| Decoded `ChatBuffer` history | Reforged queues `AsyncDecodeStr` on the Guild Wars game thread and uses the client's archive/string decoder. | Encoded ring messages are readable; the decoding call has not been ported. Both decode resolvers are in the catalog (`ui.async_decode_string_func`, `ui.validate_async_decode_str_func`), and the ABI takes a **callback function pointer** — so the missing piece is a callback stub and a text area in the block, not the search. The dialog and button labels still need the same piece. **Route A does not need it**: the game's own string table, read out of `gw.dat` and decrypted on the host, renders the same codepoints with no callback at all (`py4gw/internals/string_table.py`, `docs/STRING_DECODE_PLAN.md`). | Add the decode callback as a game-thread stub, then hand the decoded text back through the block. |
| The **ImGui text measure** `PyImGui.calc_text_size` (and the style push/pop around it) | `Utils.TokenizeMarkupText` (`py4gwcorelib_src/Utils.py:280-408`) wraps markup text to a pixel width by measuring it: it pulls a `PyImGui.StyleConfig()`, zeroes `CellPadding`/`ItemSpacing` for the duration (`284-290`, restored `404-406`), and asks `PyImGui.calc_text_size(...)` for every word and protected colour block (`339`, `363`). | **Not built, and it is the first member in this port that needs the client's ImGui at all.** `PyImGui` is an in-client binding module; the port has no call into the client's ImGui, no text-measure resolver, and no string-in form for it. The member raises and names this (`py4gw/py4gwcorelib_src/utils.py`, `docs/UTILS_PORT.md`). | Establish how the client's ImGui is reached from outside — the measure is a pure function of a string, a font and the current style, so the question is the call's address, ABI and string form, not state — then port `TokenizeMarkupText` against it. The same call is what `Map`'s `IsMouseOver` and click-coordinate members will need, so it is worth taking once, deliberately. |
| **Control actions** — `ui::Keydown`/`Keyup`/`Keypress` | `ui::Keypress(key)` (`ui_methods.cpp:1408-1426`) is `SendFrameUIMessage(GetButtonActionFrame(), kKeyDown, &packet::KeyAction{key})` followed by a `game_thread::Enqueue` of the matching `kKeyUp`; `packet::KeyAction` is the 4-byte control-action id. Skills go through it: `GW::skillbar::UseSkill`/`PointBlankUseSkill` press `ControlAction_UseSkill1 + slot` (`skillbar_methods.cpp:439-447`), and the hero form presses `ControlAction_HeroNSkill1 + skill` (`skillbar_bindings.cpp:88-115`). | **Built (round 67) for `UIManager`'s three members, both branches.** The pieces this row said were "not joined" are joined: the frame path is the client's `__thiscall` sender with a one-word `KeyAction` in the block, and `frame_id == 0` is `GetButtonActionFrame()` — the label hashed **by the client** (`ui.create_hash_from_wchar_func`, the wide label placed in the data region) then `GetFrameIDByHash`'s scan then one `g_get_child_frame_id_func` call. `Keypress` is the down and the up, which is what the source's own `Enqueue` does when it runs inline on the game thread. | **What is left is `SkillBar`'s three members**, and it is not this mechanism: they need the **control-action values** (`ControlAction_UseSkill1 + slot`, `ControlAction_HeroNSkill1 + skill`) as native declares them, which is a table the port has not ported — `py4gw/skillbar.py:344` raises for exactly that. A live client is still required to verify a key press, because pressing a control action moves the game. |
| GW.dat reader (the string table Route A decodes from) | `GWDatReader::ReadDatFile` (`gw_dat_reader.cpp:1441-1461`): `FileHashToFileId` → `FileHashToRecObj` (or `OpenFileByFileId`) → `ReadFileBuffer(rec, &size)` → a bounded copy out → `FreeFileBuffer` → `CloseRecObj`. | **The archive read is ported and live**: `py4gw/dat_reader.py` (the port of `PyDatReader`) issues all five calls on the client's own thread, and `tests/test_live_dat.py` read a real file (91,114 bytes, 1024 entries) and rendered a real dialog body from it. The block it needs is version 3 — the command record gained `arg4`/`arg5` for `OpenFileByFileId`'s five words — and that block was installed live for the first time in the same run. **`UnpackGWDat` is not on this path** (nothing here decompresses; the direct-file path uses it, for linked icon textures). **The rest of `GWDatReader` is not ported**: image decode, the D3D9 texture cache and dye blending (`gw_dat_reader.cpp:160-1439`), which need a device inside the client. | Port the texture half where the sources take the device from — an `EndScene`/`Reset` detour, the same one `GwDxContext` waits on (below). |
| Native action and setter paths | Item, trade, guild, camera, party, agent, chat, and UI modules call internal functions or write client state. | The call mechanism exists and is verified, and the first eleven are ported: `Player`'s target, interaction, movement, faction, title, dialog and status actions call their functions through it. The rest are still to port. | Port only concrete Native operations, one at a time, with their exact ABI, parameters, thread rule, and recovery behavior. |
| Packet layer (CToS / StoC) | Native and Reforged send and observe client-to-server and server-to-client packets; salvage option selection is packet-driven (`0x7A` materials, `0x7B` upgrade). | **The observation half is now built at the stub level** (round 84 — see the StoC callbacks row below: a replaced handler pointer, a per-header emitted stub, the packet's words carried out in the event record). What is still absent is the packet *struct family*: Salvage's `0x7A`/`0x7B` option reads, and every other declared `StoC` field layout, are the largest block of unported declared data, and nothing here **sends** a packet. | Port the packet struct declarations first (read-only), then decide which sends are in scope. |
| Callback-owned context pointers | Reforged Native captured `WorldMapContext`, `MissionMapContext`, and `SalvageSessionInfo` through UI callbacks. | **Resolved without injection.** Both map contexts are live-verified read-only through the frame array, open and closed; `SalvageSessionInfo` resolves the same way but its open/close handoff is untested. | No action required. See [`UI_FRAME_TREE.md`](UI_FRAME_TREE.md). |
| `GwDxContext` render state | Native captures it from `EndScene`/`Reset` detours (`src/GW/render/render.cpp:75-111`); it is not a frame callback. | The structure is declared (`py4gw/context/render_context.py`, `GwDxContextStruct`, 0x11A0); the pointer is not read yet, because native's own `Context::GetRenderContext()` is the `g_dx_context` **its detours assign** (`context_methods.cpp:315-316`) and nothing else publishes it. **A member now waits on it**: `Map.MissionMap.GetScale` is `frame_info.viewport_scale()` (`FrameTree/frame.py:1381-1398`) over `viewport_scale_x/y`, which Reforged does not read from a record — native *computes* them in `FramePosition::GetViewportScale` (`include/GW/ui/ui.h:553-561`) as `render.GetViewportWidth()/Height()` divided by the frame's own viewport size, and those two come from the DX context. `Utils.GwinchToPixels` and `Utils.PixelsToGwinch` raise from `Map.MissionMap.GetScale` for exactly this reason ([`UTILS_PORT.md`](UTILS_PORT.md)). | **The capture is live-verified (2026-09-27).** Two runs, both elevated, both bounded, neither killing anything: the first was **read-only** (`tests/probe_render_entry.py`, `game_thread=False`, so it cannot place code) and it resolved the render entries and read their heads — `render.end_scene_func` at `0x8DFF10` with entry `55 8b ec 83 ec 48 a1 80 74 e0 00 33 c5 …`, whose first seven bytes are whole instructions and contain no relative branch, which is what let them be pinned as `_RENDER_HOOK_BYTES` the way the other three hooks' prologues are. The second used the **write** connection (`tests/probe_render_capture.py`) and read it back: `observing_render: true`, the captured pointer `0xA2C8698`, 4512 bytes read there (exactly the declared `sizeof(GwDxContextStruct)`, `0x11A0`), **viewport 1678×1368** and device `0xA9B7C40` — plausible for a windowed client — and after `disconnect`, `observing_render_after_disconnect: false`, so the hook was taken out and the client's own entry bytes restored. The two words the geometry has been waiting on are those two numbers. **What is left is the consumers — and they need the root as well, which round 33 got wrong and round 36 corrected.** `Map.MissionMap.GetScale` is `frame_info.viewport_scale()` (`Py4GWCoreLib/Map.py:1024-1029`), and that member reads the wrapper's `viewport_scale_x`/`viewport_scale_y`, which the binding computes as `GetViewportScale(root)` — **the render viewport divided by the root's viewport size** (`ui.h:553-561`, with `root ? root->position.viewport_width : viewport_width` as the divisor). So this capture supplies the **numerator** and the root frame supplies the **denominator**, and neither alone answers any member of that family: the earlier note here that `GetScale` "needs only this, since it calls `viewport_scale()` with no root" was a misreading — the call has no root argument, but the value it returns was computed with one. **The root is reachable**: the catalog carries `ui.get_root_frame_func` (`offsets/ui.json:414-416`, resolved by scanning the `get_root_frame` pattern), native's `GetRootFrame` is that pointer's call, and the frame id is the word at `+FrameStruct.frame_id.offset` (`ui_methods.cpp:415-417`; the port declares `frame_id` at `0xBC`). **`FrameTree.root()` is in as well (round 36)** — one no-argument call plus one word read, exactly as native does it: `call_function("ui.get_root_frame_func", CallForm.NO_ARGS)`, the pointer being the **command record's `result`** (a call answers with the record of the completed command, not the callee's value), and the id the word at `+FrameStruct.frame_id.offset`. The source's `_root_id` cache is kept, so a transient zero from the engine holds the last good id, and `viewport_height` now reads through it. What remains for the geometry family is the arithmetic itself — `GetTopLeftOnScreen`/`GetBottomRightOnScreen`/`GetSizeOnScreen` over the root plus the render viewport — which is fully written down above and now has both of its inputs. |

| The client's **label hash** — `PyUIManager.UIManager.get_hash_by_label` / `get_frame_id_by_label` | Native resolves a frame by label by hashing the label **in the client**: `GetHashByLabel(label)` is `g_create_hash_from_wchar_func(label, -1)` (`ui_methods.cpp:542-546`, a pattern-resolved pointer to the client's own `CreateHashFromWChar`), and `GetFrameByLabel` (`:556-568`) then scans the frame array for `relation.frame_hash_id == hash`; `GetFrameIDByHash` (`:575-588`) is that same array scan without the hashing. | **Half ported (2026-09-27).** The read half is in and tested: `_FrameTree.anchor_ids` and `_FrameTree.by_hash` scan this port's frame array for the hash, mirroring `GetFrameIDByHash` including native's own `IsFrameValid` (`:405-407`, a null/`-1` record — here a slot that read back `None`). The **call half is missing**: hashing an arbitrary label needs a **wide string placed in the client** and passed by pointer, and the vocabulary has no such form (`FLOAT_PTR = 6` passes a pointer, but nothing writes a wide string into the block). Three members wait on it — `_FrameTree.by_label` and `_FrameTree.hash_for_label` raise naming it, and `anchor_ids`' label fallback raises inside the source's own `except Exception`, which turns it into 0 so the hash lookup underneath still answers. The offline table `frame_names.NAME_TO_HASH` is the source's *earlier* step and is ported; it cannot replace this, because the client route exists precisely for labels the table does not know. | Add the wide-string call form — a text region in the shared block, a pointer form, and the same resolve-then-restore discipline the other calls use — then set the label hash with it. The three members are at `Py4GWCoreLib/FrameTree/frame.py:426-460` and `579-588`. The read half needs no live run (it runs on the frame array); the call half needs a live client to confirm the hash equals the client's own.

| The client's **title table** — `PyUIManager.UIManager.get_frame_label_by_frame_id` / `get_frame_title_by_frame_id` | Both names bind **one** native function: `ui_bindings.cpp:817-821` wraps `GW::ui::GetFrameTitle(GW::ui::GetFrameById(frame_id))` twice (once through `SafeWide`, once through `WideToUtf8`). And `GetFrameTitle` (`ui_methods.cpp:1784` and on) is not a read: it returns null unless the frame, two client function pointers and `ClientContext::GetTitleTableAddress()` are all present, reads the frame's **non-client word at `+0xCC`**, binary-searches the client's title table with `g_title_binary_search_func(table, nullptr, nonclient, &entry)`, and takes the wide string through the title getter. | **Not built (2026-09-27).** `Frame.label` and `Frame.title` are declared and name this entry. `label`'s source wraps the binding in `except Exception` and returns `""`, so the member reports *no label* rather than a stand-in; the rest of the member — the frame record by id — is a read this port already does. | Two client calls plus a table address owned by the client's context: resolve `g_title_binary_search_func`, the title getter and the title-table address the way the catalog resolves its other functions, then call them in native's order (`nonclient` word first, so a frame without one costs no call). Callers are `Frame.label`, `Frame.title` and the dialog's title reads. Needs a live client: the table exists only with a UI context.

| **Frame actions and setters** — `Frame.click`/`double_click`/`mouse_action`/`mouse_click_action`/`send_message`/`send_message_text`/`set_text`/`set_visible`/`set_disabled`/`show`/`set_layer`/`set_opacity` | Resolving these bindings (2026-09-27) showed **one shape for all of them: a `GW::game_thread::Enqueue`** — the write happens on the client's own thread, not on the caller's. `test_mouse_action`/`test_mouse_click_action` enqueue `ui::TestMouseAction`/`TestMouseClickAction(frame_id, current_state, wparam, lparam)` (`ui_bindings.cpp:1093-1103`); `SendFrameUIMessage`/`SendFrameUIMessageWString` enqueue `ui::SendFrameUIMessage(GetFrameById(fid), message, wparam, lparam)` (`:1066-1078`), whose body requires a non-empty callback array and calls the client's `g_send_frame_ui_message_original(&frame->frame_callbacks, nullptr, message_id, wparam, lparam)` — **five** words, the first an address inside the frame record (`ui_methods.cpp:1332-1352`); `set_text_label_by_frame_id` enqueues a write of the encoded label on the `TextLabelFrame` (`:1447-1452`); `button_click` enqueues `ui::ButtonClick(frame)` (`:1080-1084`), which requires the frame and its parent to be `IsCreated()`, builds a `packet::MouseAction{frame_id, child_offset_id}` and a `ButtonParam{unk, wparam, lparam}` and sends through the frame's parent (`ui_methods.cpp:1249+`). The setters are record writes: `SetFrameVisible` is `frame->frame_state &= ~0x200u` (or sets it) (`ui_methods.cpp:1739`), `SetFrameLayer` is `frame->field10_0x28 = layer` (`:654-660`), and `SetFrameDisabled`/`SetFrameOpacity` are their own writes. | **Partly built, and the call shape is now settled by the live client (round 59).** `Frame.send_message` answers, and the shape it settles is the client's **`__thiscall`** method: Native declares the sender `void(__fastcall*)(callbacks, void* edx, message_id, wparam, lparam)` for its detour ABI (`ui_patterns.cpp:32`), so the call needs `CallForm.FASTCALL_U32_U32_U32` — `&frame->frame_callbacks` in **ECX**, the dummy in EDX, three words on the stack, and the callee pops them (read live: the target ends `ret 0xc`). Push-five-words cdecl was wrong and would have taken the host's frame apart. **`Frame.click`** is built on it too — native's `ui::ButtonClick`: parent reached by relation pointer, both `IsCreated` checks, `MouseAction{child_offset_id, child_offset_id, MouseUp, &ButtonParam{0, field105_0x1c4, 0}}` placed in the block's data region, sent as `kMouseClick2` to the **parent's** callbacks — and clicking a real dialog button in the live client **advanced the dialog** (round 59). `Frame.double_click`, `mouse_action`, `mouse_click_action`, `send_message_text`, `set_text` and the five setters still carry the source's own guard and then raise naming the call they need; `Frame.content_coords`/`viewport_dimensions` and the tree's `root`/`viewport_height` wait behind the same item where they need the root frame. This is the same boundary the control actions sit on (`ui::Keypress`, above). | Build it once, deliberately: the port's `py4gw/game_thread` layer **is** the analogue of that enqueue, the call vocabulary already carries the five-word form `ui::SendFrameUIMessage` needs, the frame's callback array is a declared field at `0xA8` (so the first argument is `record_address + 0xA8`), and the packet structs (`packet::MouseAction`, `ButtonParam`) go in the block's data region. Then the setters are the port's existing `WRITE_MEMORY` path into the record, exactly as `Camera` writes its own. **Needs a live client and explicit user scope for the write**: these move the UI, so verification is a deliberate, user-present operation.

| The binding-side **frame-position wrapper** — the `*_on_screen` and `viewport_scale_*` values | Reforged's `PyUIManager.UIFrame.position` is **not** the raw struct: `ui_bindings.cpp:445-462` copies the record's own fields and then, **only when the UI root exists**, fills `left_on_screen`/`top_on_screen`/`right_on_screen`/`bottom_on_screen` from `frame->position.GetTopLeftOnScreen(root)` and `GetBottomRightOnScreen(root)`, `width_on_screen`/`height_on_screen` from `GetSizeOnScreen(root)`, and `viewport_scale_x`/`viewport_scale_y` from `GetViewportScale(root)`. Those four methods are declared at `include/GW/ui/ui.h:361-366`; `GetViewportScale` divides the **render** viewport by the frame's own viewport size. | **Half answered (2026-09-27).** What the raw record carries answers: `Frame.viewport_dimensions`, `position_ex`, `native_size`, `min_size` and `client_border` read the client's own `screen_*` / `content_*` / `flags` and the `0x50-0x64` words. `Frame.rect`, `Frame.size` and `Frame.viewport_scale` name this entry instead of reading fields that do not exist — `FramePositionStruct` has no `*_on_screen` or `viewport_scale_*` at all, which a test now asserts against the struct itself. | **Implemented (round 37), where native puts it**: `FramePositionStruct` (`py4gw/ui/frame.py`) now carries `viewport_scale`, `top_left_on_screen`, `bottom_right_on_screen` and `size_on_screen`, `GW::render::GetViewportWidth`/`Height` is ported as `get_viewport_size()` (`py4gw/context/render_context.py`, `render_methods.cpp:56-63`), and `Frame.rect`, `size`, `coords`, `viewport_scale` and `content_coords` answer on top of them — **zeros and the identity without a root**, which is what Reforged's wrapper gives there, since the binding fills those words only `if (root)`. **The consumers need nothing new**: `Map.MissionMap.GetScale` (`Map.py:1024-1029`) is `frame_info.viewport_scale()`, so it is the same two inputs, and `Utils.GwinchToPixels`/`PixelsToGwinch` call it. **A correction to what follows in this cell**: the sentence further along that `GetScale` "needs only the second of the two, since it calls `viewport_scale()` with no root" is wrong — round 36 read `Map.py` and the divisor is the **root's** viewport size. The arithmetic it reproduces, for the record: the three on-screen computations — **their bodies are now read, and they are pure arithmetic** (`include/GW/ui/ui.h:504-551`): `GetTopLeftOnScreen` is `{screen_left * scale.x, (height - screen_top) * scale.y}` and its three siblings differ only in which pair of position words they scale, with `height` taken from the **root's** `viewport_height` (the argument) or the frame's own when no root is passed, and `scale = GetViewportScale(frame)`. **The scale is where the chain ends**, and it was traced to its last hop: `ui.h:553-561` divides `GW::render::GetViewportWidth()/Height()` by the root's (or own) `viewport_width`/`viewport_height`, and those two accessors are `render_methods.cpp:56-63` → `Context::GetRenderContext()->viewport_width/height` — the pointer **native's own `EndScene`/`Reset` detours assign** (`render.cpp:75-111`), which is the `GwDxContext` row above. So the whole geometry is exactly **two inputs**: the **root frame** (a client call, `ui_methods.cpp:415`) and the **DX context** (that detour capture). `Map.MissionMap.GetScale` needs only the second of the two — it calls `viewport_scale()` with no root, so the frame's own viewport size is the divisor — and is therefore the first member the detour capture unblocks.

| **A raw three-word UI-message send**, and a UI-message payload of native's width — `PyUIManager.UIManager.SendUIMessageRaw` / `SendUIMessage` | `SendUIMessageRaw` (``ui_bindings.cpp:1062-1065``) is a **direct** call: ``GW::ui::SendUIMessage(static_cast<UIMessage>(msgid), reinterpret_cast<void*>(wparam), reinterpret_cast<void*>(lparam), skip_hooks)``, whose two words reach the client's own sender untouched (``g_send_ui_message_original``, a 3-word ``__cdecl``, ``ui_patterns.cpp:31``). ``SendUIMessage`` goes the other way: ``SendUIMessagePacked`` (``:60-74``) zeroes a **sixteen-word** POD, copies the whole ``values`` list into the front and passes its address as ``wparam``. | **Built (round 64, `UIManager`).** ``ConnectedClient.send_ui_message_raw`` (``py4gw/client.py``) is the raw call: the **held** sender address with ``CallForm.U32_U32_U32`` and the caller's own words, which is the one route that must not re-resolve it (the entry is patched, so a second scan answers the function before it). ``UIManager.SendUIMessage`` now builds native's sixteen-word payload in the block's data region, copies ``values`` into the front and calls that raw path — so the two-word limit is gone and a longer list is native's own ``i < 16`` bound. | No action required offline. **A live client is owed** for both: the message travels through this project's observer hook, so the run reads the client's behaviour afterwards rather than a return value. |
| **The client's key-remap table** — `PyUIManager.UIManager.get_key_mappings` / `set_key_mappings` | Native's current revision has no such member; the older runtime's binding scans for the client's ``FrKey.cpp`` assertion ``"count == arrsize(s_remapTable)"``, reads the table pointer the found sequence embeds, validates it against the data section, and returns/writes ``0x75`` words (``py_ui.h:4757-4772``, ``:4774-4790``; ``SetKeyMappings`` copies ``min(0x75, len(mappings))`` words into the client **on the game thread**). | **Built (round 66)**, over a resolver derived offline for this build — ``ui.key_mappings_table`` in ``offsets/ui.json``: the assertion's message literal, the **first** of its two ``.text`` uses, **+0xD** to the ``mov`` immediate that loads the table, then a ``.data`` check. ``Tools/key_mappings_hunt.py`` measured it: both uses read ``0x00C14C58`` inside ``.data``. The two members read and write that table (``min(0x75, len(mappings))`` words through ``WRITE_MEMORY``). **GWCA's own offset (``0x13``) does not reproduce on this build** — the port's number is a derivation from the file, not that constant. | No action required offline. **A live client is owed**: the table sits in ``.data``'s **uninitialised tail**, so its contents exist only at runtime — the live read is the only witness that the derivation lands on the client's own remap table. |
| **The injected runtime's own state** — `GetFrameLogs`/`ClearFrameLogs`, `GetUIMessageLogs`/`ClearUIMessageLogs`, `SetOpenLinks` | Three surfaces that exist only inside the injected runtime and hold **nothing the client owns**: GWCA's ``frame_logs`` (``UIMgr.cpp:106``, filled only by its ``CreateUIComponent`` detour at ``:160``, 5000-entry cap), Native's ``g_ui_message_logs`` deque (``ui.cpp:1077``, filled by its own message hook at ``:1136-1150``, ``ui.h:712`` entry shape) and Native's ``g_open_links`` flag (``ui.cpp:1078``, consulted only by its ``kOpenTemplate`` handler, which blocks the message and calls ``ShellExecuteW``, ``ui.cpp:309-324``). | **Unbuilt, and correctly so (2026-09-27, `UIManager`)**: each member raises and names the runtime state behind it. No client read reproduces any of them. | **This project already hooks both functions those journals watch** — ``ui.send_ui_message_func`` (the connection's own observer) and, for frame creation, nothing yet. So the equivalent is a capture on this project's own hook layer, which is the same kind of work as the effects observer above: an entry hook that records the message (or the created component's label) into a block slot, and a host-side list. Only worth taking if a consumer appears — ``Frame.click`` and the dialog module already read the client directly for what they need.
| **Strings as call arguments** — `PyUIManager.UIManager.set_string_preference`, `frame.get_hash_by_label` / `get_frame_id_by_label`, `PyUIManager.UIManager.SendFrameUIMessageWString` | Native hands the client **the caller's own wide buffer** and passes its address: `g_set_string_preference_func(pref, value)` over a ``std::wstring``'s data (``ui_methods.cpp:1639-1651``, ``ui_bindings.cpp:1055-1057``); `GetHashByLabel` over ``wide_label.c_str()`` (``:542-546``); `SendFrameUIMessage` over ``text.data()`` (``:1073-1079``). | **No missing capability — corrected 2026-09-27 (round 65).** This row used to say the port lacked "a text region in the shared block and a pointer form". It does not: ``ConnectedClient.bridge.write_data`` places arbitrary bytes in the block's data region — memory **inside** the client — and answers that address, which is exactly what a pointer argument needs. ``UIManager.SetStringPreference`` is built on it and answers (the caller's UTF-16 text written there, its address passed). The label hash's resolver is in the catalog too (``ui.create_hash_from_wchar_func``, a ``__cdecl(wchar_t*, int)``, called with ``-1`` as native does). | **The bodies, not a mechanism**: `_FrameTree.hash_for_label` and `_FrameTree.by_label` are one call each over that resolver with the label placed the same way (`by_label` then does the array scan `by_hash` already performs), and they unblock `_FrameTree.anchor_ids`' label fallback. `Frame.set_text` is the one member still genuinely blocked, and on something else entirely: `set_text_label_by_frame_id` calls **the client's own `TextLabelFrame::SetLabel`** (``ui_bindings.cpp:1447-1452``), a method inside the client rather than a ``cdecl`` function a catalog can name. `Frame.send_message_text` waits only on the frame-message path's own string placement.
| **The four typed `SetPreference` bodies** — `UIManager.SetEnumPreference` / `SetIntPreference` / `SetBoolPreference` / `SetStringPreference` | ``ui_methods.cpp:1468-1677``: the typed guards, the value validated against the client's own option list and its ``AntiAliasing``/``TerrainQuality``/``ShaderQuality`` rewrites, ``ClampPreference`` through the client's own ``NumberPreferenceInfo::clamp_proc`` (``:385-395``), the write through ``g_set_*_preference_func``, and a **queued follow-up** that re-reads the preference and drives what depends on it — the renderer value, shadow quality, the terrain rerender, the UI scale, the five volume setters and the renderer mode. | **All four built**, in ``py4gw/ui/preferences.py`` (the home this port keeps the ``GW::ui`` preference functions in): ``set_enum_preference``, ``set_number_preference``, ``set_string_preference``, ``set_flag_preference``, ``clamp_preference`` and ``get_enum_preference_options``, with the four ``UIManager`` members as the source's own wrappers over them (rounds 64-65). Every function they call was already a resolver, so this was pure body work. | No action required offline. **A live client is owed and it is a deliberate, user-present run**: a preference write changes the client's settings, so the verification is to set one, read it back through the matching getter, and put the original value back. |
| **StoC packet callbacks** — the client's own handler table | Native's listeners register packet callbacks by **replacing the client's handler**, not by hooking a function: `g_game_server_handlers->at(header).handler_func = &StoCHandler_Func` (`stoc_methods.cpp:55-57`), keeping the client's original to chain to, and `Uninstall()` puts it back (`:130-136`). The table is reached through `stoc.handler_table_addr` — **a resolver this port already carries, byte-identical to native's** (`offsets/stoc.json`: the same pattern, mask, offset and `scan_pointer_ref`/`deref_ptr` steps). The array is `GWArray<StoCHandler>` where each entry is `{packet_template: u32*, field_count: u32, handler_func: u32}` (`stoc_patterns.cpp:9-13`), and the handler is `bool __cdecl(PacketBase* packet)`. | **Built and wired (rounds 84-85), and live-verified read-only.** `payload.build_packet_stub` emits the replacement — per header, because emitted code cannot read a struct the way native's compiled callbacks do — and `game_thread/packets.py` walks the chain native walks (resolver → `GameServer*` → `gs_codec + 0x8` → `handlers + 0x2C` → a `GW::GWArray` of 12-byte entries), places one stub per watched header, writes the pointer **on the game thread** through `WRITE_MEMORY`, reads the entry back, and restores every saved original on disconnect before anything is freed. `tests/probe_stoc_handlers.py` read the real chain on this build (server `0x1D6BC90`, codec `0x1D63388`, **487 entries in 504 slots**, all five merchant headers in range with code in `.text`) — read-only, unelevated, and it also showed the *other* reading of the resolver's value is the wrong one. The first consumer is live: `py4gw/listeners.py`'s `MerchantListener`, whose five callbacks the merchant class now reads through. **One refusal is this port's own**: a wanted header whose handler is outside the client module is refused by name rather than chained to, because a controller here can attach to a client that outlived one that died. Offline: `tests/test_payload_offline.py::PacketStubTests` (executed bytes) and `tests/test_listeners_offline.py` (the walk, the install, the restore, the in-flight wait). | **What is owed is a live run that uses it**: the capability has been **written live once** — `tests/probe_merchant_packets_live.py`, 2026-09-30, elevated, 20 s: all five entries replaced with this project's stubs, verified entry by entry, then **restored** on disconnect with the client healthy and the stubs' in-flight count at zero. **No packet of those five headers arrived while it listened**, so the *dispatcher entering a stub* has not been observed live yet — that is the merchant live pass (round 4), which also runs the trade itself: one write at a time, with the owner present. |

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

## 2026-09-27 — an observed function whose arguments are words, not a packet

**What is already in place** (all of it live-run, pid 35416): the hook on
``effects.post_process_effect_func`` (``effects.cpp:51-55``), its watch list
(``effect._WATCHED_INTENSITIES``), its own event kind (``EventKind.EFFECT_INTENSITY`` = 4), the
handler (``effect._on_post_process_effect``, ``effects.cpp:26-41``) and the reset
(``effect._reset_alcohol_state``, ``effects.cpp:81``).

**What is missing.** ``build_observer`` (``payload.py:713``) emits one event shape, and it is the UI
one: the hooked function's second argument is a **pointer to a packet**, its words become the event's
``arg0..arg3``, and a null second argument drops the event (``payload.py:762-765``). The post-process
function's two arguments are plain words, and its second is ``0`` for a plain drunk level, so no event
is ever published. What is needed is the second shape: an observer that records the hooked call's own
arguments — ``sequence``/``arg0`` = the first, ``arg1`` = the second — with no dereference and no
null-drops-event check, selected by the caller that installs it (``Bridge.install``, one shape per
observed function, as native has one handler per hooked function).

**How it is verified.** ``tests/probe_alcohol_live.py``: connect, read ``Effects.GetAlcoholLevel()``
(``0``), ``Effects.ApplyDrunkEffect(3, 0)``, wait for ``3``, ``Effects.ApplyDrunkEffect(0, 0)``, wait
for ``0``, disconnect. It must be allowed to finish — a killed run leaves a hook in the client.
