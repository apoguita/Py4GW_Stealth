# Deferred target-side implementation

This document tracks target-side code, writes, patches, and hooks that are
selected for Stealth but not implemented yet. The architecture is decided: an
external controller will install Stealth-owned target code without a
conventional injected DLL. This is still injection. Implementation proceeds
in source-backed phases with verification and recovery planning; nothing
listed here is treated as complete. See
[`NATIVE_EXECUTION_PLAN.md`](NATIVE_EXECUTION_PLAN.md) for the source inventory
and resumable overall plan.

## Current boundary

The current Stealth implementation may enumerate Guild Wars processes, scan
their modules, read validated memory ranges, and materialize bounded
source-defined structures. It does not write to `Gw.exe`, place executable
bytes or patches in it, create remote threads, install hooks, load a DLL, or
call an internal Guild Wars function. This current implementation boundary
does not require the final project to remain pure external.

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
live run output are in [`RESEARCH.md`](RESEARCH.md). Callbacks remain
unimplemented: there is no registration or event surface, only one queue
serviced at a single hook point.

## Not implemented yet

| Surface | Source behavior | Current status | Next source-backed step |
| --- | --- | --- | --- |
| Game-thread execution bridge | Native hooks `LeaveGameThread_Func` and dispatches queued work there. | Not implemented in Stealth. **This is now the primary justification for target-side code.** | Define the reusable operation/parameter contract in [`NATIVE_EXECUTION_PLAN.md`](NATIVE_EXECUTION_PLAN.md), then prove behavior in an isolated test program. |
| Decoded `ChatBuffer` history | Reforged queues `AsyncDecodeStr` on the Guild Wars game thread and uses the client's archive/string decoder. | Encoded ring messages are readable; the decoding call has not been ported. | Inventory the Native function contract and handle it as a game-thread operation once the bridge exists. |
| Native action and setter paths | Item, trade, guild, camera, party, agent, chat, and UI modules call internal functions or write client state. | Not implemented in Stealth. | Port only concrete Native operations, one at a time, with their exact ABI, parameters, thread rule, and recovery behavior. |
| Packet layer (CToS / StoC) | Native and Reforged send and observe client-to-server and server-to-client packets; salvage option selection is packet-driven (`0x7A` materials, `0x7B` upgrade). | Not implemented in Stealth; the packet struct family is the largest block of unported declared data. | Port the packet struct declarations first (read-only), then decide which sends are in scope. |
| Callback-owned context pointers | Reforged Native captured `WorldMapContext`, `MissionMapContext`, and `SalvageSessionInfo` through UI callbacks. | **Resolved without injection.** Both map contexts are live-verified read-only through the frame array; `SalvageSessionInfo` is unused by either reference project and salvage is frame/packet driven. | No action required. See [`UI_FRAME_TREE.md`](UI_FRAME_TREE.md). |
| `GwDxContext` render state | Native captures it from `EndScene`/`Reset` detours (`src/GW/render/render.cpp:75-111`); it is not a frame callback. | The structure is declared; the pointer needs target-side code, and render-state pointer work is outside the required in-game context scope. | Deferred indefinitely; revisit only if render state becomes an in-scope feature. |

## What remains active

The following work can continue without target-side writes while the selected
payload work is being implemented:

- `MapContext` read-only root and bounded source-backed records;
- the Reforged semantic item-modifier catalog, kept separate from raw item
  modifier words;
- source-parity audits and missing-property fixes for existing readers;
- source-backed pointer ownership and callback/hook implementation, using a
  Stealth-owned callback publication path rather than Reforged's DLL/shared
  memory;
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
