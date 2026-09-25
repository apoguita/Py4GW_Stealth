# Py4GW Stealth

## What this project is

Py4GW Stealth is an external Windows/Python library intended to recreate
selected Py4GW Reforged capabilities without placing a runtime inside the
Guild Wars process. **That is no longer the whole model.** The read paths are
external and read-only; on top of them, `py4gw/game_thread/` places code in the
client when asked, and `py4gw.connect()` installs it by default. There is still no
DLL and no embedded Python runtime in `Gw.exe`, but a hook and a code patch do
modify it, and this document does not claim otherwise.

Py4GW Reforged is the current injected automation library: its launcher puts
`Py4GW.dll` inside `Gw.exe`, where an embedded Python runtime uses `Py*`
bindings, shared-memory game state, widgets, hooks, and higher-level helpers.
The native companion that builds the DLL is
<https://github.com/apoguita/Py4GW_Reforged_Native>.

Stealth is a capability-by-capability external counterpart to that system, not
a promise that every in-process feature can be reproduced externally.

The current implementation is intentionally small. It provides a `py4gw`
Python package with a `Win32` process boundary and a read-only scanner that can:

- list running Windows processes;
- find every process whose executable name is `Gw.exe`; and
- report each matching process's PID and executable path when Windows allows
  that lookup;
- read validated x86 module sections through `ReadProcessMemory`; and
- resolve copied pattern and pointer-resolver definitions from `offsets/`.

The scanner and remote memory path are read-only. The scanner, resolver, and
the `CharContext`, `GameContext`, `PreGameContext`, `Cinematic`,
`GameplayContext`, `ServerRegion`, `InstanceInfo`, `TextParser`,
`AvailableCharacterArray`, `PartyContext`, `GuildContext`, and
`AccAgentContext` readers have also been
verified against one live client build. Compatibility with other builds is not established. No read
path writes anything, and no ported member calls a Guild Wars function.
`py4gw/game_thread/` does, and `py4gw.connect()` installs that layer by default:
two entry hooks, a dispatcher emitted as machine code from Python that runs typed
calls on the client's own thread, an observer, and a listener thread that delivers
events to registered callbacks. `tests/test_live_bridge.py` and
`tests/test_live_call.py` have run it against the live client — hooking,
executing, delivering a callback, and restoring both functions' own bytes, with
the client's code section hashed before and after to show it came back identical.
One module, `py4gw/win32/write_access.py`, is the transport that writes; nothing
else does. It runs from an elevated shell, because Windows refuses the rights it
needs to an unelevated caller. **Connecting is therefore a write**;
`connect(..., game_thread=False)` is the connection that only reads.

## Requirements

- Windows
- Python 3.13 32-bit for the current x86-oriented research setup
- An **elevated shell**: `py4gw.connect(...)` refuses to connect without one
- NiceGUI with native-window support (installed automatically with the project)

Python 3.12 or another supported Python version may run the process-discovery
code, but the current remote scanner requires an x86 controller for an x86
target. Match controller and target bitness when using the memory path.

Elevation is not optional, and it cannot be added later: a process cannot elevate
itself, so the shell must be elevated before the script starts. The four rights
this library needs beyond reading (`PROCESS_VM_WRITE`, `PROCESS_VM_OPERATION`,
`PROCESS_CREATE_THREAD`, `PROCESS_SUSPEND_RESUME`) are refused to an unelevated
controller with error 5. `connect` checks once and raises a `RuntimeError` that
names the pid and says to relaunch the shell as administrator, so the failure is
readable instead of surfacing later as a bare `error 5`.

Check the active interpreter with:

```text
python -c "import struct,sys; print(sys.executable); print(struct.calcsize('P') * 8)"
```

## Installation

From the project directory, install the package in editable mode:

```text
python -m pip install -e .
```

This installs the project and its Python dependencies, including NiceGUI's
native support for the optional desktop interface. Editable installation means
Python uses the files in this working directory. After changing the code, there
is no package rebuild step.

On Windows, NiceGUI native mode also uses the system's .NET Framework and
Microsoft Edge WebView2 Runtime. These are Windows components, not Python
packages, and are not installed by pip.

Run scripts with the same interpreter explicitly:

```text
python path\to\script.py
```

Do not rely on launching `script.py` directly through the Windows file
association; that association can point to a different Python installation.

## Pyright and Pylance

Pyright and the VS Code Pylance extension use the Python interpreter selected
in VS Code. They do not automatically use whichever `python` command happens
to appear first in another terminal.

Select the interpreter where NiceGUI is installed, then verify it from the
project root:

```text
python -c "import sys, nicegui; print(sys.executable); print(nicegui.__file__)"
```

The repository's `pyrightconfig.json` checks the project package and project
tests, while excluding the source checkouts under `external/`.

Run the project check from the project root with:

```text
pyright
```

## Using the library

Any Python script can import the package after installation:

```python
from py4gw import Win32

win32 = Win32()
processes = win32.find_guild_wars()
print(win32.format_processes(processes))
```

To inspect a selected process read-only, obtain its main module and use the
scanner with an explicit context manager:

```python
from py4gw import ProcessMemoryReader, RemoteScanner, Win32

win32 = Win32()
pid = 1234  # choose one result from find_guild_wars()
module = win32.get_main_module(pid)

with ProcessMemoryReader(win32, pid) as reader:
    scanner = RemoteScanner(reader, module["base_address"], module["size"])
    scanner.initialize()
    print(scanner.get_section_range("text"))
```

The reader requests query and VM-read access only and closes its handle when
the `with` block ends. The scanner reads validated x86 module ranges; it does
not write memory or execute target code. The scanner and context readers have
been verified against one live client build, but compatibility with other
builds is not established.

The complete low-level context example keeps the reader open for the entire
snapshot operation:

```python
from py4gw import (
    CharContext,
    PatternCatalog,
    ProcessMemoryReader,
    RemoteScanner,
    Win32,
)

win32 = Win32()
pid = 1234  # choose one result from find_guild_wars()
module = win32.get_main_module(pid)

with ProcessMemoryReader(win32, pid) as reader:
    scanner = RemoteScanner(reader, module["base_address"], module["size"])
    scanner.initialize()
    patterns = PatternCatalog.from_directory("offsets")
    context = CharContext(reader, scanner, patterns)
    context.initialize()  # scan once and cache the stable resolver address
    print(context.read_player_name())
```

`context.read()` re-reads the dynamic context pointer chain but does not scan
the module again. Call `context.initialize()` again only when you deliberately
want to refresh the cached resolver address. A new `ConnectedClient` performs
this initialization automatically during `py4gw.connect(...)`.

For normal scripts, use the shorter client-selection facade instead of
constructing the scanner yourself:

```python
import py4gw

clients = py4gw.win32.list_processes()
client = py4gw.connect(clients[0])
print("attached:", client.is_connected)

char_context = py4gw.context.charcontext.get()
if char_context is not None and char_context.is_logged_in:
    print(char_context.player_name_str or "in selection menus")

instance_info = py4gw.context.instanceinfo.get()
if instance_info is not None and instance_info.current_map_info is not None:
    print(f"Map file id: {instance_info.current_map_info.file_id}")

py4gw.disconnect()
```

`py4gw.win32.list_processes()` returns only running `Gw.exe` clients.
`py4gw.connect(...)` selects one client and keeps its handle open. Call
`py4gw.disconnect()` when the script is finished. Run the script from an elevated
shell: `connect` refuses without one, and `py4gw.Win32().is_elevated()` says whether
the current shell is elevated.

`CharContext` follows the JSON `context.base_ptr` resolver and the maintained
Reforged structure offsets. `PatternCatalog.from_directory("offsets")` also
finds the project-root `offsets/` directory when called from a project
subdirectory. It reads a snapshot externally; it does not cast or dereference
remote pointers inside the Python process.

For detailed timing of the connection scan, cached context reads, and derived
array properties, run the live harness:

```text
python tests\perf_context.py
```

The harness accepts `--samples N` and `--pid PID` and reports elapsed time,
percentiles, remote-read counts, and requested bytes for each stage.

To run the live context check directly, keep Guild Wars running and execute:

```text
python tests\test_context.py
python tests\test_gameplay_context.py
python tests\test_server_region_context.py
python tests\test_instance_info_context.py
python tests\test_text_parser_context.py
python tests\test_available_character_context.py
```

This test reads the complete `CharContextStruct`, resolves its address through
the JSON resolver, and prints the live character name. It skips clearly when
no Guild Wars client is running. The GameplayContext test performs the same
read-only verification for the gameplay structure and its mission-map zoom.
The ServerRegion test verifies the signed region value resolved from the
copied `map.json` resolver. The InstanceInfo test verifies the root structure,
its current area metadata, and the nested fixed-width records. The TextParser
test follows `GameContext.text_parser` and reads the native root structure.

## Running the main UI

From the project directory:

```text
python main.py
```

The first tab lists running Guild Wars clients, shows their live character
names when available, labels clients in the selection menus, and provides PID
selection plus a Connect button. Listing and inspecting a row are read-only
(`game_thread=False`); connecting installs the game-thread layer. After connecting, the `Client data`
tab displays the available `CharContext`, `GameContext`, `PreGameContext`,
`Cinematic`, `GameplayContext`, `ServerRegion`, `InstanceInfo`, `TextParser`,
`AvailableCharacters`, `PartyContext`, `GuildContext`, and `AccAgentContext`
snapshots.
The migration order is `CharContext`, `GameContext`, `PreGameContext`,
`Cinematic`, `GameplayContext`, `ServerRegion`, `InstanceInfo`, `TextParser`,
`AvailableCharacterArray`, `PartyContext`, `GuildContext`, then
`AccAgentContext`.

Scripts do not need to be placed in the project root. They may live in a
separate `scripts/` directory or another location, as long as they use the
same Python environment where the editable package was installed.

## Project layout

```text
main.py         Main NiceGUI window and current Win32 test surface
py4gw/          The Python package
tests/          Automated tests and manual dependency probes
docs/           Design and programming-style rules
external/       Local research checkouts; intentionally excluded from Git
```

The [performance guide](docs/PERFORMANCE.md) documents the `PerfCounter`
contract, resolver caching, and the detailed live timing harness.

## Research boundary

The package identifies `Gw.exe` candidates by executable filename and has a
read-only scanner for validated x86 module ranges. Neither is proof of a
particular supported game build. Capabilities are added one at a time and each is
documented before it is added: the write path is limited to
`py4gw/win32/write_access.py` and the layer built on it,
`py4gw/game_thread/`.
