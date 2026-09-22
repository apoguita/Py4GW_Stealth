# Deferred injection-dependent work

This document freezes work that cannot be completed inside Stealth's current
pure-external, read-only boundary. Nothing listed here is deleted or silently
treated as complete. Each item stays here with the source evidence and the
conditions required before work may resume.

## Current boundary

Stealth may enumerate Guild Wars processes, scan their modules, read validated
memory ranges, and materialize bounded source-defined structures. It does not
write to `Gw.exe`, place executable bytes or patches in it, create remote
threads, install hooks, load a DLL, or call an internal Guild Wars function.

`External host` does not mean `non-injected` by itself. A payload that is
written into the process is still injection even when Python remains outside.

## Frozen work

| Surface | Source behavior | Why it is frozen | Resume requirement |
| --- | --- | --- | --- |
| Decoded `ChatBuffer` history | Reforged queues `AsyncDecodeStr` on the Guild Wars game thread and uses the client's archive/string decoder. | The encoded ring messages are readable, but `Gw.dat` is locked to the external reader and the native `GWDatReader` exposes callable client functions rather than an external archive object. GwAu3 uses an assembly payload for this operation. | Either validate a separately accessible archive/string-table source, or explicitly authorize and design an in-process execution mechanism. |
| Game-thread execution bridge | Future helpers would execute Guild Wars functions on the game thread. | A generic remote call is unsafe without the function ABI, thread affinity, lifetime, synchronization, and rollback contract for each function. | A function-specific design, explicit scope approval, and a documented verification/rollback plan. |
| Native action and setter paths | Item, trade, guild, camera, party, agent, chat, and UI actions call internal functions or write client state. | These are writes, hooks, callbacks, or target-code execution rather than memory reads. | Explicit write/injection scope, target-specific ABI, safety checks, and live rollback tests. |
| `MissionMapContext` / `WorldMapContext` pointer publication | Reforged receives these pointers through injected UI callbacks/shared-memory publication. | Stealth has no independent external pointer source. Copying the layout without a pointer source would not be parity. | An independently verified external pointer source, or an explicit architecture change. |
| Render and active UI surfaces | Source code resolves render/UI functions, callbacks, and in-process state. | Read-only object pointers are not established; manipulation would require hooks, callbacks, writes, or target execution. | First define a read-only pointer source. Defer manipulation until injection scope is explicit. |
| `SalvageSessionInfo` | Native code owns the state through internal action/callback paths. | The copied offsets expose actions/functions, not a verified external object pointer. | A source-backed external pointer path and a separate decision for salvage actions. |

## What remains active

The following work does not require further injection and may continue under the
current boundary:

- `MapContext` read-only root and bounded source-backed records;
- the Reforged semantic item-modifier catalog, kept separate from raw item
  modifier words;
- source-parity audits and missing-property fixes for existing readers;
- pointer freshness, stale-data handling, error reporting, and performance;
- live verification against supported client builds; and
- packaging, tests, documentation, and the external NiceGUI inspection surface.

These items must not acquire hidden writes or target-code calls as a shortcut.

## Resume checklist

Before reopening any frozen item:

1. Name the exact source function, callback, or state being reproduced.
2. Decide whether the proposed mechanism is read-only, payload injection, or
   DLL injection; do not call a payload non-injected.
3. Record the target ABI, thread-affinity, pointer lifetime, synchronization,
   failure behavior, and rollback plan.
4. Confirm matching controller/target bitness and validate the target build.
5. Add offline safety tests and a bounded live test before enabling the feature.
6. Update this document, the parity audit, and the public API contract before
   implementation.

