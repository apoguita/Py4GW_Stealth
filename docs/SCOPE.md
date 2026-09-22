# Project Scope

## Purpose

Py4GW Stealth is the external counterpart research project for Py4GW Reforged.
Py4GW Reforged runs Python inside Guild Wars through the injected
`Py4GW.dll`. Stealth investigates how selected Reforged capabilities can be
recreated from an external Python process instead.

This is capability-by-capability work. Stealth is not a complete replacement
for Py4GW Reforged, and no feature is assumed to be externally possible until
its design and evidence are clear.

**Current parity status: full source/API parity has been achieved for no
context.** Existing readers are verified external read slices with documented
gaps, not completed Reforged/native context replacements.

When a context is migrated, the target is parity with the active behavior in
`Py4GW_Reforged_Native` and `Py4GW_Reforged`. We migrate fields and helpers
that those sources actually use or expose. We do not treat every unused native
declaration as required work, and we do not invent a different public contract
for the external reader. Only the process-memory transport changes.

The current reader inventory is not a parity claim by itself. See
[`CONTEXT_PARITY_AUDIT.md`](CONTEXT_PARITY_AUDIT.md) for the source-by-source
status of every migrated reader and the missing work recorded for partial
surfaces.

Work that requires target-code execution, writes, hooks, callbacks, or
injected state is deliberately frozen in
[`DEFERRED_INJECTION.md`](DEFERRED_INJECTION.md). It is not part of the active
read-only migration until its architecture and safety contract are approved.

The long-term intent is broader than reading contexts: some future features
may need code to execute on the Guild Wars game thread. An external reader
cannot do that by itself. The intended direction is to avoid loading a DLL,
while evaluating a smaller in-process payload/hook approach similar to the
mechanism observed in GwAu3. That is still injection in the technical sense
and is not implemented yet.

## Current deliverable

The first deliverable has three deliberately separated parts:

1. a project-owned `py4gw` package with a `Win32` class for read-only Windows
   process and memory operations;
2. a reusable scanner that consumes the copied `offsets/` definitions; and
3. a root-level `main.py` NiceGUI window for exercising the process surface.

The UI is not a second process library. It is a presentation and testing
surface over the package. Windows process and memory behavior stays inside the
`Win32` and `ProcessMemoryReader` boundaries.

## In scope

- Python code running outside `Gw.exe`.
- Read-only Windows process enumeration.
- Case-insensitive discovery of processes named `Gw.exe`.
- Best-effort executable-path reporting with preserved Windows errors.
- Read-only process-memory reads and x86 module-section scanning.
- Pattern and resolver definitions loaded from the copied `offsets/` directory.
- A small native NiceGUI window for testing the current library behavior.
- Tests and documentation that explain each capability.
- Small project-owned wrappers around documented Windows APIs.

## Current capability

The current `py4gw` package can:

- list running Windows processes;
- find every process whose executable filename is `Gw.exe`; and
- report its PID and executable path when Windows allows that lookup;
- open a selected process for read-only memory access; and
- scan validated x86 module ranges using copied pattern definitions;
- resolve and read the maintained `CharContext`, `GameContext`,
  `PreGameContext`, `Cinematic`, `GameplayContext`, `ServerRegion`,
  `InstanceInfo`, `TextParser`, `AvailableCharacterArray`, `PartyContext`,
  `GuildContext`, `AccAgentContext`, `Camera`, `FriendList`, `ChatBuffer`,
  `WorldContext`, `TradeContext`, `ItemContext`, `AccountContext`,
  `GadgetContext`, and the read-only `MapContext` root with bounded spawn and
  initial pathing-context records
  structures; and
- read the source-defined ItemContext auxiliary tables (formulas,
  composite-model records, storage state, and PvP metadata) through cached
  offset resolvers; and
- expose a selected-client connection for scripts and the root UI; and
- measure execution time in the external Python controller.

The root UI currently exposes these operations in the `Guild Wars clients` tab:

- `Refresh` discovers every running `Gw.exe` client;
- each row displays its PID, character name or `in selection menus`, and path;
- a PID selector chooses one client; and
- `Connect selected` keeps that client's read-only connection available.

This identifies process candidates by filename. The scanner can inspect bytes
and resolve addresses, and the context readers can decode the maintained
structures externally. This does not claim compatibility with every client
build or provide all Reforged context behavior.

## NiceGUI contract

NiceGUI is used only as the presentation layer for the current test window.
The native window is started with `ui.run(native=True)` and uses pywebview
underneath. UI callbacks may call public `Win32` methods and display their
results, but they must not contain Windows API declarations, process-handle
management, memory operations, or Guild Wars target assumptions.

The UI must remain understandable without knowing NiceGUI internals. New tabs
or controls should be added only for a capability that already has a library
method and a documented contract.

`PerfCounter` is controller-side instrumentation. It does not inspect or
execute code inside the Guild Wars process.

The resolver scan occurs during connection and its stable pointer location is
cached. Context object pointers are re-read for each snapshot because they may
change with client state. See [Performance](PERFORMANCE.md) for the timing
contract and live harness.

## Out of scope for the current capability

The current implementation does not:

- write to Guild Wars memory;
- inject a DLL, payload, executable code, or patch;
- create a remote thread or hook a game function;
- reproduce Py4GW `Py*` bindings, widgets, or automation helpers;
- select a client by character, map, or memory signature; or
- promise compatibility with every Reforged feature.

Any expansion beyond the current read-only scanner must be documented and
designed before implementation.

## Terminology

`Pure external` means that the controller runs outside `Gw.exe` and does not
place executable code or patches in it. Read-only process-memory reads are
part of the current capability; writes are not.

`External host` means that the primary logic runs outside `Gw.exe`. It does not,
by itself, prove that the game process is unmodified.

`Payload injection` means that an external program writes executable code or a
code patch into `Gw.exe` without loading a conventional DLL. It is still
injection.

`DLL injection` means that an in-process DLL owns a runtime. Current Py4GW
Reforged uses this model.

## Project rules

- Keep the public library API small and explicitly typed.
- Keep generic Windows mechanics separate from Guild Wars-specific knowledge.
- Keep all project code compatible with the checked-in `pyrightconfig.json`.
- Run Pyright with the same interpreter in which the project dependencies are
  installed.
- Record capability decisions and live observations in the documentation.
