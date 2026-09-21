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
  performance.py  Controller-side execution timing
  win32/
    __init__.py
    win32.py
  memory/
    memory.py       Read-only process-memory transport
  scanner/
    scanner.py      Offline pattern matching
    remote.py       PE sections and remote scanning
    patterns.py     Offset definitions and resolver chains
  context/
    char_context.py Reforged CharContext layout, reader, and accessor
    game_context.py External GameContext layout, resolver, and reader
    pre_game_context.py External PreGameContext layout, resolver, and reader
    cinematic_context.py External Cinematic layout and reader
    gameplay_context.py External GameplayContext layout and reader
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

## Current capability

The current read-only library surface is deliberately small:

1. ask Windows for the running process list;
2. find processes named `Gw.exe`, case-insensitively;
3. return each matching process's PID, executable name, and path when
   available; and
4. open a selected process with query and VM-read access only;
5. parse its x86 PE section ranges and scan them with masked patterns; and
6. load the copied `offsets/` definitions and execute their resolver steps.

The library does not change a process, inject anything, or run code in a
process. The first target-specific structure readers were migrated in this
order: `CharContext`, `GameContext`, `PreGameContext`, `Cinematic`, and
`GameplayContext`; broader
Guild Wars structure interpretation remains outside
the current capability.
A `Gw.exe` result is a candidate found by filename, and a scanner result is
only an address selected by a pattern or resolver.

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
currently expose `Cinematic`, `GameplayContext`, `PreGameContext`, `GameContext`,
and `CharContext`,
each displaying every field in its maintained structure with the target offset.
The migration order for these readers is `CharContext`, `GameContext`,
`PreGameContext`, `Cinematic`, then `GameplayContext`.
The tables are paginated, sortable, filterable where applicable, and
selectable; long values wrap inside the normal window. `PreGameContext` is
allowed to be inactive while the client is in-game; in that state it reports
that no selection-menu context is currently available. Additional contexts
will be added as additional subtabs under this tab.

The UI catches `OSError` from the library and displays the diagnostic message.
It closes temporary inspection handles and keeps only the explicitly selected
connection open. It does not write memory or execute target code.

## External memory architecture

The external memory path has three separate layers. The scanner and
process-memory transport are implemented, and `context.CharContext`,
`context.GameContext`, `context.PreGameContext`, `context.Cinematic`, plus
`context.GameplayContext` are the
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
`context.PreGameContextStruct`, `context.CinematicStruct`, and
`context.GameplayContextStruct` are the first
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

`ConnectedClient` is the small composition layer for scripts and the UI. It
selects one discovered PID, creates the reader, scanner, and context objects,
and owns the read-only process handle. The convenience facade exposes this as
`py4gw.connect(...)` and `py4gw.context.charcontext.get()`; it does not add a
second memory implementation. `ConnectedClient.is_connected` reports whether
the selected process handle is still open. `CharContextStruct.is_logged_in`
reports whether the snapshot contains a character; these are separate states.

`ConnectedClient` initializes the resolver-backed contexts during connection.
`GameContext` performs the JSON signature scan and caches the stable
module-global pointer location. `GameplayContext` and `PreGameContext` each
cache their own global-pointer resolver. `Cinematic` follows the
`GameContext.cinematic` pointer, `CharContext` follows
`GameContext.character`. Each later context read re-reads only its short dynamic pointer chain
and structure bytes, so a context fetch does not scan the module again. The
dynamic values are intentionally not cached because they can change when the
client changes login or game state.

`PerfCounter` measures named controller operations with `perf_counter_ns`,
keeps bounded rolling histories, and produces minimum, average, percentile,
and maximum reports. Its context manager records a measurement even when the
wrapped operation raises. The native profiler's optional grouped averaging is
available through `samples_per_record`; Python call-stack tracing is separate
and is not enabled by this class.

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
scanner implementation. They would add a different capability boundary and
are outside the current read-only design.

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

It uses `PerfCounter.measure(...)` for each stage and reports resolver scans,
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

The current implementation is pure external and read-only. It can read
validated target ranges but does not modify any process. A `Gw.exe` result or
scanner address is not proof of a supported Guild Wars build.

The user-provided live observation recorded in `RESEARCH.md` found PID `39212`
at `F:\GW\GW1\Gw.exe` with the client open and no candidates after the client
was closed. The build/version and exact timestamp were not recorded.

GwAu3 remains comparative research. Its later character-name scanning,
remote payloads, and broad process access are not part of this class.
