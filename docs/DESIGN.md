# Current Design Contract

The naming and general Python rules for this project are recorded in the
[programming style guide](STYLE.md). New code follows that guide unless an
external API requires a different spelling.

The project is a normal editable Python package. `pyproject.toml` is the
package-configuration file at the project root. It includes the `py4gw`
package and declares NiceGUI's native extra as a runtime dependency.

## Current architecture

```text
main.py
  MainWindow
    NiceGUI native window
      Guild Wars client-selection tab
        py4gw.Win32 + ConnectedClient
          documented Windows APIs

py4gw/
  __init__.py
  client.py       Selected-client connection and script facade
  perf_counter.py  Ported PyProfiler performance counters
  win32/
    __init__.py
    win32.py
  memory/
    memory.py       Read-only process-memory transport
    mailbox.py      Fixed-width mailbox record codec; no target writer yet
  scanner/
    scanner.py      Offline pattern matching
    remote.py       PE sections and remote scanning
    patterns.py     Offset definitions and resolver chains
  ui/
    frame.py         UI frame, callback, and message layouts; frame-array reader
    frame_tree.py    Read-only frame relations and callback-based lookup
    frame_context.py Frame-published context location and frame-id cross-check
  context/
    char_context.py Reforged CharContext layout, reader, and accessor
    game_context.py External GameContext layout, resolver, and reader
    pre_game_context.py External PreGameContext layout, resolver, and reader
    cinematic_context.py External Cinematic layout and reader
    gameplay_context.py External GameplayContext layout and reader
    server_region_context.py External ServerRegion layout, resolver, and reader
    instance_info_context.py External InstanceInfo layout, resolver, and reader
    text_parser_context.py External TextParser layout and GameContext reader
    available_character_context.py External account-roster array reader
    party_context.py External PartyContext hierarchy and list readers
    guild_context.py External GuildContext hierarchy and guild record readers
    acc_agent_context.py External AgentContext summary and movement readers
    camera_context.py External Camera layout and reader
    friend_list_context.py External FriendList layout and reader
    chat_buffer_context.py External ChatBuffer layout and reader
    world_context.py External WorldContext root and child readers
    trade_context.py External TradeContext root and offer readers
    item_context.py External ItemContext, Bag, Item, Inventory, formula,
                    composite-model, storage, and PvP readers
    account_context.py External AccountContext root reader
    gadget_context.py External GadgetContext root and bounded info reader
    gw_list.py     External intrusive GwList/link readers
    gw_array.py    External GW_Array and array-view readers
```

The library owns process behavior. The root UI presents and exercises that
behavior. The UI must not become a second implementation of Windows process
handling.

The source inventory for the context layer is maintained in
[CONTEXT_INVENTORY.md](CONTEXT_INVENTORY.md). It is the checklist for
comparing native C++ roots, Reforged Python modules, and external Stealth
readers. Context work must account for the fact that one Python module can
aggregate several native structures; a file-for-file copy is not the design.
The per-context parity verdict, including missing source-backed properties and
helpers, is maintained in
[CONTEXT_PARITY_AUDIT.md](CONTEXT_PARITY_AUDIT.md).
The binary, one-context-at-a-time certification procedure is maintained in
[PARITY_CERTIFICATION_CHECKLIST.md](PARITY_CERTIFICATION_CHECKLIST.md).

## Source-port migration contract

The primary implementation task is an exhaustive source port, not a reduced
read-only redesign. `Py4GW_Reforged_Native` and `Py4GW_Reforged` are the
authority for the context declarations and public Python surface.

The Reforged Python context is the first porting source for class names,
properties, helpers, and facade methods. The native C++ context is used to
verify the byte layout, pointer ownership, resolver relationship, and any
operation that has no Python declaration. When the two sources expose
different names for the same bytes, preserve the source name and add a
documented alias rather than choosing one and deleting the other.

For every source context we port:

1. copy every `ctypes.Structure`, `_fields_` entry, fixed-size array, field
   name, property, helper, lifecycle method, and public alias from the source;
2. preserve source names, offsets, relationships, and behavior; additive
   snake-case aliases may be provided for this project's style, but source
   names are never removed or renamed;
3. copy declarations even when the member is not ported yet. A write, callback,
   injected cache, or game-thread operation is declared with the same public
   signature and reports an explicit `NotImplementedError` naming the mechanism
   it still needs until that mechanism is built;
4. adapt only the transport boundary: in-process `POINTER(T)` dereferences
   become fixed-width target addresses plus a remote read, and direct
   `GW_Array` views become bounded remote views; and
5. record the exact source operation and what the member still needs. Do not
   remove a declaration because it is inconvenient, infer a new meaning from
   an offset, or replace a source traversal with an invented one.

This produces two separate answers for each member: **declared parity** (the
source field/property/method exists with the source contract) and **runtime
availability** (the operation can currently execute through the external
transport). A context is not called source/API-parity complete until both are
complete, but an operation that is not ported yet must still be visible in the
code and stubs.

## Current capability

The current library surface is deliberately small, and only part of it is
read-only:

1. ask Windows for the running process list;
2. find processes named `Gw.exe`, case-insensitively;
3. return each matching process's PID, executable name, and path when
   available; and
4. open a selected process with query and VM-read access only;
5. parse its x86 PE section ranges and scan them with masked patterns; and
6. load the copied `offsets/` definitions and execute their resolver steps.

The read half of the library does not change a process, inject anything, or run code
in a process. On top of it, and separately from it, `py4gw/game_thread/` does all
three: `py4gw.connect()` installs two entry hooks, a dispatcher emitted as machine
code from Python, an observer and the shared block the two sides exchange through,
and `py4gw.disconnect()` puts both functions' original bytes back and frees
everything it placed. Connecting is therefore a write; `connect(...,
game_thread=False)` is the read-only connection, and every reader below is reached
the same way on either. The first target-specific structure readers were migrated in
this order: `CharContext`, `GameContext`, `PreGameContext`, `Cinematic`,
`GameplayContext`, `ServerRegion`, `InstanceInfo`, `TextParser`,
`AvailableCharacterArray`, `PartyContext`, `GuildContext`, `AccAgentContext`,
`Camera`, `FriendList`, `ChatBuffer`, `WorldContext`, `TradeContext`,
`ItemContext`, `AccountContext`, and `GadgetContext`; broader
Guild Wars structure interpretation is
still to port.
A `Gw.exe` result is a candidate found by filename, and a scanner result is
only an address selected by a pattern or resolver.

The `MailboxRecord` type validates a proposed fixed-width record format for a
WorldMap callback pointer handoff. It only converts and validates
local byte strings; it does not allocate memory in, write to, or execute code
inside a process. Nothing uses it: the frame-array route reaches the same pointer
without a hook, so the hook-based handoff it was written for has not been ported.

`py4gw/ui/` is the separate package for user-interface engine primitives. It
holds the `Frame` and callback layouts, the read-only frame-array reader, the
frame relations, and the frame-id cross-check that accepts a context pointer
only when the context agrees on its owning frame. `WorldMapContext` uses it to
acquire its root address without a hook. The package reads target memory only;
it creates, destroys, and dispatches nothing. Its evidence status and live test
procedure are in [`UI_FRAME_TREE.md`](UI_FRAME_TREE.md).

## The `Win32` class

There is one project class for the current process capability: `Win32`.

The class owns:

- the Windows API declarations;
- process-list enumeration;
- `Gw.exe` matching;
- executable-path lookup;
- Windows error reporting;
- native handle cleanup; and
- simple text formatting for console callers.

The scanner and memory reader are separate because they have different
responsibilities: the reader transports bytes and owns a process handle, while
the scanner interprets bytes as patterns and addresses. There is still no
separate process-model, error, presenter, or generic API-wrapper class.

### Public methods

#### `Win32.list_processes()`

Returns a current, PID-sorted snapshot:

```python
[
    {"pid": 1234, "name": "Gw.exe"},
    {"pid": 5678, "name": "explorer.exe"},
]
```

A process can exit after the snapshot is returned.

#### `Win32.find_guild_wars()`

Returns every case-insensitive `Gw.exe` match:

```python
[
    {
        "pid": 1234,
        "name": "Gw.exe",
        "path": r"C:\Games\Guild Wars\Gw.exe",
        "path_error": None,
    }
]
```

If Windows does not allow the path lookup, the process remains in the result,
with `path` set to `None` and the Windows error number in `path_error`.

#### `Win32.format_processes(processes)`

Returns a readable table for a console or log. It is presentation only;
callers should keep using the structured dictionaries as data.

## Main UI contract

`main.py` contains the `MainWindow` class and is the current test surface. It
is intentionally a root-level script so it can be launched directly:

```text
python main.py
```

The first tab is named `Guild Wars clients` and provides:

- `Refresh`, which discovers running `Gw.exe` clients;
- a PID selector and `Connect selected` button;
- a table showing PID, executable name, character, state, and path; and
- a live character read through `ConnectedClient` for each discovered client.

After a connection succeeds, the `Client data` tab is enabled. Its subtabs
currently expose `Cinematic`, `Camera`, `FriendList`, `ChatBuffer`, `WorldContext`, `GameplayContext`, `ServerRegion`, `InstanceInfo`,
`TextParser`, `AvailableCharacters`, `PartyContext`, `GuildContext`,
`PreGameContext`, `GameContext`, and `CharContext`,
each displaying every field in its maintained structure with the target offset.
The migration order for these readers is `CharContext`, `GameContext`,
`PreGameContext`, `Cinematic`, `GameplayContext`, `ServerRegion`,
`InstanceInfo`, `TextParser`, `AvailableCharacterArray`, `PartyContext`,
`GuildContext`, `AccAgentContext`, `Camera`, `FriendList`, `ChatBuffer`, then
the `WorldContext` root, party attributes/effects, player/NPC, hero/pet, and
skillbar, quest, title, TradeContext, and the ItemContext bag/item plus
source-defined auxiliary-table readers.
World child arrays, trade offers, and item arrays are bounded and read lazily.
The tables are paginated, sortable, filterable where applicable, and
selectable; long values wrap inside the normal window. `PreGameContext` is
allowed to be inactive while the client is in-game; in that state it reports
that no selection-menu context is currently available. Additional contexts
will be added as additional subtabs under this tab.

The UI catches `OSError` and `RuntimeError` from the library and displays the
diagnostic message — including the elevation refusal, which is what an unelevated
launch now produces when a client is selected. It closes temporary inspection
handles and keeps only the explicitly selected
connection open. The client-list inspection opens read-only
(`game_thread=False`), so refreshing the list never patches anything; a selected
connection installs the game-thread layer and takes it back out on disconnect.

## External memory architecture

The external memory path has three separate layers. The scanner and
process-memory transport are implemented, and `context.CharContext`,
`context.GameContext`, `context.PreGameContext`, `context.Cinematic`, plus
`context.GameplayContext`, `context.ServerRegion`, `context.InstanceInfo`,
`context.TextParser`, `context.AvailableCharacterArray`,
`context.PartyContext`, `context.GuildContext`, and
`context.AccAgentContext`, and `context.Camera` are the
first target-specific structure readers.

### Scanner

The scanner follows the native `PY4GW::Scanner` contract. It consumes the
existing `offsets/` definitions, searches validated ranges, and returns target
addresses as integer values. It does not return local Python pointers and does
not decode object fields.

The native scanner responsibilities to preserve are:

- initialize module and section ranges (`.text`, `.rdata`, `.data`);
- search a section or explicit address range using a byte pattern and mask;
- apply a signed result offset to a match;
- find assertion locations;
- find the first or nth use of an address;
- find the first or nth use of an ANSI or wide string;
- resolve x86 near-call targets;
- search backwards for a function start; and
- validate that an address belongs to an expected section.

`FileScanner` is the native implementation helper that maps a PE image and
performs the byte search. In Stealth, `RemoteScanner` obtains bytes through
the memory-reader boundary instead of dereferencing its own address space.

### Memory reader

The memory reader opens a selected process with read-only access, performs
bounded `ReadProcessMemory` operations, validates requested ranges, preserves
Windows error details, and closes its handles explicitly. It returns bytes; it
does not interpret them as game objects. It is the transport used by the
scanner, not a competing scanner API.

### Structure reader

The structure reader takes an address plus a documented target layout, reads
the required byte span through the memory reader, and decodes complete typed
structures. `context.CharContextStruct`, `context.GameContextStruct`,
`context.PreGameContextStruct`, `context.CinematicStruct`,
`context.GameplayContextStruct`, `context.ServerRegionStruct`,
`context.InstanceInfoStruct`, `context.TextParserStruct`,
`context.AvailableCharacterInfoStruct`, `context.PartyContextStruct`, and
`context.GuildContextStruct` are
the first
implementations. Their field names and order are ported from the
corresponding Reforged context sources;
the external version replaces host pointers with fixed-width target integers.
`context.GWArray` and its two views provide the corresponding external form
of Reforged's `GW_Array`, including contiguous value arrays and arrays of
remote structure pointers.

The injected Python context code can use `cast(pointer).contents` because its
pointer is inside the same process. Stealth must instead read the structure's
bytes and use an equivalent decode operation such as `from_buffer_copy`.
Pointer fields are still target addresses and must be followed through the
memory reader explicitly; they must not be dereferenced as local Python
pointers. This applies to `GW_Array` buffers, observer matches, progress bars,
and wide strings referenced by those structures.

The intended relationship is:

```text
offsets definitions -> Scanner -> address/pointer
                                  |
                                  v
                         Memory reader -> bytes
                                             |
                                             v
                                  Structure reader -> typed object
```

The scanner and memory reader remain target-agnostic at their core. Guild
Wars-specific signatures, pointer interpretation, and structure layouts belong
in the target-specific `context` layer that consumes these primitives.

#### Item and modifier boundary

The native item record stores a `mod_struct` pointer at `+0x10` and a
`mod_struct_size` count at `+0x14`. Those fields are represented as fixed-width
target values and are followed only through the bounded lazy modifier reader.
The reader exposes the native `ItemModifier` raw word (`0x4` bytes), its bit
accessors, and the native item helper rules. The semantic modifier types and
identifier tables from Reforged's `mods_types.py` and `mods_core.py` remain a
separate future layer. The current item reader follows the bag-owned item
arrays and keeps the raw global item array explicitly bounded and optional.

`ConnectedClient` is the small composition layer for scripts and the UI. It
selects one discovered PID, creates the reader, scanner, and context objects,
and owns the read-only process handle. The convenience facade exposes this as
`py4gw.connect(...)` and `py4gw.context.charcontext.get()`; it does not add a
second memory implementation. `ConnectedClient.is_connected` reports whether
the selected process handle is still open. `CharContextStruct.is_logged_in`
reports whether the snapshot contains a character; these are separate states.

`ConnectedClient` initializes the resolver-backed contexts during connection.
`GameContext` performs the JSON signature scan and caches the stable
module-global pointer location. `GameplayContext`, `PreGameContext`, and
`ServerRegion` each cache their own resolver scan, and `InstanceInfo` caches the
`map.instance_info_ptr_ref` slot. `Cinematic` follows the
`GameContext.cinematic` pointer, `CharContext` follows
`GameContext.character`. Each later context read re-reads only its short dynamic pointer chain
and structure bytes, so a context fetch does not scan the module again. The
dynamic values are intentionally not cached because they can change when the
client changes login or game state.

The rule behind that is stated once, in
[`READINESS_GATE.md`](READINESS_GATE.md): cache what the pattern scan produced,
because that is stable; never cache a dereferenced pointer, because that is
map-scoped. `InstanceInfo` caches the *address of* the pointer and dereferences
it per read, which is what the native runtime does and why a null slot reads as
`InstanceType.LOADING` instead of a stale map. Map-scoped reads are guarded by
`Map.IsMapReady()`, which is re-evaluated per read rather than cached, so no
time-to-live window exists.

Where a ported source member carries `@frame_cache`, the decorator is **dropped**,
not adapted: Reforged invalidates it from a per-frame in-process callback, and
Stealth has no frame tick. The reasoning and the rule are in
[`PORTING_RULES.md`](PORTING_RULES.md).

`PerfCounter` is the port of Reforged Native's `PyProfiler`: named stopwatches
over a 600-sample rolling history, reported as
`(min, avg, p50, p95, p99, max)`. One averaged sample is stored every six
completed measurements, which is the native throttle rather than a parameter.
Its context manager records a measurement even when the wrapped operation
raises. Python call-stack tracing is a separate instrument from Reforged's
`Profiling.py` and is not ported yet.

The native `Patterns` subsystem is a separate layer above `Scanner`. Stealth's
`PatternCatalog` loads the copied JSON definitions and executes resolver
chains such as scan, add, dereference, read-u32, and section validation. It
retains fallback attempts and a step trace so a failed resolution is
diagnosable.

## Low-level implementation choices

The initial implementation uses Python's standard library plus documented
Windows APIs called through `ctypes`:

- `ctypes` for `OpenProcess`, `ReadProcessMemory`, `VirtualQueryEx`, module
  enumeration, and handle cleanup;
- `struct` and `ctypes.Structure` for fixed-width x86 values and context
  decoding;
- `json` for the copied `offsets/` definitions; and
- `bytes`, `memoryview`, and built-in byte operations for local pattern scans.

The scanner should minimize `ReadProcessMemory` calls by reading bounded
sections in chunks and scanning the returned bytes locally. The Windows call
and data transfer are expected to dominate the cost; hand-written assembly for
the byte comparison is not justified until profiling demonstrates a local
matching bottleneck. If that ever happens, a small compiled helper can be
considered without changing the offsets or scanner contract.

Assembly, remote code, hooks, and function execution are not part of the
scanner implementation. The scanner reads bytes and resolves addresses; the code
this project places in the client lives in `py4gw/game_thread/` and nowhere else.
Keeping them apart is deliberate: a scan never patches anything, so no read path
carries the risk of a write path.

NiceGUI is a presentation dependency, not part of the Win32 library API. UI
callbacks may call public `Win32` methods and format returned records for
display. They must not contain `ctypes` declarations, Windows handle
management, memory operations, or Guild Wars signatures.

The separate `tests/nicegui_probe.py` script remains a small manual dependency
check. It is not the main application and does not replace the root UI.

## Implementation rules

- Keep Windows API declarations and native handle ownership inside the
  `Win32`/memory-reader boundary. The scanner calls that boundary instead of
  declaring `ctypes` APIs itself.
- Keep error handling inside `Win32` and preserve the Windows error number.
- Request only query access needed to read an executable path.
- Close every native handle in the same method that opened it.
- Enumerate all processes and return all matches; never silently choose one.
- Match `Gw.exe` by filename only. Do not add window-title, module, signature,
  character-name, or memory rules to this step.
- Do not keep process handles open after a method returns.
- Keep methods short enough that a reader can follow the Windows operation from
  start to finish.
- Document each public method in plain language, including what it returns and
  what can fail.
- Keep UI state in `MainWindow`; do not add UI state to `Win32`.
- Add a UI control only when the corresponding library behavior already has a
  documented contract.

## Verification contract

Run the focused process tests directly from the project root or from the
`tests` directory:

```text
python tests\test_win32.py
```

The scanner and resolver slices have their own direct checks:

```text
python tests\test_scanner.py
python tests\test_memory.py
python tests\test_remote_scanner.py
python tests\test_patterns.py
python tests\test_context.py
```

These use offline byte buffers, synthetic PE images, or a local process. They
do not claim that the copied offsets work against a live Guild Wars build.
`tests\test_context.py` is different: it is a live integration test and
requires a running, logged-in Guild Wars client.

Run the manual NiceGUI dependency probe when the UI dependency or environment
changes:

```text
python tests\nicegui_probe.py
```

Run the main test surface with:

```text
python main.py
```

For detailed live timing of the context path, run the direct harness while a
Guild Wars client is running:

```text
python tests\perf_context.py
```

It times each stage with `PerfCounter.start`/`end` through a private helper,
and reports resolver scans,
pointer dereferences, fixed-structure reads, and array/property reads with
percentiles and remote-read counts. This keeps diagnosis separate from the
main UI's single latest-read display.

Run static type checking from the project root:

```text
pyright
```

`pyrightconfig.json` checks `main.py`, `py4gw/`, and `tests/`, while excluding
the local research checkouts under `external/`. Pyright and Pylance must use
the same interpreter where the project dependencies are installed.

## Evidence and boundary

The ported read surface is pure external and read-only: it reads validated target
ranges and does not modify any process. A `Gw.exe` result or
scanner address is not proof of a supported Guild Wars build.

**The project as a whole is no longer pure external.** The game-thread layer places
code inside the target process, which the external reader alone cannot do, so it is
built as a Stealth-owned payload and patch installed by the external host, without a
conventional injected DLL. It is still injection. `py4gw.connect()` installs it —
two entry patches, a dispatcher emitted as machine code from Python, an observer, and
the shared block the two sides exchange through — and `py4gw.disconnect()` restores
both functions' own bytes and frees everything it placed. The mechanism is
live-verified: work published by the controller ran on the client's own thread, a
source-backed function call changed the client's state, callbacks were delivered as
they arrived, and the client's code section hashed identical before and after.
`connect(..., game_thread=False)` is the connection that only reads. “No DLL”
describes the delivery approach; it does not mean the target is unmodified or that
the payload is undetectable. See
[`NATIVE_EXECUTION_PLAN.md`](NATIVE_EXECUTION_PLAN.md) for the phased record.

The first pointer that appeared to require that payload, `WorldMapContext`, is
acquired read-only through the UI frame array instead. That route is now confirmed
on a live client for both map contexts: with the surface open, the frame that
registered the callback published the root, the `frame_id` cross-check passed and the
values read back consistent; with it closed, that frame's slot was null, no live
frame registered or published the pointer, and the independent visibility flag
flipped. See [`UI_FRAME_TREE.md`](UI_FRAME_TREE.md). The callback plan in
[`CALLBACK_POINTER_RESEARCH.md`](CALLBACK_POINTER_RESEARCH.md) remains the
fallback if the read-only route does not hold on another build.

The user-provided live observation recorded in `RESEARCH.md` found PID `39212`
at `F:\GW\GW1\Gw.exe` with the client open and no candidates after the client
was closed. The build/version and exact timestamp were not recorded.

GwAu3 remains comparative research. Its later character-name scanning,
remote payloads, and broad process access are not part of this class.
