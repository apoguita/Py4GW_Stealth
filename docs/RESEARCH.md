# Py4GW Stealth Research Record

This document contains the detailed research history and source comparisons
that were intentionally kept out of the GitHub front page. It is not the
project's short description or installation guide.

Status: current active research project; first process-discovery slice implemented
Scope: establish what an external Guild Wars controller can read, write, execute, and observe before expanding capabilities.
Authority: inspected current Py4GW Reforged and Py4GW Reforged Native sources; inspected the GwAu3 source checkout; verified the current read-only process-discovery behavior. No live-client memory behavior has been verified.

## Intent

Py4GW Stealth is intended to recreate selected useful capabilities of Py4GW
Reforged for Guild Wars from an external Python process, without loading a DLL
into `Gw.exe` or placing executable code or patches in it. In that sense,
Stealth is the non-injected, external counterpart to the current Reforged
runtime.

The project is capability-by-capability research. It does not assume that
every in-process Reforged feature can be reproduced externally, and it does
not promise a complete replacement before each capability has been tested.

The immediate purpose is to understand the capability boundary between:

1. a pure external process that does not place executable code or patches in `Gw.exe`;
2. an external controller that uses a small remote payload rather than an injected DLL; and
3. the current Py4GW Reforged model, where a DLL embeds Python and owns an in-process runtime.

This document deliberately does not select an architecture, promise a botting surface, or prescribe an implementation. Those decisions depend on research into individual Guild Wars data and command paths.

The current implementation is intentionally narrower than the long-term
research question: it is a project-owned `Win32` class for read-only process
discovery, plus a small NiceGUI window for exercising that class. The UI does
not expand the library's process or memory capabilities.

## Terminology

`External host` means the primary logic runs outside `Gw.exe`. It does not, by itself, mean that the game process is unmodified.

`Pure external` means the tool does not allocate executable remote memory, write code into `Gw.exe`, or patch its code. Process-memory reads and writes may still occur.

`Payload injection` means an external program writes a small executable payload and/or code patch into `Gw.exe`, without loading a conventional DLL. It is still injection in the technical sense.

`DLL injection` means an in-process DLL owns a substantial runtime. Current Py4GW Reforged uses this model.

“Non-injected” is shorthand for the pure-external model above. If a future
experiment places a payload, executable code, or a patch in `Gw.exe`, it is
technically injection and must not be described as non-injected.

## Relationship to Py4GW Reforged

Py4GW Reforged is a Python automation and scripting library for Guild Wars. It
provides tools for in-game interaction, from single-character helpers to
multi-account bots. Python does not run as a standalone interpreter in that
model: the launcher injects `Py4GW.dll` into the game, and the DLL embeds the
Python runtime inside `Gw.exe`.

Reforged reaches the game through two connected paths:

- `Py*` bindings such as `PyAgent`, `PyPlayer`, `PyImGui`, and `PySystem`, with
  wrapper classes in `Py4GWCoreLib`;
- shared memory containing live game state such as agent positions, health,
  map state, and world context.

The native companion project builds the injected `Py4GW.dll`:
<https://github.com/apoguita/Py4GW_Reforged_Native>

Stealth is intended to investigate how selected Reforged capabilities could be
recreated from an external Python process. It is not currently a replacement
for the complete Reforged library, and each capability must be designed and
validated separately.

## Current Implementation

Status: verified from the current source, Pyright run, and focused tests.

The current project surface is:

```text
main.py                 NiceGUI native test window
py4gw/                  project package
  win32/win32.py        Win32 process-discovery class
tests/test_win32.py     focused process tests
tests/nicegui_probe.py  manual NiceGUI dependency check
```

The `Win32` class currently provides `list_processes`,
`find_guild_wars`, and `format_processes`. `find_guild_wars` matches the
executable filename `Gw.exe` case-insensitively and reports the PID, name,
path, and path error when applicable.

The root `main.py` window has one `Win32 process test` tab. Its `List all
processes` and `Find Gw.exe` buttons call the public class methods and show
structured results in a table. NiceGUI is a presentation dependency only; it
does not own Windows API declarations, process handles, memory operations, or
Guild Wars-specific rules.

The project enforces this code boundary with `pyrightconfig.json`: Pyright
checks `main.py`, `py4gw/`, and `tests/`, while excluding the local research
checkouts under `external/`. The selected Pyright/Pylance interpreter must be
the same interpreter where NiceGUI and the editable project are installed.

## Confirmed Research

### Current Py4GW Reforged

- The Python repository describes `Py4GW.dll` as embedding Python inside Guild Wars. The external bridge communicates with an injected bridge widget; it does not replace the injected runtime.
- The native repository identifies itself as a Windows-only, 32-bit injected DLL. Its runtime creates hooks and runs frame/callback work in process. Relevant owners include `src/Py4GW.cpp`, `src/dllmain.cpp`, `src/base/hooker.cpp`, and `include/callback/callback.h`.
- The native code uses MinHook through `HookBase`. Its game- and render-driven callbacks are therefore in-process behavior, not an externally delivered callback mechanism.

Conclusion: the existing `Py*` modules and Python callback system cannot be imported by an ordinary external Python interpreter. They exist because the DLL has embedded a Python runtime inside `Gw.exe`.

### GwAu3

GwAu3's AutoIt application is external, but its command execution mechanism is not pure external memory access.

- `API/Core/GwAu3_Core_Assembler.au3`, `Assembler_ModifyMemory()`, allocates executable memory in `Gw.exe` with `VirtualAllocEx`, writes generated assembly, and installs detours including `MainStart -> MainProc`.
- Its generated `MainProc` checks a remote command queue and transfers execution to the queued command when the game reaches the detoured main path.
- `API/Core/GwAu3_Core.au3`, `Core_Enqueue()`, uses `WriteProcessMemory` to place externally-built command records in that queue.
- `API/Core/GwAu3_Core_Scanner.au3` also uses a remotely created thread for its scan procedure.

Conclusion: GwAu3 demonstrates that an external controller can gain broad game-thread execution capabilities without an injected DLL or embedded scripting runtime. It does so by injecting a smaller executable payload and patching game code. AutoIt is not the special capability; a 32-bit Python process with appropriate Windows interop could use the same operating-system primitives.

## Capability Boundary So Far

| Capability | Pure external process | External host plus remote payload | Current Py4GW DLL |
|---|---|---|---|
| Read process memory | Yes | Yes | Yes |
| Write process memory | Yes | Yes | Yes |
| Run controller logic outside the game | Yes | Yes | Bridge/client split only |
| Reliably execute code on a known game path | Not established | Yes, as GwAu3 demonstrates | Yes |
| Hook internal functions / receive internal callbacks | No normal detour callback path | Yes | Yes |
| Use Py4GW `Py*` modules | No | No, unless separately recreated | Yes |
| In-game D3D/ImGui overlay | No | Possible only with further in-process code | Yes |

Important distinction: an external process can ask Windows to start code in another process, but that does not prove that a particular Guild Wars function is safe on that thread. Thread affinity, calling convention, object lifetime, and game state must be established per function.

## Open Research Questions

1. Which useful Guild Wars state can be read externally with stable, validated pointer chains?
2. Which game-owned command, UI-message, or packet paths can be driven by external writes alone, without a new payload?
3. For each desired internal function, what are its x86 ABI, argument lifetime, required state, and thread-affinity constraints?
4. Can a strict pure-external prototype provide enough value before considering any remote payload?
5. If a remote payload is ever considered, what is the smallest auditable scope and how can installation, version mismatch, shutdown, and recovery be made observable?

## Current Project Boundary

The first read-only runtime exists in the `py4gw` package. It currently lists
Windows processes and finds `Gw.exe` candidates by executable filename. The
root NiceGUI window is only a test and presentation surface over that runtime.
Neither component reads target memory or modifies any process.

No claim in this document is live-client verified. GwAu3 behavior was established from source inspection; Py4GW Reforged behavior was established from current repository sources and project documentation.

## Current Starting Scope: Generic Process-Scanning Library

The first deliverable is a project-owned Windows library plus a small test
surface that can:

1. enumerate running processes and present a useful list;
2. find every process whose executable filename is `Gw.exe`; and
3. leave process-memory scanning for a separately defined future capability.

The implemented part is generic Windows process handling plus one explicit
`Gw.exe` filename filter. It contains no Guild Wars signatures, layouts,
pointer chains, command paths, or behavior interpretation. The root UI exposes
the implemented operations without adding a second process layer.

There is still no decision about payload injection, DLL injection, remote
execution, hooks, or memory scanning. Those questions remain outside the
current starting scope.

### Design order for this deliverable

- [x] Define the public vocabulary and data returned when processes are
  listed: the minimum process summary, unavailable metadata, and errors.
- [ ] Define how a caller selects a process: explicit PID input and the
  lifetime of the resulting library object.
- [ ] Define exactly what “scan” means for version one: what is searched,
  what the query looks like, and what a successful result contains.
- [x] Define the library boundary versus a presentation layer. The library
  returns structured data; `main.py` renders it without becoming the library
  API.
- [x] Choose the narrowest Windows APIs and Python implementation needed for
  the current read-only capability.

### Current design decision

The current direction is: build the generic process-scanning library from
small project-owned pieces, progressing one public capability at a time. The
NiceGUI window is deliberately limited to testing and presenting capabilities
that already exist in the library.

### First concrete capability: Guild Wars process discovery

The first capability is discovery of running Guild Wars processes so a caller
can locate them. A process is a Guild Wars *candidate* when its executable
filename is `Gw.exe`, compared case-insensitively. This is process discovery
only, not proof of a supported client build or of any future memory-scanning
capability.

Discovery returns every candidate, not just the first one. Each result should
at minimum preserve:

- PID (the value used to select a specific process later);
- executable filename used for the match; and
- executable path when Windows makes it available, with an explicit
  unavailable/error status when it does not.

The console API and the NiceGUI table may render those records, but the
records remain structured library data. No process is opened for modification
and no process memory is scanned in this capability.

The implementation rules and object responsibilities for this first slice are
the active [process-discovery design contract](docs/DESIGN.md).

The project-wide naming and Python conventions are in the [programming style
guide](docs/STYLE.md).

## MemLib Context

MemLib has been fetched as an external source checkout at `external/MemLib`, pinned by the checkout currently present at commit `d044a4f8ab5f12121501650e648c9895f8f14eb0`.

The fetched source describes MemLib as a Windows-only Python package that provides Win32 process/module/thread wrappers, remote memory operations, binary scanners, FASM assembly helpers, simple inline jump hooks, and shared-memory utilities. It is a candidate mechanism library for future experiments, not a selected runtime dependency or a statement of supported project behavior.

Important limits established from its own README and source:

- `Hook` is an inline jump helper, not a complete detour engine or a proof that a chosen patch point is safe.
- MemLib can provide process and transport mechanisms, but it does not supply Guild Wars signatures, function ABIs, thread-affinity facts, data layouts, or lifecycle policy.
- No MemLib method has been called against Guild Wars for this project.

## GwAu3 Source Availability

GwAu3 is available locally for historical and comparative source inspection at
`external/GwAu3`, fetched from
`https://github.com/GwAu3-Projects/GwAu3.git` and currently pinned at commit
`f5af99dc3004c81dfdeb119c6fa1e41edb23ddc1`.

This checkout is research context only and is not a Stealth dependency. The
existing GwAu3 conclusions in this document were recorded from the previously
isolated checkout named under Sources Consulted; this fresh revision has not
yet been re-inspected or used to revise those conclusions.

The user-provided `BUILDING_WITH_MEMLIB.md` was reviewed as technical reference material. It contains design proposals and examples; it is not treated as an instruction source or as verification of MemLib/Guild Wars behavior. Any later adoption decision must be supported by the fetched MemLib source, project-specific investigation, and targeted tests.

## Local Ownership Decision

Py4GW Stealth will not depend on or import MemLib for its initial work. The fetched checkout remains research context only.

The current implementation is one small, project-owned `Win32` class for the
first process-discovery capability:

```text
py4gw/
    win32/
        win32.py      Win32 class: process listing and Gw.exe discovery
```

This is not authorization to copy MemLib wholesale. Reimplement the small
required surface against documented Windows behavior. If a later change
deliberately borrows actual MemLib source, preserve its MIT license notice and
record exact file-level provenance in the project documentation.

The current local work is only pure external, read-only process discovery.
Memory reads, module inspection, signatures, remote allocation, memory writes,
remote threads, DLL loading, executable payloads, and hooks are outside the
current scope.

## Live Observation: Gw.exe Discovery

Status: verified from a user-provided run of the current package.

The same read-only command was run with the Guild Wars client open and closed:

```text
python -c "from py4gw import Win32; win32=Win32(); print(win32.format_processes(win32.find_guild_wars()))"
```

With the client open, the observed result was:

```text
PID   | Name   | Path
39212 | Gw.exe | F:\GW\GW1\Gw.exe
```

With the client closed, the observed result was:

```text
No Gw.exe candidates are currently running.
```

This verifies the current filename-based process discovery behavior across
those two states. The Guild Wars build/version and exact observation timestamp
were not recorded in the report. The operation was read-only and performed no
cleanup or target modification.

## Sources Consulted

- `C:\Users\Apo\Py4GW_Reforged\README.md`
- `C:\Users\Apo\Py4GW_Reforged\docs\architecture\reference\py4-gw-conceptual-model.md`
- `C:\Users\Apo\Py4GW_Reforged\py4gw_bridge\README.md`
- `C:\Users\Apo\Py4GW_Reforged_Native\AGENTS.md`
- `C:\Users\Apo\Py4GW_Reforged_Native\src\Py4GW.cpp`
- `C:\Users\Apo\Py4GW_Reforged_Native\src\base\hooker.cpp`
- `C:\tmp\gwau3-analysis-20260920\API\Core\GwAu3_Core.au3`
- `C:\tmp\gwau3-analysis-20260920\API\Core\GwAu3_Core_Assembler.au3`
- `C:\tmp\gwau3-analysis-20260920\API\Core\GwAu3_Core_Scanner.au3`
- `C:\Users\Apo\Py4GW_Stealth\external\MemLib\README.md` (fetched source, commit `d044a4f8ab5f12121501650e648c9895f8f14eb0`)
- `C:\Users\Apo\Py4GW_Stealth\external\MemLib\MemLib\Process.py`
- `C:\Users\Apo\Py4GW_Stealth\external\MemLib\MemLib\SharedMemory.py`
- `C:\Users\Apo\Py4GW_Stealth\external\MemLib\MemLib\Hook.py`
- `C:\Users\Apo\Downloads\BUILDING_WITH_MEMLIB.md` (user-supplied technical reference; proposals/examples, not instruction authority)
- <https://nicegui.io/documentation> (Python UI components and project model)
- <https://nicegui.io/documentation/section_configuration_deployment> (native
  mode and pywebview requirements)
- <https://nicegui.io/documentation/tabs> (tab and panel usage)
- <https://nicegui.io/documentation/table> (table rows and updates)
