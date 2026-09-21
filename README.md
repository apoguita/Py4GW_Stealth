# Py4GW Stealth

Py4GW Stealth is an external Python library for recreating selected Py4GW
Reforged capabilities without injecting a Python runtime or executable
payload into the Guild Wars process.

The project is being developed one capability at a time. The current library
provides read-only `Gw.exe` discovery, a reusable x86 pattern scanner, and
external readers for Reforged's maintained `CharContext`, `GameContext`,
`PreGameContext`, `Cinematic`, `GameplayContext`, `ServerRegion`,
`InstanceInfo`, `TextParser`, `AvailableCharacterArray`, `PartyContext`,
`GuildContext`, and `AccAgentContext`
layouts. A small NiceGUI
window exercises the
client-selection and read-only connection surface.

## Install

From the project directory:

```text
python -m pip install -e .
```

This installs the package and its Python dependencies, including NiceGUI's
native-window support. The editable install keeps Python connected to the
working source tree.

Run scripts through the selected Python interpreter:

```text
python path\to\script.py
```

This is preferred over typing `script.py` by itself, because Windows may use a
different interpreter for the `.py` file association.

## Example

```python
from py4gw import Win32

win32 = Win32()
print(win32.format_processes(win32.find_guild_wars()))
```

For a selected PID, the read-only scanner path is:

```python
from py4gw import ProcessMemoryReader, RemoteScanner, Win32

win32 = Win32()
pid = 1234  # choose a PID returned by find_guild_wars()
module = win32.get_main_module(pid)

with ProcessMemoryReader(win32, pid) as reader:
    scanner = RemoteScanner(
        reader,
        module_base=module["base_address"],
        module_size=module["size"],
    )
    scanner.initialize()
    print(scanner.get_section_range("text"))
```

This opens the selected process with read-only access and returns section
addresses. It does not write to or execute code in the process. The scanner
and the context readers have been verified against one live client build.
Compatibility with other builds is not established.

## Main UI

Run the current test surface from the project directory:

```text
python main.py
```

The first tab lists every running Guild Wars client, shows its live character
name when available, labels clients at the selection menus, and lets you
refresh and connect to a selected PID. After connecting, the `Client data`
tab becomes available; its context subtabs display the live structure fields:
`Cinematic`, `GameplayContext`, `ServerRegion`, `InstanceInfo`, `TextParser`,
`AvailableCharacters`, `PartyContext`, `GuildContext`, `AccAgentContext`,
`PreGameContext`, `GameContext`, and `CharContext`. The migration order for
these readers is `CharContext`, `GameContext`, `PreGameContext`, `Cinematic`,
`GameplayContext`, `ServerRegion`, `InstanceInfo`, `TextParser`,
`AvailableCharacterArray`, `PartyContext`, `GuildContext`, then
`AccAgentContext`.
`PreGameContext` reports when the client is outside the selection menus.
The context tables support sorting by their
headers, pagination, filtering, row selection, and wrapped values for long
fields.
The context status lines show the latest refresh state.

For a detailed live breakdown of resolver, structure, and pointer/array costs,
run the direct performance harness while Guild Wars is running:

```text
python tests/perf_context.py
```

Use `--samples N` to change the repeated sample count or `--pid PID` to select
a specific client. The harness reports elapsed time, percentiles, remote-read
counts, and requested byte counts for each stage.

The UI is a presentation and testing surface. The `Win32` class remains the
owner of all Windows process operations.

For scripts, the same client-selection path is available through a small
facade:

```python
import py4gw

clients = py4gw.win32.list_processes()
selected_client = clients[0]
client = py4gw.connect(selected_client)
print("attached:", client.is_connected)

char_context = py4gw.context.charcontext.get()
if char_context is not None and char_context.is_logged_in:
    print(char_context.player_name_str or "in selection menus")

game_context = py4gw.context.gamecontext.get()
if game_context is not None:
    print(f"CharContext address: 0x{game_context.char_context:08X}")

gameplay_context = py4gw.context.gameplaycontext.get()
if gameplay_context is not None:
    print(f"Mission-map zoom: {gameplay_context.mission_map_zoom:.3f}")

instance_info = py4gw.context.instanceinfo.get()
if instance_info is not None and instance_info.current_map_info is not None:
    print(f"Map file id: {instance_info.current_map_info.file_id}")

text_parser = py4gw.context.textparser.get()
if text_parser is not None:
    print(f"Text language: {text_parser.language_id}")

available_characters = py4gw.context.availablecharacters.get()
if available_characters is not None:
    print([entry.player_name_str for entry in available_characters.characters])

party = py4gw.context.partycontext.get()
if party is not None:
    print(f"Party leader: {party.is_party_leader}")

py4gw.disconnect()
```

`py4gw.connect` opens the selected process for read-only access and owns the
handle until `py4gw.disconnect()` is called. Connection performs the one-time
signature scan and caches its stable pointer location; later context reads do
not rescan the module.

Controller-side execution timing is available through `PerfCounter`:

```python
import py4gw
from py4gw import PerfCounter

perf = PerfCounter()
with perf.measure("context.read"):
    context = py4gw.context.charcontext.get()

print(perf.report("context.read").average_ms)
```

This measures Python/controller work only; it does not measure code executing
inside Guild Wars.

## Documentation

- [Scope](docs/SCOPE.md) — what the project is and is not
- [Installation guide](INSTALL.md) — setup and usage details
- [Design contract](docs/DESIGN.md) — current implementation rules
- [Performance](docs/PERFORMANCE.md) — timing, resolver caching, and the live harness
- [Context inventory](docs/CONTEXT_INVENTORY.md) — native/Reforged context mapping and Stealth status
- [AgentArray plan](docs/AGENT_ARRAY_PLAN.md) — the staged plan for bounded agent traversal and lazy reads
- [Programming style](docs/STYLE.md) — naming and coding conventions
- [Research record](docs/RESEARCH.md) — detailed source analysis and history

## Current boundary

The current library only performs read-only operations. It can discover
processes and scan/read selected process memory, but it does not write to a
process, inject code, create remote threads, or install hooks.
