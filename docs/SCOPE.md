# Project Scope

## Purpose

Py4GW Stealth is an independent external-host project for reading Guild Wars
data and, eventually, executing source-backed work on the game's thread. It
aims to be self-sufficient: Py4GW Reforged and Py4GW_Reforged_Native are
source references, not runtime dependencies. Stealth must not rely on
Reforged's injected DLL, embedded Python runtime, or shared-memory mapping.
The selected architecture for callback and game-thread work is a
Stealth-owned payload or patch without loading a conventional DLL. That still
modifies the process and is injection. The first target is the WorldMap UI
callback pointer; its payload is not implemented yet.

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

**Native and Reforged are the sources of truth. `external/GwAu3` is a reference
project, not an authority.** Where GwAu3 disagrees with either base project, the
base projects win. GwAu3 is useful for framing a question and for historical
context; it is never the answer to "what does this do". The open salvage
questions — `Salvage()` argument order and the meanings of the `0x78`/`0x79`
packet headers — were being held as Native-vs-GwAu3 contradictions; they are not
contradictions to resolve but cases where the native source decides.

Where Native and Reforged *Python* disagree, Native wins as well. Two examples
from the `Player` port, both recorded in [`PLAYER_PORT.md`](PLAYER_PORT.md):
Native resolves duplicated fields with `PickHighest` (which discards `0` and
`0xFFFFFFFF`) while Reforged's Python uses `max`; and Reforged's
`IsPlayerLoaded` carries a `750` fallback threshold that appears nowhere in the
native tree.

The current reader inventory is not a parity claim by itself. See
[`CONTEXT_PARITY_AUDIT.md`](CONTEXT_PARITY_AUDIT.md) for the source-by-source
status of every migrated reader and the missing work recorded for partial
surfaces.

The current implementation is read-only, but pure external reads are not
enough to obtain every source-defined pointer or execute Native's
game-thread operations. The Native source shows which pointers, hooks,
callbacks, patches, and calls are involved. The goal is to reproduce those
source-backed mechanisms in Stealth, with a reusable design that can gain a
new mechanism or parameter form when a concrete Native operation requires it.
Unknown or hypothetical mechanisms are not part of the initial design. The
inventory and resumable phases are in
[`NATIVE_EXECUTION_PLAN.md`](NATIVE_EXECUTION_PLAN.md); the first callback
pointer slice is detailed in
[`CALLBACK_POINTER_RESEARCH.md`](CALLBACK_POINTER_RESEARCH.md). No target-side
payload, patch, or call has been implemented.

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
- Source-backed research into pointer lifetimes and callback/hook paths needed
  for self-sufficient context reads. The selected payload architecture and
  first callback target are recorded in the execution plan; implementation is
  still pending.
- Future source-backed hooks, callbacks, and game-thread operations needed
  for Reforged Native parity, implemented one reviewed mechanism at a time as
  described in [`NATIVE_EXECUTION_PLAN.md`](NATIVE_EXECUTION_PLAN.md).

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
  `GadgetContext`, and the read-only `MapContext` root with bounded spawn,
  pathing-context, and pathing-child arrays
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
- reproduce Py4GW's native `Py*` binding modules, its UI widgets, or the game
  actions its wrappers perform;
- select a client by character, map, or memory signature; or
- promise compatibility with every Reforged feature.

The distinction that matters is between a wrapper's **data surface**, which is
in scope, and its **bindings and actions**, which are not:

| Surface | Status |
| --- | --- |
| Reforged wrapper data members (`Player.GetLevel`, `Player.GetAgent`, ...) | **in scope** — ported as read-only accessors over the context readers |
| Accessor classes ported from Reforged and Native (`Map`, `Party`, `Player`) | **in scope** — ported member for member, see [`PORTING_RULES.md`](PORTING_RULES.md) |
| Native `Py*` binding modules (`PyPlayer`, `PyInventory`, ...) | **out of scope** — they require code inside the client |
| UI widgets, ImGui panels, and the host framework | **out of scope** |
| Wrapper action members (`Player.Move`, `Player.SendChat`, ...) | **out of scope** — ported as members that refuse, so a migrated script fails at the call site |

Ported action members are present but disabled; they raise and never execute.
The reason a wrapper class is worth porting even when many of its members
refuse is that the *names and signatures* are the migration contract: a script
moves over unchanged, and the members that cannot work say so instead of
returning a plausible wrong value. See
[`PLAYER_PORT.md`](PLAYER_PORT.md) for the reference implementation.

Target-side writes, code, or patches are part of the selected architecture,
not an open design choice. The first source-backed implementation target is
the WorldMap callback capture described in
[`CALLBACK_POINTER_RESEARCH.md`](CALLBACK_POINTER_RESEARCH.md). It remains
unimplemented. “No DLL” describes the delivery approach; it does not mean the
target is unmodified or that the payload is undetectable.

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
