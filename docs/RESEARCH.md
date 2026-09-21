# Py4GW Stealth Research Record

This document contains the detailed research history and source comparisons
that were intentionally kept out of the GitHub front page. It is not the
project's short description or installation guide.

Status: current active research project; read-only process discovery and the
reusable scanner slice implemented
Scope: establish what an external Guild Wars controller can read, write, execute, and observe before expanding capabilities.
Authority: inspected current Py4GW Reforged and Py4GW Reforged Native sources; inspected the GwAu3 source checkout; and verified process discovery, section scanning, and the CharContext, GameContext, PreGameContext, Cinematic, GameplayContext, ServerRegion, InstanceInfo, TextParser, AvailableCharacterArray, PartyContext, GuildContext, and AccAgentContext read paths against one live client build. Other context behavior remains unverified.

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
research question: it is a project-owned `Win32` boundary, a reusable
read-only scanner consuming the copied offsets definitions, and a small
NiceGUI window for exercising process discovery. The UI does not expand the
library's process or memory capabilities.

The current source inventory for the native and Reforged context surfaces is
maintained in [CONTEXT_INVENTORY.md](CONTEXT_INVENTORY.md). It records the
native root accessors, the Reforged Python modules, their many-to-one mapping,
and which surfaces Stealth has actually implemented. That inventory is
comparative source evidence; it is not evidence that every context has been
externally validated.

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
  memory/memory.py      Read-only process-memory transport
  scanner/scanner.py    Offline pattern scanner core
  scanner/remote.py     PE sections and remote scanner
  scanner/patterns.py   Offset definitions and resolver chains
  context/char_context.py  Reforged CharContext layout, reader, and accessor
  context/game_context.py External GameContext layout, resolver, and reader
  context/pre_game_context.py External PreGameContext layout, resolver, and reader
  context/cinematic_context.py External Cinematic layout and reader
  context/gameplay_context.py External GameplayContext layout and reader
  context/server_region_context.py External ServerRegion layout, resolver, and reader
  context/instance_info_context.py External InstanceInfo layout, resolver, and reader
  context/text_parser_context.py External TextParser layout and GameContext reader
  context/available_character_context.py External account-roster array reader
  context/party_context.py External PartyContext hierarchy and list readers
  context/guild_context.py External GuildContext hierarchy and guild readers
  context/acc_agent_context.py External AgentContext summary and movement readers
tests/test_win32.py     focused process tests
tests/test_scanner.py   offline scanner tests
tests/test_remote_scanner.py  synthetic PE scanner tests
tests/test_patterns.py  offsets/resolver tests
tests/test_cinematic_context.py live Cinematic integration test
tests/test_gameplay_context.py live GameplayContext integration test
tests/test_server_region_context.py live ServerRegion integration test
tests/test_instance_info_context.py live InstanceInfo integration test
tests/test_text_parser_context.py live TextParser integration test
tests/test_available_character_context.py live AvailableCharacterArray integration test
tests/test_party_context.py live PartyContext integration test
tests/test_guild_context.py live GuildContext integration test
tests/test_acc_agent_context.py live AccAgentContext integration test
tests/test_context.py   live CharContext integration test
tests/nicegui_probe.py  manual NiceGUI dependency check
```

The `Win32` class currently provides `list_processes`,
`find_guild_wars`, and `format_processes`. `find_guild_wars` matches the
executable filename `Gw.exe` case-insensitively and reports the PID, name,
path, and path error when applicable.

The `Scanner` class scans a local byte snapshot. It supports the
Reforged escaped pattern literals, masks, signed result offsets, bounded
ranges, first/all/nth matches, and the native C-string compatibility behavior
used by the copied offsets definitions. It is deliberately independent of
Windows handles.

The `ProcessMemoryReader` and `RemoteScanner` add the read-only external path:
they open a selected process, parse its x86 PE section ranges, scan those
ranges in bounded chunks, and execute the copied `Patterns` resolver
operations. Their section and resolver path, plus the `CharContext`,
`GameContext`, `PreGameContext`, `Cinematic`, `GameplayContext`,
`ServerRegion`, `InstanceInfo`, and `TextParser` readers have been implemented
and verified. `AvailableCharacterArray`, `PartyContext`, `GuildContext`, and
`AccAgentContext` have also been implemented and verified
against one live client build. This does not establish compatibility with
other builds.

The root `main.py` window has a client-selection tab and read-only context
tabs for a connected client. NiceGUI is a presentation
dependency only; it does not own Windows API declarations, process handles,
memory operations, or Guild Wars-specific rules.

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

### GwAu3 character-name discovery

Status: verified by source inspection of the checked-out GwAu3 revision. This
is not yet verified against a live Guild Wars client from Stealth.

GwAu3 uses the character name to make a list of `Gw.exe` candidates useful for
human selection. Its character-name path is:

1. Enumerate processes whose executable name is `gw.exe`.
2. Open one candidate process and discover its main module base address.
3. Read the module's PE headers and record the virtual ranges of sections such
   as `.text`.
4. Read the `.text` section and search for the x86 byte pattern
   `8B 03 83 C4 10 A3`.
5. From the match, read a 32-bit pointer at the pattern-relative offset used
   by GwAu3 (`match + 6 - 0xF`).
6. Read a fixed-size UTF-16/wchar character-name value from that pointer.
7. When the caller supplied a character name, compare the trimmed result and
   keep the matching PID/window. When scanning all clients, return the name
   associated with each candidate.

The relevant source paths are `API/Core/GwAu3_Core.au3`,
`API/Core/GwAu3_Core_Scanner.au3`, `API/Modules/Data/GwAu3_Data_Player.au3`,
and `API/Core/GwAu3_Core_Memory.au3`. `Scanner_ScanGW` does not check the
character-pattern result before calling `Player_GetCharName`, which is a
source-level weakness rather than evidence that every candidate is identified.

This mechanism is a read-only pattern scan and pointer dereference. GwAu3
opens the process with an all-access mask (`0x1F0FFF`), but Stealth should not
copy that privilege choice for a read-only identity probe. The pattern and
offset are historical comparative evidence, not a current-build guarantee.
They must be revalidated against the target build and treated as a target-
specific adapter rather than hidden inside generic Win32 process code.

### Implemented capability: reusable read-only scanner

The implemented scanner is reusable, not character-specific. Its job is to
search validated byte ranges in a selected process and report matches without
knowing what those matches mean. Guild Wars character-name discovery will be a
consumer of this scanner, not part of the scanner engine itself. The current
consumers are the maintained `CharContext`, `GameContext`, `PreGameContext`,
`Cinematic`, `GameplayContext`, `ServerRegion`, `InstanceInfo`, `TextParser`,
`AvailableCharacterArray`, `PartyContext`, `GuildContext`, and
`AccAgentContext` readers.

The scanner foundation should provide:

- bounded reads from a selected process and address range;
- exact byte patterns and explicitly represented wildcard bytes;
- correct handling of matches that cross read-chunk boundaries;
- zero, one, or many match results with their target addresses;
- validation of requested ranges and target pointer width;
- distinct outcomes for unreadable ranges, incomplete reads, and no matches;
- explicit ownership and closing of process handles; and
- deterministic offline tests that do not require a live Guild Wars client.

The implementation was staged as offline matching, bounded process-memory
transport, section/range selection, remote helper operations, and finally the
offsets resolver. A target-specific signature, pointer offset, or
text-decoding rule must not be hidden inside the reusable scanner.

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

The first read-only runtime exists in the `py4gw` package. It lists Windows
processes, finds `Gw.exe` candidates by executable filename, opens a selected
process for query/VM-read access, and scans validated x86 module sections.
The root NiceGUI window is only a test and presentation surface over process
discovery; it does not own the memory path or modify any process.

Claims about GwAu3 and Reforged behavior are source-based. The Stealth
CharContext, GameContext, PreGameContext, Cinematic, GameplayContext,
ServerRegion, InstanceInfo, process reader, and scanner observations marked as
live below were reproduced against one client build. None of these
observations establish compatibility with other builds or with the remaining
contexts.

## Initial Deliverable: Generic Process-Scanning Library

The first deliverable is a project-owned Windows library plus a small test
surface that can:

1. enumerate running processes and present a useful list;
2. find every process whose executable filename is `Gw.exe`; and
3. open a selected process read-only and scan its validated x86 module ranges;
4. load the copied `offsets/` definitions and execute reusable resolver chains.

The implemented part is generic Windows process handling, a bounded memory
reader, PE section discovery, a reusable pattern scanner, an offsets
resolver, and the first seven Guild Wars structure readers, migrated in this
order: `CharContext`, `GameContext`, `PreGameContext`, `Cinematic`,
`GameplayContext`, `ServerRegion`, and `InstanceInfo`. It does
not yet contain the
remaining context readers, command paths, or behavior interpretation. The root
UI exposes process discovery and these read-only context surfaces without
adding a second process layer.

Payload injection, DLL injection, remote execution, hooks, and writes remain
outside the current scope. Memory scanning is read-only and is now part of the
implemented foundation.

### Design order for this deliverable

- [x] Define the public vocabulary and data returned when processes are
  listed: the minimum process summary, unavailable metadata, and errors.
- [x] Define how a caller selects a process: explicit PID input and the
  lifetime of the resulting library object.
- [x] Define exactly what “scan” means for version one: validated module
  sections, masked patterns, bounded ranges, and target addresses.
- [x] Define the library boundary versus a presentation layer. The library
  returns structured data; `main.py` renders it without becoming the library
  API.
- [x] Choose the narrowest Windows APIs and Python implementation needed for
  the current read-only capability.

### Current design decision

The current direction is: keep the generic process-scanning library in small
project-owned pieces, progressing one public capability at a time. The
NiceGUI window remains deliberately limited to testing and presenting
capabilities that already exist in the library.

### First concrete capability: Guild Wars process discovery

The first capability is discovery of running Guild Wars processes so a caller
can locate them. A process is a Guild Wars *candidate* when its executable
filename is `Gw.exe`, compared case-insensitively. This is process discovery
only, not proof of a supported client build or of the scanner's compatibility
with that build.

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

The current implementation is a small, project-owned set of boundaries:

```text
py4gw/
    win32/
        win32.py      Win32 class: process listing and Gw.exe discovery
    memory/
        memory.py     read-only process-memory transport
    scanner/
        scanner.py    offline pattern matching
        remote.py     PE section and remote scanning
        patterns.py   offsets and resolver chains
```

This is not authorization to copy MemLib wholesale. Reimplement the small
required surface against documented Windows behavior. If a later change
deliberately borrows actual MemLib source, preserve its MIT license notice and
record exact file-level provenance in the project documentation.

The current local work is pure external, read-only process discovery and
read-only module scanning. Remote allocation, memory writes, remote threads,
DLL loading, executable payloads, and hooks are outside the current scope.

## Native scanner migration plan

The current `Py4GW_Reforged_Native` scanner is useful comparative design
material, but it is not one class with one responsibility. It has two layers:

1. `Scanner`/`FileScanner` provide section discovery, masked byte-pattern
   searches, range searches, address/string-use searches, near-call and
   function-start helpers, and section pointer validation.
2. `Patterns` loads pattern definitions and resolver chains, then combines scan,
   dereference, integer-read, arithmetic, section-validation, and fallback
   steps while preserving a resolution trace and failure policy.

The native implementation runs inside the target module. It can inspect mapped
module bytes directly and also map the module file from disk. Stealth runs
outside `Gw.exe`, so the Python version must replace those assumptions with
read-only `ReadProcessMemory` calls against a selected PID, explicit module
and section ranges, fixed-width x86 fields, and bounded reads. This is a
behavioral migration, not a line-by-line translation.

`ReadProcessMemory` does not introduce another signature set. It is only the
external transport used to obtain bytes from `Gw.exe`. The pattern bytes,
masks, offsets, section names, and resolver descriptions remain the same data
used by Reforged Native. The current Stealth repository now contains a copied
`offsets/` directory; future updates can be copied from Reforged into that
directory without maintaining a second Python translation of the signatures.
The Python loader must consume this JSON schema directly and every scan should
record the offsets source revision/build it used.

The offsets locate addresses and describe resolution steps; they do not by
themselves describe the fields of every object at those addresses. Those
layouts already exist as maintained context definitions in Reforged Native's
`GW::Context` headers and Reforged's Python `ctypes.Structure` declarations.
Stealth's structure reader should reuse or deliberately port those definitions
instead of inventing a competing model. The injected Python version can cast a
pointer and access `.contents` because it runs in the game process; the
external version must read the target bytes first and decode them, while
treating embedded pointers as target addresses that require explicit follow-up
reads.

The migration is intentionally staged:

1. **Parity inventory.** Record the native public operations and their exact
   success/failure behavior. Keep scanner mechanics separate from Guild Wars
   signatures and meanings.
2. **Offline pattern engine.** Implement typed byte patterns and masks, input
   validation, first/all/nth match behavior, offsets, and deterministic tests
   over ordinary byte buffers. No process access is involved.
3. **External memory reader.** Extend the existing Win32 boundary with a
   selected-process, read-only handle and bounded reads that preserve Windows
   error context. Add explicit close/context-manager ownership.
4. **Remote module sections.** Read and validate the target PE headers, expose
   `.text`, `.rdata`, and `.data` ranges, and reject invalid or unreadable
   ranges before scanning.
5. **Remote scanner.** Scan section/range data in chunks with overlap so a
   pattern crossing a chunk boundary is found. Return structured match and
   diagnostic results rather than a bare zero address.
6. **Scanner helpers.** Add the reusable native-style helpers one at a time:
   address uses, string uses, near-call resolution, function-start search, and
   section pointer validation. Each helper gets offline tests before any live
   process test.
7. **Pattern definitions and resolvers.** Only after the scanner core is
   stable, add a Python representation for pattern records and resolver chains,
   including fallback attempts, step traces, and continue/halt policies.
8. **Guild Wars consumers.** Add target-specific adapters, beginning with the
   maintained context readers. These adapters own signatures, pointer offsets,
   decoding, and semantic validation; the reusable scanner remains target
   agnostic.

Steps 1 through 8 now have project-owned implementations and focused tests.
The first Guild Wars-specific consumers are the externally read
`CharContext`, `GameContext`, `PreGameContext`, `Cinematic`,
`GameplayContext`, `ServerRegion`, and `InstanceInfo`, in that migration
order. All seven have been validated against one live client build.
Additional contexts remain separate future consumers and must be validated
independently.

## CharContext implementation and resolution

Status: source-verified and verified against one live client build.

The maintained Reforged definitions agree on the relevant layout:

- `CharContext` is `0x448` bytes;
- `CharContext.player_name` is an inline UTF-16/wchar field at offset `0x74`,
  with 20 code units;
- `GameContext.character` is a 32-bit target pointer at offset `0x44`.

The native context code obtains `GameContext` through the resolved
`context.base_ptr`: dereference that global to a base-context table, read the
entry at table offset `0x18` (index `6`), then read `GameContext + 0x44` to get
the `CharContext` address. Stealth uses the same target addresses with
explicit `ReadProcessMemory` calls; it does not cast remote pointers locally.

The copied `offsets/context.json` provides the `context.base_ptr` resolver.
`GameContext.initialize()` executes that resolver once and caches the
module-global pointer location for the lifetime of the connection.
`CharContext` reuses that initialized reader and follows the dynamic
character pointer for each read because the base, game, and character context
objects may change during client state transitions.

## GameContext implementation and resolution

Status: source-verified and verified against one live client build.

The external `GameContextStruct` follows the native and Reforged layout:

- it is `0x5C` bytes;
- `agent_context` is at `0x08`;
- `map_context` is at `0x14`;
- `char_context` is at `0x44`;
- `party_context` is at `0x4C`; and
- `trade_context` is at `0x58`.

All pointer fields are represented as fixed-width 32-bit target addresses.
The reader resolves `context.base_ptr` from the copied JSON definitions,
reads the base-context table, selects its `+0x18` entry, and decodes the
resulting `GameContext` bytes. The resolver location is cached for the
connection, while the base table and current context pointer are re-read for
each snapshot.

The live test observed `GameContext` at `0x024D9018`, with its character and
world pointers matching the independently read context addresses. This is a
read-only observation for one client build, not a cross-build guarantee.

## PreGameContext implementation and resolution

Status: source-verified and verified against one live client build.

The external `PreGameContextStruct` is `0x100` bytes and the nested
`LoginCharacter` record is `0x78` bytes, matching the native and Reforged
definitions. Its `chars_array` is read as a contiguous value array through the
existing external `GWBaseArray`/`GWArrayValueView` boundary. Pointer fields are
fixed-width target addresses, including the login-character item buffer and
model pointer.

The native context initializer resolves `context.pregame_context_addr` as a
stable global-pointer location. The external reader caches that location and
re-reads the pointed-to value for each snapshot. The pointed-to context is
allowed to be null: that is the expected state while the client is outside the
selection menus, so `read()` returns `None` rather than treating it as a
resolver failure.

The live test resolved the global pointer at `0x015EA2EC`. During the recorded
run the pointed-to value was null because the client was already in-game; the
reader reported the inactive pre-game state correctly.

## Cinematic implementation and resolution

Status: source-verified and verified against one live client build.

The native `Cinematic` record is an `0x08`-byte pair of fixed-width `uint32`
fields (`h0000` and `h0004`). It is owned by `GameContext` at offset `0x30`.
The external reader reuses the connection's initialized `GameContext` resolver,
reads that pointer for each snapshot, and returns `None` when the pointer is
null. This keeps the context optional while preserving the native pointer
relationship; it does not add a second signature scan.

The live test resolved `Cinematic` at `0x025065D8` and read both fields as
`0x00000000` during the recorded run. The address and values are observations
for one client build, not cross-build guarantees.

## GameplayContext implementation and resolution

Status: source-verified and verified against one live client build.

The native and Reforged definitions agree on a fixed `0x78`-byte structure:

- `h0000` contains 19 `uint32` values;
- `mission_map_zoom` is a `float` at offset `0x4C`; and
- `unk` contains 10 trailing `uint32` values.

The native context layer resolves `context.gameplay_context_addr` as a stable
global-pointer location. The external reader caches that resolver during
connection, re-reads the pointed-to gameplay context for each snapshot, and
returns `None` when the target pointer is null. It uses the copied JSON
resolver and does not add a second signature definition.

The live test resolved the global pointer at `0x015EAAB8`, the current
`GameplayContext` at `0x02421248`, and read `mission_map_zoom` as `1.500`.
These addresses and values are observations for one client build, not
cross-build guarantees.

## ServerRegion implementation and resolution

Status: source-verified and verified against one live client build.

The native and Reforged definitions agree that `ServerRegion` is a single
signed 32-bit value, not a pointer to a larger context structure. Reforged's
`ServerRegionStruct` contains one `c_int32 region_id` field, and the native
enum uses `-2` for International, `0` for America, then the named regional
values, with `0xff` reserved for Unknown.

The native resolver stores the address of that value in
`Context::g_region_id_addr`. Its JSON-backed resolver is
`map.region_id_addr`: it scans the `region_id_ref` pattern and applies the
native dereference step. Stealth therefore resolves that address once during
connection, caches the resolver result, and reads four bytes for each
snapshot. It does not introduce a hard-coded field offset or scan the pattern
again for every read.

The focused test is `tests/test_server_region_context.py`. It checks the
fixed-width layout, resolver address, and signed value when a client is
running. The recorded run resolved the value at `0x017C63A8` and read region
ID `0` (America). These are observations for one client build, not
cross-build guarantees.

## InstanceInfo implementation and resolution

Status: source-verified and verified against one live client build.

The native and Reforged definitions agree on these fixed-width layouts:

- `MapDimensionsStruct` is `0x18` bytes;
- `AreaInfoStruct` is `0x7C` bytes; and
- `InstanceInfoStruct` is `0x14` bytes, with target pointers at offsets
  `0x00`, `0x08`, and `0x10`.

The native map resolver exposes `map.instance_info_addr`, which resolves the
current `InstanceInfo` structure address from the copied `instance_info_ref`
signature. Stealth caches that resolved address during connection and reads
the root structure on demand. Its nested `terrain_info1`, `current_map_info`,
and `terrain_info2` properties follow their target-process pointers through
`ReadProcessMemory`; they never dereference those addresses as local Python
pointers. The `AreaInfoStruct` flag and file-ID properties are ported from the
Reforged source.

The live test resolved `InstanceInfo` at `0x01C4A150`, read instance type `0`,
and read current map metadata with campaign `1`, region `0`, and file ID `0`.
These values and addresses are observations for one client build.

## TextParser implementation and resolution

Status: source-verified and verified against one live client build.

The native `TextParser` pointer is a field of the already-resolved
`GameContext`, at offset `+0x18`. Stealth follows that field for each read; it
does not add a second signature scan or invent a global pointer resolver. The
native root layout is `0x1D4` bytes, with the `TextCache*` field at `+0x30`,
the auxiliary structure pointer at `+0x180`, and `language_id` at `+0x1D0`.
Those pointer fields are followed through the external memory reader when the
corresponding properties are requested.

The live test read `TextParser` at `0x0257E9E0` and observed language ID `0`.
That address and value are observations for one client build.

## AvailableCharacterArray implementation and resolution

Status: source-verified and verified against one live client build.

The native account roster is a global `GWArray<AvailableCharacterInfo>`
resolved by `player.available_characters_addr`. It is distinct from the
`PreGameContext::chars_buffer` preview array. Stealth caches the resolved
`GWArray` address, rereads its header for each snapshot, and follows the array
buffer through the external memory reader. Each entry is `0x84` bytes and
includes the fixed UTF-16 name plus packed map, profession, campaign, level,
and PvP properties.

The live test resolved the roster array at `0x017AF28C`, read 14 entries, and
observed `Fezzik The Untamed` as the first entry. These values and the address
are observations for one client build.

## PartyContext implementation and resolution

Status: source-verified and verified against one live client build.

The native party accessor follows `GameContext.party`; no separate signature
or callback is required. The root structure is `0xD0` bytes and contains
remote `GWArray` headers for parties and searches plus intrusive request and
sending lists. Stealth reads those arrays and traverses `GwList` links with
fixed-width x86 addresses and a bounded loop guard.

The live test resolved `PartyContext` at `0x024A5D78`, observed one party, one
party-search entry, and a party-leader state. These values and the address are
observations for one client build.

`WorldMapContext` is intentionally not claimed as migrated yet. The native
implementation receives its pointer from an injected UI callback and publishes
it through Reforged shared memory. The copied offsets contain no direct
external resolver for that context, so adding a guessed pattern would violate
the external-reader design.

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

## Live Observation: Remote scanner initialization

Status: verified from a user-provided read-only run against a live `Gw.exe`.

The external scanner opened PID `47852`, identified the main module as
`F:\GW\GW1\Gw.exe`, and successfully parsed these sections:

```text
.text  14553088 - 20026880
.rdata 20029440 - 22866432
.data  22867968 - 28505400
.rsrc  28508160 - 30277632
.reloc 30277632 - 30573056
```

The reported module base was `14548992` and its image size was `16027648`.
This verifies process opening, main-module discovery, PE parsing, and section
range initialization against that live client. The later CharContext
observation records the separate verification of a copied Guild Wars resolver
and its target pointer chain.

## Live Observation: Remote byte scan

Status: verified from a user-provided read-only run against the same live
client.

The scanner read 16 bytes at the beginning of `.text`, built a pattern from
the first four bytes, and searched the remote `.text` range. The observed
addresses were:

```text
text start:  0x00DE1000
scan result: 0x00DE1000
```

This verifies the complete read-and-search path against live Guild Wars
memory. It is a transport and scanner check only; it does not validate a
Guild Wars-specific signature or resolver definition.

## Live Observation: CharContext resolver and name read

Status: verified from a user-provided read-only run against the same live
client.

The `context.base_ptr` resolver succeeded with this trace:

```text
scan_ref       0x00E6CE4B
deref_ptr      0x015E6170
validate_ptr   success in .data
```

Following the documented target layout produced:

```text
base_context   0x0251C348
game_context   0x024D9018
char_context   0x0251DA70
player_name    non-empty UTF-16 name decoded successfully
```

The name was read from `CharContext + 0x74` as a fixed 20-code-unit
UTF-16LE field. This verifies the initial target-specific read path: a copied
resolver, explicit 32-bit pointer reads, and a structure field decode. The
same path is now exposed by `py4gw.context.CharContext`; the observation does
not prove that the same offsets work across other client builds.

The context port also includes the Reforged `GW_Array` header and its two
array-view behaviors. `GWArrayValueView` reads contiguous values from a
remote buffer, while `GWArrayView` reads target pointers and then the remote
structures they reference. This is an external adaptation of the Reforged
behavior: those pointers are never dereferenced as local Python pointers.

## Live Observation: Context performance breakdown

Status: verified by `tests/perf_context.py` against the same running client;
the Guild Wars build and host load were not recorded.

Before resolver caching, one five-sample run measured the following
approximate averages:

```text
resolver.pattern_scan       4.664 ms, 9 reads, 589,878 bytes
resolver.pointer_chain      0.030 ms, 4 reads, 16 bytes
context.read                4.739 ms, 14 reads, 590,990 bytes
context.read.cached_address 0.009 ms, 1 read, 1,096 bytes
```

This separates the repeated `.text` signature scan from structure decoding:
the scan dominates `CharContext.read`, while decoding a structure at an
already-resolved address is negligible. The UI's derived array views are a
separate cost; in this run `h00EC_ptrs` performed 520 remote reads and took
about 2.7 ms. These numbers are one live observation, not a cross-build or
cross-machine benchmark.

The resolver is now initialized during `ConnectedClient` construction and its
stable module-global pointer location is cached. A follow-up five-sample run
measured approximately `0.012 ms` for cached address resolution and
`0.026 ms` for `context.read`, with four remote reads for the dynamic pointer
chain plus the 0x448-byte structure. The one-time connection initialization
still took approximately `3.766 ms`, which is the intended location for the
signature scan cost.

This cache boundary matches Reforged Native. `GW::Context::Initialize()`
resolves `context.base_ptr` once and is guarded by `g_initialized`. Its
`GetGameContext()` then re-reads the pointer stored at `g_base_ptr` and selects
the game-context slot at `+0x18`; `GetCharContext()` re-reads the character
pointer at `GameContext + 0x44`. Therefore the external reader caches the
resolver's stable pointer location but does not cache the dynamic context
object addresses.

## Live Observation: GuildContext

Status: verified against the same running client build with
`tests/test_guild_context.py`.

`GuildContext` is reached directly from the current `GameContext` at the
maintained `guild_context` field. No new signature scan or callback bridge is
needed. The reader follows that pointer, reads the complete maintained
0x368-byte field surface, and follows its remote `GW_Array` members through
the external memory reader. The native header contains an older `0x3BC` size
comment, but its explicit field offsets end at the 0x368-byte roster array;
the Python layout follows those concrete offsets.

The live test resolved `GuildContext` at `0x025732D8` and observed player
`Fezzik The Untamed`, 101 guild records, 42 roster entries, and 20 history
entries. These values are one observation and are not assumed stable across
client builds or account state.

## Live Observation: AccAgentContext

Status: verified against the same running client build with
`tests/test_acc_agent_context.py`.

The Reforged Python module calls this surface `AccAgentContext`; the native
project defines the same root as `GW::Context::AgentContext`. It is reached
directly through `GameContext.agent` at `+0x08`. The external reader follows
that pointer and reads the maintained 0x1B0-byte root, including the summary
array and movement-pointer array. Nested pointers are read through the
external memory reader and are never treated as local Python pointers.

The live test resolved `AgentContext` at `0x0257E208` and observed 2,296
summary entries, 45 movement entries, 45 valid movement IDs, and instance
timer `1709016840`. These values are one observation and are not assumed
stable across client builds or account state.

## AgentArray traversal and materialization

### Verified in Py4GW Reforged Native

The native agent array is a `GWArray<Agent*>` resolved through the
`agent.agent_array_addr` signature. `Context::GetAgentArray()` returns that
array when its header is valid. `GetAgentByID()` performs the bounds and
non-null pointer checks, then applies the stale-agent gate:

```text
agent_movement.size() > agent_id
and agent_movement[agent_id] != nullptr
```

The native code then uses the existing in-process `Agent*`. It does not copy a
full `Agent` structure for each traversal.

The native shared-memory updater does traverse the populated array each frame.
For every valid pointer it reads the common `Agent` fields needed for
classification: type flags at `Agent + 0x9C`, and, for living agents,
allegiance at `AgentLiving + 0xB5` and the related living flags. It publishes
only the agent pointer, agent ID, and categorized ID/index references. The
shared-memory cap is 300 entries.

The updater also refuses to publish an array while the map is not ready, while
the client is observing, or during loading. This is a state-validity gate in
addition to the pointer and movement-array checks.

### Verified in Reforged Python

The public `AgentArray.Get*Array()` methods first consume the native shared
memory wrapper. They return IDs from the already-classified arrays: enemy,
ally, neutral, living, item, gadget, and so on. This path does not
materialize a full ctypes agent for every entry.

`AgentArray.GetAgentByID()` materializes one requested `AgentStruct` from the
published pointer. Filters and sorts then operate on IDs and call methods such
as `Agent.GetAllegiance`, `Agent.IsAlive`, and `Agent.GetXY`; those calls
materialize or access the selected agent as needed.

The direct `AgentArrayStruct.raw_agents` path can materialize every pointer and
classify the entire array in Python, but its recurring cache-update callback is
disabled in the inspected source. It is therefore not the normal public
agent-array path.

### Consequence for Stealth

The agent array is populated, and allegiance is a required classification
field. A Stealth traversal that must produce enemy/ally/living categories must
read enough of every valid candidate to inspect at least the common type and,
for living records, the allegiance field. That work cannot be eliminated.

It can still avoid full object materialization. The proposed external design
is:

1. Read the bounded pointer table once and capture `(agent_id, address)`
   references.
2. Apply the movement-array stale-agent check.
3. Read a small classification projection containing the common type and the
   living fields needed for allegiance/dead-state categorization.
4. Build ID/reference lists for all, ally, enemy, items, gadgets, and other
   categories.
5. Materialize the complete `Agent`, `AgentLiving`, `AgentItem`, or
   `AgentGadget` structure only for callers that request detailed data.

This preserves the native/Reforged separation: classification traverses the
populated array, while detailed structures remain on demand. The cost should
be measured as remote-read calls, bytes transferred, and Python object count;
the number of agents alone is not enough to identify the bottleneck.

## Sources Consulted

- `C:\Users\Apo\Py4GW_Reforged\README.md`
- `C:\Users\Apo\Py4GW_Reforged\docs\architecture\reference\py4-gw-conceptual-model.md`
- `C:\Users\Apo\Py4GW_Reforged\py4gw_bridge\README.md`
- `C:\Users\Apo\Py4GW_Reforged_Native\AGENTS.md`
- `C:\Users\Apo\Py4GW_Reforged_Native\include\GW\context\context.h`
- `C:\Users\Apo\Py4GW_Reforged_Native\include\GW\context\game.h`
- `C:\Users\Apo\Py4GW_Reforged_Native\src\GW\context\context.cpp`
- `C:\Users\Apo\Py4GW_Reforged_Native\src\GW\context\context_methods.cpp`
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
